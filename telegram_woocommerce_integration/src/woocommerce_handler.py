# woocommerce_handler_py_content
import logging
from woocommerce import API
from src.config import (
    logger,
    WOOCOMMERCE_STORE_URL,
    WOOCOMMERCE_CONSUMER_KEY,
    WOOCOMMERCE_CONSUMER_SECRET
)

def get_wc_api_client():
    """
    Initializes and returns a WooCommerce API client.
    Returns None if configuration is missing.
    """
    if not all([WOOCOMMERCE_STORE_URL, WOOCOMMERCE_CONSUMER_KEY, WOOCOMMERCE_CONSUMER_SECRET]):
        logger.error("WooCommerce API credentials (URL, Key, or Secret) are not fully configured in .env.")
        return None

    try:
        wcapi = API(
            url=WOOCOMMERCE_STORE_URL,
            consumer_key=WOOCOMMERCE_CONSUMER_KEY,
            consumer_secret=WOOCOMMERCE_CONSUMER_SECRET,
            version="wc/v3",
            timeout=10  # Added timeout
        )
        logger.info(f"WooCommerce API client initialized for URL: {WOOCOMMERCE_STORE_URL}")
        return wcapi
    except Exception as e:
        logger.error(f"Failed to initialize WooCommerce API client: {e}", exc_info=True)
        return None

def test_woocommerce_connection():
    """
    Tests the connection to the WooCommerce API by fetching store information.
    Returns True if connection is successful, False otherwise.
    """
    logger.info("Testing WooCommerce API connection...")
    wcapi = get_wc_api_client()
    if not wcapi:
        logger.error("Cannot test WooCommerce connection: API client failed to initialize.")
        return False

    try:
        # A simple GET request, like fetching system status or main endpoint
        response = wcapi.get("") # Fetches the index of the API
        if response.status_code == 200:
            store_data = response.json()
            logger.info(f"WooCommerce API connection successful. Store name: {store_data.get('name', 'N/A')}")
            return True
        else:
            logger.error(f"WooCommerce API connection test failed. Status code: {response.status_code}, Response: {response.text[:200]}")
            return False
    except Exception as e:
        logger.error(f"Error during WooCommerce API connection test: {e}", exc_info=True)
        return False

def get_product_by_sku(sku: str):
    """
    Retrieves a product from WooCommerce by its SKU.
    Returns the product data if found, None otherwise.
    """
    if not sku:
        logger.warning("SKU not provided for get_product_by_sku.")
        return None

    wcapi = get_wc_api_client()
    if not wcapi:
        return None

    logger.info(f"Searching for product with SKU: {sku}")
    try:
        response = wcapi.get("products", params={"sku": sku})
        products = response.json()
        if response.status_code == 200 and products:
            logger.info(f"Found product with SKU '{sku}': {products[0]['name']}")
            return products[0]
        elif not products:
            logger.info(f"No product found with SKU: {sku}")
            return None
        else:
            logger.error(f"Failed to get product by SKU '{sku}'. Status: {response.status_code}, Response: {response.text[:200]}")
            return None
    except Exception as e:
        logger.error(f"Exception while getting product by SKU '{sku}': {e}", exc_info=True)
        return None

def create_woocommerce_product(product_data: dict):
    """
    Creates a new product in WooCommerce.
    product_data should be a dictionary conforming to WooCommerce API for products.
    Example: {'name': 'Test Product', 'type': 'simple', 'regular_price': '10.99', 'sku': 'TEST001'}
    Returns the created product data from API or None on failure.
    """
    wcapi = get_wc_api_client()
    if not wcapi:
        return None

    logger.info(f"Attempting to create WooCommerce product: {product_data.get('name', 'N/A')} (SKU: {product_data.get('sku', 'N/A')})")
    try:
        response = wcapi.post("products", product_data)
        if response.status_code == 201: # 201 Created
            created_product = response.json()
            logger.info(f"Successfully created product '{created_product['name']}' (ID: {created_product['id']}) in WooCommerce.")
            return created_product
        else:
            logger.error(f"Failed to create product. Status: {response.status_code}, Response: {response.text[:500]}") # Log more of the error
            return None
    except Exception as e:
        logger.error(f"Exception during product creation: {e}", exc_info=True)
        return None

