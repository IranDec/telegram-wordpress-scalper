from telegram import Update, Message # Added Message for type hinting
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import logging

from src.config import TELEGRAM_BOT_TOKEN, OUT_OF_STOCK_KEYWORD, logger, get_telegram_channel_id
# Import the new processing functions that will be defined in main.py (or a new module)
# Note: If these functions are not yet defined in main.py, importing them will cause a runtime error
# until they are implemented. This is a structural change.
try:
    from src.main import process_telegram_post_to_product, process_telegram_reply_for_stock_update
except ImportError:
    logger.error("Failed to import processing functions from src.main. Ensure they are defined there.")
    # Define dummy functions if not found, so the bot can start, but processing won't work.
    async def process_telegram_post_to_product(message: Message, bot_instance):
        logger.warning(f"Dummy 'process_telegram_post_to_product' called for message ID {message.message_id}. Real function missing in src.main.")
    async def process_telegram_reply_for_stock_update(original_post: Message, reply_text: str, bot_instance):
        logger.warning(f"Dummy 'process_telegram_reply_for_stock_update' called for original post ID {original_post.message_id}. Real function missing in src.main.")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    channel_id = get_telegram_channel_id()
    await update.message.reply_html(
        rf"Hi {user.mention_html()}! I am your WooCommerce integration bot. "
        f"I am configured to monitor Telegram source ID: <b>{channel_id if channel_id else 'NOT SET'}</b>.",
    )
    logger.info(f"User {user.id} ({user.username}) initiated /start. Bot is set to monitor: {channel_id}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    channel_id = get_telegram_channel_id()
    help_text = (
        f"This bot monitors the Telegram channel/group: <b>{channel_id if channel_id else 'NOT SET'}</b> for new product posts.\n"
        f"It will attempt to add these products to your WooCommerce store.\n\n"
        f"If a reply to a product post in <b>{channel_id if channel_id else 'NOT SET'}</b> contains the keyword '<b>{OUT_OF_STOCK_KEYWORD}</b>' (case-insensitive), "
        "the corresponding product in WooCommerce will be marked as out of stock.\n\n"
        "<b>Available commands:</b>\n"
        "/start - Shows a welcome message and the monitored channel ID.\n"
        "/help - Displays this help message.\n\n"
        "<b>Important:</b>\n"
        "- Ensure all configurations (API keys, URLs, Channel ID) are correctly set in the <code>.env</code> file.\n"
        f"- The bot must be an administrator in the channel/group <b>{channel_id if channel_id else 'NOT SET'}</b> to read posts and replies."
    )
    await update.message.reply_html(help_text)
    logger.info(f"User {update.effective_user.id} requested /help for channel {channel_id}.")

async def handle_channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message: Message = update.channel_post
    if not message:
        logger.debug("Received CHANNLE_POST update without 'channel_post' attribute. Ignoring.")
        return

    logger.info(f"Received new post in channel {message.chat.id}. Message ID: {message.message_id}. Forwarding for processing.")
    await process_telegram_post_to_product(message, context.bot)

async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message: Message = update.message
    if not message or not message.reply_to_message:
        logger.debug("Message is not a reply or reply_to_message is missing. Ignoring.")
        return

    original_post: Message = message.reply_to_message
    logger.info(f"Received reply (ID: {message.message_id}) in chat {message.chat.id} to original message ID {original_post.message_id}. Reply text: '{message.text}'")

    if message.text and OUT_OF_STOCK_KEYWORD.lower() in message.text.lower():
        logger.info(f"Keyword '{OUT_OF_STOCK_KEYWORD}' detected in reply by {message.from_user.username or message.from_user.id}. Forwarding for stock update processing.")
        await process_telegram_reply_for_stock_update(original_post, message.text, context.bot)
    else:
        logger.debug(f"Reply (Message ID: {message.message_id}) did not contain keyword '{OUT_OF_STOCK_KEYWORD}'.")

def create_telegram_application():
    if not TELEGRAM_BOT_TOKEN:
        logger.critical("FATAL: TELEGRAM_BOT_TOKEN is not configured.")
        raise ValueError("Telegram Bot Token not found. Check .env file.")

    channel_id_str = get_telegram_channel_id()
    if not channel_id_str:
        logger.critical("FATAL: TELEGRAM_CHANNEL_ID is not configured.")
        raise ValueError("TELEGRAM_CHANNEL_ID not found. Check .env file.")

    logger.info(f"Initializing Telegram Application with Bot Token (ends '...{TELEGRAM_BOT_TOKEN[-5:]}').")
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))

    try:
        if channel_id_str.startswith('@'):
            chat_filter_id = channel_id_str
            logger.info(f"Configuring message handlers for Telegram username: {chat_filter_id}")
        elif channel_id_str.startswith('-') and channel_id_str[1:].isdigit():
            chat_filter_id = int(channel_id_str)
            logger.info(f"Configuring message handlers for numeric Telegram chat ID: {chat_filter_id}")
        else:
            err_msg = f"Invalid TELEGRAM_CHANNEL_ID format: '{channel_id_str}'. Must be '@username' or a negative number like '-100xxxxxxx'."
            logger.critical(f"FATAL: {err_msg}")
            raise ValueError(err_msg)

        application.add_handler(MessageHandler(filters.UpdateType.CHANNEL_POST & filters.Chat(chat_id=chat_filter_id), handle_channel_post))
        application.add_handler(MessageHandler(filters.REPLY & filters.Chat(chat_id=chat_filter_id) & filters.TEXT & (~filters.COMMAND), handle_reply))
        logger.info(f"Successfully configured message handlers for source: {chat_filter_id}")

    except ValueError as e:
        logger.critical(f"FATAL: Could not set up message handlers due to TELEGRAM_CHANNEL_ID issue: {e}")
        raise

    logger.info("Telegram Application initialized successfully.")
    return application

if __name__ == '__main__':
    logger.info("Running telegram_handler.py directly for testing...")
    try:
        # This import is crucial for the test to run properly if config.py does validation.
        from src.config import validate_basic_config
        validate_basic_config() # Validate .env variables
        app = create_telegram_application()
        logger.info("Telegram application created for testing. Starting polling...")
        # Note: This will only test the bot's ability to receive messages and call the imported
        # (or dummy) processing functions. The actual processing logic is in src.main.
        app.run_polling()
    except ValueError as ve: # Catch configuration errors specifically
        logger.critical(f"Testing setup failed due to invalid configuration: {ve}")
    except ImportError as ie:
        logger.critical(f"Import error during testing setup: {ie}. This might be due to missing functions in src.main.")
    except Exception as e:
        logger.critical(f"An unexpected error occurred during testing setup or polling: {e}", exc_info=True)
