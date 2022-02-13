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
)
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


def recommended_software_welcome(update: Update, context: CallbackContext) -> None:
    save_user_interaction(update.message.text, user=update.message.from_user)

    update.message.reply_text(
        "Qui ti suggerirò dei programmi molto validi che sono fra i più utilizzati da tutti gli astrofotografi del mondo.\nTroverai anche un video che ti spiegherà come utilizzare ogni programma!\nAh, sono tutti gratis 😃"
    )

    update.message.reply_text(
        "<b>Elaborazioni deep sky</b>\nProgramma: http://deepskystacker.free.fr/english/index.html\nTutorial: https://youtu.be/jf4pqQ7v4y0",
        disable_web_page_preview=True,
        parse_mode="HTML",
    )

    update.message.reply_text(
        "<b>Elaborazioni riprese planetarie</b>\nProgramma 1: https://sites.google.com/site/astropipp/downloads\nProgramma 2: https://www.autostakkert.com/wp/download/\nProgramma 3: http://www.astronomie.be/registax/download.html\nTutorial (include tutti e 3 i programmi appena citati): https://youtu.be/U3_o3q846Aw",
        disable_web_page_preview=True,
        parse_mode="HTML",
    )

    update.message.reply_text(
        "Programma 4: http://astrosurface.com/page-it.html\nTutorial: https://youtu.be/6YXt3bRbd8Q",
        disable_web_page_preview=True,
    )


def add_recommended_software_handlers(dispatcher):
    dispatcher.add_handler(
        MessageHandler(
            Filters.regex(f"^{recommended_software_button_name}$"),
            recommended_software_welcome,
        )
    )
