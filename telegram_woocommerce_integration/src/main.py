import logging
from src.config import validate_basic_config, logger, get_telegram_channel_id
from src.telegram_handler import create_telegram_application

def main():
    logger.info("Application starting up...")
    try:
        validate_basic_config()
        channel_id = get_telegram_channel_id()
        logger.info(f"Configuration validated. Bot will monitor Telegram source: {channel_id}.")
    except ValueError as e:
        logger.critical(f"Configuration validation failed: {e}. Application cannot continue.")
        return

    try:
        application = create_telegram_application()
        logger.info("Telegram application instance created. Starting bot polling...")
        application.run_polling()
    except ValueError as e:
        logger.critical(f"Failed to initialize/run Telegram application: {e}")
    except Exception as e:
        logger.critical(f"Unexpected critical error running the bot: {e}", exc_info=True)
    finally:
        logger.info("Application shutting down or bot polling has stopped.")

if __name__ == "__main__":
    main()
