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

(FEEDBACK,) = range(1)


def feedback_command(update: Update, context: CallbackContext) -> int:
    update.message.reply_text(
        "Inviami pure il tuo feedback", reply_markup=ReplyKeyboardRemove()
    )
    update.message.reply_sticker(sticker=feedback_sticker)

    return FEEDBACK


def feedback_choice(update: Update, context: CallbackContext) -> int:
    first_name = update.message.from_user.first_name
    last_name = update.message.from_user.last_name
    user_name = update.message.from_user.username

    feedback = f"{first_name} {last_name} @{user_name}: {update.message.text}"

    bot = Bot(token=token)
    bot.send_message(chat_id="", text=feedback)

    update.message.reply_text(
        "Grazie per aver inviato il tuo feedback!",
        reply_markup=ReplyKeyboardMarkup(main_menu_keyboard),
    )

    update.message.reply_sticker(sticker=community_sticker,)

    return end_conversation(update, context)


def end_timeout_conversation(update: Update, context: CallbackContext) -> int:
    update.message.reply_text(
        "Hai impiegato troppo tempo per dare una risposta",
        reply_markup=ReplyKeyboardMarkup(main_menu_keyboard),
    )
    update.message.reply_sticker(sticker=error_sticker)
    return end_conversation(update, context)


def end_conversation(update: Update, context: CallbackContext) -> int:
    context.user_data.clear()
    return ConversationHandler.END


def add_feedback_handlers(dispatcher):
    conv_feedback_handler = ConversationHandler(
        entry_points=[
            MessageHandler(Filters.regex(f"^{feedback_button_name}$"), feedback_command)
        ],
        states={
            FEEDBACK: [MessageHandler(Filters.regex(f"(.*)"), feedback_choice)],
            ConversationHandler.TIMEOUT: [
                MessageHandler(Filters.regex(".*"), end_timeout_conversation)
            ],
        },
        fallbacks=[MessageHandler(Filters.regex(".*"), end_conversation)],
        conversation_timeout=30,
    )
    dispatcher.add_handler(conv_feedback_handler)
