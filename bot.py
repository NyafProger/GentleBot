import csv
from datetime import datetime
import io
from random import choice, choices
from telegram import ReplyKeyboardMarkup, BotCommand, InputFile
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
    This method selects a random word based on both the frequency of correct answers and the time since it was last guessed.

    Example:
    /quiz
    """

    db = SessionLocal()
    try:
        words = db.query(Word).all()
        if not words:
            await update.message.reply_text(bot_phrases["empty_db"])
            return

        # Calculate weight for each word based on last guessed time
        current_time = datetime.now()

        # Weights will be based on two factors: correct_answer_count and time since last guessed
        weights = []
        for word in words:
            # Calculate days since the word was last guessed
            days_since_last_guessed = (current_time - word.last_guessed).days

            # Adjust the weight based on the last guessed time (add extra weight after a week)
            if days_since_last_guessed > 7:
                time_weight = (days_since_last_guessed - 7)  # Incremental weight for each day after a week
            else:
                time_weight = 0

            # Reverse weight calculation: Less correct answers -> higher weight
            # Increase weight when correct_answer_count is low, decrease when it's high
            correct_answer_weight = max(0, 10 - word.correct_answer_count)  # We use a max to avoid negative weights

            # Final weight is a combination of the reversed correct_answer_count and the time weight
            weight = correct_answer_weight + time_weight
            weights.append(weight)

        # Select a word based on the calculated weights
        selected_word = choices(words, weights=weights, k=1)[0]

        # Update the last guessed time to now
        selected_word.last_guessed = current_time
        db.commit()

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
            word.correct_answer_count += 1
            context.user_data["quiz_correct"] += 1
            await update.message.reply_text(bot_phrases["quiz_correct"])
        else:
            word.correct_answer_count -= 1
            await update.message.reply_text(bot_phrases["incorrect_answer"].format(correct_answer=correct_answer))

        db.commit()
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

async def export_words_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Exports the entire Word table as a CSV file and sends it to the user.

    This method queries all words from the database, converts them to CSV format, and sends the CSV file to the user.
    Example: /export_words
    """

    db = SessionLocal()
    try:
        # Query all words from the database
        words = db.query(Word).all()

        # Create an in-memory file to write CSV data
        output = io.StringIO()
        csv_writer = csv.writer(output)

        # Write CSV header
        csv_writer.writerow(["ID", "Word", "Translation", "Example", "Correct Answer Count"])

        # Write each word's data as a row
        for word in words:
            csv_writer.writerow([word.id, word.word, word.translation, word.example, word.correct_answer_count])

        # Move the cursor to the beginning of the file for reading
        output.seek(0)

        # Send the CSV file to the user
        await update.message.reply_document(
            document=InputFile(output, filename="words.csv"),
            caption="Here is the list of all words in CSV format."
        )

    except Exception as e:
        await update.message.reply_text(bot_phrases["export_error"].format(error=str(e)))
    finally:
        db.close()