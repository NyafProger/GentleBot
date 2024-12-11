from telegram.ext import Application, CommandHandler, MessageHandler, filters
from bot import *
from database.base import engine, Base
import os
from dotenv import load_dotenv

def main() -> None:
    """Start the bot."""
    # Load environment variables from the .env file
    load_dotenv()
    api_key = os.getenv("API_KEY")
    application = Application.builder().token(api_key).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("add_word", add_word_command))
    application.add_handler(CommandHandler("quiz", quiz_command))
    application.add_handler(MessageHandler(filters.Regex("^(Далі|Хочу закінчити)$"), handle_quiz_choice))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_answer))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    main()