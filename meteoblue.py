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
from constants import *
from geocities import *
from statistics_log import *

from utility import *
import traceback

link_meteoblue_button_name = "Collegati a MeteoBlue 🌍"
what_meteoblue_button_name = "Cosa fa MeteoBlue? 🤔"
advanced_meteoblue_button_name = "Guida Avanzata 🌲"
basic_meteoblue_button_name = "Guida Base 🌱"


def meteoblue_command(update: Update, context: CallbackContext) -> None:
    save_user_interaction(update.message.text, user=update.message.from_user)

    keyboard = [
        [link_meteoblue_button_name],
        [what_meteoblue_button_name, basic_meteoblue_button_name],
        [advanced_meteoblue_button_name, back_button_name],
    ]

    reply_markup = ReplyKeyboardMarkup(keyboard)

    update.message.reply_text(
        "Scegli quale comando visualizzare", reply_markup=reply_markup
    )


def link_meteoblue(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        "/meteoblue città - Se lanci questo comando con la tua città accedi a MeteoBlue già localizzato"
    )


def city_meteoblue(update: Update, context: CallbackContext) -> None:
    try:
        city = context.matches[0].group(1).lower().replace(" ", "_").replace("-", "_")

        geocode = geocities[city]

        city = city.lower().replace("_", "-")
        update.message.reply_text(
            f"https://www.meteoblue.com/it/tempo/outdoorsports/seeing/{city}_italia_{geocode}"
        )
    except Exception as e:
        write_on_error_log(
            update.message.from_user,
            "ERRORE in city meteoblue",
            e,
            traceback.format_exc(),
        )
        update.message.reply_text(
            "https://www.meteoblue.com/it/tempo/outdoorsports/seeing/roma_italia_3169070"
        )

    update.message.reply_sticker(sticker=meteoblue_sticker)


def what_meteoblue(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        "<b>Cosa fa Meteoblue?</b>\nL'Astronomy seeing (o visibilità astronomica) in italiano di meteoblue offre un servizio per astronomi, meteorologi, nonché altri utenti che dipendono da una buona previsione della visibilità dell'aria e delle condizioni atmosferiche dei seguenti giorni.",
        parse_mode="HTML",
    )


def advanced_meteoblue(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        "<b>Guida avanzata</b>\nAttenzione, i valori possono non riflettere la realtà in modo preciso perché ci sono molti fattori d'influenza. Al fine di ottenere buone condizioni di visibilità del cielo, cercate colori blu scuro nelle nuvolosità, nonché valori verdi negli indici di Vista e del jet stream.\n\nLa nuvolosità viene rappresentata a 3 strati diversi (0-4 km, 4-8 km, 8-15 km). La nuvolosità è in percentuale del tempo di visualizzazione. La percentuale integra il volume e la densità delle nuvole previste. Una nuvolosità parziale in 2 strati può avere come conseguenza un'ostruzione totale delle visibilità del cielo, a causa della sovrapposizione delle nuvole. Quanto alle nuvole alte, una nuvolosità parziale può totalmente ostruire la visibilità del cielo. Sulle montagne molto alte, sopra i 4000 m, la previsione delle nuvole basse sarà nulla e dovrebbe essere ignorata poiché interesserà unicamente le valli al di sotto dei 4000 m.\nLa nebbia o le nuvole molto basse non sono rappresentate in questi diagrammi (vedere il pictocast per la nebbia).\n\nL'indice di visibilità n°1 e l'indice di visibilità n°2 sono due diversi modelli per calcolare la visibilità e sono indipendenti dalla nuvolosità. Questi valori vengono calcolati secondo l'integrazione degli strati turbolenti nell'atmosfera. Rappresentano soltanto la visibilità attraverso parti del cielo che si suppongono sgombre da nuvole e indicano il modo in cui i gradienti di densità atmosferica influenzano la visibilità. La Visibilità 2 da maggiore rilevanza all'effetto di fluttuazioni di densità e indicherà il tremolio dell'aria causato dalla turbolenza. Questo indice NON include la nuvolosità. È possibile che non ci sia alcuna osservazione con un indice di vista di \"5\", se la nuvolosità è totale. Invece, è possibile che la nuvolosità sia nulla (tutte le stelle \"visibili\"), ma l'osservazione sia fastidiosamente ridotta da un indice di visibilità (\"1\"), a causa di turbolenze.\nCi sono 2 motivi per i quali gli indici di visibilità non tengono in considerazione la nuvolosità:\n\n1. La visibilità dipende dallo stato della colonna d'aria e quindi è indipendente dalla nuvolosità.\n\n2. A volte le nuvole sono sparse ed allora le osservazioni sono possibili tra le nuvole. In tal caso, sarebbe difficile fissare una \"confine\" della nuvolosità che inficerebbe l'osservazione.\n\nL'arcsecond o secondo d'arco in italiano è un'unità di misura angolare uguale a 1/3'600 di 1 grado o a 1/1'296'000 di un cerchio. Il secondo d'arco può essere usato per stimare la taglia minimale di un oggetto che è sempre visibile usando un telescopio puntando verso il cielo aperto, espresso come un angolo. Le misure d'arcsecond presentate nel grafico sono basate su \"Visibilità n°1\", \"Visibilità n°2\" e \"Bad layers\"\nInformazione basica sul calcolo.(in francese)\n\nUn jet stream a grande velocità (>35m/s) equivale normalmente ad una visibilità ridotta.\nI bad layers o strati cattivi in italiano sono strati dell'atmosfera nei quali la turbolenza produce perturbazioni dell'aria e delle particelle ed influenzano dunque la \"Visibilità\" astronomica. I bad layers hanno un gradiente di temperatura > 0.5K/100m. Il gradiente vero viene dato in K/100m. L'altezza massima e minima dei bad layers viene indicata da bad layer min/max.\n\nI pianeti visibili e le coordinate considerano anche le temperature dei diversi strati atmosferici. I pianeti seguenti sono disponibili: MVMJSUNP => Mercurio, Venere, Marte, Giove, Saturno, Urano, Nettuno e Plutone.",
        parse_mode="HTML",
    )


