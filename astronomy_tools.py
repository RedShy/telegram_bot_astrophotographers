from decimal import Context
from traceback import format_exc
from typing_extensions import final
from selenium.webdriver.chrome.webdriver import WebDriver
from telegram import (
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Bot,
)
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    CallbackContext,
    Filters,
    ConversationHandler,
)
from telegram.ext.dispatcher import run_async
from utility import *
from constants import *
from longlats_cities import *
import re
from lxml import html
import requests
from datetime import datetime, timedelta
import calendar
from time import time
from websitecities import *
import geopy.distance
from pytz import timezone
from statistics_log import *

import time
import base64

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.remote.webelement import WebElement

from PIL import Image

import threading
import traceback

GET_MODE, GET_TARGET, GET_FOCAL, GET_SENSOR, GET_BARLOW, END = range(6)

user_data_lock = threading.Lock()


def write_user_data(user_data, key, value):
    user_data_lock.acquire()
    user_data[key] = value
    user_data_lock.release()


def read_user_data(user_data, key):
    user_data_lock.acquire()
    value = user_data[key]
    user_data_lock.release()

    return value


# la condizione per fare il polling passivo per la chiusura connessione
close_connection_condition = threading.Condition()
# una variabile condivisa di segnalazione chiusura connessione per ogni thread
close_connections = dict()

# la condizione per fare il polling passivo per la fine setup driver
setup_driver_condition = threading.Condition()
# una variabile condivisa di segnalazione fine setup driver per ogni thread
setup_driver_finished = dict()


def start_web_driver_thread(user_data):
    # creo il thread che andrà a fare il setup del web driver
    web_driver_thread = threading.Thread(
        target=setup_astronomy_tools_driver, args=(user_data,)
    )
    web_driver_thread.start()

    # creo la variabile condivisa per questo thread
    close_connection_condition.acquire()
    close_connections[web_driver_thread.ident] = False
    close_connection_condition.release()

    write_user_data(user_data, "web_driver_thread", web_driver_thread)


def setup_astronomy_tools_driver(user_data):
    op = webdriver.ChromeOptions()
    op.add_argument("--headless")
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=op)
    write_user_data(user_data, "driver", driver)

    driver.get("https://astronomy.tools/calculators/field_of_view/")

    # tolgo cookie
    driver.execute_script(
        "document.getElementsByClassName('cc-window cc-banner cc-type-info cc-theme-classic cc-bottom cc-color-override--1555015938 ')[0].style.display = 'None';"
    )

    # ingrandisco finestra browser per contenere più elementi da cliccare
    driver.set_window_size(1920, 1080)

    # ho finito il setup, segnalo che ho finito
    setup_driver_condition.acquire()
    setup_driver_finished[threading.get_ident()] = True
    setup_driver_condition.release()

    # metti il thread in attesa di una condition
    # attendi la chiamata di chiudere la connessione
    # deve controllare la variabile shared con il main thread per la segnalazione di fine
    # 1. prendi la struttura dati che contiene le variabili condivise per ogni thread
    # 2. prendi la tua variabile condivisa con il lock
    # 3. leggi la variabile: se devi chiudere, chiudi, altrimenti torna a dormire
    close_connection_condition.acquire()
    close_connection = close_connections.get(threading.get_ident(), False)
    while not close_connection:
        close_connection_condition.wait()

        close_connection = close_connections.get(threading.get_ident(), False)
    close_connection_condition.release()

    # elimina la variabile usata per segnalare la fine setup e la condition
    del setup_driver_finished[threading.get_ident()]
    del close_connections[threading.get_ident()]

    driver.close()
    driver.quit()


def astronomy_tools_start_conversation(update: Update, context: CallbackContext) -> int:
    save_user_interaction(update.message.text, user=update.message.from_user)
    start_web_driver_thread(context.user_data)

    update.message.reply_text(
        "Per prima cosa dimmi: vuoi andare in modalità visuale o sensore?"
    )

    return GET_MODE


def get_mode(update: Update, context: CallbackContext) -> int:
    text = update.message.text.replace(" ", "").lower()

    # modalità non riconosciuta
    if text.find("visuale") == -1 and text.find("sensore") == -1:
        return end_error_conversation(update, context, "Modalità non riconosciuta")

    # modalità visuale
    if text.find("visuale") != -1:
        write_user_data(context.user_data, "mode", "visual")
    # modalità sensore
    elif text.find("sensore") != -1:
        write_user_data(context.user_data, "mode", "imaging")

    update.message.reply_text(
        "Okay! Per ottenere il campo inquadrato dal tuo setup inviami il target che vuoi testare.\n(Alcuni target NGC potrebbero non funzionare. Questo è dovuto ad un bug interno di Astronomy Tools e non al bot.)\nEsempi target supportati:\nM21\nNGC 7000\nIC 1805\nGiove"
    )

    return GET_TARGET


def get_target(update: Update, context: CallbackContext) -> int:
    def get_target_and_type(text):
        # prova messier
        match = re.search("[mM](\d+)", text)
        if match is not None:
            number = int(match.group(1))
            if number > max_messier:
                raise Exception("Numero messier troppo grande")

            target = match.group(0)
            type_target = "messier"
            return target, type_target

        # prova NGC o IC
        match = re.search("^ngc\d+[a-z]?$|^ic\d+$", text)
        if match is not None:
            target = match.group(0)
            type_target = "ngc"
            return target, type_target

        # prova sistema solare
        match = re.search("^\w+$", text)
        if match is not None:
            target = target_solar_italian[match.group(0)]
            type_target = "solar"
            return target, type_target

        raise Exception(f"'{text}' - non trovato né messier né ngc e né sistema solare")

    text = update.message.text.lower().replace(" ", "")

    try:
        target, type_target = get_target_and_type(text)
    except Exception as e:
        write_on_error_log(
            update.message.from_user,
            "ERRORE in get target astronomy tools",
            e,
            traceback.format_exc(),
        )
        return end_error_conversation(update, context, "Oggetto non riconosciuto")

    write_user_data(context.user_data, "target", target)
    write_user_data(context.user_data, "type_target", type_target)

    update.message.reply_text(
        "Okay! Inviami anche la focale del tuo telescopio in mm\nEsempio 1200 mm"
    )

    return GET_FOCAL


def get_focal(update: Update, context: CallbackContext) -> int:
    try:
        focal = get_number_greater_zero(update.message.text)
    except:
        return end_error_conversation(
            update, context, "Dato per la focale non riconosciuto"
        )

    write_user_data(context.user_data, "focal", focal)

    mode = read_user_data(context.user_data, "mode")
    if mode == "imaging":
        update.message.reply_text(
            "Ottimo! Ora inviami il nome del tuo sensore\nEsempio:\nZWO 224"
        )
    elif mode == "visual":
        update.message.reply_text(
            "Ottimo! Ora inviami il nome del tuo oculare\nEsempio:\nSkywatcher 28"
        )

    return GET_SENSOR


def get_sensor(update: Update, context: CallbackContext) -> int:
    def all_tokens_in_key(tokens, key):
        for token in tokens:
            match = re.search(
                f"{token}",
                key.replace("|", "").replace(" ", "").replace("-", "").lower(),
            )
            if match is None:
                return False
        return True

    def find_sensor_eye_piece(tokens, names):
        for name_key in list(names.keys()):
            if all_tokens_in_key(tokens, name_key):
                return names[name_key]

        return None

    text = update.message.text.replace("-", " ").replace('"', "").lower()

    # tokenizziamo text
    tokens = text.split(" ")

    # a seconda della modalità, vado a pescare i nomi su cui fare la ricerca
    mode = read_user_data(context.user_data, "mode")
    if mode == "imaging":
        names = cameras
        sensor_eye_piece_prompt = "Sensore"
    elif mode == "visual":
        names = eyepieces
        sensor_eye_piece_prompt = "Oculare"

    # trovo il nome del sensore o dell'eyepiece
    sensor_eye_piece = find_sensor_eye_piece(tokens, names)

    if sensor_eye_piece is None:
        return end_error_conversation(
            update, context, f"{sensor_eye_piece_prompt} non trovato"
        )

    update.message.reply_text(f"Ho trovato: {sensor_eye_piece}")

    write_user_data(context.user_data, "sensor_eye_piece_name", sensor_eye_piece)

    update.message.reply_text(
        f'Perfetto! Ora inserisci "no" se non utilizzi nessuna Barlow o riduttore altrimenti inserisci il fattore moltiplicativo del tuo accessorio.\nEsempio:\n- 2 (rappresenta una Barlow 2x)\n- 0.5 (rappresenta un riduttore 0.5x)'
    )

    return GET_BARLOW


def get_barlow_and_terminate(update: Update, context: CallbackContext) -> int:
    def wait_web_driver_thread():
        # Attendo che il thread driver abbia finito
        web_driver_thread = read_user_data(context.user_data, "web_driver_thread")

        setup_driver_condition.acquire()
        setup_finished = setup_driver_finished.get(web_driver_thread.ident, False)
        while not setup_finished:
            setup_driver_condition.wait()

            setup_finished = setup_driver_finished.get(web_driver_thread.ident, False)

        setup_driver_condition.release()

    def parse_barlow_from_user_text(text):
        default_barlow = 1

        if text == "no":
            return default_barlow

        try:
            barlow = float(text)
            if barlow in barlows:
                return barlow

            raise Exception("Barlow non trovato")
        except Exception as e:
            write_on_error_log(
                update.message.from_user,
                "ERRORE in astronomy tools",
                e,
                traceback.format_exc(),
            )
            update.message.reply_text("Moltiplicatore/riduttore barlow non trovato")

            return default_barlow

    text = (
        update.message.text.replace(" ", "").replace(",", ".").lower().replace("x", "")
    )

    user_barlow = parse_barlow_from_user_text(text)

    update.message.reply_text("Elaborazione immagine in corso...")

    wait_web_driver_thread()
    try:
        imageBuffer = get_canvas(
            driver=read_user_data(context.user_data, "driver"),
            target=read_user_data(context.user_data, "target"),
            focal=read_user_data(context.user_data, "focal"),
            sensor_eyepiece_name=read_user_data(
                context.user_data, "sensor_eye_piece_name"
            ),
            mode=read_user_data(context.user_data, "mode"),
            barlow=user_barlow,
            type_target=read_user_data(context.user_data, "type_target"),
        )
        update.message.reply_photo(photo=imageBuffer)
        imageBuffer.close()
    except Exception as e:
        write_on_error_log(
            update.message.from_user,
            "ERRORE in astronomy tools",
            e,
            traceback.format_exc(),
        )
        return end_error_conversation(
            update,
            context,
            f"C'è stato un problema durante la generazione dell'immagine finale: {e}",
        )

    return end_conversation(update, context)


