import telegram
import logging
import asyncio # Required for python-telegram-bot v20+
from . import config

logger = logging.getLogger(__name__)

async def send_telegram_message(message):
    """
    Sends a message to the Telegram channel specified in the config.
    """
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHANNEL_ID:
        logger.error("Telegram Bot Token or Channel ID is not configured.")
        return False

    try:
        bot = telegram.Bot(token=config.TELEGRAM_BOT_TOKEN)
        logger.info(f"Attempting to send message to channel {config.TELEGRAM_CHANNEL_ID}: {message[:50]}...") # Log first 50 chars

        # Ensure TELEGRAM_CHANNEL_ID is correctly formatted (e.g., '@channelusername' or chat_id)
        # For public channels, it's usually '@channelusername'. For private, it's the chat_id.
        # If channel_id is a numeric string, it might need to be an int.
        chat_id = config.TELEGRAM_CHANNEL_ID
        try:
            chat_id = int(chat_id)
        except ValueError:
            # If it's not a number, it's likely a username like '@channelname'
            pass

        await bot.send_message(chat_id=chat_id, text=message, parse_mode=telegram.constants.ParseMode.HTML)
        logger.info("Message sent successfully to Telegram.")
        return True
    except telegram.error.TelegramError as e:
        logger.error(f"Telegram Error: {e} - Response: {e.message}")
        # Specific error handling based on error type
        if isinstance(e, telegram.error.BadRequest):
            logger.error(f"Bad Request: {e.message}. This might be due to an invalid chat_id or message format.")
        elif isinstance(e, telegram.error.Unauthorized):
            logger.error(f"Unauthorized: {e.message}. Check your bot token.")
        elif isinstance(e, telegram.error.ChatMigrated):
            logger.error(f"Chat migrated to a new chat ID: {e.new_chat_id}")
            # Potentially update config or notify admin
        elif isinstance(e, telegram.error.NetworkError):
            logger.error(f"Network error: {e.message}. Check internet connection or Telegram service status.")
        else:
            logger.error(f"An unexpected Telegram error occurred: {e.message}")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred while sending Telegram message: {e}")
        return False

async def send_product_update_to_telegram(product_name, product_url, old_status, new_status):
    """
    Formats and sends a product status update to Telegram.
    """
    message = (
        f"<b>Product Stock Update:</b>\n"
        f"Product: <a href='{product_url}'>{product_name}</a>\n"
        f"Status changed from <b>{old_status}</b> to <b>{new_status}</b>."
    )
    return await send_telegram_message(message)

async def send_out_of_stock_notification(product_name, product_id, product_permalink):
    """
    Sends a notification for a product that is newly out of stock.
    """
    message = (
        f"<b>❗ Out of Stock Alert ❗</b>\n\n"
        f"Product: <b>{product_name}</b> (ID: {product_id})\n"
        f"Is now marked as out of stock or contains the keyword '{config.OUT_OF_STOCK_KEYWORD}'.\n"
        f"Link: <a href='{product_permalink}'>{product_permalink}</a>\n\n"
        f"Please verify and update the product listing if necessary."
    )
    return await send_telegram_message(message)

if __name__ == '__main__':
    # This is for testing purposes.
    # Remember to set up your .env file with actual credentials before running.
    import logging.config
    logging.config.dictConfig(config.LOGGING_CONFIG)

    logger.info("Testing Telegram Handler...")

    # Create a .env file with your actual bot token and channel ID for testing
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHANNEL_ID:
        logger.warning("Telegram environment variables (token or channel ID) are not set. Skipping live API test.")
        print("Please set up your .env file with Telegram credentials to test this module.")
    else:
        async def main_test():
            test_message_sent = await send_telegram_message("<b>Test Message:</b> Hello from the WooCommerce Integration Script! (Async test)")
            if test_message_sent:
                logger.info("Test message sent successfully via send_telegram_message.")
            else:
                logger.error("Failed to send test message via send_telegram_message.")

            # Test product update message
            test_product_update_sent = await send_product_update_to_telegram(
                product_name="Awesome T-Shirt",
                product_url="http://example.com/product/awesome-t-shirt",
                old_status="In Stock",
                new_status="Out of Stock (Keyword)"
            )
            if test_product_update_sent:
                logger.info("Test product update message sent successfully.")
            else:
                logger.error("Failed to send test product update message.")

            test_out_of_stock_notification = await send_out_of_stock_notification(
                product_name="Sample Product Gone",
                product_id="12345",
                product_permalink="http://example.com/product/sample-product-gone"
            )
            if test_out_of_stock_notification:
                logger.info("Test out-of-stock notification sent successfully.")
            else:
                logger.error("Failed to send test out-of-stock notification.")

        # Running the async main_test function
        # In a script, you would typically use asyncio.run(main_test())
        # For compatibility with various environments, using get_event_loop if already running
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError: # 'RuntimeError: There is no current event loop...'
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            # If loop is already running (e.g. in Jupyter), create a task
            loop.create_task(main_test())
        else:
            asyncio.run(main_test())

    logger.info("Telegram Handler test finished.")