def update_woocommerce_product_stock(product_id: int, stock_status: str = 'outofstock', stock_quantity: int = 0):
    """
    Updates the stock status and quantity of a product in WooCommerce.
    product_id: The WooCommerce product ID.
    stock_status: 'instock', 'outofstock', or 'onbackorder'.
    stock_quantity: The new stock quantity. Only set if manage_stock is true for the product.
    """
    wcapi = get_wc_api_client()
    if not wcapi:
        return None

    data = {
        "stock_status": stock_status
    }
    # If manage_stock is True for a product, WooCommerce expects stock_quantity.
    # However, simply setting stock_status is often sufficient for products not managing stock at product level.
    # For robustness, this example primarily focuses on stock_status.
    # If stock_quantity is explicitly provided and non-zero, or if the intention is to manage stock,
    # this part might need adjustment, e.g. by first fetching product to check 'manage_stock'
    # data['manage_stock'] = True # If you want to enforce stock management
    # data['stock_quantity'] = stock_quantity # Then also set quantity

    logger.info(f"Attempting to update stock for product ID {product_id} to '{stock_status}'.")
    try:
        response = wcapi.put(f"products/{product_id}", data)
        if response.status_code == 200:
            updated_product = response.json()
            logger.info(f"Successfully updated stock for product ID {product_id}. New status: {updated_product.get('stock_status')}")
            return updated_product
        else:
            logger.error(f"Failed to update stock for product ID {product_id}. Status: {response.status_code}, Response: {response.text[:500]}")
            return None
    except Exception as e:
        logger.error(f"Exception during stock update for product ID {product_id}: {e}", exc_info=True)
        return None

if __name__ == "__main__":
    logger.info("Running woocommerce_handler.py directly for testing...")
    # Ensure config is loaded and validated if you are using validate_basic_config from config.py
    # from src.config import validate_basic_config
    # try:
    #     validate_basic_config() # This is important if the functions rely on it for pre-checks
    # except ValueError as e:
    #    logger.error(f"Configuration validation failed: {e}. Tests might not run correctly.")
    #    # Depending on severity, you might exit or just warn

    connection_ok = test_woocommerce_connection()
    logger.info(f"WooCommerce connection test result: {'OK' if connection_ok else 'Failed'}")

    if connection_ok:
        logger.info("Attempting further tests (get, create, update)... This requires a live WooCommerce store and valid API keys.")

        sku_to_test = "TESTSKU123" # Example SKU
        product = get_product_by_sku(sku_to_test)
        if product:
            logger.info(f"Found product by SKU '{sku_to_test}': ID {product['id']}, Name: {product['name']}")
        else:
            logger.info(f"Product with SKU '{sku_to_test}' not found or API call failed. This might be expected if it doesn't exist.")

        new_product_data = {
            'name': 'Bot Test Product Py',
            'type': 'simple',
            'regular_price': '23.99',
            'sku': 'BOTTESTPY001', # Using a unique SKU
            'description': 'This is a test product created by the bot script for testing purposes.',
            'stock_status': 'instock' # Initially in stock
        }

        # Check if product with this SKU already exists to avoid error on re-run
        existing_test_product = get_product_by_sku(new_product_data['sku'])
        created_product = None
        if not existing_test_product:
            created_product = create_woocommerce_product(new_product_data)
            if created_product:
                logger.info(f"Test product created: ID {created_product['id']}, Name: {created_product['name']}")
            else:
                logger.error("Failed to create test product. Further tests depending on it will be skipped.")
        else:
            logger.info(f"Test product with SKU {new_product_data['sku']} already exists (ID: {existing_test_product['id']}). Using existing product for update test.")
            created_product = existing_test_product


        if created_product and created_product.get('id'):
            product_id_to_update = created_product['id']

            # Test updating stock to 'outofstock'
            logger.info(f"Attempting to mark product ID {product_id_to_update} as out of stock...")
            updated_product_stock_out = update_woocommerce_product_stock(product_id_to_update, stock_status='outofstock')
            if updated_product_stock_out:
                logger.info(f"Stock updated for product ID {product_id_to_update}. New status: {updated_product_stock_out.get('stock_status')}")
            else:
                logger.error(f"Failed to update stock to 'outofstock' for product ID {product_id_to_update}.")

            # Test updating stock back to 'instock' (optional, good for cleanup)
            # logger.info(f"Attempting to mark product ID {product_id_to_update} as back in stock...")
            # updated_product_stock_in = update_woocommerce_product_stock(product_id_to_update, stock_status='instock')
            # if updated_product_stock_in:
            #     logger.info(f"Stock updated for product ID {product_id_to_update}. New status: {updated_product_stock_in.get('stock_status')}")
            # else:
            #     logger.error(f"Failed to update stock to 'instock' for product ID {product_id_to_update}.")
        elif not created_product : #Only log if it failed and was not pre-existing
             logger.warning("Skipping product update tests as test product creation/retrieval failed.")

    else:
        logger.warning("Skipping further WooCommerce interaction tests as the initial connection test failed (likely due to placeholder credentials or network issues).")

    logger.info("woocommerce_handler.py test run finished.")
