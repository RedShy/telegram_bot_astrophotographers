import logging

from telegram import (
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    CallbackContext,
    Filters,
)
import sys
import random
import os
from traceback import format_exc

sys.path.insert(0, "./catalogo")
from constants import *
from messier import *
from campionamento import *
from pixinsight import *
from meteoblue import *
from feedback import *
from shoot_timing import *
from polar import *
from iss import *
from recommended_software import *
from datetime import datetime
from targets_month import *
from statistics_log import *
from astronomy_tools import *
from exercises_files import *
import calendar
import traceback
import threading

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


def first_start(update: Update, context: CallbackContext) -> int:
    save_user_interaction(update.message.text, user=update.message.from_user)

    main_menu(update, context)


def main_menu(update: Update, context: CallbackContext) -> int:
    update.message.reply_text(
        "Scegli un'opzione:", reply_markup=ReplyKeyboardMarkup(main_menu_keyboard)
    )


def other(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [iss_button_name, community_button_name],
        [recommended_software_button_name, messier_button_name],
        [astronomy_tools_button_name, prints_astropic_button_name],
        [back_button_name, "In via di sviluppo 🔜"],
    ]

    update.message.reply_text(
        other_button_name, reply_markup=ReplyKeyboardMarkup(keyboard)
    )


def messier_command(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        f"""Sono presenti {len(messier)} oggetti nel catalogo. Cosa vuoi vedere?
        /messier - Aggiungi il numero per ottenere l'oggetto singolo dal catalogo
        /messier_rand - Mostra un oggetto casuale"""
    )


def messier_show(update: Update, messier_object):
    name = messier_object[0]
    description = messier_object[1]
    link = messier_object[2]

    update.message.reply_text(f'<a href="{link}"><b>{name}</b></a>', parse_mode="HTML")
    update.message.reply_text(f"{description}")


def messier_random_command(update: Update, context: CallbackContext) -> None:
    # scegli casualmente un numero tra quelli dell'array
    messier_object = random.choice(messier)

    messier_show(update, messier_object)


def messier_single_command(update: Update, context: CallbackContext) -> None:
    try:
        index = context.args[0]
    except:
        update.message.reply_text(
            "Inserisci il numero dell'oggetto Messier da visualizzare"
        )
        return

    # prova a convertire il numero dato in indice
    try:
        index = int(index) - 1
        if index < 0 or index > len(messier):
            raise Exception("Oggetto Messier fuori range")
    except:
        update.message.reply_text(f"Oggetto {context.args[0]} non trovato")
        return

    messier_object = messier[index]

    messier_show(update, messier_object)

    # update.message.reply_text(f"{name}\n{description}\n{link}")


def youtube_command(update: Update, context: CallbackContext) -> None:
    save_user_interaction(update.message.text, user=update.message.from_user)

    with open("./resources/images/sigla_youtube.jpg", "rb") as photo:
        update.message.reply_photo(
            photo=photo,
            caption="Se sei appassionato di astronomia e astrofotografia vieni subito a far parte di AstroPic 🚀🚀🚀\nIscriviti al canale YouTube 😃\nhttps://www.youtube.com/channel/UCJppF2HEzMj5CIZKa_J9Mww?sub_confirmation=1",
        )

    # update.message.reply_sticker(sticker=astroPic_sticker)


def telegram_channel_command(update: Update, context: CallbackContext) -> None:
    save_user_interaction(update.message.text, user=update.message.from_user)

    with open("./resources/images/foto_canale_telegram.jpg", "rb") as photo:
        update.message.reply_photo(
            photo=photo,
            caption="Unisciti al canale Telegram di AstroPic per rimanere sempre aggiornato riguardo l'attrezzatura consigliata, l'attrezzatura in offerta, i gadget a tema astronomia/astrofotografia e molto altro 🚀🚀🚀\nhttps://t.me/AstropicCanale",
        )


target_month_lock = threading.Lock()


def target_month_command(update: Update, context: CallbackContext) -> None:
    def show_month(update: Update, targets):
        random.shuffle(targets)
        for target in targets:
            # Nome::Costellazione::Magnitudine::Sensore::Focale::Foto
            name = target[0]
            costellation = target[1]
            magnitude = target[2]
            sensor = target[3]
            focal = target[4]
            photo = target[5]

            result = ""
            result += f'<a href="{photo}"><b>{name} - {costellation}</b></a>\n'
            result += f"<b>Magnitudine:</b> {magnitude}\n"
            result += (
                f"Attrezzatura consigliata (il sensore è quello utilizzato da me)\n"
            )
            result += f"<b>Sensore:</b> {sensor}\n"
            result += f"<b>Focale:</b> {focal}\n\n"
            update.message.reply_text(result, parse_mode="HTML")

    save_user_interaction(update.message.text, user=update.message.from_user)

    # prendi il mese corrente
    month = calendar.month_name[datetime.utcnow().month].lower()

    # prendi i target del mese
    target_month_lock.acquire()
    targets = targets_month.get(month, None).copy()
    target_month_lock.release()

    # se nessun target è presente, comunica errore
    if targets is None:
        write_on_error_log(
            update.message.from_user,
            "ERRORE in target del mese",
            f"Nessun target per il mese di {month}",
            "None",
        )
        update.message.reply_text(
            f"Non ci sono targets per il mese di {italian_months_by_index[datetime.utcnow().month]}"
        )
        update.message.reply_sticker(sticker=error_sticker)
        return

    # elabora il mese
    show_month(update, targets)


