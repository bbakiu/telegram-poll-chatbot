import logging
import logging.config
import os
import time

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Poll
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackQueryHandler,
    PollHandler,
)
import telegram

from _model import *

questions = [
    {
        'question': 'What is your favorite drink?',
        'options': ['wine', 'water', 'soda'],
        'explanation': 'It depends on what you eat'
    },
    {
        'question': 'What is your favorite food?',
        'options': ['wine', 'water', 'soda'],
        'explanation': 'It depends on what you feel'
    },
    {
        'question': 'What is your favorite appetizer?',
        'options': ['wine', 'water', 'soda'],
        'explanation': 'It depends on how you want to start'
    }
]

user_answers = []

index = 0


def get_chat_id(update, context):
    chat_id = -1

    if update.message is not None:
        chat_id = update.message.chat.id
    elif update.callback_query is not None:
        chat_id = update.callback_query.message.chat.id
    elif update.poll is not None:
        chat_id = context.bot_data[update.poll.id]

    return chat_id


def get_user(update):
    user: User = None

    _from = None

    if update.message is not None:
        _from = update.message.from_user
    elif update.callback_query is not None:
        _from = update.callback_query.from_user

    if _from is not None:
        user = User()
        user.id = _from.id
        user.first_name = _from.first_name if _from.first_name is not None else ""
        user.last_name = _from.last_name if _from.last_name is not None else ""
        user.lang = _from.language_code if _from.language_code is not None else "n/a"

    logging.info(f"from {user}")

    return user


def start_command_handler(update, context):
    """Send a message when the command /start is issued."""
    update.message.reply_text("Welcome to Chatbot quiz Bot.")
    add_typing(update, context)
    send_next_question(update, context)


def send_next_question(update, context):
    global index

    if index < len(questions):
        # for question in questions:
        quiz_question = QuizQuestion()
        quiz_question.question = questions[index].get("question")
        quiz_question.answers = questions[index].get("options")
        quiz_question.explanation = questions[index].get("explanation")

        add_quiz_question(update, context, quiz_question)
    else:
        # reply
        add_typing(update, context)
        add_text_message(update, context, "This was the last question. Thank you for your participation! 🎉")


def help_command_handler(update, context):
    """Send a message when the command /help is issued."""
    update.message.reply_text("This is the Quiz Chat Bot. Type /start to start!")


def hi_command_handler(update, context):
    """Send a message when the command /hi is issued."""
    update.message.reply_text("This is the  Quiz Chat Bot Bot. Type /start to start!")


def start(update, context):
    context.bot.send_message(chat_id=get_chat_id(update, context), text="I'm a bot, please talk to me!")


def main_handler(update, context):
    logging.info(f"update : {update}")

    if update.message is not None:
        user_input = get_text_from_message(update)
        logging.info(f"user_input : {user_input}")

        # reply
        add_typing(update, context)
        add_text_message(update, context, f"You said: {user_input}")


def poll_handler(update, context):
    global index
    global user_answers

    user_answer = Answer()
    user_answer.question = update.poll.question
    user_answer.answer = get_answer(update)

    add_typing(update, context)
    add_text_message(update, context, f"Your answer was {user_answer.answer}")
    add_text_message(update, context, f"Full answer was {user_answer}")
    user_answers.append(user_answer.as_dict())

    index = index + 1

    send_next_question(update, context)


def add_typing(update, context):
    context.bot.send_chat_action(
        chat_id=get_chat_id(update, context),
        action=telegram.ChatAction.TYPING,
        timeout=1,
    )
    time.sleep(1)


def add_text_message(update, context, message):
    context.bot.send_message(chat_id=get_chat_id(update, context), text=message)


def add_suggested_actions(update, context, response):
    options = []

    for item in response.items:
        options.append(InlineKeyboardButton(item, callback_data=item))

    reply_markup = InlineKeyboardMarkup([options])

    context.bot.send_message(
        chat_id=get_chat_id(update, context),
        text=response.message,
        reply_markup=reply_markup,
    )


# question date type: question, options, open period, explanation,
def add_quiz_question(update, context, quiz_question):
    message = context.bot.send_poll(
        chat_id=get_chat_id(update, context),
        question=quiz_question.question,
        options=quiz_question.answers,
        type=Poll.REGULAR,
        open_period=40,
        is_anonymous=True,
        explanation=quiz_question.explanation,
        explanation_parse_mode=telegram.ParseMode.MARKDOWN_V2,
    )

    # Save some info about the poll the bot_data for later use in receive_quiz_answer
    context.bot_data.update({message.poll.id: message.chat.id})


def get_text_from_message(update):
    return update.message.text


def get_answer(update):
    answers = update.poll.options

    ret = ""

    for answer in answers:
        if answer.voter_count == 1:
            ret = answer.text

    return ret


def get_text_from_callback(update):
    return update.callback_query.data


def error(update, context):
    """Log Errors caused by Updates."""
    logging.warning('Update "%s" ', update)
    logging.exception(context.error)


def main():
    updater = Updater(DefaultConfig.TELEGRAM_TOKEN, use_context=True)

    dp = updater.dispatcher

    # command handlers
    dp.add_handler(CommandHandler("help", help_command_handler))
    dp.add_handler(CommandHandler("hi", help_command_handler))
    dp.add_handler(CommandHandler("start", start_command_handler))

    # message handler
    dp.add_handler(MessageHandler(Filters.text, main_handler))

    # suggested_actions_handler
    dp.add_handler(
        CallbackQueryHandler(main_handler, pass_chat_data=True, pass_user_data=True)
    )

    # quiz answer handler
    dp.add_handler(PollHandler(poll_handler, pass_chat_data=True, pass_user_data=True))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    if DefaultConfig.MODE == "webhook":

        updater.start_webhook(
            listen="0.0.0.0",
            port=int(DefaultConfig.PORT),
            url_path=DefaultConfig.TELEGRAM_TOKEN,
        )
        updater.bot.setWebhook(DefaultConfig.WEBHOOK_URL + DefaultConfig.TELEGRAM_TOKEN)

        logging.info(f"Start webhook mode on port {DefaultConfig.PORT}, webhook {DefaultConfig.WEBHOOK_URL}")
    else:
        updater.start_polling()
        logging.info(f"Start polling mode")

    updater.idle()


class DefaultConfig:
    PORT = int(os.environ.get("PORT", 5000))
    TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "1858579947:AAHMNzb0kBQ0FMHGxPOhkvfsfJ2yvUxov5w")
    MODE = os.environ.get("MODE", "webhook")
    WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "https://telegram-chat-bot-bujar-ppyoll.herokuapp.com/")

    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

    @staticmethod
    def init_logging():
        logging.basicConfig(
            format="%(asctime)s - %(levelname)s - %(message)s",
            level=DefaultConfig.LOG_LEVEL,
        )


if __name__ == "__main__":
    # Enable logging
    DefaultConfig.init_logging()

    main()
