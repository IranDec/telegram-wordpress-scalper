import os
from dotenv import load_dotenv
import logging

dotenv_paths_to_check = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env')),
    os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '.env')),
    os.path.abspath('.env')
]

loaded_dotenv_path = None
for path_option in dotenv_paths_to_check:
    if os.path.exists(path_option):
        load_dotenv(path_option)
        loaded_dotenv_path = path_option
        break

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
WOOCOMMERCE_STORE_URL = os.getenv('WOOCOMMERCE_STORE_URL')
WOOCOMMERCE_CONSUMER_KEY = os.getenv('WOOCOMMERCE_CONSUMER_KEY')
WOOCOMMERCE_CONSUMER_SECRET = os.getenv('WOOCOMMERCE_CONSUMER_SECRET')
TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
OUT_OF_STOCK_KEYWORD = os.getenv('OUT_OF_STOCK_KEYWORD', 'تمام')
LOG_FILE_PATH = os.getenv('LOG_FILE_PATH', 'logs/app.log')
CRON_JOB_INTERVAL_MINUTES = int(os.getenv('CRON_JOB_INTERVAL_MINUTES', 15))

log_dir = os.path.dirname(LOG_FILE_PATH)
if log_dir and not os.path.exists(log_dir):
    os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE_PATH),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_telegram_channel_id():
    return TELEGRAM_CHANNEL_ID

def validate_basic_config():
    if loaded_dotenv_path:
        logger.info(f"Successfully loaded .env file from: {loaded_dotenv_path}")
    else:
        logger.warning(f"Could not find .env file at expected locations: {dotenv_paths_to_check}. Environment variables might not be loaded.")

    required_vars = {
        'TELEGRAM_BOT_TOKEN': TELEGRAM_BOT_TOKEN,
        'WOOCOMMERCE_STORE_URL': WOOCOMMERCE_STORE_URL,
        'WOOCOMMERCE_CONSUMER_KEY': WOOCOMMERCE_CONSUMER_KEY,
        'WOOCOMMERCE_CONSUMER_SECRET': WOOCOMMERCE_CONSUMER_SECRET,
        'TELEGRAM_CHANNEL_ID': get_telegram_channel_id()
    }
    missing_vars_details = [key for key, value in required_vars.items() if not value]
    if missing_vars_details:
        message = f"CRITICAL: Missing required configuration variables: {', '.join(missing_vars_details)}. Please check your .env file."
        logger.critical(message)
        raise ValueError(message)

    channel_id_val = get_telegram_channel_id()
    if channel_id_val and not channel_id_val.startswith('-') and not channel_id_val.startswith('@'):
        logger.warning(
            f"TELEGRAM_CHANNEL_ID ('{channel_id_val}') may not be in the correct format. "
            "Expected formats: '@channelusername' for public channels, or '-100xxxxxxxxxx' for private channels/supergroups."
        )
    logger.info("Basic configuration variables loaded. Validation passed.")

if __name__ == '__main__':
    logger.info("Running config.py self-test...")
    try:
        validate_basic_config()
        logger.info(f"Telegram Bot Token (first 5 chars): {TELEGRAM_BOT_TOKEN[:5] if TELEGRAM_BOT_TOKEN else 'Not Set'}...")
        logger.info(f"WooCommerce Store URL: {WOOCOMMERCE_STORE_URL}")
        logger.info(f"Telegram Channel ID from config: {get_telegram_channel_id()}")
        logger.info(f"Log file path: {LOG_FILE_PATH}")
    except ValueError as e:
        logger.error(f"Self-test validation failed: {e}")
