from telegram import (
    Update,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    MessageHandler,
    CallbackContext,
    Filters,
)
from constants import *
from faq_pixinsight import *
from statistics_log import *


def pixinsight_command(update: Update, context: CallbackContext) -> None:
    save_user_interaction(update.message.text, user=update.message.from_user)

    questions = list(faq_pixinsight.keys())

    keyboard = [
        [questions[0], questions[1], questions[2],],
        [questions[3], questions[4], back_button_name,],
    ]

    reply_markup = ReplyKeyboardMarkup(keyboard)

    update.message.reply_text("Scegli quale FAQ avviare", reply_markup=reply_markup)


def faq_pixinsight_command(update: Update, context: CallbackContext) -> None:
    question = context.matches[0].group(1)
    answer = faq_pixinsight[question]

    update.message.reply_text(f"<b>{question}</b>\n{answer}", parse_mode="HTML")


def add_pixinsight_handlers(dispatcher):
    dispatcher.add_handler(
        MessageHandler(
            Filters.regex(f"^{faq_pixinsight_button_name}$"), pixinsight_command
        )
    )

    questions = list(faq_pixinsight.keys())
    for i, q in enumerate(questions):
        questions[i] = q.replace("?", "\?")

    dispatcher.add_handler(
        MessageHandler(
            Filters.regex(
                f"({questions[0]}|{questions[1]}|{questions[2]}|{questions[3]}|{questions[4]})"
            ),
            faq_pixinsight_command,
        )
    )