def get_canvas(
    driver: WebDriver,
    target: str,
    focal: str,
    sensor_eyepiece_name: str,
    mode: str,
    barlow,
    type_target: str,
) -> BytesIO:
    def get_canvas_until_ready(canvas):
        # get the canvas as a PNG base64 string
        # canvas_base64 = driver.execute_script(
        #    "return arguments[0].toDataURL('image/png').substring(21);", canvas
        # )

        # attendo per far caricare l'immagine intermedia
        time.sleep(0.250)
        canvas_base64 = canvas.screenshot_as_base64

        # il controllo se l'immagine è stata generata oppure no
        # si basa sulla lunghezza della stringa dell'immagine
        # all'inizio l'immagine è bianca, e quando viene generata la lunghezza
        # della stringa dell'immagine aumenta
        # prova una serie di tentativi e poi ritorna qualunque immagine sia presente
        attempt = 0
        max_attempts = 24
        blank_len = len(canvas_base64)
        final_len = len(canvas_base64)
        while final_len <= blank_len and attempt < max_attempts:
            attempt += 1
            time.sleep(0.250)

            # canvas_base64 = driver.execute_script(
            #    "return arguments[0].toDataURL('image/png').substring(21);", canvas
            # )
            canvas_base64 = canvas.screenshot_as_base64
            final_len = len(canvas_base64)

        # attendo per far caricare completamente l'immagine
        time.sleep(0.250)
        canvas_base64 = canvas.screenshot_as_base64

        return canvas_base64

    def wait_until_ngc_loaded(driver: WebDriver):
        number_of_elements = len(
            driver.find_element_by_id("ui-id-1").find_elements_by_tag_name("li")
        )

        attempt = 0
        max_attempts = 16
        while number_of_elements <= 0 and attempt <= max_attempts:
            time.sleep(0.150)

            number_of_elements = len(
                driver.find_element_by_id("ui-id-1").find_elements_by_tag_name("li")
            )

    if mode == "imaging":
        # clicca su imaging mode
        imaging_button = driver.find_element_by_xpath(
            "//input[@value='imaging']/parent::label"
        )
        imaging_button.click()
    elif mode == "visual":
        # clicca su visual mode
        visual_button = driver.find_element_by_xpath(
            "//input[@value='visual']/parent::label"
        )
        visual_button.click()

    if type_target == "solar":
        # seleziona l'oggetto del sistema solare
        solar_select = Select(driver.find_element_by_id("fov_solar_system_object"))
        solar_select.select_by_value(f"{target}")
    elif type_target == "messier":
        # seleziona l'oggetto messier
        messier_select = Select(driver.find_element_by_id("fov_messier_object"))
        messier_select.select_by_value(f"{target}")
    elif type_target == "ngc":
        # splitta il nome dal numero
        match = re.match(r"([a-z]+)([0-9]+[a-d]?)", target, re.IGNORECASE)
        if match:
            name, number = match.groups()

        # 1 scrivi nella barra di ricerca il tipo di oggetto da cercare
        ngc_search_elem = driver.find_element_by_id("fov_object_search")
        ngc_search_elem.clear()
        ngc_search_elem.send_keys(f"{name}")

        # 2 rendi visibile il menu a tendina
        driver.execute_script(
            "document.getElementById('ui-id-1').style.display = 'block';"
        )

        # attendi che vengano caricati gli NGC
        wait_until_ngc_loaded(driver)

        # 3 seleziona l'oggetto NGC dal menu a tendina se presente
        try:
            driver.find_element_by_xpath(
                f"//li//a[contains(text(),'{number}')]"
            ).click()
        except:
            raise Exception(f"oggetto {target} non trovato")

    # inserisco lunghezza focale
    focal_length_elem = driver.find_element_by_id("fov_telescope_focal_length")
    focal_length_elem.clear()
    focal_length_elem.send_keys(f"{focal}")

    if mode == "imaging":
        # scelgo la camera
        driver.execute_script(
            "document.getElementById('fov_select_camera').style.display = 'block';"
        )
        camera_select = Select(driver.find_element_by_id("fov_select_camera"))
        camera_select.select_by_value(f"{sensor_eyepiece_name}")
    elif mode == "visual":
        # scelgo l'oculare
        driver.execute_script(
            "document.getElementById('fov_select_eyepiece').style.display = 'block';"
        )
        eyepiece_select = Select(driver.find_element_by_id("fov_select_eyepiece"))
        eyepiece_select.select_by_value(f"{sensor_eyepiece_name}")

    # scelgo il barlow/riduttore
    barlow_select = Select(driver.find_element_by_id("fov_reducer_barlow"))
    barlow_select.select_by_value(f"{str(barlow).replace('.0','')}")

    # premo su "add to view"
    add_to_view_button = driver.find_element_by_id("fov_add_to_view_button")
    add_to_view_button.click()

    # rimuovo il modale che avverte il caricamento lento
    if type_target == "ngc":
        # attendo che il modale appaia
        time.sleep(0.250)

        # rimuovo il modale
        driver.execute_script(
            "document.getElementById('fov_custom_object_modal').style.display = 'none';"
        )

    # scarico l'immagine
    canvas_element = driver.find_element_by_id("fov_canvas")

    # attendo che l'immagine venga caricata
    canvas_base64 = get_canvas_until_ready(canvas_element)

    # decode
    canvas_png = base64.b64decode(canvas_base64)

    imageBuffer = BytesIO(canvas_png)
    return imageBuffer


def end_error_conversation(
    update: Update, context: CallbackContext, message: str
) -> int:
    update.message.reply_text(
        message, reply_markup=ReplyKeyboardMarkup(main_menu_keyboard)
    )
    update.message.reply_sticker(sticker=error_sticker)
    return end_conversation(update, context)


def end_timeout_conversation(update: Update, context: CallbackContext) -> int:
    update.message.reply_text(
        "Hai impiegato troppo tempo ad inviare una risposta",
        reply_markup=ReplyKeyboardMarkup(main_menu_keyboard),
    )
    update.message.reply_sticker(sticker=error_sticker)
    return end_conversation(update, context)


def end_conversation(update: Update, context: CallbackContext) -> int:
    thread = read_user_data(context.user_data, "web_driver_thread")

    # segnalo di chiudere la connessione
    close_connection_condition.acquire()
    close_connections[thread.ident] = True
    close_connection_condition.notify_all()
    close_connection_condition.release()

    context.user_data.clear()
    return ConversationHandler.END


def add_astronomy_tools_handlers(dispatcher):
    # dispatcher.add_handler(
    #    MessageHandler(
    #        Filters.regex(f"^{astronomy_tools_button_name}$"), astronomy_tools_welcome,
    #    )
    # )

    # ESECUZIONE IN MULTITHREAD
    conv_astronomy_tools_handler = ConversationHandler(
        entry_points=[
            MessageHandler(
                Filters.regex(f"^{astronomy_tools_button_name}$"),
                astronomy_tools_start_conversation,
            )
        ],
        states={
            GET_MODE: [MessageHandler(Filters.regex(f"^.*$"), get_mode),],
            GET_TARGET: [MessageHandler(Filters.regex(f"^.*$"), get_target),],
            GET_FOCAL: [MessageHandler(Filters.regex(f"^.*$"), get_focal),],
            GET_SENSOR: [MessageHandler(Filters.regex(f"^.*$"), get_sensor)],
            GET_BARLOW: [
                MessageHandler(
                    Filters.regex(f"^.*$"), get_barlow_and_terminate, run_async=True
                ),
            ],
            ConversationHandler.TIMEOUT: [
                MessageHandler(Filters.regex(".*"), end_timeout_conversation)
            ],
        },
        fallbacks=[MessageHandler(Filters.regex(".*"), end_conversation)],
        conversation_timeout=30,
    )

    dispatcher.add_handler(conv_astronomy_tools_handler)


target_solar_italian = {
    "sole": "sun",
    "mercurio": "mercury",
    "venere": "venus",
    "luna": "moon",
    "marte": "mars",
    "giove": "jupiter",
    "saturno": "saturn",
    "urano": "uranus",
    "nettuno": "neptune",
}

