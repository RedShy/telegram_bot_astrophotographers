from telegram import (
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Bot,
    replykeyboardmarkup,
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
from statistics_log import save_user_interaction
from utility import *

id_messages = {
    "Giove": 12,
    "Marte": 14,
    "Luna": 13,
    "Nebulosa Manubrio": 15,
    "Saturno": 16,
}


def exercises_files_command(update: Update, context: CallbackContext) -> int:
    save_user_interaction(update.message.text, user=update.message.from_user)

    keyboard = [
        ["File Giove", "File Marte"],
        ["File Luna", "File Nebulosa Manubrio"],
        ["File Saturno", back_button_name],
    ]

    update.message.reply_text(
        "Quale file vuoi scaricare?", reply_markup=ReplyKeyboardMarkup(keyboard)
    )


def forward_files_command(update: Update, context: CallbackContext) -> int:
    # prendi l'id del messaggio da inoltrare
    id_message = id_messages[context.match.group(1)]

    # prendi l'id della chat da cui prendere il messaggio da inoltrare
    source_chat_id = ""

    # prendi la chat_id dove inoltrare il messaggio
    target_chat_id = update.message.chat_id

    bot = context.bot
    bot.forward_message(
        from_chat_id=source_chat_id, message_id=id_message, chat_id=target_chat_id
    )

    reply_message = "A tuo supporto trovi, ovviamente, anche tutti i video tutorial che ho pubblicato sul <b>canale YouTube:</b>\n"
    reply_message += "• TUTORIAL | Elaborazione planetaria con PIPP, AUTOSTAKKERT e REGISTAX: https://youtu.be/U3_o3q846Aw\n"
    reply_message += "• TUTORIAL | Elaborazione dati con DEEP SKY STACKER: https://youtu.be/jf4pqQ7v4y0\n"
    reply_message += "• TUTORIAL | Elaborazione dati con PIXINSIGHT: https://youtu.be/NUVbcQxOxnE\n\n"
    reply_message += "Ti basterà installare <b>Telegram</b> sul tuo <b>PC</b> ed il gioco sarà fatto. <b>Tasto destro</b> sul file, <b>salva</b> 👨‍💻\n"
    reply_message += "• Se non sai come installare Telegram sul tuo pc puoi seguire la seguente guida: https://www.aranzulla.it/come-installare-telegram-su-pc-1136335.html\n"
    reply_message += "• Trovi i file compressi ed in formato .7z, per poterli usare devi estrarli utilizzando il software\n7-Zip: https://www.7-zip.org/download.html\n"
    reply_message += "• Qui invece trovi la guida che ti spiega come estrarre i file: https://www.aranzulla.it/come-aprire-i-file-7z-19036.html"

    update.message.reply_text(
        text=reply_message, parse_mode="HTML", disable_web_page_preview=True
    )


def add_exercises_files_handlers(dispatcher):
    dispatcher.add_handler(
        MessageHandler(
            Filters.regex(f"^{exercises_files_button_name}$"), exercises_files_command
        )
    )

    dispatcher.add_handler(
        MessageHandler(Filters.regex(f"^File (Giove)$"), forward_files_command)
    )

    dispatcher.add_handler(
        MessageHandler(Filters.regex(f"^File (Marte)$"), forward_files_command)
    )

    dispatcher.add_handler(
        MessageHandler(Filters.regex(f"^File (Luna)$"), forward_files_command)
    )

    dispatcher.add_handler(
        MessageHandler(
            Filters.regex(f"^File (Nebulosa Manubrio)$"), forward_files_command
        )
    )

    dispatcher.add_handler(
        MessageHandler(Filters.regex(f"^File (Saturno)$"), forward_files_command)
    )