def basic_meteoblue(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        "<b>Guida base</b>\n1) Cerca i colori blu scuro nella copertura nuvolosa e i valori verdi negli indici di visibilità e nella corrente a getto per buone condizioni di visibilità.\n\n2) Gli indici di visibilità stimati (1 e 2) vanno da 1 (scarse) a 5 (eccellenti) condizioni di visibilità. Questi valori sono calcolati in base all'integrazione degli strati turbolenti nell'atmosfera.\n\n3) La copertura nuvolosa varia dal blu scuro (0%) al bianco (100%). La nebbia o le nuvole molto basse non sono mostrate qui.\n\n4) Le alte velocità del jet stream (>20 m/s) di solito corrispondono a un cattivo seeing.\n\n5) I bad layers hanno un gradiente di temperatura superiore a 0.5 K/100 m. Sono indicate le altezze superiori e inferiori degli strati danneggiati.\n\n6) LMVMJSUNP => Luna, Mercurio, Venere, Marte, Giove, Saturno, Urano, Nettuno e Plutone.",
        parse_mode="HTML",
    )


def add_meteoblue_handlers(dispatcher):
    dispatcher.add_handler(
        MessageHandler(Filters.regex(f"^{meteoblue_button_name}$"), meteoblue_command)
    )

    dispatcher.add_handler(
        MessageHandler(Filters.regex(f"^{link_meteoblue_button_name}$"), link_meteoblue)
    )

    what_meteoblue_button_name_no_mark = what_meteoblue_button_name.replace("?", "\?")
    dispatcher.add_handler(
        MessageHandler(
            Filters.regex(f"^{what_meteoblue_button_name_no_mark}$"), what_meteoblue
        )
    )

    dispatcher.add_handler(
        MessageHandler(
            Filters.regex(f"^{advanced_meteoblue_button_name}$"), advanced_meteoblue
        )
    )

    dispatcher.add_handler(
        MessageHandler(
            Filters.regex(f"^{basic_meteoblue_button_name}$"), basic_meteoblue
        )
    )

    dispatcher.add_handler(
        MessageHandler(Filters.regex(f"^/meteoblue (.*)$"), city_meteoblue)
    )

    # dispatcher.add_handler(CommandHandler("meteoblue", city_meteoblue))