cameras = {
    "ALCCD|QHY-21c": "ALCCD|QHY-21c|4.54|4.54|1940.00|1460.00|175",
    "ALCCD|QHY-22c": "ALCCD|QHY-22c|4.54|4.54|2758.00|2208.00|174",
    "ALCCD|QHY-23c": "ALCCD|QHY-23c|3.69|3.69|3388.00|2712.00|173",
    "Altair|GPCAM2 AR0130 M": "Altair|GPCAM2 AR0130 M|3.75|3.75|1280.00|960.00|408",
    "Altair Astro|GPCAM MT9M034M": "Altair Astro|GPCAM MT9M034M|3.75|3.75|1280.00|960.00|134",
    "Altair Astro|GPCAMV2 IMX224 C": "Altair Astro|GPCAMV2 IMX224 C|3.75|3.75|1280.00|960.00|256",
    "Astro Video Systems|DSO-1": "Astro Video Systems|DSO-1|5.00|7.40|768.00|494.00|220",
    "Atik|11000": "Atik|11000|9.00|9.00|4008.00|2672.00|41",
    "Atik|16200 Mono": "Atik|16200 Mono / Colour|6.00|6.00|4499.00|3599.00|409",
    "Atik|16200 Colour": "Atik|16200 Mono / Colour|6.00|6.00|4499.00|3599.00|409",
    "Atik|16ic": "Atik|16ic|7.40|7.40|659.00|494.00|178",
    "Atik|314L Plus": "Atik|314L Plus|6.45|6.45|1392.00|1040.00|2",
    "Atik|320E": "Atik|320E|4.40|4.40|1620.00|1220.00|78",
    "Atik|383L+": "Atik|383L+|5.40|5.40|3362.00|2504.00|21",
    "Atik|4000": "Atik|4000|7.40|7.40|2048.00|2048.00|42",
    "Atik|4120EX": "Atik|4120EX|3.10|3.10|4242.00|2830.00|65",
    "Atik|414EX": "Atik|414EX|6.45|6.45|1392.00|1040.00|64",
    "Atik|420": "Atik|420|4.40|4.40|1619.00|1219.00|4420",
    "Atik|428EX": "Atik|428EX|4.54|4.54|1932.00|1452.00|40",
    "Atik|450": "Atik|450|3.45|3.45|2448.00|2050.00|75",
    "Atik|460EX": "Atik|460EX|4.54|4.54|2750.00|2200.00|8",
    "Atik|490EX": "Atik|490EX|3.69|3.69|3380.00|2704.00|39",
    "Atik|ACIS 12.3": "Atik|ACIS 12.3|3.45|3.45|4096.00|3008.00|5366",
    "Atik|ACIS 2.4": "Atik|ACIS 2.4|5.86|5.86|1936.00|1216.00|5365",
    "Atik|ACIS 7.1": "Atik|ACIS 7.1|4.50|4.50|3208.00|2200.00|4366",
    "Atik|Apx60 (CosMOS)": "Atik|Apx60 (CosMOS)|3.76|3.76|9576.00|6388.00|5367",
    "Atik|GP": "Atik|GP|3.75|3.75|1296.00|964.00|17",
    "Atik|Horizon": "Atik|Horizon|3.80|3.80|4644.00|3506.00|949",
    "Atik|Infinity": "Atik|Infinity|6.45|6.45|1392.00|1040.00|117",
    "Atik|One 6.0": "Atik|One 6.0|4.54|4.54|2750.00|2200.00|1",
    "Atik|One 9.0": "Atik|One 9.0|3.69|3.69|3380.00|2704.00|12",
    "Atik|Titan": "Atik|Titan|7.40|7.40|659.00|494.00|15",
    "Canon|1000D": "Canon|1000D|5.71|5.71|3888.00|2591.00|129",
    "Canon|10D": "Canon|10D|7.38|7.38|3072.00|2048.00|107",
    "Canon|1200D": "Canon|1200D|4.30|4.30|5184.00|3456.00|280",
    "Canon|20D": "Canon|20D|6.40|6.40|3520.00|2344.00|62",
    "Canon|30D": "Canon|30D|6.42|6.42|3504.00|2336.00|22",
    "Canon|350D": "Canon|350D|6.41|6.41|3456.00|2304.00|96",
    "Canon|450D": "Canon|450D|5.10|5.10|4272.00|2848.00|61",
    "Canon|50d": "Canon|50d|4.70|4.70|4752.00|3168.00|88",
    "Canon|550D": "Canon|550D|4.30|4.30|5184.00|3456.00|119",
    "Canon|5DS": "Canon|5DS|4.13|4.13|8988.00|5792.00|777",
    "Canon|5DSR": "Canon|5DSR|4.14|4.14|8688.00|5792.00|859",
    "Canon|600D": "Canon|600D|4.31|4.31|5184.00|3456.00|104",
    "Canon|60Da": "Canon|60Da|4.30|4.30|5184.00|3456.00|27",
    "Canon|6D": "Canon|6D|6.54|6.54|5472.00|3648.00|90",
    "Canon|70D": "Canon|70D|4.10|4.10|5472.00|3648.00|109",
    "Canon|760D": "Canon|760D|3.70|3.70|6000.00|4000.00|176",
    "Canon|7D": "Canon|7D|4.30|4.30|5184.00|3456.00|98",
    "Canon|EOS 1000D": "Canon|EOS 1000D|5.71|5.71|3888.00|2592.00|6",
    "Canon|EOS 100D": "Canon|EOS 100D|4.30|4.30|5196.00|3464.00|4",
    "Canon|EOS 1100D": "Canon|EOS 1100D|5.18|5.18|4272.00|2848.00|16",
    "Canon|EOS 40D": "Canon|EOS 40D|5.70|5.70|3888.00|2592.00|23",
    "Canon|EOS 500D": "Canon|EOS 500D|4.68|4.68|4752.00|3168.00|14",
    "Canon|EOS 5D Mk11": "Canon|EOS 5D Mk11|6.40|6.40|5616.00|3744.00|26",
    "Canon|EOS 5D Mk111": "Canon|EOS 5D Mk111|6.25|6.25|5760.00|3840.00|24",
    "Canon|EOS 5D MkIV": "Canon|EOS 5D MkIV|5.30|5.30|6720.00|4480.00|142",
    "Canon|EOS 700D": "Canon|EOS 700D|4.30|4.30|5184.00|3456.00|83",
    "Canon|EOS 750D": "Canon|EOS 750D|3.70|3.70|6024.00|4022.00|196",
    "Canon|EOS 7D mkII": "Canon|EOS 7D mkII|4.10|4.10|5472.00|3648.00|146",
    "Canon|EOS 80D": "Canon|EOS 80D|3.70|3.70|6000.00|4000.00|310",
    "Celestron|NexImage 10": "Celestron|NexImage 10|1.67|1.67|3856.00|2764.00|338",
    "Celestron|Neximage 5": "Celestron|Neximage 5|2.20|2.20|2592.00|1944.00|20",
    "Celestron|Neximage Burst": "Celestron|Neximage Burst|3.75|3.75|1280.00|960.00|54",
    "Celestron|NexImage Solar System Imager": "Celestron|NexImage Solar System Imager|3.00|3.00|1280.00|720.00|55",
    "Celestron|Nightscape 8300": "Celestron|Nightscape 8300|5.40|5.40|3326.00|2504.00|74",
    "Celestron|Skyris 132": "Celestron|Skyris 132|3.75|3.75|1280.00|960.00|157",
    "Celestron|Skyris 236": "Celestron|Skyris 236|2.80|2.80|1920.00|1200.00|118",
    "Celestron|Skyris 274": "Celestron|Skyris 274|4.40|4.40|1600.00|1200.00|19",
    "Celestron|Skyris 445": "Celestron|Skyris 445|3.75|3.75|1280.00|960.00|18",
    "Celestron|Skyris 618": "Celestron|Skyris 618|5.60|5.60|640.00|480.00|3",
    "FLI|ML 8300": "FLI|ML 8300|5.40|5.40|3326.00|2504.00|79",
    "FLI|ML-09000": "FLI|ML-09000|12.00|12.00|3056.00|3056.00|36",
    "FLI|ML11002": "FLI|ML11002|9.00|9.00|4008.00|2672.00|100",
    "FLI|ML16803": "FLI|ML16803|9.00|9.00|4096.00|4096.00|243",
    "FLI|ML50100": "FLI|ML50100|6.00|6.00|8176.00|6132.00|131",
    "FLI|Proline PL 16803": "FLI|Proline PL 16803|9.00|9.00|4096.00|4096.00|321",
    "Fujifilm|X-T1": "Fujifilm|X-T1|4.80|4.80|4869.00|3264.00|212",
    "Imaging Source|DMK 41AU02": "Imaging Source|DMK 41AU02|4.65|4.65|1360.00|1024.00|11",
    "iNova|PLB-Cx": "iNova|PLB-Cx|3.75|3.75|1280.00|960.00|30",
    "Lacerta|MGEN-3": "Lacerta|MGEN-3|3.75|3.75|1280.00|960.00|3727",
    "Lacerta|MGEN-II": "Lacerta|MGEN-II|4.70|4.70|752.00|582.00|2495",
    "Lumix|GH2": "Lumix|GH2|3.75|3.75|4608.00|3456.00|154",
    "MallinCam|SkyRaider": "MallinCam|SkyRaider|3.75|3.75|1280.00|960.00|188",
    "Mallincam|SkyRaider 23DS Plus": "Mallincam|SkyRaider 23DS Plus|5.86|5.86|1936.00|1216.00|319",
    "Meade|DSI 2": "Meade|DSI 2|8.30|8.60|752.00|582.00|115",
    "Meade|DSI III Pro": "Meade|DSI III Pro|6.45|6.45|1360.00|1024.00|136",
    "Meade|DSI-C": "Meade|DSI-C|9.60|7.50|510.00|492.00|122",
    "Microsoft|HD Lifecam": "Microsoft|HD Lifecam|3.10|3.10|1280.00|720.00|106",
    "Moravian|16803": "Moravian|16803|9.00|9.00|4096.00|4096.00|303",
    "Moravian|G2-4000": "Moravian|G2-4000|7.40|7.40|2056.00|2042.00|86",
    "Moravian|G3-1000": "Moravian|G3-1000|24.00|24.00|1024.00|1024.00|244",
    "Moravian|G3-11000": "Moravian|G3-11000|9.00|9.00|4032.00|2688.00|168",
    "Moravian|G3-16200": "Moravian|G3-16200|6.00|6.00|4540.00|3640.00|248",
    "Moravian Instruments|G2-8300": "Moravian Instruments|G2-8300|5.40|5.40|3358.00|2536.00|102",
    "NIKON|D300S": "NIKON|D300S|5.50|5.50|4288.00|2848.00|167",
    "Nikon|D3300": "Nikon|D3300|3.90|3.90|4000.00|6000.00|153",
    "Nikon|D5100": "Nikon|D5100|4.78|4.78|4928.00|3264.00|87",
    "Nikon|D5300": "Nikon|D5300|3.92|3.92|6000.00|4000.00|123",
    "Nikon|D5500": "Nikon|D5500|3.89|3.89|6000.00|4000.00|186",
    "Nikon|D7000": "Nikon|D7000|4.70|4.70|4991.00|3280.00|73",
    "Nikon|D70S": "Nikon|D70S|7.90|7.90|3008.00|2000.00|296",
    "Nikon|D750": "Nikon|D750|5.97|5.98|6016.00|4016.00|127",
    "Nikon|D7500": "Nikon|D7500|4.20|4.20|5568.00|3712.00|1345",
    "Nikon|D800": "Nikon|D800|4.88|4.88|7360.00|4912.00|150",
    "Nikon|D810a": "Nikon|D810a|4.88|4.88|7360.00|4912.00|108",
    "Nikon|V1": "Nikon|V1|3.41|3.39|3872.00|2592.00|126",
    "Olympus|E-PM1": "Olympus|E-PM1|4.29|4.29|4032.00|3024.00|608",
    "Olympus|OMD Em-5 mk2": "Olympus|OMD Em-5 mk2|3.74|3.74|4608.00|3456.00|207",
    "Opticstar|DS-616C XL": "Opticstar|DS-616C XL|7.80|7.80|3032.00|2014.00|114",
    "Orion|SSAG": "Orion|SSAG|5.20|5.20|1280.00|1024.00|120",
    "Orion|StarShoot AutoGuider": "Orion|StarShoot AutoGuider|5.20|5.20|1280.00|1024.00|97",
    "Orion|StarShoot G3 Mono": "Orion|StarShoot G3 Mono|8.60|8.30|752.00|852.00|103",
    "Orion|StarShoot IV": "Orion|StarShoot IV|3.60|3.60|1280.00|1024.00|69",
    "Panasonic|DMC-G3": "Panasonic|DMC-G3|3.77|3.77|4592.00|3448.00|6482",
    "Panasonic|DMC-GH4": "Panasonic|DMC-GH4|3.75|3.75|4608.00|3456.00|171",
    "PCO Imaging|PCO Edge": "PCO Imaging|PCO Edge|6.50|6.50|2560.00|2160.00|182",
    "Pentax|K-30": "Pentax|K-30|4.80|4.80|4928.00|3264.00|291",
    "Phil Dyer|PD1": "Phil Dyer|PD1|6.50|6.25|752.00|582.00|183",
    "Phillips|SPC900NC": "Phillips|SPC900NC|5.60|5.60|640.00|480.00|70",
    "Player One|Mars-C": "Player One|Mars-C|2.90|2.90|1944.00|1096.00|7335",
    "Player One|Mars-M": "Player One|Mars-M|2.90|2.90|1944.00|1096.00|7281",
    "Player One|Neptune-C": "Player One|Neptune-C|2.40|2.40|3096.00|2078.00|6898",
    "Player One|Neptune-C II": "Player One|Neptune-C II|2.90|2.90|2712.00|1538.00|6886",
    "Player One|Neptune-M": "Player One|Neptune-M|2.40|2.40|3096.00|2078.00|7060",
    "Point Grey|Blackfly IMX249": "Point Grey|Blackfly IMX249|5.86|5.86|1920.00|1080.00|313",
    "Point Grey|Chameleon3 IMX264": "Point Grey|Chameleon3 IMX264|3.45|3.45|2448.00|2048.00|312",
    "Point Grey|Chameleon3 IMX265": "Point Grey|Chameleon3 IMX265|3.45|3.45|2048.00|1536.00|314",
    "Point Grey Research|Chameleon Color 1&quot;": "Point Grey Research|Chameleon Color 1/3&quot;|3.75|3.75|1296.00|964.00|149",
    "Point Grey Research|Chameleon Color 3&quot;": "Point Grey Research|Chameleon Color 1/3&quot;|3.75|3.75|1296.00|964.00|149",
    "Pt Grey|Grasshopper": "Pt Grey|Grasshopper|4.54|4.54|1920.00|1440.00|195",
    "QHY|09000A": "QHY|09000A|12.00|12.00|3056.00|3056.00|5323",
    "QHY|10": "QHY|10|6.05|6.05|3900.00|2616.00|132",
    "QHY|11": "QHY|11|9.00|9.00|4032.00|2688.00|4392",
    "QHY|12": "QHY|12|5.12|5.12|4610.00|3080.00|133",
    "QHY|128C": "QHY|128C|5.97|5.97|6036.00|4028.00|5311",
    "QHY|16200A": "QHY|16200A|6.00|6.00|4540.00|3630.00|170",
    "QHY|163M": "QHY|163M/C|3.80|3.80|4656.00|3522.00|5310",
    "QHY|163C": "QHY|163M/C|3.80|3.80|4656.00|3522.00|5310",
    "QHY|16803A": "QHY|16803A|9.00|9.00|4096.00|4096.00|5322",
    "QHY|168C": "QHY|168C|4.80|4.80|4952.00|3288.00|5313",
    "QHY|174M": "QHY|174M/C/GPS|5.86|5.86|1920.00|1200.00|5315",
    "QHY|174C": "QHY|174M/C/GPS|5.86|5.86|1920.00|1200.00|5315",
    "QHY|174GPS": "QHY|174M/C/GPS|5.86|5.86|1920.00|1200.00|5315",
    "QHY|178C": "QHY|178M/C|2.40|2.40|3072.00|2048.00|5304",
    "QHY|178M": "QHY|178M/C|2.40|2.40|3072.00|2048.00|5304",
    "QHY|183M": "QHY|183M/C|2.40|2.40|5544.00|3694.00|5299",
    "QHY|183C": "QHY|183M/C|2.40|2.40|5544.00|3694.00|5299",
    "QHY|21": "QHY|21|4.50|4.50|1940.00|1460.00|492",
    "QHY|22": "QHY|22|4.50|4.50|2758.00|2208.00|1752",
    "QHY|224C": "QHY|224C|3.75|3.75|1280.00|960.00|4453",
    "QHY|23": "QHY|23|3.69|3.69|3388.00|2712.00|113",
    "QHY|247C": "QHY|247C|3.91|3.91|6024.00|4024.00|5312",
    "QHY|268C Pro": "QHY|268C PH/EB/Pro|3.76|3.76|6280.00|4210.00|5285",
    "QHY|268C EB": "QHY|268C PH/EB/Pro|3.76|3.76|6280.00|4210.00|5285",
    "QHY|268C PH": "QHY|268C PH/EB/Pro|3.76|3.76|6280.00|4210.00|5285",
    "QHY|27": "QHY|27|5.50|5.50|4964.00|3332.00|711",
    "QHY|28": "QHY|28|7.40|7.40|4932.00|3300.00|4611",
    "QHY|29": "QHY|29|5.50|5.50|6644.00|4452.00|4612",
    "QHY|290C": "QHY|290M/C|2.90|2.90|1920.00|1080.00|5124",
    "QHY|290M": "QHY|290M/C|2.90|2.90|1920.00|1080.00|5124",
    "QHY|294M Pro": "QHY|294M/C Pro|4.63|4.63|4164.00|2796.00|5268",
    "QHY|294C Pro": "QHY|294M/C Pro|4.63|4.63|4164.00|2796.00|5268",
    "QHY|367C Pro": "QHY|367C Pro|4.88|4.88|7376.00|4938.00|5309",
    "QHY|410C": "QHY|410C|5.94|5.94|6072.00|4044.00|5308",
    "QHY|461": "QHY|461|3.76|3.76|11760.00|8896.00|5171",
    "QHY|5": "QHY|5|5.20|5.20|1280.00|1024.00|156",
    "QHY|5-II-M": "QHY|5-II-M|5.60|5.60|1280.00|1024.00|928",
    "QHY|5-III-174C": "QHY|5-III-174M/C|5.86|5.86|1920.00|1200.00|5201",
    "QHY|5-III-174M": "QHY|5-III-174M/C|5.86|5.86|1920.00|1200.00|5201",
    "QHY|5-III-178C": "QHY|5-III-178M/C|2.40|2.40|3072.00|2048.00|5245",
    "QHY|5-III-178M": "QHY|5-III-178M/C|2.40|2.40|3072.00|2048.00|5245",
    "QHY|5-III-185C": "QHY|5-III-185C|3.75|3.75|1920.00|1200.00|5082",
    "QHY|5-III-224C": "QHY|5-III-224C|3.75|3.75|1280.00|960.00|4287",
    "QHY|5-III-290C": "QHY|5-III-290M/C|2.90|2.90|1920.00|1080.00|2557",
    "QHY|5-III-290M": "QHY|5-III-290M/C|2.90|2.90|1920.00|1080.00|2557",
    "QHY|5-III-462C": "QHY|5-III-462C|2.90|2.90|1920.00|1080.00|5296",
    "QHY|550M": "QHY|550M/C/P|3.45|3.45|2464.00|2056.00|5314",
    "QHY|550C": "QHY|550M/C/P|3.45|3.45|2464.00|2056.00|5314",
    "QHY|550P": "QHY|550M/C/P|3.45|3.45|2464.00|2056.00|5314",
    "QHY|5L-II-C": "QHY|5L-II-M/C|3.75|3.75|1280.00|960.00|289",
    "QHY|5L-II-M": "QHY|5L-II-M/C|3.75|3.75|1280.00|960.00|289",
    "QHY|5P-II-M": "QHY|5P-II-M/C|2.20|2.20|2592.00|1944.00|112",
    "QHY|5P-II-C": "QHY|5P-II-M/C|2.20|2.20|2592.00|1944.00|112",
    "QHY|5R-II-C": "QHY|5R-II-C|5.60|5.60|720.00|576.00|5317",
    "QHY|6": "QHY|6|6.50|6.25|752.00|582.00|226",
    "QHY|600C L": "QHY|600M/C L/PH/Pro|3.76|3.76|9576.00|6388.00|5278",
    "QHY|600C PH": "QHY|600M/C L/PH/Pro|3.76|3.76|9576.00|6388.00|5278",
    "QHY|600C Pro": "QHY|600M/C L/PH/Pro|3.76|3.76|9576.00|6388.00|5278",
    "QHY|600M L": "QHY|600M/C L/PH/Pro|3.76|3.76|9576.00|6388.00|5278",
    "QHY|600M PH": "QHY|600M/C L/PH/Pro|3.76|3.76|9576.00|6388.00|5278",
    "QHY|600M Pro": "QHY|600M/C L/PH/Pro|3.76|3.76|9576.00|6388.00|5278",
    "QHY|695A": "QHY|695A|4.54|4.54|2758.00|2208.00|5064",
    "QHY|8": "QHY|8|7.80|7.80|3000.00|2000.00|13",
    "QHY|814A": "QHY|814A|3.69|3.69|3468.00|2728.00|3091",
    "QHY|8Pro": "QHY|8L/Pro|7.80|7.80|3110.00|2030.00|66",
    "QHY|8L": "QHY|8L/Pro|7.80|7.80|3110.00|2030.00|66",
    "QHY|9": "QHY|9/9S|5.40|5.40|3358.00|2536.00|71",
    "QHY|9S": "QHY|9/9S|5.40|5.40|3358.00|2536.00|71",
    "QHY|90A": "QHY|90A|5.40|5.40|3358.00|2536.00|5321",
    "QHY|IMG132E": "QHY|IMG132E|3.63|3.63|1329.00|1049.00|67",
    "QHY|miniCAM5": "QHY|miniCAM5|3.75|3.75|1280.00|960.00|211",
    "QSI|532 wsg": "QSI|532 wsg|6.80|6.80|2184.00|1472.00|169",
    "QSI|583": "QSI|583|5.40|5.40|3326.00|2504.00|57",
    "QSI|6120": "QSI|6120|3.10|3.10|4250.00|2838.00|92",
    "QSI|616": "QSI|616|9.00|9.00|1536.00|1024.00|1421",
    "QSI|6162": "QSI|6162|6.00|6.00|4499.00|3599.00|5068",
    "QSI|632": "QSI|632|6.80|6.80|2184.00|1472.00|284",
    "QSI|660": "QSI|660|4.54|4.54|2758.00|2208.00|58",
    "QSI|683": "QSI|683|5.40|5.40|3326.00|2504.00|5",
    "QSI|690": "QSI|690|3.69|3.69|3388.00|2712.00|10",
    "RasberryPi v2|Sony IMX219 PQ CMOS": "RasberryPi v2|Sony IMX219 PQ CMOS|1.12|1.12|3280.00|2464.00|1977",
    "Raspberry pi Camera|version 1.3": "Raspberry pi Camera|version 1.3|1.40|1.40|2592.00|1944.00|326",
    "S-BIG|ST 8300C": "S-BIG|ST 8300C|5.40|5.40|3326.00|2504.00|135",
    "SBIG|ST-1001E": "SBIG|ST-1001E|24.00|24.00|1024.00|1024.00|94",
    "SBIG|ST-10XME": "SBIG|ST-10XME|6.80|6.80|2184.00|1472.00|63",
    "SBIG|ST-2000XM": "SBIG|ST-2000XM|7.40|7.40|1600.00|1200.00|93",
    "SBIG|ST-237": "SBIG|ST-237|7.40|7.40|640.00|480.00|200",
    "SBIG|STF-8300": "SBIG|STF-8300|5.40|5.40|2.00|2.00|111",
    "SBIG|STF-8300M": "SBIG|STF-8300M|5.20|5.20|3326.00|2504.00|9",
    "SBIG|STL-1001e": "SBIG|STL-1001e|24.00|24.00|1024.00|1024.00|110",
    "SBIG|STX-16803": "SBIG|STX-16803|9.00|9.00|4096.00|4096.00|89",
    "Sony|A100": "Sony|A100|6.10|6.10|3872.00|2592.00|217",
    "Sony|A580": "Sony|A580|4.76|4.76|4912.00|3264.00|274",
    "Sony|A7s": "Sony|A7s|8.40|8.40|4240.00|2832.00|101",
    "Sony|Alpha 3000": "Sony|Alpha 3000|4.30|4.30|5456.00|3632.00|38",
    "Sony|Alpha a55": "Sony|Alpha a55|4.75|4.75|4912.00|3264.00|60",
    "Sony|NEX 5N": "Sony|NEX 5N|5.00|5.00|4592.00|3056.00|68",
    "Sony|Playstation Eye": "Sony|Playstation Eye|6.00|6.00|640.00|480.00|160",
    "Starlight Xpress|CoStar": "Starlight Xpress|CoStar|5.20|5.20|1304.00|1024.00|53",
    "Starlight Xpress|H16": "Starlight Xpress|H16|7.40|7.40|2048.00|2048.00|80",
    "Starlight Xpress|Lodestar": "Starlight Xpress|Lodestar|8.20|8.40|752.00|580.00|33",
    "Starlight Xpress|Lodestar C": "Starlight Xpress|Lodestar C|8.60|8.30|752.00|580.00|34",
    "Starlight Xpress|Lodestar X2": "Starlight Xpress|Lodestar X2|8.20|8.40|752.00|580.00|32",
    "Starlight Xpress|Superstar": "Starlight Xpress|Superstar|4.65|4.65|1392.00|1040.00|52",
    "Starlight Xpress|SX Trius CSX-249 CMOS": "Starlight Xpress|SX Trius CSX-249 CMOS|6.00|6.00|1920.00|1200.00|2455",
    "Starlight Xpress|SX Trius CSX-290 CMOS": "Starlight Xpress|SX Trius CSX-290 CMOS|2.90|2.90|1945.00|1097.00|2456",
    "Starlight Xpress|SX Trius CSX-304 CMOS": "Starlight Xpress|SX Trius CSX-304 CMOS|3.45|3.45|4096.00|3000.00|2454",
    "Starlight Xpress|SXVR-H18": "Starlight Xpress|SXVR-H18|5.40|5.40|3326.00|2504.00|59",
    "Starlight Xpress|SXVR-H9": "Starlight Xpress|SXVR-H9|6.45|6.45|1392.00|1040.00|4782",
    "Starlight Xpress|Trius PRO-834": "Starlight Xpress|Trius PRO-834|3.10|3.10|4240.00|2824.00|2397",
    "Starlight Xpress|Trius SX-16": "Starlight Xpress|Trius SX-16|7.40|7.40|2048.00|2048.00|51",
    "Starlight Xpress|Trius SX-25C": "Starlight Xpress|Trius SX-25C|7.80|7.80|3024.00|2016.00|43",
    "Starlight Xpress|Trius SX-26C": "Starlight Xpress|Trius SX-26C|6.05|6.05|3900.00|2616.00|44",
    "Starlight Xpress|Trius SX-46": "Starlight Xpress|Trius SX-46|6.00|6.00|4540.00|3640.00|925",
    "Starlight Xpress|Trius SX-56": "Starlight Xpress|Trius SX-56|9.00|9.00|4096.00|4096.00|924",
    "Starlight Xpress|Trius SX-9": "Starlight Xpress|Trius SX-9|6.45|6.45|1392.00|1040.00|48",
    "Starlight Xpress|Trius PRO-35": "Starlight Xpress|Trius SX/PRO-35|9.00|9.00|4032.00|2688.00|45",
    "Starlight Xpress|Trius SX-35": "Starlight Xpress|Trius SX/PRO-35|9.00|9.00|4032.00|2688.00|45",
    "Starlight Xpress|Trius SX-36": "Starlight Xpress|Trius SX/PRO-36|7.40|7.40|4904.00|3280.00|46",
    "Starlight Xpress|Trius PRO-36": "Starlight Xpress|Trius SX/PRO-36|7.40|7.40|4904.00|3280.00|46",
    "Starlight Xpress|Trius PRO-674": "Starlight Xpress|Trius SX/PRO-674|4.54|4.54|1940.00|1460.00|49",
    "Starlight Xpress|Trius SX-674": "Starlight Xpress|Trius SX/PRO-674|4.54|4.54|1940.00|1460.00|49",
    "Starlight Xpress|Trius PRO-694": "Starlight Xpress|Trius SX/PRO-694|4.54|4.54|2750.00|2200.00|35",
    "Starlight Xpress|Trius SX-694": "Starlight Xpress|Trius SX/PRO-694|4.54|4.54|2750.00|2200.00|35",
    "Starlight Xpress|Trius PRO-814": "Starlight Xpress|Trius SX/PRO-814|3.69|3.69|3380.00|2704.00|47",
    "Starlight Xpress|Trius SX-814": "Starlight Xpress|Trius SX/PRO-814|3.69|3.69|3380.00|2704.00|47",
    "Starlight Xpress|Trius SX-825": "Starlight Xpress|Trius SX/PRO-825|6.40|6.40|1392.00|1040.00|1160",
    "Starlight Xpress|Trius PRO-825": "Starlight Xpress|Trius SX/PRO-825|6.40|6.40|1392.00|1040.00|1160",
    "Starlight Xpress|Ultrastar": "Starlight Xpress|Ultrastar|6.45|6.45|1392.00|1040.00|116",
    "Toucam Pro|SC4": "Toucam Pro|SC4|9.90|9.90|659.00|494.00|29",
    "ToupTek|GCMOS01200KMA Mono Imager/Guider": "ToupTek|GCMOS01200KMA Mono Imager/Guider|3.75|3.75|1280.00|960.00|235",
    "ToupTek|GCMOS01200KPA Colour Imager/Guider": "ToupTek|GCMOS01200KPA Colour Imager/Guider|3.75|3.75|1280.00|960.00|234",
    "ZWO|ASI034MC": "ZWO|ASI034MC|5.60|5.60|728.00|512.00|265",
    "ZWO|ASI071MC-Pro": "ZWO|ASI071MC-Pro|4.78|4.78|4944.00|3284.00|438",
    "ZWO|ASI094MC-Pro": "ZWO|ASI094MC-Pro|4.88|4.88|7736.00|4928.00|922",
    "ZWO|ASI120MC-S": "ZWO|ASI120MC-S|3.75|3.75|1280.00|960.00|151",
    "ZWO|ASI120Mini": "ZWO|ASI120MM/MC/Mini|3.75|3.75|1280.00|960.00|7",
    "ZWO|ASI120MM": "ZWO|ASI120MM/MC/Mini|3.75|3.75|1280.00|960.00|7",
    "ZWO|ASI120MC": "ZWO|ASI120MM/MC/Mini|3.75|3.75|1280.00|960.00|7",
    "ZWO|ASI128MC-Pro": "ZWO|ASI128MC-Pro|5.97|5.97|6032.00|4032.00|923",
    "ZWO|ASI1600": "ZWO|ASI1600|3.80|3.80|4656.00|3520.00|242",
    "ZWO|ASI1600GT": "ZWO|ASI1600MM/MC/GT|3.80|3.80|4656.00|3520.00|272",
    "ZWO|ASI1600MM": "ZWO|ASI1600MM/MC/GT|3.80|3.80|4656.00|3520.00|272",
    "ZWO|ASI1600MC": "ZWO|ASI1600MM/MC/GT|3.80|3.80|4656.00|3520.00|272",
    "ZWO|ASI174Mini": "ZWO|ASI174MM/MC/Mini|5.86|5.86|1936.00|1216.00|268",
    "ZWO|ASI174MM": "ZWO|ASI174MM/MC/Mini|5.86|5.86|1936.00|1216.00|268",
    "ZWO|ASI174MC": "ZWO|ASI174MM/MC/Mini|5.86|5.86|1936.00|1216.00|268",
    "ZWO|ASI178MC": "ZWO|ASI178MM/MC|2.40|2.40|3096.00|2080.00|267",
    "ZWO|ASI178MM": "ZWO|ASI178MM/MC|2.40|2.40|3096.00|2080.00|267",
    "ZWO|ASI183MM": "ZWO|ASI183MM/MC/GT|2.40|2.40|5496.00|3672.00|1115",
    "ZWO|ASI183MC": "ZWO|ASI183MM/MC/GT|2.40|2.40|5496.00|3672.00|1115",
    "ZWO|ASI183GT": "ZWO|ASI183MM/MC/GT|2.40|2.40|5496.00|3672.00|1115",
    "ZWO|ASI185MC": "ZWO|ASI185MC|2.90|2.90|3840.00|2160.00|7874",
    "ZWO|ASI224MC": "ZWO|ASI224MC|3.75|3.75|1304.00|976.00|266",
    "ZWO|ASI2400MC-Pro": "ZWO|ASI2400MC-Pro|5.94|5.94|6072.00|4042.00|4300",
    "ZWO|ASI2600MC-Pro": "ZWO|ASI2600MM/MC-Pro|3.76|3.76|6248.00|4176.00|3258",
    "ZWO|ASI2600MM": "ZWO|ASI2600MM/MC-Pro|3.76|3.76|6248.00|4176.00|3258",
    "ZWO|ASI290MM": "ZWO|ASI290MM/MC/Mini|2.90|2.90|1936.00|1096.00|258",
    "ZWO|ASI290MC": "ZWO|ASI290MM/MC/Mini|2.90|2.90|1936.00|1096.00|258",
    "ZWO|ASI290Mini": "ZWO|ASI290MM/MC/Mini|2.90|2.90|1936.00|1096.00|258",
    "ZWO|ASI294MM": "ZWO|ASI294MM/MC-Pro|4.63|4.63|4144.00|2822.00|1134",
    "ZWO|ASI294MC-Pro": "ZWO|ASI294MM/MC-Pro|4.63|4.63|4144.00|2822.00|1134",
    "ZWO|ASI385MC": "ZWO|ASI385MC|3.75|3.75|1936.00|1096.00|1131",
    "ZWO|ASI462MC": "ZWO|ASI462MC|2.90|2.90|1936.00|1096.00|4400",
    "ZWO|ASI482MC": "ZWO|ASI482MC|5.80|5.80|1920.00|1080.00|7873",
    "ZWO|ASI533MC-Pro": "ZWO|ASI533MC-Pro|3.76|3.76|3008.00|3008.00|3106",
    "ZWO|ASI6200MM": "ZWO|ASI6200MM/MC-Pro|3.76|3.76|9576.00|6388.00|3264",
    "ZWO|ASI6200MC-Pro": "ZWO|ASI6200MM/MC-Pro|3.76|3.76|9576.00|6388.00|3264",
}

