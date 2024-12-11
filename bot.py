from random import choice
from telegram import ReplyKeyboardMarkup, BotCommand
from telegram import ForceReply, Update
from telegram.ext import ContextTypes
from database.base import SessionLocal
from database.repositories import add_word
from database.models import Word
import json


def load_phrases(file_path="bot_phrases.json"):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

bot_phrases = load_phrases()


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Sends a welcome message when the /start command is issued.

    This method is triggered when a user sends the /start command to the bot. It sends a greeting message to the user
    and includes a forced reply keyboard to ensure that the user can respond to the message. The message content
    is fetched from the `bot_phrases["start_message"]`.

    Example:
    /start
    """

    await update.message.reply_html(
        bot_phrases["start_message"],
        reply_markup=ForceReply(selective=True)
    )

async def add_word_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Command to add a word and its translation to the database.

    This method checks if the user has provided the word and its translation as arguments,
    then saves the word and translation in the database. It responds with a success message
    or an error message if the operation fails.

    Example:
    /add_word hello привіт
    """

    word = context.args[0]
    translation = " ".join(context.args[1:])

    db = SessionLocal()

    try:
        new_word = add_word(db, word=word, translation=translation)
        await update.message.reply_text(bot_phrases["word_added"].format(new_word=new_word.word, translation=new_word.translation))
    except Exception as e:
        await update.message.reply_text(bot_phrases["word_added_error"].format(error=str(e)))
    finally:
        db.close()

async def quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Starts a quiz or begins a new round of the quiz.

    This method checks if there are words in the database, and if so, it selects a random word for the user to translate.
    It stores the word's ID in the user's data and initializes the quiz state. If no words are available, it prompts
    the user to add words using the /add_word command.

    Example:
    /quiz
    """

    db = SessionLocal()
    try:
        words = db.query(Word).all()
        if not words:
            await update.message.reply_text(bot_phrases["empty_db"])
            return

        selected_word = choice(words)
        context.user_data["quiz_word_id"] = selected_word.id

        if "quiz_correct" not in context.user_data:
            context.user_data["quiz_correct"] = 0

        await update.message.reply_text(bot_phrases["quiz_question"].format(word=selected_word.word))
    except Exception as e:
        await update.message.reply_text(bot_phrases["quiz_error"].format(error=str(e)))
    finally:
        db.close()

async def check_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Checks the user's answer for the current quiz question.

    This method retrieves the active word from the database using the word ID stored in the user's context data.
    It then compares the user's answer with the correct translation. If the answer is correct, it sends a success message,
    otherwise, it sends the correct answer. Afterward, the method removes the current quiz question from the user's context.
    """

    user_answer = update.message.text.strip().lower()
    word_id = context.user_data.get("quiz_word_id")

    if not word_id:
        await update.message.reply_text(bot_phrases["start_quiz_error"])
        return

    db = SessionLocal()
    try:
        word = db.query(Word).filter(Word.id == word_id).first()
        if not word:
            await update.message.reply_text(bot_phrases["word_not_exist"])
            return

        correct_answer = word.translation.strip().lower()

        if user_answer.lower() == correct_answer.lower():
            context.user_data["quiz_correct"] += 1
            await update.message.reply_text(bot_phrases["quiz_correct"])
        else:
            await update.message.reply_text(bot_phrases["incorrect_answer"].format(correct_answer=correct_answer))

        del context.user_data["quiz_word_id"]

        keyboard = [[bot_phrases["quiz_next"], bot_phrases["quiz_exit"]]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text(bot_phrases["continue_quiz"], reply_markup=reply_markup)
    except Exception as e:
        await update.message.reply_text(bot_phrases["check_answer_error"].format(error=str(e)))
    finally:
        db.close()

async def handle_quiz_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles the user's choice to either continue the quiz or exit.

    This method processes the user's response to whether they want to continue to the next word in the quiz or exit.
    If the user chooses to continue, it triggers the next round of the quiz. If the user chooses to exit,
    it shows the number of correct answers and resets the quiz counters. If the input is not recognized,
    the method prompts the user to provide a valid response.
    """

    user_choice = update.message.text.strip().lower()

    if user_choice == bot_phrases["quiz_next"].lower():
        await quiz_command(update, context)
    elif user_choice == bot_phrases["quiz_exit"].lower():
        correct_answers = context.user_data.get("quiz_correct", 0)
        await update.message.reply_text(bot_phrases["quiz_summary"].format(correct=correct_answers))

        context.user_data.pop("quiz_correct", None)
    else:
        await update.message.reply_text(bot_phrases["incorrect_input"])

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Sends a list of available commands to the user.

    This method sends a message to the user containing the list of commands they can use with the bot.
    The list is defined in the `help_message` phrase. It helps the user understand how to interact with the bot.

    Example:
    /help
    """

    commands = bot_phrases["help_message"]
    await update.message.reply_text(commands)