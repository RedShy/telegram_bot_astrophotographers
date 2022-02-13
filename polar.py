from telegram import Update
from telegram.ext import (
    MessageHandler,
    CallbackContext,
    Filters,
)
from utility import *
from constants import *
from longlats_cities import *
import datetime
from datetime import datetime, timedelta
from astropy.coordinates import EarthLocation
from astropy.time import Time
from astropy import units as u
import re
from lxml import html
import requests
import numpy as np

# import cv2
from PIL import Image
from statistics_log import *
import traceback


def polar_button_command(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        "Perfetto, ora ti aiuterò nell'allineare al polo la tua montatura 😃\nInviami /polare provincia per iniziare\nEsempio: /polare Roma"
    )


def polar_command(update: Update, context: CallbackContext) -> None:
    save_user_interaction(update.message.text, user=update.message.from_user)

    try:
        city = context.matches[0].group(1).lower().replace(" ", "_").replace("-", "_")

        lat = longlats[city]["lat"]
        lon = longlats[city]["long"]

        update.message.reply_text(
            f"{lat}\nQuesta è la tua latitudine, tienila a mente ti servirà dopo"
        )

        update.message.reply_text(
            "Per prima cosa esegui questi step\n1) Allinea al nord, anche in maniera grossolana, la tua montatura utilizzando anche la bussola dello smartphone. Il cannocchiale polare deve puntare verso nord.\n2) Metti la montatura a livello utilizzando la bolla.\n3) Regola l'altezza della montatura impostando il tuo valore di latitudine.\n4) Sblocca la declinazione (DEC) e orienta il tubo in maniera parallela al terreno. Questo per liberare e poter vedere tramite il cannocchiale polare. Serra nuovamente la DEC.\n5) Sblocca l'ascensione retta (AR) e guardando all'interno del cannocchiale polare ruota il sistema spostando lo 0 in alto e il 6 in basso, come se fosse un orologio. Serra nuovamente AR.\n6) Agisci sulle viti di Azimut e sulle viti dell'altezza per centrare e vedere la polare all'interno della grafica del cannocchiale polare."
        )
        update.message.reply_text(
            text="Okay, ora sei pronto! Trovi tutta la procedura appena descritta in questo video: https://youtu.be/Sx9mPKuYcvc",
            disable_web_page_preview=True,
        )
        update.message.reply_text(
            "Ora segui pure le istruzioni del bot 🚀🚀🚀\nTi mostrerò la corretta posizione che deve avere la stella polare all'interno del tuo cannocchiale polare"
        )

        lst = lst_string(lat, lon)
        ra = ra_polaris_string()

        format_parser = "%Hh%Mm%Ss"
        ra_polaris_time = datetime.strptime(ra, format_parser)
        lst_time = datetime.strptime(lst, format_parser)

        ha = lst_time - ra_polaris_time
        if ha.total_seconds() < 0:
            ha = timedelta(seconds=ha.total_seconds() + 24 * 60 * 60)

        angle = time_to_angle(ha.total_seconds())
        img = draw_png(angle)

        # update.message.reply_text(f"LST={lst}\nRA Polaris={ra}\nHA={ha}\nAngolo: {angle}")

        # photo = open("./resources/images/polare.png", "rb")
        # update.message.reply_photo(photo=photo)
        # photo.close()

        send_PIL_image(update, img)

    except Exception as e:
        write_on_error_log(
            update.message.from_user,
            "ERRORE in polar command",
            e,
            traceback.format_exc(),
        )

        update.message.reply_text("Località non trovata")
        update.message.reply_sticker(sticker=error_sticker)


def draw_png(angle):
    def rotate_np(point, origin, degrees):
        radians = np.deg2rad(degrees)
        x, y = point
        offset_x, offset_y = origin
        adjusted_x = x - offset_x
        adjusted_y = y - offset_y
        cos_rad = np.cos(radians)
        sin_rad = np.sin(radians)
        qx = offset_x + cos_rad * adjusted_x + sin_rad * adjusted_y
        qy = offset_y + -sin_rad * adjusted_x + cos_rad * adjusted_y
        return qx, qy

    # apro l'immagine sulla quale disegnare
    with Image.open("./resources/images/orologio.png") as clock_image:
        img = np.array(clock_image)

    with Image.open("./resources/images/stella.png") as star_image:
        star = np.array(star_image)

    # img = cv2.imread("./resources/images/orologio.png", cv2.IMREAD_COLOR)
    # star = cv2.imread("./resources/images/stella.png", cv2.IMREAD_COLOR)

    center = (int(img.shape[0] / 2), int(img.shape[0] / 2))
    radius = 507
    angle = 90 - angle
    point_on_circle = (
        int(center[0] + radius * np.cos(angle * np.pi / 180)),
        int(center[1] + radius * np.sin(angle * np.pi / 180)),
    )
    star_point = (
        point_on_circle[0] - int(star.shape[0] / 2),
        point_on_circle[1] - int(star.shape[1] / 2),
    )
    for x in range(star.shape[0]):
        for y in range(star.shape[1]):
            column = star_point[0] + x
            row = star_point[1] + y

            if np.any(star[x][y] != 255) and not np.all(star[x][y] == 0):
                img[row][column][0] = star[x][y][0]
                img[row][column][1] = star[x][y][1]
                img[row][column][2] = star[x][y][2]

    # prendo il rettangolo
    with Image.open("./resources/images/raggio.png") as radius_image:
        radius_img = np.array(radius_image)

    # radius_img = cv2.imread("./resources/images/raggio.png", cv2.IMREAD_COLOR)

    for x in range(radius_img.shape[0]):
        for y in range(radius_img.shape[1]):
            column = center[0] + x
            row = center[1] + y - int(radius_img.shape[1] / 2)

            xr, yr = rotate_np(point=(column, row), origin=center, degrees=angle + 270)

            xr = int(xr)
            yr = int(yr)

            if not np.all(radius_img[x][y] == 255):
                img[xr][yr][0] = radius_img[x][y][0]
                img[xr][yr][1] = radius_img[x][y][1]
                img[xr][yr][2] = radius_img[x][y][2]
    # Image.fromarray(img).save("./resources/images/polare.png")
    # cv2.imwrite("./resources/images/polare.png", img)

    return Image.fromarray(img)


