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
import traceback
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
import traceback


class Iss_data:
    def __init__(self, raw_date, duration, highest_point, rise, end):
        self.raw_date = raw_date
        self.duration = duration
        self.highest_point = highest_point
        self.rise = rise
        self.end = end

        self.timerise_sunset_highestpoint()

    def timerise_sunset_highestpoint(self):
        time_rise_str = re.search("\d?\d:\d\d \w\w", self.raw_date).group(0)
        duration_minutes = re.search("\d+", self.duration).group(0)

        self.time_rise = datetime.now(tz=italy_tz).replace(
            hour=datetime.strptime(time_rise_str, "%I:%M %p").hour,
            minute=datetime.strptime(time_rise_str, "%I:%M %p").minute,
            second=0,
            microsecond=0,
        )

        self.time_highestpoint = self.time_rise + timedelta(
            minutes=int(duration_minutes) / 2
        )
        self.time_sunset = self.time_rise + timedelta(minutes=int(duration_minutes))

    def is_before_current_time(self):
        difference = self.time_sunset - datetime.now(tz=italy_tz)
        return difference.total_seconds() > 0

    def stampa(self):
        print(self.raw_date)
        print(self.duration)
        print(self.highest_point)
        print(self.rise)
        print(self.end)
        print(self.time_rise)
        print(self.time_highestpoint)
        print(self.time_sunset)
        print()

    def rise_str_time_without_seconds(self):
        return re.sub(r"(\d\d:\d\d):00", r"\1", str(self.time_rise.time()))


def iss_welcome(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        "Inviami /iss località per ricevere informazioni sul passaggio della ISS 😃"
    )


def request_visible_iss_data(city: str):
    if city == "canosa_di_puglia":
        city = "Canosa_di_Puglia"
    elif city == "reggio_di_calabria":
        city = "Reggio_Calabria"
    elif city == "reggio_emilia":
        city = "Reggio_Emilia"
    elif city == "aquila":
        city = "L_Aquila"
    else:
        city = city.capitalize()

    page = requests.get(
        f"https://spotthestation.nasa.gov/sightings/view.cfm?country=Italy&region=None&city={city}"
    )
    tree = html.fromstring(page.text)
    today_date = (
        calendar.month_abbr[datetime.utcnow().month] + f" {datetime.utcnow().day}"
    )

    list_iss_data = list()
    trs = tree.xpath(f"//tr[td[contains(.,'{today_date}')]]")
    for tr in trs:
        iss_data = Iss_data(
            raw_date=tr[0].text,
            duration=tr[1].text.replace("< ", ""),
            highest_point=tr[2].text,
            rise=tr[3].text.replace(" above ", ""),
            end=tr[4].text.replace(" above ", ""),
        )
        if iss_data.is_before_current_time():
            list_iss_data.append(iss_data)

    return list_iss_data


def nearest_website_city(lat, lon):
    nearest_city = "Catanzaro"
    min_distance = -1

    # vado a vedere tutte le città del website
    for city in website_cities:
        coords_1 = (website_cities[city]["lat"], website_cities[city]["long"])
        distance = geopy.distance.geodesic(coords_1, (lat, lon)).km
        if min_distance == -1 or distance < min_distance:
            min_distance = distance
            nearest_city = city

    # prendo la città più vicina
    return nearest_city


def iss_command(update: Update, context: CallbackContext) -> None:
    save_user_interaction(update.message.text, user=update.message.from_user)

    try:
        city = context.matches[0].group(1).lower().replace(" ", "_").replace("-", "_")
        website_city = nearest_website_city(
            longlats[city]["lat"], longlats[city]["long"]
        )
    except Exception as e:
        write_on_error_log(
            update.message.from_user,
            "ERRORE in iss command, ",
            e,
            traceback.format_exc(),
        )
        update.message.reply_text("Località non trovata")
        update.message.reply_sticker(sticker=error_sticker)
        return

    update.message.reply_text("Ricerca dei passaggi per oggi in corso...")

    try:
        list_iss_data = request_visible_iss_data(website_city)
        if len(list_iss_data) == 0:
            raise Exception("Nessun passaggio")
    except Exception as e:
        write_on_error_log(
            update.message.from_user, "ERRORE in ISS", e, traceback.format_exc(),
        )

        update.message.reply_text(
            "Dalla località da te impostata, purtroppo oggi la ISS non è visibile"
        )
        update.message.reply_sticker(sticker=iss_sleep_sticker)
        return

    italian_month = italian_months_by_index[datetime.utcnow().month]
    italian_weekday = italian_weekdays_by_index[datetime.utcnow().weekday()]
    date_italian = f"{italian_weekday} {datetime.utcnow().day} {italian_month}"

    update.message.reply_text(
        f'<a href="https://cdn.mos.cms.futurecdn.net/fKZ2vtNGzTxa93C7KfaeRh.jpg">{date_italian}</a>',
        parse_mode="HTML",
    )
    # ordina i passaggi in base all'orario
    list_iss_data.sort(
        key=lambda iss_passage: (
            iss_passage.time_rise - datetime.now().astimezone()
        ).total_seconds()
    )
    for iss_data in list_iss_data:
        update.message.reply_text(
            f'Durata: <b>{iss_data.duration}</b>\nSorge: <b>{iss_data. rise_str_time_without_seconds()} - {iss_data.rise}</b>\nPunto più alto: <b>{str(iss_data.time_highestpoint.time()).replace(":00","").replace(":30","")} - {iss_data.highest_point}</b>\nTramonta: <b>{str(iss_data.time_sunset.time()).replace(":00","")} - {iss_data.end}</b>',
            parse_mode="HTML",
        )


def add_iss_handlers(dispatcher):
    dispatcher.add_handler(
        MessageHandler(Filters.regex(f"^{iss_button_name}$"), iss_welcome)
    )

    # ESECUZIONE IN MULTITHREAD
    dispatcher.add_handler(
        MessageHandler(Filters.regex(f"^/iss (.*)$"), iss_command, run_async=True)
    )


def prova():
    with open("websitecities.py", "w", encoding="utf-8") as outfile, open(
        "website.txt", "r", encoding="utf8"
    ) as file:
        lines = file.readlines()
        for line in lines:
            city = line.replace(" ", "_").lower().strip()

            print(city)

            lat = longlats[city]["lat"]
            lon = longlats[city]["long"]

            print(f'"{city}":' + "{" + f'"lat":{lat},"long":{lon}' + "}")
            outfile.write(f'"{city}":' + "{" + f'"lat":{lat},"long":{lon}' + "}\n")

