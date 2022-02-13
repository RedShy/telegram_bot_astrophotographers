from pytz import timezone
import tracemalloc

tracemalloc.start(10)
start_time_tracemalloc = tracemalloc.take_snapshot()

# (.*)\*(.*)\*(.*)\*(.*)\*(.*)\*(.*)
# \["$1","$2","$3","$4","$5","$6"\],

token = ""

num_threads_asynchronous_tasks = 8

max_messier = 110

iss_button_name = "Transito ISS 🛰"
campionamento_button_name = "Campionamento 🔢"
faq_pixinsight_button_name = "FAQ Pixinsight 💬"
meteoblue_button_name = "MeteoBlue ☀️"
feedback_button_name = "Invia feedback 📧"
shoot_timing_button_name = "Tempi acquisizione pianeti 🕓"
polaris_button_name = "Allineamento polare 🌟"
recommended_software_button_name = "Programmi consigliati 🖥"
astronomy_tools_button_name = "Astronomy Tools 👨‍💻"
ngc_button_name = "Catalogo NGC (🔜)"
messier_button_name = "Catalogo Messier 📝"
catalogs_button_name = "Cataloghi M, NGC 📝"
suggested_setup_button_name = "Setup Consigliati 🔭"
astropic_button_name = "AstroPic 📹"
share_website_button_name = "Condividi Sito 📍 (🔜)"
other_button_name = "Altro ➡️"
targets_month_button_name = "10 Target del mese 🌌"
tips_button_name = "Consigli"
community_button_name = "Community 👥"
exercises_files_button_name = "File esercitazioni 👨🏻‍🏫"
prints_astropic_button_name = "Stampe AstroPic 🖼"

back_button_name = "Indietro ⬅️"

regex_number_first_non_zero = "[1-9]\d*(?:\.|,)?\d*"
regex_number_first_zero = "0(?:\.|,)\d*[1-9]"
regex_any_number = f"(?:{regex_number_first_non_zero})|(?:{regex_number_first_zero})"

main_menu_keyboard = [
    [astropic_button_name],
    [campionamento_button_name, meteoblue_button_name],
    [polaris_button_name, shoot_timing_button_name],
    [exercises_files_button_name, targets_month_button_name],
    [suggested_setup_button_name, feedback_button_name],
    [faq_pixinsight_button_name, other_button_name],
]

campionamento_sticker = (
    "CAACAgIAAxkBAAIUOGGhQCVgzm95jiOsu-Ai4iZ-VXKmAAJ2DwACQFFBSH2QfwWWJ7NpIgQ"
)
campionamento_sticker_2 = (
    "CAACAgIAAxkBAAIURGGhQLKBWcsDZoyE8mrcnLSGThGyAAKADgAC66RQS4PPmx1H5vOhIgQ"
)
meteoblue_sticker = (
    "CAACAgIAAxkBAAIUQmGhQJqCSnY87Gl7CDBjpbHnU6doAALWAANSiZEj37yoSamyggIiBA"
)
shoot_timing_sticker = (
    "CAACAgIAAxkBAAIUQGGhQIRq3HI5wuRHt9W9y1BoCYtMAAJTCwACLw_wBkskewT5ubGGIgQ"
)
feedback_sticker = (
    "CAACAgIAAxkBAAIUPGGhQFQlak4bCyVugYv9cXnD4m9FAAIWDAAC-S7gS3bmebx8F40rIgQ"
)
error_sticker = (
    "CAACAgIAAxkBAAIUOmGhQECozi-rNDwwSo59t7UyB5qpAAKMDAACLRAQSE4bvH57SQABISIE"
)
astroPic_sticker = (
    "CAACAgIAAxkBAAIUNmGhQAtPMvU5f295G01_F5AIV1PmAALKDQACkWAhSLH3iAXwPlX4IgQ"
)
catalogs_sticker = (
    "CAACAgIAAxkBAAIUPmGhQGmjO2a1yz_DkfdIjz2TCH6mAAKyCgACTW2gSO0TCE0WMW5KIgQ"
)
iss_sleep_sticker = (
    "CAACAgIAAxkBAAIX_2GiYtZRWAABnteTtArDnPOUxpoK9AACjw8AAuks8Ut-G6UdCsIYdiIE"
)
community_sticker = (
    "CAACAgIAAxkBAAIKOGGuVakm1nCATZnCfEtGSZKVEn2lAALrDwACyCNQS6jDUfpSICM5IgQ"
)

italy_tz = timezone("Europe/Vienna")

italian_months_by_index = [
    "",
    "Gennaio",
    "Febbraio",
    "Marzo",
    "Aprile",
    "Maggio",
    "Giugno",
    "Luglio",
    "Agosto",
    "Settembre",
    "Ottobre",
    "Novembre",
    "Dicembre",
]
italian_weekdays_by_index = [
    "Lunedì",
    "Martedì",
    "Mercoledì",
    "Giovedì",
    "Venerdì",
    "Sabato",
    "Domenica",
]