barlows = [
    1,
    0.33,
    0.4,
    0.5,
    0.63,
    0.67,
    0.7,
    0.72,
    0.73,
    0.8,
    0.85,
    1.15,
    1.5,
    1.6,
    2,
    2.25,
    2.5,
    2.75,
    3,
    4,
    4.2,
    5,
]

eyepieces = {
    'Agena|2"; Super Wide Angle (SWA)|38.00': 'Agena|2"; Super Wide Angle (SWA)|38.00|70.00|251">Agena - 2',
    "Astro Essentials|Super Plossl|7.50": "Astro Essentials|Super Plossl|7.50|52.00|2233",
    "Astro Essentials|Super Plossl|10.00": "Astro Essentials|Super Plossl|10.00|52.00|2234",
    "Astro Essentials|Super Plossl|12.50": "Astro Essentials|Super Plossl|12.50|52.00|2235",
    "Astro Essentials|Super Plossl|15.00": "Astro Essentials|Super Plossl|15.00|52.00|2236",
    "Astro Essentials|Super Plossl|32.00": "Astro Essentials|Super Plossl|32.00|52.00|2245",
    "Astro-Tech|Titan|20.00": "Astro-Tech|Titan|20.00|70.00|283",
    "Astro-Tech|Titan|26.00": "Astro-Tech|Titan|26.00|70.00|284",
    "Baader|Classic Ortho|6.00": "Baader|Classic Ortho|6.00|50.00|25",
    "Baader|Classic Ortho|10.00": "Baader|Classic Ortho|10.00|50.00|113",
    "Baader|Classic Ortho|18.00": "Baader|Classic Ortho|18.00|50.00|308",
    "Baader|Classic Plossl|32.00": "Baader|Classic Plossl|32.00|50.00|114",
    "Baader|Eudiascopic|10.00": "Baader|Eudiascopic|10.00|44.40|93",
    "Baader|Eudiascopic|35.00": "Baader|Eudiascopic|35.00|45.60|92",
    "Baader|Hyperion|3.50": "Baader|Hyperion|3.50|68.00|35",
    "Baader|Hyperion|5.00": "Baader|Hyperion|5.00|68.00|38",
    "Baader|Hyperion|8.00": "Baader|Hyperion|8.00|68.00|9",
    "Baader|Hyperion|10.00": "Baader|Hyperion|10.00|68.00|1",
    "Baader|Hyperion|13.00": "Baader|Hyperion|13.00|68.00|2",
    "Baader|Hyperion|17.00": "Baader|Hyperion|17.00|68.00|3",
    "Baader|Hyperion|21.00": "Baader|Hyperion|21.00|68.00|4",
    "Baader|Hyperion|24.00": "Baader|Hyperion|24.00|68.00|5",
    "Baader|Hyperion Aspheric|31.00": "Baader|Hyperion Aspheric|31.00|72.00|56",
    "Baader|Hyperion Aspheric|36.00": "Baader|Hyperion Aspheric|36.00|72.00|57",
    "Baader Planetarium|Morpheus|4.50": "Baader Planetarium|Morpheus|4.50|76.00|178",
    "Baader Planetarium|Morpheus|6.50": "Baader Planetarium|Morpheus|6.50|76.00|179",
    "Baader Planetarium|Morpheus|9.00": "Baader Planetarium|Morpheus|9.00|76.00|180",
    "Baader Planetarium|Morpheus|12.50": "Baader Planetarium|Morpheus|12.50|76.00|181",
    "Baader Planetarium|Morpheus|14.00": "Baader Planetarium|Morpheus|14.00|76.00|182",
    "Baader Planetarium|Morpheus|17.50": "Baader Planetarium|Morpheus|17.50|76.00|183",
    "BST|Starguider|3.20": "BST|Starguider|3.20|60.00|387",
    "BST|Starguider|5.00": "BST|Starguider|5.00|60.00|388",
    "BST|Starguider|8.00": "BST|Starguider|8.00|60.00|122",
    "BST|Starguider|12.00": "BST|Starguider|12.00|60.00|188",
    "BST|Starguider|15.00": "BST|Starguider|15.00|60.00|229",
    "BST|Starguider|18.00": "BST|Starguider|18.00|60.00|228",
    "BST|Starguider|25.00": "BST|Starguider|25.00|60.00|389",
    "Celestron|Axiom|15.00": "Celestron|Axiom|15.00|70.00|213",
    "Celestron|Axiom|15.00": "Celestron|Axiom|15.00|70.00|214",
    "Celestron|E-Lux|26.00": "Celestron|E-Lux|26.00|56.00|190",
    "Celestron|E-Lux|32.00": "Celestron|E-Lux|32.00|56.00|189",
    "Celestron|E-Lux 40mm|40.00": "Celestron|E-Lux 40mm|40.00|50.00|187",
    "Celestron|Luminos|7.00": "Celestron|Luminos|7.00|82.00|50",
    "Celestron|Luminos|10.00": "Celestron|Luminos|10.00|82.00|51",
    "Celestron|Luminos|15.00": "Celestron|Luminos|15.00|82.00|52",
    "Celestron|Luminos|19.00": "Celestron|Luminos|19.00|82.00|53",
    "Celestron|Luminos|23.00": "Celestron|Luminos|23.00|82.00|54",
    "Celestron|Luminos|31.00": "Celestron|Luminos|31.00|82.00|55",
    "Celestron|Plossl|6.00": "Celestron|Plossl|6.00|52.00|206",
    "Celestron|Plossl|8.00": "Celestron|Plossl|8.00|52.00|207",
    "Celestron|Plossl|9.00": "Celestron|Plossl|9.00|52.00|864",
    "Celestron|Plossl|13.00": "Celestron|Plossl|13.00|52.00|104",
    "Celestron|Plossl|17.00": "Celestron|Plossl|17.00|52.00|208",
    "Celestron|Plossl|20.00": "Celestron|Plossl|20.00|52.00|209",
    "Celestron|Plossl|25.00": "Celestron|Plossl|25.00|60.00|215",
    "Celestron|Plossl|32.00": "Celestron|Plossl|32.00|52.00|210",
    "Celestron|Plossl|40.00": "Celestron|Plossl|40.00|43.00|105",
    "Celestron|Ultima|7.50": "Celestron|Ultima|7.50|51.00|116",
    "Celestron|Ultima|18.00": "Celestron|Ultima|18.00|51.00|117",
    "Celestron|Ultima Duo|5.00": "Celestron|Ultima Duo|5.00|68.00|98",
    "Celestron|Ultima Duo|8.00": "Celestron|Ultima Duo|8.00|68.00|99",
    "Celestron|Ultima Duo|10.00": "Celestron|Ultima Duo|10.00|68.00|100",
    "Celestron|Ultima Duo|13.00": "Celestron|Ultima Duo|13.00|68.00|101",
    "Celestron|Ultima Duo|17.00": "Celestron|Ultima Duo|17.00|68.00|102",
    "Celestron|Ultima Duo|21.00": "Celestron|Ultima Duo|21.00|68.00|103",
    "Celestron|X-Cel LX|2.30": "Celestron|X-Cel LX|2.30|60.00|83",
    "Celestron|X-Cel LX|5.00": "Celestron|X-Cel LX|5.00|60.00|84",
    "Celestron|X-Cel LX|7.00": "Celestron|X-Cel LX|7.00|60.00|85",
    "Celestron|X-Cel LX|9.00": "Celestron|X-Cel LX|9.00|60.00|86",
    "Celestron|X-Cel LX|12.00": "Celestron|X-Cel LX|12.00|60.00|87",
    "Celestron|X-Cel LX|18.00": "Celestron|X-Cel LX|18.00|60.00|88",
    "Celestron|X-Cel LX|25.00": "Celestron|X-Cel LX|25.00|60.00|89",
    "Explore Scientific|100° Series|5.50": "Explore Scientific|100° Series|5.50|100.00|143",
    "Explore Scientific|100° Series|9.00": "Explore Scientific|100° Series|9.00|100.00|144",
    "Explore Scientific|100° Series|14.00": "Explore Scientific|100° Series|14.00|100.00|145",
    "Explore Scientific|100° Series|20.00": "Explore Scientific|100° Series|20.00|100.00|146",
    "Explore Scientific|100° Series|25.00": "Explore Scientific|100° Series|25.00|100.00|147",
    "Explore Scientific|100° Series|30.00": "Explore Scientific|100° Series|30.00|100.00|148",
    "Explore Scientific|120º Series|9.00": "Explore Scientific|120º Series|9.00|120.00|167",
    "Explore Scientific|52° Series|3.00": "Explore Scientific|52° Series|3.00|52.00|843",
    "Explore Scientific|52° Series|4.50": "Explore Scientific|52° Series|4.50|52.00|844",
    "Explore Scientific|52° Series|6.50": "Explore Scientific|52° Series|6.50|52.00|845",
    "Explore Scientific|52° Series|10.00": "Explore Scientific|52° Series|10.00|52.00|846",
    "Explore Scientific|52° Series|15.00": "Explore Scientific|52° Series|15.00|52.00|847",
    "Explore Scientific|52° Series|20.00": "Explore Scientific|52° Series|20.00|52.00|848",
    "Explore Scientific|52° Series|25.00": "Explore Scientific|52° Series|25.00|52.00|849",
    "Explore Scientific|52° Series|30.00": "Explore Scientific|52° Series|30.00|52.00|850",
    "Explore Scientific|52° Series|40.00": "Explore Scientific|52° Series|40.00|52.00|852",
    "Explore Scientific|62º Series|5.50": "Explore Scientific|62º Series|5.50|62.00|390",
    "Explore Scientific|62º Series|9.00": "Explore Scientific|62º Series|9.00|62.00|391",
    "Explore Scientific|62º Series|14.00": "Explore Scientific|62º Series|14.00|62.00|392",
    "Explore Scientific|62º Series|20.00": "Explore Scientific|62º Series|20.00|62.00|393",
    "Explore Scientific|62º Series|26.00": "Explore Scientific|62º Series|26.00|62.00|394",
    "Explore Scientific|62º Series|32.00": "Explore Scientific|62º Series|32.00|62.00|395",
    "Explore Scientific|62º Series|40.00": "Explore Scientific|62º Series|40.00|62.00|396",
    "Explore Scientific|68° Maxvision|20.00": "Explore Scientific|68° Maxvision|20.00|68.00|135",
    "Explore Scientific|68° Maxvision|24.00": "Explore Scientific|68° Maxvision|24.00|68.00|134",
    "Explore Scientific|68° Maxvision|28.00": "Explore Scientific|68° Maxvision|28.00|68.00|133",
    "Explore Scientific|68° Maxvision|34.00": "Explore Scientific|68° Maxvision|34.00|68.00|132",
    "Explore Scientific|68° Maxvision|40.00": "Explore Scientific|68° Maxvision|40.00|68.00|141",
    "Explore Scientific|68° Series|16.00": "Explore Scientific|68° Series|16.00|68.00|121",
    "Explore Scientific|68° Series|20.00": "Explore Scientific|68° Series|20.00|68.00|149",
    "Explore Scientific|68° Series|24.00": "Explore Scientific|68° Series|24.00|68.00|150",
    "Explore Scientific|68° Series|28.00": "Explore Scientific|68° Series|28.00|68.00|34",
    "Explore Scientific|68° Series|34.00": "Explore Scientific|68° Series|34.00|68.00|151",
    "Explore Scientific|68° Series|40.00": "Explore Scientific|68° Series|40.00|68.00|152",
    "Explore Scientific|70º Series|10.00": "Explore Scientific|70º Series|10.00|70.00|153",
    "Explore Scientific|70º Series|15.00": "Explore Scientific|70º Series|15.00|70.00|154",
    "Explore Scientific|70º Series|20.00": "Explore Scientific|70º Series|20.00|70.00|155",
    "Explore Scientific|70º Series|25.00": "Explore Scientific|70º Series|25.00|70.00|156",
    "Explore Scientific|70º Series|30.00": "Explore Scientific|70º Series|30.00|70.00|157",
    "Explore Scientific|70º Series|35.00": "Explore Scientific|70º Series|35.00|70.00|158",
    "Explore Scientific|82º Maxvision|24.00": "Explore Scientific|82º Maxvision|24.00|82.00|142",
    "Explore Scientific|82º Series|4.70": "Explore Scientific|82º Series|4.70|82.00|159",
    "Explore Scientific|82º Series|6.70": "Explore Scientific|82º Series|6.70|82.00|160",
    "Explore Scientific|82º Series|8.80": "Explore Scientific|82º Series|8.80|82.00|161",
    "Explore Scientific|82º Series|11.00": "Explore Scientific|82º Series|11.00|82.00|162",
    "Explore Scientific|82º Series|14.00": "Explore Scientific|82º Series|14.00|82.00|163",
    "Explore Scientific|82º Series|18.00": "Explore Scientific|82º Series|18.00|82.00|164",
    "Explore Scientific|82º Series|24.00": "Explore Scientific|82º Series|24.00|82.00|165",
    "Explore Scientific|82º Series|30.00": "Explore Scientific|82º Series|30.00|82.00|166",
    "Explore Scientific|92° LER Series|12.00": "Explore Scientific|92° LER Series|12.00|92.00|379",
    "Explore Scientific|92° LER Series|17.00": "Explore Scientific|92° LER Series|17.00|92.00|247",
    "Fujiyama|HD-OR|4.00": "Fujiyama|HD-OR|4.00|42.00|171",
    "Fujiyama|HD-OR|5.00": "Fujiyama|HD-OR|5.00|42.00|1731",
    "Fujiyama|HD-OR|6.00": "Fujiyama|HD-OR|6.00|42.00|1733",
    "Fujiyama|HD-OR|7.00": "Fujiyama|HD-OR|7.00|42.00|1734",
    "Fujiyama|HD-OR|9.00": "Fujiyama|HD-OR|9.00|42.00|1735",
    "Fujiyama|HD-OR|12.50": "Fujiyama|HD-OR|12.50|42.00|1736",
    "Fujiyama|HD-OR|18.00": "Fujiyama|HD-OR|18.00|42.00|1737",
    "Fujiyama|HD-OR|25.00": "Fujiyama|HD-OR|25.00|42.00|1738",
    'GSO|2"; SuperView|38.00': 'GSO|2"; SuperView|38.00|60.00|252">GSO - 2',
    'GSO|2"; SuperView Wide Angle|30.00': 'GSO|2"; SuperView Wide Angle|30.00|68.00|1855">GSO - 2',
    'GSO|2"; SuperView Wide Angle|42.00': 'GSO|2"; SuperView Wide Angle|42.00|68.00|1854">GSO - 2',
    "Kson|2” KF|18.00": "Kson|2” KF|18.00|46.00|1730",
    "Kson|2” KF|25.00": "Kson|2” KF|25.00|46.00|1729",
    "Kson|2” KF|32.00": "Kson|2” KF|32.00|46.00|1728",
    "Lunt|H-alpha|8.00": "Lunt|H-alpha|8.00|60.00|70",
    "Lunt|H-alpha|12.00": "Lunt|H-alpha|12.00|60.00|71",
    "Lunt|H-alpha|16.00": "Lunt|H-alpha|16.00|60.00|72",
    "Lunt|H-alpha|19.00": "Lunt|H-alpha|19.00|65.00|73",
    "Lunt|H-alpha|27.00": "Lunt|H-alpha|27.00|53.00|74",
    'Masuyama|1.25"; Eyepiece|16.00': 'Masuyama|1.25"; Eyepiece|16.00|85.00|654">Masuyama - 1.25',
    'Masuyama|2"; Eyepiece|26.00': 'Masuyama|2"; Eyepiece|26.00|85.00|655">Masuyama - 2',
    'Masuyama|2"; Eyepiece|32.00': 'Masuyama|2"; Eyepiece|32.00|85.00|324">Masuyama - 2',
    'Masuyama|2"; Eyepiece|45.00': 'Masuyama|2"; Eyepiece|45.00|53.00|287">Masuyama - 2',
    'Masuyama|2"; Eyepiece|50.00': 'Masuyama|2"; Eyepiece|50.00|53.00|288">Masuyama - 2',
    'Masuyama|2"; Eyepiece|60.00': 'Masuyama|2"; Eyepiece|60.00|46.00|286">Masuyama - 2',
    "Meade|4000 QX Wide Angle|26.00": "Meade|4000 QX Wide Angle|26.00|70.00|314",
    "Meade|5000 SWA|20.00": "Meade|5000 SWA|20.00|68.00|317",
    "Meade|5000 UWA|24.00": "Meade|5000 UWA|24.00|82.00|13",
    "Meade|Series 4000|56.00": "Meade|Series 4000|56.00|52.00|106",
    "Meade|Series 4000 SWA|40.00": "Meade|Series 4000 SWA|40.00|67.00|224",
    "Meade|Series-5000 HD|9.00": "Meade|Series-5000 HD|9.00|60.00|323",
    "Meade|Series-5000 HD|12.00": "Meade|Series-5000 HD|12.00|60.00|322",
    "Meade|Series-5000 HD|18.00": "Meade|Series-5000 HD|18.00|60.00|321",
    "Meade|Series-5000 HD|25.00": "Meade|Series-5000 HD|25.00|60.00|320",
    "Meade|Super Plossl|9.70": "Meade|Super Plossl|9.70|52.00|15",
    "Meade|Super Plossl|12.40": "Meade|Super Plossl|12.40|52.00|16",
    "Orion|Expanse|9.00": "Orion|Expanse|9.00|66.00|169",
    "Orion|Q70|38.00": "Orion|Q70|38.00|72.00|191",
    "Ostara|SWA FMC|32.00": "Ostara|SWA FMC|32.00|70.00|23",
    "OVL|Myriad|3.50": "OVL|Myriad|3.50|110.00|107",
    "OVL|Myriad|5.00": "OVL|Myriad|5.00|110.00|108",
    "OVL|Myriad|9.00": "OVL|Myriad|9.00|100.00|109",
    "OVL|Myriad|20.00": "OVL|Myriad|20.00|100.00|110",
    "OVL|Nirvana-ES UWA|4.00": "OVL|Nirvana-ES UWA|4.00|82.00|804",
    "OVL|Nirvana-ES UWA|7.00": "OVL|Nirvana-ES UWA|7.00|82.00|805",
    "OVL|Nirvana-ES UWA|16.00": "OVL|Nirvana-ES UWA|16.00|82.00|806",
    "OVL|Panaview|26.00": "OVL|Panaview|26.00|70.00|126",
    "OVL|Panaview|32.00": "OVL|Panaview|32.00|70.00|6",
    "OVL|Panaview|38.00": "OVL|Panaview|38.00|70.00|8",
    "Pentax|XW|3.50": "Pentax|XW|3.50|70.00|26",
    "Pentax|XW|5.00": "Pentax|XW|5.00|70.00|27",
    "Pentax|XW|7.00": "Pentax|XW|7.00|70.00|28",
    "Pentax|XW|10.00": "Pentax|XW|10.00|70.00|29",
    "Pentax|XW|14.00": "Pentax|XW|14.00|70.00|30",
    "Pentax|XW|20.00": "Pentax|XW|20.00|70.00|31",
    "Pentax|XW|30.00": "Pentax|XW|30.00|70.00|32",
    "Pentax|XW|40.00": "Pentax|XW|40.00|70.00|33",
    "Revelation|32mm Plossl|32.00": "Revelation|32mm Plossl|32.00|52.00|185",
    "Sky-Watcher|Aero ED SWA|40.00": "Sky-Watcher|Aero ED SWA|40.00|68.00|124",
    "Sky-watcher|Super-MA|10.00": "Sky-watcher|Super-MA|10.00|52.00|68",
    "Sky-watcher|Super-MA|25.00": "Sky-watcher|Super-MA|25.00|50.00|67",
    "Sky-Watcher|Ultrawide|9.00": "Sky-Watcher|Ultrawide|9.00|66.00|111",
    "Sky-watcher|UWA-Planetary|2.50": "Sky-watcher|UWA-Planetary|2.50|58.00|96",
    "Skywatcher|LET|28.00": "Skywatcher|LET|28.00|56.00|2267",
    "StellaLyra|15mm SuperView|15.00": "StellaLyra|15mm SuperView|15.00|68.00|1596",
    "StellaLyra|20mm SuperView|20.00": "StellaLyra|20mm SuperView|20.00|68.00|1597",
    "StellaLyra|30mm SuperView|30.00": "StellaLyra|30mm SuperView|30.00|68.00|1598",
    "StellaLyra|42mm SuperView|42.00": "StellaLyra|42mm SuperView|42.00|58.00|1599",
    "StellaLyra|50mm SuperView|50.00": "StellaLyra|50mm SuperView|50.00|48.00|1600",
    'StellaLyra|8-24mm 1.25"; Lanthanum Zoom|8.00': 'StellaLyra|8-24mm 1.25"; Lanthanum Zoom|8.00|40.00|1813">StellaLyra - 8-24mm 1.25',
    'StellaLyra|8-24mm 1.25"; Lanthanum Zoom|16.00': 'StellaLyra|8-24mm 1.25"; Lanthanum Zoom|16.00|50.00|1814">StellaLyra - 8-24mm 1.25',
    'StellaLyra|8-24mm 1.25"; Lanthanum Zoom|24.00': 'StellaLyra|8-24mm 1.25"; Lanthanum Zoom|24.00|60.00|1815">StellaLyra - 8-24mm 1.25',
    "StellaLyra|KITAKARU RPL|18.00": "StellaLyra|KITAKARU RPL|18.00|62.00|1821",
    "StellaLyra|KITAKARU RPL|25.00": "StellaLyra|KITAKARU RPL|25.00|62.00|1822",
    "StellaLyra|KITAKARU RPL|30.00": "StellaLyra|KITAKARU RPL|30.00|62.00|1823",
    "StellaLyra|KITAKARU RPL|40.00": "StellaLyra|KITAKARU RPL|40.00|65.00|1824",
    "StellaLyra|KITAKARU RPL|45.00": "StellaLyra|KITAKARU RPL|45.00|62.00|1825",
    "StellaLyra|LER|3.00": "StellaLyra|LER|3.00|55.00|1820",
    "StellaLyra|LER|5.00": "StellaLyra|LER|5.00|55.00|1819",
    "StellaLyra|LER|6.00": "StellaLyra|LER|6.00|55.00|1818",
    "StellaLyra|LER|9.00": "StellaLyra|LER|9.00|55.00|1817",
    "StellaLyra|LER|12.50": "StellaLyra|LER|12.50|55.00|1816",
    "StellaLyra|Super-Plossl|9.00": "StellaLyra|Super-Plossl|9.00|52.00|2120",
    "StellaLyra|Super-Plossl|25.00": "StellaLyra|Super-Plossl|25.00|52.00|2122",
    "Stellarvue|EOP-03.6|3.60": "Stellarvue|EOP-03.6|3.60|110.00|890",
    "Stellarvue|EOP-04.7|4.70": "Stellarvue|EOP-04.7|4.70|110.00|889",
    "Stellarvue|EOP-09.0|9.00": "Stellarvue|EOP-09.0|9.00|100.00|891",
    "Stellarvue|EOP-13.5|13.50": "Stellarvue|EOP-13.5|13.50|100.00|892",
    "Stellarvue|EOP-20.0|20.00": "Stellarvue|EOP-20.0|20.00|100.00|893",
    "Stellarvue|EUW-04.0|4.00": "Stellarvue|EUW-04.0|4.00|82.00|894",
    "Stellarvue|EUW-08.0|8.00": "Stellarvue|EUW-08.0|8.00|82.00|896",
    "Stellarvue|EUW-15.0|15.00": "Stellarvue|EUW-15.0|15.00|82.00|895",
    "Takahashi|Abbe|4.00": "Takahashi|Abbe|4.00|44.00|601",
    "Takahashi|Abbe|6.00": "Takahashi|Abbe|6.00|44.00|602",
    "Takahashi|Abbe|9.00": "Takahashi|Abbe|9.00|44.00|603",
    "Takahashi|Abbe|12.50": "Takahashi|Abbe|12.50|44.00|604",
    "Takahashi|Abbe|18.00": "Takahashi|Abbe|18.00|44.00|605",
    "Takahashi|Abbe|25.00": "Takahashi|Abbe|25.00|44.00|606",
    "Takahashi|Abbe|32.00": "Takahashi|Abbe|32.00|44.00|607",
    "Takahashi|LE|5.00": "Takahashi|LE|5.00|52.00|617",
    "Takahashi|LE|7.50": "Takahashi|LE|7.50|52.00|618",
    "Takahashi|LE|10.00": "Takahashi|LE|10.00|52.00|619",
    "Takahashi|LE|12.50": "Takahashi|LE|12.50|52.00|620",
    "Takahashi|LE|18.00": "Takahashi|LE|18.00|52.00|621",
    "Takahashi|LE|24.00": "Takahashi|LE|24.00|52.00|622",
    "Takahashi|LE|30.00": "Takahashi|LE|30.00|52.00|623",
    "Takahashi|LE|40.00": "Takahashi|LE|40.00|52.00|624",
    "Takahashi|LE|50.00": "Takahashi|LE|50.00|52.00|625",
    "Takahashi|TOE|2.50": "Takahashi|TOE|2.50|52.00|626",
    "Takahashi|TOE|3.30": "Takahashi|TOE|3.30|52.00|627",
    "Takahashi|TOE|4.00": "Takahashi|TOE|4.00|52.00|628",
    "Tele Vue|Apollo 11|11.00": "Tele Vue|Apollo 11|11.00|85.00|1113",
    "Tele Vue|Delite|3.00": "Tele Vue|Delite|3.00|62.00|686",
    "Tele Vue|Delite|4.00": "Tele Vue|Delite|4.00|62.00|687",
    "Tele Vue|Delite|5.00": "Tele Vue|Delite|5.00|62.00|293",
    "Tele Vue|Delite|7.00": "Tele Vue|Delite|7.00|62.00|292",
    "Tele Vue|Delite|9.00": "Tele Vue|Delite|9.00|62.00|274",
    "Tele Vue|Delite|9.00": "Tele Vue|Delite|9.00|62.00|275",
    "Tele Vue|Delite|11.00": "Tele Vue|Delite|11.00|62.00|205",
    "Tele Vue|Delite|13.00": "Tele Vue|Delite|13.00|62.00|688",
    "Tele Vue|Delite|15.00": "Tele Vue|Delite|15.00|62.00|280",
    "Tele Vue|Delite|18.20": "Tele Vue|Delite|18.20|62.00|226",
    "Tele Vue|Delos|3.50": "Tele Vue|Delos|3.50|72.00|639",
    "Tele Vue|Delos|4.50": "Tele Vue|Delos|4.50|72.00|367",
    "Tele Vue|Delos|6.00": "Tele Vue|Delos|6.00|72.00|276",
    "Tele Vue|Delos|8.00": "Tele Vue|Delos|8.00|72.00|97",
    "Tele Vue|Delos|10.00": "Tele Vue|Delos|10.00|72.00|11",
    "Tele Vue|Delos|12.00": "Tele Vue|Delos|12.00|72.00|170",
    "Tele Vue|Delos|14.00": "Tele Vue|Delos|14.00|72.00|12",
    "Tele Vue|Delos|17.30": "Tele Vue|Delos|17.30|72.00|273",
    "Tele Vue|Ethos|3.70": "Tele Vue|Ethos|3.70|110.00|138",
    "Tele Vue|Ethos|4.70": "Tele Vue|Ethos|4.70|110.00|238",
    "Tele Vue|Ethos|6.00": "Tele Vue|Ethos|6.00|100.00|140",
    "Tele Vue|Ethos|8.00": "Tele Vue|Ethos|8.00|100.00|37",
    "Tele Vue|Ethos|10.00": "Tele Vue|Ethos|10.00|100.00|300",
    "Tele Vue|Ethos|13.00": "Tele Vue|Ethos|13.00|100.00|14",
    "Tele Vue|Ethos|17.00": "Tele Vue|Ethos|17.00|100.00|119",
    "Tele Vue|Ethos|21.00": "Tele Vue|Ethos|21.00|100.00|36",
    "Tele Vue|Nagler|26.00": "Tele Vue|Nagler|26.00|82.00|168",
    "Tele Vue|Nagler T-5|11.00": "Tele Vue|Nagler T-5|11.00|82.00|139",
    "Tele Vue|Nagler T-5|20.00": "Tele Vue|Nagler T-5|20.00|82.00|221",
    "Tele Vue|Nagler T-5|26.00": "Tele Vue|Nagler T-5|26.00|82.00|237",
    "Tele Vue|Nagler T-5|31.00": "Tele Vue|Nagler T-5|31.00|82.00|123",
    "Tele Vue|Nagler T-6|2.50": "Tele Vue|Nagler T-6|2.50|82.00|236",
    "Tele Vue|Nagler T-6|3.50": "Tele Vue|Nagler T-6|3.50|82.00|217",
    "Tele Vue|Nagler T-6|5.00": "Tele Vue|Nagler T-6|5.00|82.00|218",
    "Tele Vue|Nagler T-6|7.00": "Tele Vue|Nagler T-6|7.00|82.00|186",
    "Tele Vue|Nagler T-6|7.00": "Tele Vue|Nagler T-6|7.00|82.00|219",
    "Tele Vue|Nagler T-6|9.00": "Tele Vue|Nagler T-6|9.00|82.00|220",
    "Tele Vue|Nagler T-6|11.00": "Tele Vue|Nagler T-6|11.00|82.00|235",
    "Tele Vue|Nagler T-6|13.00": "Tele Vue|Nagler T-6|13.00|82.00|216",
    "Tele Vue|Nagler T4|12.00": "Tele Vue|Nagler T4|12.00|82.00|291",
    "Tele Vue|Nagler T4|17.00": "Tele Vue|Nagler T4|17.00|82.00|10",
    "Tele Vue|Nagler T4|22.00": "Tele Vue|Nagler T4|22.00|82.00|338",
    "Tele Vue|Nagler T5|16.00": "Tele Vue|Nagler T5|16.00|82.00|333",
    "Tele Vue|Nagler Zoom|3.00": "Tele Vue|Nagler Zoom|3.00|50.00|689",
    "Tele Vue|Nagler Zoom|4.00": "Tele Vue|Nagler Zoom|4.00|50.00|690",
    "Tele Vue|Nagler Zoom|5.00": "Tele Vue|Nagler Zoom|5.00|50.00|691",
    "Tele Vue|Nagler Zoom|6.00": "Tele Vue|Nagler Zoom|6.00|50.00|692",
    "Tele Vue|Panoptic|15.00": "Tele Vue|Panoptic|15.00|68.00|234",
    "Tele Vue|Panoptic|19.00": "Tele Vue|Panoptic|19.00|68.00|222",
    "Tele Vue|Panoptic|24.00": "Tele Vue|Panoptic|24.00|68.00|232",
    "Tele Vue|Panoptic|27.00": "Tele Vue|Panoptic|27.00|68.00|233",
    "Tele Vue|Panoptic|35.00": "Tele Vue|Panoptic|35.00|68.00|223",
    "Tele Vue|Panoptic|41.00": "Tele Vue|Panoptic|41.00|68.00|227",
    "Tele Vue|Plössl|8.00": "Tele Vue|Plössl|8.00|50.00|330",
    "Tele Vue|Plössl|11.00": "Tele Vue|Plössl|11.00|50.00|329",
    "Tele Vue|Plössl|15.00": "Tele Vue|Plössl|15.00|50.00|501",
    "Tele Vue|Plössl|20.00": "Tele Vue|Plössl|20.00|50.00|328",
    "Tele Vue|Plössl|25.00": "Tele Vue|Plössl|25.00|50.00|327",
    "Tele Vue|Plössl|32.00": "Tele Vue|Plössl|32.00|50.00|326",
    "Tele Vue|Plössl|40.00": "Tele Vue|Plössl|40.00|43.00|325",
    "Tele Vue|Plössl|55.00": "Tele Vue|Plössl|55.00|50.00|641",
    "Tele Vue|Radian|10.00": "Tele Vue|Radian|10.00|60.00|184",
    "Tele Vue|Radian|14.00": "Tele Vue|Radian|14.00|60.00|19",
    "TS|NED|12.00": "TS|NED|12.00|68.00|193",
    "TS|NED|18.00": "TS|NED|18.00|68.00|192",
    "TS Optics|Planetary HR|5.00": "TS Optics|Planetary HR|5.00|58.00|307",
    'TS Optics|Superview 40mm 1.25";|40.00': 'TS Optics|Superview 40mm 1.25";|40.00|46.00|199">TS Optics - Superview 40mm 1.25',
    "Vixen|HR|1.60": "Vixen|HR|1.60|42.00|304",
    "Vixen|HR|2.00": "Vixen|HR|2.00|42.00|305",
    "Vixen|HR|2.40": "Vixen|HR|2.40|42.00|306",
    "Vixen|HR|3.40": "Vixen|HR|3.40|42.00|629",
    "Vixen|LVW|3.50": "Vixen|LVW|3.50|65.00|75",
    "Vixen|LVW|5.00": "Vixen|LVW|5.00|65.00|76",
    "Vixen|LVW|8.00": "Vixen|LVW|8.00|65.00|77",
    "Vixen|LVW|13.00": "Vixen|LVW|13.00|65.00|78",
    "Vixen|LVW|17.00": "Vixen|LVW|17.00|65.00|79",
    "Vixen|LVW|22.00": "Vixen|LVW|22.00|65.00|80",
    "Vixen|LVW|30.00": "Vixen|LVW|30.00|65.00|81",
    "Vixen|LVW|42.00": "Vixen|LVW|42.00|65.00|82",
    "Vixen|NPL (Plossl)|4.00": "Vixen|NPL (Plossl)|4.00|50.00|58",
    "Vixen|NPL (Plossl)|6.00": "Vixen|NPL (Plossl)|6.00|50.00|59",
    "Vixen|NPL (Plossl)|8.00": "Vixen|NPL (Plossl)|8.00|50.00|66",
    "Vixen|NPL (Plossl)|10.00": "Vixen|NPL (Plossl)|10.00|50.00|60",
    "Vixen|NPL (Plossl)|15.00": "Vixen|NPL (Plossl)|15.00|50.00|61",
    "Vixen|NPL (Plossl)|20.00": "Vixen|NPL (Plossl)|20.00|50.00|62",
    "Vixen|NPL (Plossl)|25.00": "Vixen|NPL (Plossl)|25.00|50.00|63",
    "Vixen|NPL (Plossl)|30.00": "Vixen|NPL (Plossl)|30.00|50.00|64",
    "Vixen|NPL (Plossl)|40.00": "Vixen|NPL (Plossl)|40.00|40.00|65",
    "Vixen|SLV|2.50": "Vixen|SLV|2.50|50.00|39",
    "Vixen|SLV|4.00": "Vixen|SLV|4.00|50.00|40",
    "Vixen|SLV|5.00": "Vixen|SLV|5.00|50.00|46",
    "Vixen|SLV|6.00": "Vixen|SLV|6.00|50.00|41",
    "Vixen|SLV|9.00": "Vixen|SLV|9.00|50.00|42",
    "Vixen|SLV|10.00": "Vixen|SLV|10.00|50.00|47",
    "Vixen|SLV|12.00": "Vixen|SLV|12.00|50.00|43",
    "Vixen|SLV|15.00": "Vixen|SLV|15.00|50.00|48",
    "Vixen|SLV|20.00": "Vixen|SLV|20.00|50.00|49",
    "Vixen|SLV|25.00": "Vixen|SLV|25.00|50.00|44",
    "Vixen|SSW|3.50": "Vixen|SSW|3.50|83.00|173",
    "Vixen|SSW|5.00": "Vixen|SSW|5.00|83.00|174",
    "Vixen|SSW|7.00": "Vixen|SSW|7.00|83.00|175",
    "Vixen|SSW|10.00": "Vixen|SSW|10.00|83.00|176",
    "Vixen|SSW|14.00": "Vixen|SSW|14.00|83.00|177",
    "William Optics|SPL|3.00": "William Optics|SPL|3.00|55.00|194",
    "William Optics|SPL|6.00": "William Optics|SPL|6.00|55.00|195",
    "William Optics|SPL|12.50": "William Optics|SPL|12.50|55.00|118",
    "William Optics|SWAN|9.00": "William Optics|SWAN|9.00|72.00|90",
    "William Optics|SWAN|15.00": "William Optics|SWAN|15.00|72.00|91",
    "William Optics|UWAN|16.00": "William Optics|UWAN|16.00|82.00|112",
    "William Optics|UWAN|28.00": "William Optics|UWAN|28.00|82.00|45",
    "William Optics|UWAN|28.00": "William Optics|UWAN|28.00|82.00|211",
    "Williams optics|SPL|6.00": "Williams optics|SPL|6.00|55.00|137",
    "Williams Optics|SWAN|40.00": "Williams Optics|SWAN|40.00|70.00|95",
    "Williams Optics|UWAN|4.00": "Williams Optics|UWAN|4.00|82.00|94",
}