def time_to_angle(seconds):
    # ad ogni secondo corrisponde un incremento di 0.00416°
    # lo 0° è fissato a 00:00 ed è fissato come vettore ortogonale verso il basso
    return seconds * 0.00416


def ra_polaris_string():
    # year = datetime.utcnow().year
    # month = datetime.utcnow().month
    # day = datetime.utcnow().day

    # page = requests.get(
    #     f"https://in-the-sky.org/data/object.php?id=TYC4628-237-1&day={day}&month={month}&year={year}"
    # )
    # tree = html.fromstring(page.text)
    # tree = tree.xpath(
    #     "//td[contains(text(),'Right ascension:')]/following-sibling::*//text()"
    # )
    # ra = ""
    # ra += tree[0]
    # ra += tree[1]
    # ra += tree[2]
    # ra += tree[3]
    # ra += tree[4]
    # ra += tree[5]

    # prendo l'anno e il mese corrente corrente
    year = datetime.utcnow().year
    month = datetime.utcnow().month
    ra = ra_polaris_months[f"{month}-{year}"]

    return ra


def lst_string(lat, lon):
    observing_location = EarthLocation(lat=lat, lon=lon)
    observing_time = Time(datetime.utcnow(), scale="utc", location=observing_location)
    lst = str(observing_time.sidereal_time("mean"))

    return re.search("(\d?\dh\d?\dm\d?\d)", lst).group(1) + "s"


def add_polar_handlers(dispatcher):
    dispatcher.add_handler(
        MessageHandler(Filters.regex(f"^{polaris_button_name}$"), polar_button_command)
    )

    # ESECUZIONE IN MULTITHREAD
    dispatcher.add_handler(
        MessageHandler(Filters.regex("^/polare (.*)$"), polar_command, run_async=True)
    )


ra_polaris_months = {
    "12-2021": "2h59m09s",
    "1-2022": "2h59m18s",
    "2-2022": "2h59m23s",
    "3-2022": "2h59m26s",
    "4-2022": "2h59m31s",
    "5-2022": "2h59m40s",
    "6-2022": "2h59m51s",
    "7-2022": "3h00m00s",
    "8-2022": "3h00m04s",
    "9-2022": "3h00m08s",
    "10-2022": "3h00m14s",
    "11-2022": "3h00m23s",
    "12-2022": "3h00m33s",
    "1-2023": "3h00m42s",
    "2-2023": "3h00m48s",
    "3-2023": "3h00m52s",
    "4-2023": "3h00m58s",
    "5-2023": "3h01m07s",
    "6-2023": "3h01m18s",
    "7-2023": "3h01m27s",
    "8-2023": "3h01m33s",
    "9-2023": "3h01m37s",
    "10-2023": "3h01m43s",
    "11-2023": "3h01m53s",
    "12-2023": "3h02m05s",
    "1-2024": "3h02m14s",
    "2-2024": "3h02m19s",
    "3-2024": "3h02m24s",
    "4-2024": "3h02m32s",
    "5-2024": "3h02m41s",
    "6-2024": "3h02m52s",
    "7-2024": "3h03m01s",
    "8-2024": "3h03m08s",
    "9-2024": "3h03m13s",
    "10-2024": "3h03m19s",
    "11-2024": "3h03m29s",
    "12-2024": "3h03m42s",
    "1-2025": "3h03m52s",
    "2-2025": "3h03m58s",
    "3-2025": "3h04m02s",
    "4-2025": "3h04m10s",
    "5-2025": "3h04m21s",
    "6-2025": "3h04m33s",
    "7-2025": "3h04m42s",
    "8-2025": "3h04m49s",
    "9-2025": "3h04m55s",
    "10-2025": "3h05m02s",
    "11-2025": "3h05m12s",
    "12-2025": "3h05m24s",
}
