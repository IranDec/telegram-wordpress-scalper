import logging
import logging.config
import time
import schedule
import asyncio
from datetime import datetime

from . import config
from . import woocommerce_handler as wc
from . import telegram_handler as tg

# Configure logging
logging.config.dictConfig(config.LOGGING_CONFIG)
logger = logging.getLogger(__name__)

# In-memory store for product stock states
# Structure: {product_id: {"name": "Product Name", "is_out_of_stock": False, "permalink": "url"}}
# This helps in detecting changes in stock status.
PRODUCT_STOCK_STATES = {}
INITIAL_RUN_COMPLETE = False # Flag to track if the first full scan is done

async def check_and_notify_products():
    """
    Fetches all products from WooCommerce, checks their stock status,
    and sends a Telegram notification if a product is found to be out of stock
    and hasn't been notified about recently or its status changed.
    """
    global PRODUCT_STOCK_STATES, INITIAL_RUN_COMPLETE
    logger.info("Starting product stock check run...")

    current_products_api = wc.get_all_products()
    if not current_products_api:
        logger.warning("No products returned from WooCommerce API. Skipping this run.")
        return

    current_cycle_product_ids = set()

    for product in current_products_api:
        product_id = product.get('id')
        product_name = product.get('name', 'Unknown Product')
        permalink = product.get('permalink', '')
        current_cycle_product_ids.add(product_id)

        if not product_id:
            logger.warning(f"Product missing ID: {product_name}. Skipping.")
            continue

        is_currently_out_of_stock = wc.check_product_stock_status(product)
        previous_state = PRODUCT_STOCK_STATES.get(product_id)

        if previous_state is None:
            # New product or first run
            PRODUCT_STOCK_STATES[product_id] = {
                "name": product_name,
                "is_out_of_stock": is_currently_out_of_stock,
                "permalink": permalink,
                "notified": False # Add a notified flag
            }
            if is_currently_out_of_stock:
                logger.info(f"New product or first scan: '{product_name}' (ID: {product_id}) is out of stock.")
                if INITIAL_RUN_COMPLETE: # Only notify for new products if after initial scan
                    await tg.send_out_of_stock_notification(product_name, product_id, permalink)
                    PRODUCT_STOCK_STATES[product_id]["notified"] = True
            # else: No need to log if it's in stock on first sight unless debugging

        else:
            # Existing product, check for state change
            if is_currently_out_of_stock != previous_state["is_out_of_stock"]:
                logger.info(f"Stock status changed for '{product_name}' (ID: {product_id}): "
                            f"From {'Out of Stock' if previous_state['is_out_of_stock'] else 'In Stock'} "
                            f"to {'Out of Stock' if is_currently_out_of_stock else 'In Stock'}.")
                PRODUCT_STOCK_STATES[product_id]["is_out_of_stock"] = is_currently_out_of_stock

                if is_currently_out_of_stock:
                    await tg.send_out_of_stock_notification(product_name, product_id, permalink)
                    PRODUCT_STOCK_STATES[product_id]["notified"] = True
                else:
                    # Optional: Notify when back in stock
                    # await tg.send_telegram_message(f"Product '{product_name}' is back in stock!\n{permalink}")
                    PRODUCT_STOCK_STATES[product_id]["notified"] = False # Reset notified status
                    logger.info(f"Product '{product_name}' (ID: {product_id}) is back in stock.")

            elif is_currently_out_of_stock and not previous_state.get("notified", False):
                # It was already out of stock, but we haven't notified yet (e.g. if script restarted)
                # Or if it was out of stock on the very first run AND INITIAL_RUN_COMPLETE was false
                logger.info(f"Re-confirming out of stock for '{product_name}' (ID: {product_id}). Sending notification.")
                await tg.send_out_of_stock_notification(product_name, product_id, permalink)
                PRODUCT_STOCK_STATES[product_id]["notified"] = True

        # Update permalink and name in case they changed
        if previous_state and (previous_state["name"] != product_name or previous_state["permalink"] != permalink) :
            PRODUCT_STOCK_STATES[product_id]["name"] = product_name
            PRODUCT_STOCK_STATES[product_id]["permalink"] = permalink


    # After the first full successful run, set the flag
    if not INITIAL_RUN_COMPLETE and current_products_api: # Ensure API call was successful
        INITIAL_RUN_COMPLETE = True
        logger.info("Initial product scan complete. Future new out-of-stock items will trigger notifications immediately.")
        # For products that were out of stock on the very first scan run:
        # Iterate through PRODUCT_STOCK_STATES and send notifications if they are out_of_stock and not notified
        # This ensures that items OOS at startup are also notified once after the first scan.
        logger.info("Sending notifications for products found out of stock during the initial scan...")
        for product_id, state in PRODUCT_STOCK_STATES.items():
            if state["is_out_of_stock"] and not state.get("notified", False):
                logger.info(f"Initial scan: Notifying for OOS product '{state['name']}' (ID: {product_id}).")
                await tg.send_out_of_stock_notification(state['name'], product_id, state['permalink'])
                PRODUCT_STOCK_STATES[product_id]["notified"] = True


    # Remove products from PRODUCT_STOCK_STATES if they are no longer in the API (e.g., deleted)
    # This prevents the dictionary from growing indefinitely with old products.
    deleted_product_ids = set(PRODUCT_STOCK_STATES.keys()) - current_cycle_product_ids
    if deleted_product_ids:
        for product_id in deleted_product_ids:
            logger.info(f"Product ID {product_id} (Name: {PRODUCT_STOCK_STATES[product_id]['name']}) no longer found in API. Removing from local state.")
            del PRODUCT_STOCK_STATES[product_id]

    logger.info(f"Product stock check finished. Current state for {len(PRODUCT_STOCK_STATES)} products tracked.")


def run_scheduler():
    """
    Runs the scheduler for periodically checking products.
    """
    logger.info(f"Scheduler started. Will run job every {config.CRON_JOB_INTERVAL_MINUTES} minutes.")

    # Run the job once immediately, then schedule
    # Using asyncio.run for the async function
    try:
        asyncio.run(check_and_notify_products())
    except Exception as e:
        logger.error(f"Error during initial async job run: {e}", exc_info=True)

    schedule.every(config.CRON_JOB_INTERVAL_MINUTES).minutes.do(lambda: asyncio.run(check_and_notify_products_job()))

    while True:
        schedule.run_pending()
        time.sleep(1)

async def check_and_notify_products_job():
    """ Helper for scheduling async job """
    try:
        await check_and_notify_products()
    except Exception as e:
        logger.error(f"Error during scheduled async job run: {e}", exc_info=True)


if __name__ == "__main__":
    logger.info("Application starting...")
    if not all([config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHANNEL_ID,
                config.WOOCOMMERCE_STORE_URL, config.WOOCOMMERCE_CONSUMER_KEY,
                config.WOOCOMMERCE_CONSUMER_SECRET]):
        logger.error("CRITICAL: One or more essential environment variables are not set. Exiting.")
        print("Error: Essential environment variables are missing. Please check your .env file or environment configuration.")
    else:
        logger.info("All essential configurations seem to be in place.")
        try:
            run_scheduler()
        except KeyboardInterrupt:
            logger.info("Application shutting down...")
        except Exception as e:
            logger.critical(f"An unhandled exception occurred in main: {e}", exc_info=True)
        finally:
            logger.info("Application stopped.")
