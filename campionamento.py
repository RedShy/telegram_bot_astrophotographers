from telegram import (
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    replymarkup,
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
from utility import *
from constants import *
from statistics_log import *

DIAMETER, FOCAL, WAVELENGHT, PIXELS = range(4)

keyboard_campionamento = [
    ["Pianeti con sensore a colori 🪐", "Deep Sky ⭐️"],
    ["Pianeti con sensore mono 🪐", back_button_name],
]


def campionamento_command(update: Update, context: CallbackContext) -> None:
    save_user_interaction(update.message.text, user=update.message.from_user)

    update.message.reply_text(
        "Scegli il tipo di campionamento",
        reply_markup=ReplyKeyboardMarkup(keyboard_campionamento),
    )

    update.message.reply_text(
        "• <b>Pianeti con sensore a colori</b>: se stai lavorando nel visibile. Generalmente le camere a colori hanno la massima sensibilità proprio nel visibile.\n• <b>Pianeti con sensore mono</b>: se stai lavorando nel non visibile. Generalmente le camere mono vengono utilizzate per riprese nel non visibile come ad esempio nell’infrarosso.\n• <b>Deep Sky</b>: se vuoi eseguire un’acquisizione dati dello spazio profondo.",
        parse_mode="HTML",
    )


def campionamento_color_command(update: Update, context: CallbackContext) -> int:
    update.message.reply_text(
        "Per ottenere il campionamento ideale del tuo setup inviami il diametro del tuo telescopio espresso in mm\nEsempio 20 cm = 200 mm",
        reply_markup=ReplyKeyboardRemove(),
    )

    return DIAMETER


def campionamento_color_diameter_choice(
    update: Update, context: CallbackContext
) -> int:
    try:
        diameter = get_number_greater_zero(update.message.text)
    except:
        return campionamento_error(update, context)

    campionamento1 = 37 / diameter
    campionamento2 = (115 / diameter) / 4
    best_campionamento = round((campionamento1 + campionamento2) / 2, 2)
    context.user_data["best_campionamento"] = best_campionamento

    update.message.reply_text(
        "Okay! Inviami anche la dimensione dei pixel del tuo sensore in mm per ottenere la focale ideale\nEsempio 3.75 micron = 0.00375 mm"
    )

    return FOCAL


def campionamento_color_focal_choice(update: Update, context: CallbackContext) -> int:
    try:
        dimension_pixels = get_number_greater_zero(update.message.text)
    except:
        return campionamento_error(update, context)

    best_campionamento = context.user_data["best_campionamento"]

    result = round((dimension_pixels / best_campionamento) * 206265, 2)
    update.message.reply_text(
        f'Il campionamento ideale è:\n{best_campionamento}" per pixel\n\nLa focale ottimale è:\n{result} mm'
    )

    return campionamento_done(update, context)


def campionamento_done(update: Update, context: CallbackContext) -> int:
    # ritorna al menu iniziale dei campionamenti
    update.message.reply_sticker(
        sticker=campionamento_sticker,
        reply_markup=ReplyKeyboardMarkup(keyboard_campionamento),
    )

    context.user_data.clear()
    return ConversationHandler.END


def campionamento_mono_command(update: Update, context: CallbackContext) -> int:
    return campionamento_color_command(update, context)


def campionamento_mono_diameter_choice(update: Update, context: CallbackContext) -> int:
    try:
        diameter = get_number_greater_zero(update.message.text)
    except:
        return campionamento_error(update, context)

    context.user_data["diameter"] = diameter

    update.message.reply_text(
        "Ora invia il picco della tua lunghezza d'onda in mm\nEsempio 550 nm = 0.0005 mm"
    )

    return WAVELENGHT


def campionamento_mono_wavelenght_choice(
    update: Update, context: CallbackContext
) -> int:
    try:
        wavelenght = get_number_greater_zero(update.message.text)
    except:
        return campionamento_error(update, context)

    context.user_data["wavelenght"] = wavelenght

    update.message.reply_text(
        "Okay! Inviami anche la dimensione dei pixel del tuo sensore in mm per ottenere la focale ideale\nEsempio 3.75 micron = 0.00375 mm"
    )

    return FOCAL


def campionamento_mono_focal_choice(update: Update, context: CallbackContext) -> int:
    try:
        dimension_pixels = get_number_greater_zero(update.message.text)
    except:
        return campionamento_error(update, context)

    wavelenght = context.user_data["wavelenght"]
    diameter = context.user_data["diameter"]
    best_campionamento = round(0.33 * (wavelenght / diameter) * 206265, 2)

    result = round((dimension_pixels * diameter) / (0.33 * wavelenght), 2)
    update.message.reply_text(
        f'Il campionamento ideale è:\n{best_campionamento}" per pixel\n\nLa focale ottimale è:\n{result} mm'
    )

    return campionamento_done(update, context)


def campionamento_deep_command(update: Update, context: CallbackContext) -> int:
    update.message.reply_text(
        "Inviami la dimensione dei pixel del tuo sensore in mm per il campionamento ideale\nEsempio 3.75 micron = 0.00375 mm",
        reply_markup=ReplyKeyboardRemove(),
    )

    return PIXELS


def campionamento_deep_pixels_choice(update: Update, context: CallbackContext) -> int:
    try:
        dimension_pixels = get_number_greater_zero(update.message.text)
    except:
        return campionamento_error(update, context)

    context.user_data["dimension_pixels"] = dimension_pixels

    update.message.reply_text(
        "Okay! Inviami anche la focale del tuo telescopio in mm\nEsempio 1200 mm"
    )

    return FOCAL


def campionamento_deep_focal_choice(update: Update, context: CallbackContext) -> int:
    try:
        focal = get_number_greater_zero(update.message.text)
    except:
        return campionamento_error(update, context)

    dimension_pixels = context.user_data["dimension_pixels"]

    result = round((dimension_pixels / focal) * 206265, 2)
    update.message.reply_text(f'Il campionamento ideale è:\n{result}" per pixel')
    update.message.reply_text(
        'Il campionamento ideale in fotografia deep sky è fortemente influenzato dal seeing atmosferico.\nVisto il seeing medio, almeno in Italia, il campionamento ideale è compreso nel seguente intervallo chiuso 1" per pixel - 2" per pixel'
    )

    return campionamento_done(update, context)


def campionamento_error(update: Update, context: CallbackContext) -> int:
    update.message.reply_text(
        "Dato non riconosciuto",
        reply_markup=ReplyKeyboardMarkup(keyboard_campionamento),
    )

    return end_error_conversation(update, context)


def end_timeout_conversation(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("Hai impiegato troppo tempo per dare una risposta")
    return end_error_conversation(update, context)


def end_error_conversation(update: Update, context: CallbackContext) -> int:
    update.message.reply_sticker(
        sticker=error_sticker, reply_markup=ReplyKeyboardMarkup(keyboard_campionamento)
    )
    context.user_data.clear()
    return ConversationHandler.END


def add_campionamento_handlers(dispatcher):
    dispatcher.add_handler(
        MessageHandler(
            Filters.regex(f"^{campionamento_button_name}$"), campionamento_command
        )
    )

    conv_campionamento_color_handler = ConversationHandler(
        entry_points=[
            MessageHandler(
                Filters.regex("^Pianeti con sensore a colori 🪐$"),
                campionamento_color_command,
            )
        ],
        states={
            DIAMETER: [
                MessageHandler(
                    Filters.regex(f"^.*$"), campionamento_color_diameter_choice,
                ),
            ],
            FOCAL: [
                MessageHandler(
                    Filters.regex(f"^.*$"), campionamento_color_focal_choice,
                ),
            ],
            ConversationHandler.TIMEOUT: [
                MessageHandler(Filters.regex(".*"), end_timeout_conversation)
            ],
        },
        fallbacks=[MessageHandler(Filters.regex(".*"), campionamento_error),],
        conversation_timeout=30,
    )
    dispatcher.add_handler(conv_campionamento_color_handler)

    conv_campionamento_mono_handler = ConversationHandler(
        entry_points=[
            MessageHandler(
                Filters.regex("^Pianeti con sensore mono 🪐$"),
                campionamento_mono_command,
            )
        ],
        states={
            DIAMETER: [
                MessageHandler(
                    Filters.regex(f"^.*$"), campionamento_mono_diameter_choice,
                ),
            ],
            WAVELENGHT: [
                MessageHandler(
                    Filters.regex(f"^.*$"), campionamento_mono_wavelenght_choice,
                ),
            ],
            FOCAL: [
                MessageHandler(
                    Filters.regex(f"^.*$"), campionamento_mono_focal_choice,
                ),
            ],
            ConversationHandler.TIMEOUT: [
                MessageHandler(Filters.regex(".*"), end_timeout_conversation)
            ],
        },
        fallbacks=[MessageHandler(Filters.regex(".*"), campionamento_error),],
        conversation_timeout=30,
    )
    dispatcher.add_handler(conv_campionamento_mono_handler)

    conv_campionamento_deep_handler = ConversationHandler(
        entry_points=[
            MessageHandler(Filters.regex("^Deep Sky ⭐️$"), campionamento_deep_command,)
        ],
        states={
            PIXELS: [
                MessageHandler(
                    Filters.regex(f"^.*$"), campionamento_deep_pixels_choice,
                ),
            ],
            FOCAL: [
                MessageHandler(
                    Filters.regex(f"^.*$"), campionamento_deep_focal_choice,
                ),
            ],
            ConversationHandler.TIMEOUT: [
                MessageHandler(Filters.regex(".*"), end_timeout_conversation)
            ],
        },
        fallbacks=[MessageHandler(Filters.regex(".*"), campionamento_error),],
        conversation_timeout=30,
    )
    dispatcher.add_handler(conv_campionamento_deep_handler)