def community_command(update: Update, context: CallbackContext) -> None:
    save_user_interaction(update.message.text, user=update.message.from_user)

    update.message.reply_text(
        "Attraverso questo link puoi far parte della community Telegram di AstroPic 😃\nQui troverai tanti astrofotografi di tutti i livelli che ti potranno senz'altro essere di aiuto 🚀🚀🚀"
    )
    update.message.reply_text("https://t.me/AstroPicCommunity")
    update.message.reply_sticker(sticker=community_sticker)


def prints_astropic_command(update: Update, context: CallbackContext) -> None:
    save_user_interaction(update.message.text, user=update.message.from_user)

    reply_message = "Esplora il negozio di AstroPic all'interno del quale puoi acquistare fantastiche stampe astronomiche applicate su molteplici supporti! Hai a tua completa disposizione:\n"
    reply_message += "- Poster (con diverse finiture)\n"
    reply_message += "- Tela\n"
    reply_message += "- T-Shirt\n"
    reply_message += "- Cover per smartphone\n"
    reply_message += "- Stampe metallizzate\n"
    reply_message += "- E molto, molto altro 🚀\n"
    reply_message += "https://www.redbubble.com/people/AstroPic-Store/shop?asc=u&ref=account-nav-dropdown"

    update.message.reply_text(
        text=reply_message, parse_mode="HTML", disable_web_page_preview=True
    )


def print_id_sticker(update: Update, context: CallbackContext) -> None:
    print("ricevuto sticker")
    print(update.message.sticker.file_id)
    update.message.reply_text(update.message.sticker.file_id)


def print_id_animation(update: Update, context: CallbackContext) -> None:
    print("ricevuto sticker")
    print(update.message.animation.file_id)
    update.message.reply_text(update.message.animation.file_id)


def print_id_document(update: Update, context: CallbackContext) -> None:
    # metodo utile per prendere l'id di un channel:
    # 1 manda un messaggio nel channel
    # 2 inoltra quel messaggio del channel al bot
    # 3 fai stampare al bot update.message.forward_from_chat.id per ottenere l'id del channel
    update.message.reply_text(update.message.document.file_id)
    update.message.reply_text(update.message.forward_from_message_id)
    update.message.reply_text(update.message.forward_from_chat.id)


def handle_error(update: Update, context: CallbackContext) -> None:
    write_on_error_log(
        None,
        "ERRORE GENERICO DELL'ERROR HANDLER",
        context.error,
        traceback.format_exc(),
    )


def main() -> None:
    updater = Updater(token=token, workers=num_threads_asynchronous_tasks)

    updater.dispatcher.add_handler(CommandHandler("start", first_start))

    updater.dispatcher.add_handler(
        MessageHandler(Filters.regex(f"^{messier_button_name}$"), messier_command)
    )

    updater.dispatcher.add_handler(
        CommandHandler("messier_rand", messier_random_command)
    )
    updater.dispatcher.add_handler(CommandHandler("messier", messier_single_command))

    updater.dispatcher.add_handler(
        MessageHandler(Filters.regex(f"^{astropic_button_name}$"), youtube_command)
    )

    updater.dispatcher.add_handler(
        MessageHandler(Filters.regex(f"^{community_button_name}$"), community_command)
    )

    updater.dispatcher.add_handler(
        MessageHandler(
            Filters.regex(f"^{prints_astropic_button_name}$"), prints_astropic_command
        )
    )

    updater.dispatcher.add_handler(
        MessageHandler(
            Filters.regex(f"^{suggested_setup_button_name}$"), telegram_channel_command
        )
    )

    updater.dispatcher.add_handler(
        MessageHandler(
            Filters.regex(f"^{targets_month_button_name}$"),
            target_month_command,
            run_async=True,
        )
    )

    updater.dispatcher.add_handler(
        MessageHandler(Filters.regex(f"^{other_button_name}$"), other)
    )

    # CAMPIONAMENTO
    add_campionamento_handlers(updater.dispatcher)

    # PIXINSIGHT
    add_pixinsight_handlers(updater.dispatcher)

    # METEOBLUE
    add_meteoblue_handlers(updater.dispatcher)

    # FEEDBACK
    add_feedback_handlers(updater.dispatcher)

    # SHOOT TIMING
    add_shoot_timing_handlers(updater.dispatcher)

    # POLARE
    add_polar_handlers(updater.dispatcher)

    # ISS
    add_iss_handlers(updater.dispatcher)

    # RECOMMENDED SOFTWARE
    add_recommended_software_handlers(updater.dispatcher)

    # ASTRONOMY TOOLS
    add_astronomy_tools_handlers(updater.dispatcher)

    # FILE ESERCITAZIONE
    add_exercises_files_handlers(updater.dispatcher)

    updater.dispatcher.add_handler(
        MessageHandler(Filters.regex(f"^{back_button_name}"), main_menu)
    )

    updater.dispatcher.add_error_handler(handle_error)

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
