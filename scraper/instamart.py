from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
import time
import traceback
from datetime import datetime
import json
import gzip
import zlib
import re

def scrape_instamart(query, location):
    options = Options()
    options.headless = True
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    # options.add_argument('disable-capture=True')
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 5)  # Reduced wait for faster interaction
    products = []

    try:
        print("🔎 Opening Swiggy homepage...")
        driver.get("https://www.swiggy.com")
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        print("✅ Swiggy homepage loaded.")

        # Step 2: Select location
        print("🔎 Looking for location block...")
        location_block = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "_3YigA")))
        driver.execute_script("arguments[0].scrollIntoView(true);", location_block)
        location_block.click()
        print("✅ Location block clicked.")

        print("🔎 Entering location...")
        area_input = wait.until(
            EC.element_to_be_clickable((By.XPATH, '//input[@placeholder="Enter your delivery location" or @placeholder="Search for area, street name..."]'))
        )
        area_input.clear()
        area_input.send_keys(location)
        print("✅ Location entered.")
        time.sleep(1)
        wait.until(EC.visibility_of_element_located((By.XPATH, '//div[contains(@class,"_3bVtO")]//div[contains(@class,"_2BgUI")]')))
        first_suggestion = driver.find_element(By.XPATH, '(//div[contains(@class,"_3bVtO")]//div[contains(@class,"_2BgUI")])[1]')
        driver.execute_script("arguments[0].scrollIntoView(true);", first_suggestion)
        first_suggestion.click()
        print("✅ Location suggestion clicked.")
        time.sleep(3)
        # Step 3: Go to Instamart
        print("🔎 Looking for Instamart link...")
        instamart_block = wait.until(EC.element_to_be_clickable((By.XPATH, '//a[contains(@href,"instamart")]')))
        driver.execute_script("arguments[0].scrollIntoView(true);", instamart_block)
        instamart_block.click()
        print("✅ Instamart link clicked.")

        # Step 4: Search
        print("🔎 Looking for search button...")
        search_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[@data-testid="search-container"]')))
        driver.execute_script("arguments[0].click();", search_button)
        print("✅ Search button clicked.")

        # Click search box as soon as it appears
        time.sleep(1)
        search_box = wait.until(EC.element_to_be_clickable((By.XPATH, '//input[@data-testid="search-page-header-search-bar-input"]')))
        search_box.click()
        search_box.clear()
        search_box.send_keys(query)
        search_box.send_keys(Keys.ENTER)
        print(f"✅ Search for '{query}' submitted.")

        # Step 5: Wait for products
        time.sleep(3)
        print("🔎 Waiting for product results...")
        wait.until(EC.presence_of_all_elements_located((By.XPATH, '//div[@data-testid="default_container_ux4"]')))
        items = driver.find_elements(By.XPATH, '//div[@data-testid="default_container_ux4"]')
        print(f"✅ Found {len(items)} products.")

        # Scroll the product list container into view once
        if items:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", items[0])
            time.sleep(0.05)  # Short pause for initial images to load

        # Scrape products fast
        for idx, item in enumerate(items[:10]):  # Limit to 10 products for speed
            try:
                print(f"🔎 Scraping product {idx + 1}...")
                # Scroll product into view to trigger lazy loading of images
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", item)
                time.sleep(0.1)  # Even shorter pause for image to load

                name = item.find_element(By.XPATH, './/div[contains(@class,"novMV")]').text

                try:
                    # Explicitly wait for image if not present
                    img_tag = None
                    try:
                        img_tag = item.find_element(By.TAG_NAME, "img")
                    except:
                        WebDriverWait(item, 1).until(
                            lambda d: d.find_element(By.TAG_NAME, "img")
                        )
                        img_tag = item.find_element(By.TAG_NAME, "img")
                    img = img_tag.get_attribute("src") or img_tag.get_attribute("data-src") or img_tag.get_attribute(
                        "srcset")
                except Exception as e:
                    print(f"⚠️ Product {idx + 1}: No image found: {e}")
                    img = None

                try:
                    price = item.find_element(By.XPATH, './/div[@data-testid="item-offer-price"]').get_attribute(
                        "aria-label")
                except Exception as e:
                    print(f"⚠️ Product {idx + 1}: No price found: {e}")
                    price = None

                try:
                    quantity = item.find_element(By.XPATH,
                                                 './/div[contains(@class,"sc-aXZVg") and @aria-label]').get_attribute(
                        "aria-label")
                except Exception as e:
                    print(f"⚠️ Product {idx + 1}: No quantity found: {e}")
                    quantity = None

                try:
                    delivery_time = item.find_element(By.XPATH, './/div[contains(@class, "_1y_Uf")]').text.lower()
                except Exception as e:
                    print(f"⚠️ Product {idx + 1}: No delivery time found: {e}")
                    delivery_time = None

                products.append({
                    "name": name,
                    "price": price,
                    "image": img,
                    "quantity": quantity,
                    "delivery_time": delivery_time,
                    "source": "Instamart",
                    "search_query": query,
                    "location": location,
                    "scraped_at": datetime.now()
                })

            except Exception as e:
                print(f"❌ Failed to scrape product {idx + 1}: {e}")
                continue

        # --- Extract storeid, product_id, and rating from JSON response ---
        print("🔎 Extracting product details from JSON responses...")
        storeid = None
        product_id_map = {}
        rating_map = {}
        store_id_map = {}

        for request in getattr(driver, "requests", []):
            if request.response and "search" in request.url and request.response.headers.get('Content-Type', '').startswith('application/json'):
                try:
                    body = request.response.body
                    try:
                        data = gzip.decompress(body).decode('utf-8')
                    except Exception:
                        try:
                            data = zlib.decompress(body, 16+zlib.MAX_WBITS).decode('utf-8')
                        except Exception:
                            data = body.decode('utf-8')

                    j = json.loads(data)

                    def normalize(name):
                        return name.strip().lower() if name else ""

                    scraped_names_set = set(normalize(p['name']) for p in products)

                    widgets = j.get("data", {}).get("widgets", [])
                    for widget in widgets:
                        for product in widget.get("data", []):
                            pname = product.get("display_name") or product.get("product_name_without_brand") or product.get("brand") or "Unknown"
                            norm_pname = normalize(pname)
                            if norm_pname in scraped_names_set and product.get("product_id"):
                                rating = product.get("rating", {}).get("value")
                                store_id = product.get("store_id")
                                if not rating or not store_id:
                                    if product.get("variations"):
                                        first_var = product["variations"][0]
                                        rating = rating or first_var.get("rating", {}).get("value")
                                        store_id = store_id or first_var.get("store_id")
                                product_id_map[pname] = product.get("product_id")
                                rating_map[pname] = rating
                                store_id_map[pname] = store_id
                            for variation in product.get("variations", []):
                                vpname = variation.get("display_name") or variation.get("product_name_without_brand") or variation.get("brand") or "Unknown"
                                norm_vpname = normalize(vpname)
                                if norm_vpname in scraped_names_set and variation.get("product_id"):
                                    product_id_map[vpname] = variation.get("product_id")
                                    rating_map[vpname] = variation.get("rating", {}).get("value")
                                    store_id_map[vpname] = variation.get("store_id")

                except Exception as e:
                    print("❌ Error parsing JSON:", e)
                    continue

        print("🔎 Enriching scraped products with IDs and ratings...")
        def normalize(name):
            if not name:
                return ""
            name = name.strip().lower()
            name = re.sub(r'[^a-z0-9 ]', '', name)
            name = re.sub(r'\s+', ' ', name)
            return name

        scraped_names_set = set(normalize(p['name']) for p in products)
        normalized_json_map = {normalize(k): k for k in product_id_map.keys()}

        for p in products:
            norm_name = normalize(p['name'])
            json_name = normalized_json_map.get(norm_name)
            if json_name:
                p['product_id'] = product_id_map.get(json_name)
                p['rating'] = rating_map.get(json_name)
                p['storeid'] = store_id_map.get(json_name)
                if p['product_id'] and p['storeid']:
                    p['product_url'] = f"https://www.swiggy.com/instamart/item/{p['product_id']}?storeId={p['storeid']}"
                else:
                    p['product_url'] = None
            else:
                p['product_id'] = None
                p['rating'] = None
                p['storeid'] = None
                p['product_url'] = None

        print("✅ Instamart scraping finished.")

    except Exception as e:
        print("❌ Error while scraping:")
        traceback.print_exc()

    finally:
        driver.quit()

    return products
