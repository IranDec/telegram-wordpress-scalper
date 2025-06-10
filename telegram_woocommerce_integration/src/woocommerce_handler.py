import requests
import logging
from . import config

logger = logging.getLogger(__name__)

def get_products(page=1, per_page=10):
    """
    Fetches products from WooCommerce API.
    Handles pagination.
    """
    if not config.WOOCOMMERCE_STORE_URL or \
       not config.WOOCOMMERCE_CONSUMER_KEY or \
       not config.WOOCOMMERCE_CONSUMER_SECRET:
        logger.error("WooCommerce API credentials are not configured.")
        return []

    products_url = f"{config.WOOCOMMERCE_STORE_URL.rstrip('/')}/wp-json/wc/v3/products"
    params = {
        "consumer_key": config.WOOCOMMERCE_CONSUMER_KEY,
        "consumer_secret": config.WOOCOMMERCE_CONSUMER_SECRET,
        "page": page,
        "per_page": per_page,
        "status": "publish", # Fetch only published products
    }
    try:
        response = requests.get(products_url, params=params, timeout=20)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching products from WooCommerce: {e}")
        return []

def get_all_products():
    """
    Fetches all products from WooCommerce, handling pagination.
    """
    all_products = []
    page = 1
    per_page = 20 # Adjust as needed, max 100 for WooCommerce
    while True:
        logger.info(f"Fetching products page {page}...")
        products = get_products(page=page, per_page=per_page)
        if not products:
            break
        all_products.extend(products)
        if len(products) < per_page: # Last page
            break
        page += 1
    logger.info(f"Total products fetched: {len(all_products)}")
    return all_products

def check_product_stock_status(product):
    """
    Checks if a product is out of stock based on its name containing a keyword.
    Returns True if out of stock, False otherwise.
    """
    if not product or 'name' not in product:
        logger.warning("Invalid product data received.")
        return False

    product_name = product['name'].lower()
    # Check if the product is marked as out of stock or if its name contains the keyword
    is_out_of_stock_api = not product.get('in_stock', True) # if in_stock is missing, assume it is in stock

    keyword_in_name = config.OUT_OF_STOCK_KEYWORD.lower() in product_name

    if is_out_of_stock_api:
        logger.info(f"Product '{product['name']}' (ID: {product['id']}) is out of stock via API status.")
        return True

    if keyword_in_name:
        logger.info(f"Product '{product['name']}' (ID: {product['id']}) contains out-of-stock keyword.")
        return True

    return False

if __name__ == '__main__':
    # This is for testing purposes.
    # Remember to set up your .env file with actual credentials before running.
    import logging.config
    logging.config.dictConfig(config.LOGGING_CONFIG)

    logger.info("Testing WooCommerce Handler...")

    # Create a .env file with your actual store URL and keys for testing
    if not all([config.WOOCOMMERCE_STORE_URL, config.WOOCOMMERCE_CONSUMER_KEY, config.WOOCOMMERCE_CONSUMER_SECRET]):
        logger.warning("WooCommerce environment variables are not set. Skipping live API test.")
        print("Please set up your .env file with WooCommerce credentials to test this module.")
    else:
        logger.info(f"Fetching products from {config.WOOCOMMERCE_STORE_URL}")

        # Test fetching a single page of products
        # products_page = get_products(per_page=5)
        # if products_page:
        #     logger.info(f"Successfully fetched {len(products_page)} products for the first page.")
        #     for prod in products_page:
        #         logger.info(f"Product: {prod['name']} (ID: {prod['id']}), Stock Status: {'Out of Stock' if not prod.get('in_stock') else 'In Stock'}")
        # else:
        #     logger.warning("Could not fetch any products for the first page test.")

        # Test fetching all products
        all_prods = get_all_products()
        if all_prods:
            logger.info(f"Successfully fetched a total of {len(all_prods)} products.")
            out_of_stock_count = 0
            for i, prod in enumerate(all_prods):
                # if i < 5: # Log details for the first 5 products
                #     logger.info(f"Product: {prod['name']} (ID: {prod['id']}), Stock Status: {'Out of Stock' if not prod.get('in_stock') else 'In Stock'}, Price: {prod.get('price')}")
                if check_product_stock_status(prod):
                    out_of_stock_count += 1
                    logger.info(f"Product identified as out of stock: {prod['name']}")
            logger.info(f"Total products identified as out of stock by keyword or API: {out_of_stock_count}")
        else:
            logger.warning("Could not fetch any products for the all products test.")
    logger.info("WooCommerce Handler test finished.")
