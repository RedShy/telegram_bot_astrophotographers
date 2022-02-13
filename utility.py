from io import BytesIO
from telegram import Update, User
from datetime import datetime
import threading

lock = threading.Lock()


def send_PIL_image(update, img):
    # Probabilmente il lock non serve
    lock.acquire()

    # salva in RAM l'immagine anziché su file e poi la va a leggere dalla RAM
    bio = BytesIO()
    img.save(bio, "PNG")
    bio.seek(0)
    update.message.reply_photo(photo=bio)
    bio.close()

    lock.release()


def get_number_greater_zero(text):
    number = float(text.replace("m", "").replace(" ", "").replace(",", "."))
    if number == 0:
        raise Exception("Numero uguale a 0")
    elif number < 0:
        raise Exception("Numero negativo")

    return number


error_log_lock = threading.Lock()


def write_on_error_log(user: User, text, exception, traceback):
    name_file = f"./error_log/{datetime.utcnow().day}_{datetime.utcnow().month}_{datetime.utcnow().year}.txt"

    username = ""
    user_id = ""
    first_name = ""
    last_name = ""
    if user is not None:
        username = user.username
        user_id = user.id
        first_name = user.first_name
        last_name = user.last_name

    entry = f"{datetime.utcnow()}------{first_name} {last_name} @{username}------{user_id}------{text}------{exception}------{traceback}\n"

    error_log_lock.acquire()
    try:
        # apro il file giorno-mese-anno.txt e ci butto dentro tutti i prompt
        with open(name_file, "a+", encoding="utf-8") as file:
            file.write(entry)
    finally:
        error_log_lock.release()


def send_today_error_log(update: Update):
    name_file = f"./error_log/{datetime.utcnow().day}_{datetime.utcnow().month}_{datetime.utcnow().year}.txt"

    error_log_lock.acquire()
    try:
        with open(name_file, "rb") as file:
            update.message.reply_document(document=file)
    except Exception as e:
        update.message.reply_text(
            f"Errore durante l'apertura del file di error log:\n{e}"
        )
    finally:
        error_log_lock.release()


def is_admin(user_id):
    if user_id == 234660655 or user_id == 45264012:
        return True

    return False
