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
from constants import *
from bot import main_menu

from lxml import html
import requests

from bs4 import BeautifulSoup

from statistics_log import *


sun_button_name = "Sole"
mercury_button_name = "Mercurio"
venus_button_name = "Venere"
moon_button_name = "Luna"
mars_button_name = "Marte"
jupiter_button_name = "Giove"
saturn_button_name = "Saturno"
uranus_button_name = "Urano"
neptune_button_name = "Nettuno"


DIAMETER, SOLAR_SYSTEM = range(2)


def shoot_timing_entry_conversation(update: Update, context: CallbackContext) -> int:
    save_user_interaction(update.message.text, user=update.message.from_user)

    update.message.reply_text(
        "Inviami il diametro del tuo telescopio espresso in mm\nEsempio 20 cm = 200 mm"
    )

    return DIAMETER


def shoot_timing_error(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("Diametro non riconosciuto")
    update.message.reply_sticker(sticker=error_sticker)
    return ConversationHandler.END


def shoot_timing_receive_diameter(update: Update, context: CallbackContext) -> int:
    try:
        diameter = float(update.message.text.replace("m", "").replace(" ", ""))
        if diameter <= 0:
            return shoot_timing_error(update, context)
    except:
        return shoot_timing_error(update, context)

    resolution = 115 / diameter
    context.user_data["resolution"] = resolution

    keyboard = [
        [sun_button_name, mercury_button_name],
        [venus_button_name, moon_button_name],
        [mars_button_name, jupiter_button_name],
        [saturn_button_name, uranus_button_name],
        [neptune_button_name, back_button_name],
    ]
    update.message.reply_text(
        "Okay! Ora scegli l'oggetto del sistema solare",
        reply_markup=ReplyKeyboardMarkup(keyboard),
    )

    return SOLAR_SYSTEM


def distance_from_planet(planet):
    page = requests.get(f"https://theskylive.com/how-far-is-{planet}")

    soup = BeautifulSoup(page.text)
    for div in soup.find_all("div", {"class": "keyinfobox"}):
        distance = div.ar.text.replace(",", "")
        break

    return int(distance)


def calculate_shoot_timing(distance_from_earth, data_planet, resolution_instrument):
    K = 7.72e-7
    rotation_time = data_planet["rotation"]
    radius_planet = data_planet["radius"]

    result = (
        K
        * (distance_from_earth * rotation_time * resolution_instrument)
        / radius_planet
    )

    return int(round(result, 0))


def message_shoot_timing(data_planet, shoot_timing_seconds):
    def seconds_2_hours_minutes_seconds(seconds):
        # prendo le ore
        hours, _ = divmod(seconds / 3600, 1)

        # prendo i minuti
        minutes, decimal_minutes = divmod(seconds / 60, 1)

        # prendo i secondi
        seconds_ = round(decimal_minutes * 60, 0)

        return (int(hours), int(minutes), int(seconds_))

    name = data_planet["italian"]
    message = f"Hai scelto {name}! Il tempo massimo di acquisizione dati è:\n"

    hours, minutes, seconds = seconds_2_hours_minutes_seconds(shoot_timing_seconds)

    hours_str = "ore"
    if hours == 1:
        hours_str = "ora"

    minutes_str = "minuti"
    if minutes == 1:
        minutes_str = "minuto"

    seconds_str = "secondi"
    if seconds == 1:
        seconds_str = "secondo"

    if shoot_timing_seconds <= 200:
        message += f"{shoot_timing_seconds} secondi"
    elif shoot_timing_seconds >= 3660:
        message += (
            f"{hours} {hours_str}, {minutes} {minutes_str} e {seconds} {seconds_str}"
        )
    else:
        message += f"{minutes} {minutes_str} e {seconds} {seconds_str}"

    return message


def planet_timing_command(update: Update, context: CallbackContext) -> int:
    button_name = update.message.text
    data_planet = planets_data[button_name]

    distance = distance_from_planet(data_planet["english"])
    resolution_instrument = context.user_data["resolution"]
    shoot_timing = calculate_shoot_timing(distance, data_planet, resolution_instrument)

    image_url = data_planet["image_url"]
    update.message.reply_text(
        f'<a href="{image_url}">{button_name}</a>', parse_mode="HTML"
    )
    update.message.reply_text(message_shoot_timing(data_planet, shoot_timing))

    update.message.reply_sticker(sticker=shoot_timing_sticker)

    # update.message.reply_text("Distanza: " + f"{distance:,}" + " km")

    return SOLAR_SYSTEM


def ignore(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("Scegli l'oggetto del sistema solare")

    return SOLAR_SYSTEM


def cancel_back(update: Update, context: CallbackContext) -> int:
    main_menu(update, context)

    context.user_data.clear()
    return ConversationHandler.END


def add_shoot_timing_handlers(dispatcher):
    conv_shoot_timing_handler = ConversationHandler(
        entry_points=[
            MessageHandler(
                Filters.regex(f"^{shoot_timing_button_name}$"),
                shoot_timing_entry_conversation,
            )
        ],
        states={
            DIAMETER: [
                MessageHandler(Filters.regex(f".*"), shoot_timing_receive_diameter,),
            ],
            SOLAR_SYSTEM: [
                MessageHandler(
                    Filters.regex(f"^{sun_button_name}$"),
                    planet_timing_command,
                    run_async=True,
                ),
                MessageHandler(
                    Filters.regex(f"^{mercury_button_name}$"),
                    planet_timing_command,
                    run_async=True,
                ),
                MessageHandler(
                    Filters.regex(f"^{venus_button_name}$"),
                    planet_timing_command,
                    run_async=True,
                ),
                MessageHandler(
                    Filters.regex(f"^{moon_button_name}$"),
                    planet_timing_command,
                    run_async=True,
                ),
                MessageHandler(
                    Filters.regex(f"^{mars_button_name}$"),
                    planet_timing_command,
                    run_async=True,
                ),
                MessageHandler(
                    Filters.regex(f"^{jupiter_button_name}$"),
                    planet_timing_command,
                    run_async=True,
                ),
                MessageHandler(
                    Filters.regex(f"^{saturn_button_name}$"),
                    planet_timing_command,
                    run_async=True,
                ),
                MessageHandler(
                    Filters.regex(f"^{uranus_button_name}$"),
                    planet_timing_command,
                    run_async=True,
                ),
                MessageHandler(
                    Filters.regex(f"^{neptune_button_name}$"),
                    planet_timing_command,
                    run_async=True,
                ),
                # MessageHandler(Filters.regex(f"{back_button_name}"), cancel_back),
                # MessageHandler(Filters.command, cancel_back),
                MessageHandler(Filters.regex(f".*"), cancel_back),
            ],
        },
        fallbacks=[MessageHandler(Filters.regex(f".*"), cancel_back),],
    )
    dispatcher.add_handler(conv_shoot_timing_handler)


planets_data = {
    sun_button_name: {
        "rotation": 2.33e6,
        "radius": 695000,
        "italian": "il Sole",
        "english": "sun",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b4/The_Sun_by_the_Atmospheric_Imaging_Assembly_of_NASA%27s_Solar_Dynamics_Observatory_-_20100819.jpg/520px-The_Sun_by_the_Atmospheric_Imaging_Assembly_of_NASA%27s_Solar_Dynamics_Observatory_-_20100819.jpg",
    },
    mercury_button_name: {
        "rotation": 5.06e6,
        "radius": 2440,
        "italian": "Mercurio",
        "english": "mercury",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/30/Mercury_in_color_-_Prockter07_centered.jpg/520px-Mercury_in_color_-_Prockter07_centered.jpg",
    },
    venus_button_name: {
        "rotation": 10.08e6,
        "radius": 6050,
        "italian": "Venere",
        "english": "venus",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/bc/Venuspioneeruv.jpg/520px-Venuspioneeruv.jpg",
    },
    moon_button_name: {
        "rotation": 2.55e6,
        "radius": 1737,
        "italian": "la Luna",
        "english": "moon",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e1/FullMoon2010.jpg/520px-FullMoon2010.jpg",
    },
    mars_button_name: {
        "rotation": 8.8e4,
        "radius": 3400,
        "italian": "Marte",
        "english": "mars",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/02/OSIRIS_Mars_true_color.jpg/520px-OSIRIS_Mars_true_color.jpg",
    },
    jupiter_button_name: {
        "rotation": 3.58e4,
        "radius": 69911,
        "italian": "Giove",
        "english": "jupiter",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2b/Jupiter_and_its_shrunken_Great_Red_Spot.jpg/520px-Jupiter_and_its_shrunken_Great_Red_Spot.jpg",
    },
    saturn_button_name: {
        "rotation": 3.85e4,
        "radius": 60270,
        "italian": "Saturno",
        "english": "saturn",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b4/Saturn_%28planet%29_large.jpg/387px-Saturn_%28planet%29_large.jpg",
    },
    uranus_button_name: {
        "rotation": 6.20e4,
        "radius": 25570,
        "italian": "Urano",
        "english": "uranus",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3d/Uranus2.jpg/520px-Uranus2.jpg",
    },
    neptune_button_name: {
        "rotation": 5.796e4,
        "radius": 24750,
        "italian": "Nettuno",
        "english": "neptune",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/63/Neptune_-_Voyager_2_%2829347980845%29_flatten_crop.jpg/520px-Neptune_-_Voyager_2_%2829347980845%29_flatten_crop.jpg",
    },
}
