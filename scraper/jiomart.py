import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from selenium.webdriver.common.action_chains import ActionChains
import warnings
import sys
from datetime import datetime
import random

if sys.platform == "win32":
    warnings.filterwarnings("ignore", category=ResourceWarning)

def safe_del(self):
    try:
        self.quit()
    except Exception:
        pass

uc.Chrome.__del__ = safe_del

def scrape_jiomart(query, location):
    options = uc.ChromeOptions()
    # REMOVE headless for debugging
    # options.headless = True
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    prefs = {
        "profile.default_content_setting_values.geolocation": 2
    }
    options.add_experimental_option("prefs", prefs)

    driver = uc.Chrome(options=options)
    wait = WebDriverWait(driver, 8)
    products = []

    try:
        print("🔎 Opening JioMart homepage...")
        driver.get("https://www.jiomart.com/")
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        print("✅ Page loaded.")

        # --- Click "Select Location Manually" button if present ---
        try:
            print("🔎 Looking for 'Select Location Manually' button...")
            manual_btn = wait.until(
                EC.element_to_be_clickable((By.ID, "select_location_popup"))
            )
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", manual_btn)
            manual_btn.click()
            print("✅ Clicked 'Select Location Manually'.")
        except Exception as e:
            print("❌ Could not click 'Select Location Manually' button:", e)

        # --- Location Modal Handling ---
        for attempt in range(3):  # Try up to 3 times
            try:
                print(f"🔎 Attempt {attempt+1}: Setting location...")
                select_location_input = wait.until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//input[@placeholder='Search for area, landmark']")
                    )
                )
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", select_location_input)
                select_location_input.click()

                location_input = wait.until(EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "input#searchin.pac-target-input")
                ))
                driver.execute_script("arguments[0].scrollIntoView(true);", location_input)

                location_input.clear()
                for char in location:
                    location_input.send_keys(char)
                    time.sleep(0.01)  # Fast typing

                time.sleep(1)  # Short wait for suggestions

                location_input.send_keys(Keys.ARROW_DOWN)
                time.sleep(0.1)
                location_input.send_keys(Keys.ENTER)
                time.sleep(0.3)

                # Confirm Location
                try:
                    confirm_btn = wait.until(EC.element_to_be_clickable(
                        (
                            By.XPATH,
                            "//button[contains(@class, 'j-button') and contains(@class, 'primary') and contains(@aria-label, 'Confirm Location')]"
                        )
                    ))
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", confirm_btn)
                    confirm_btn.click()
                    print("✅ Location confirmed.")
                    time.sleep(0.3)
                except Exception as e:
                    print("❌ Could not click Confirm Location button:", e)
                break  # Success, exit retry loop
            except Exception as e:
                print(f"❌ Location setting attempt {attempt+1} failed:", e)
                driver.save_screenshot(f"jiomart_location_fail_{attempt+1}.png")
                if attempt == 2:
                    with open("location_fail.html", "w", encoding="utf-8") as f:
                        f.write(driver.page_source)
                    print("❌ Location setting failed after retries:", e)
                    return []
                else:
                    time.sleep(1)  # Shorter retry wait

        print("🔎 Searching for products...")
        search_box = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input#autocomplete-0-input")))
        search_box.clear()
        search_box.send_keys(query)
        search_box.send_keys(Keys.ENTER)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.ais-InfiniteHits")))
        print("✅ Product list loaded.")

        # ✅ Scrape Products (no sleep, limit to 10)
        items = driver.find_elements(By.CSS_SELECTOR, "ol.ais-InfiniteHits-list > li.ais-InfiniteHits-item")[:10]
        print(f"🔎 Found {len(items)} product cards.")
        for idx, item in enumerate(items):
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", item)
            time.sleep(0.1)
            try:
                # Only scroll if you notice images not loading
                # driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", item)
                url = item.find_element(By.CSS_SELECTOR, "a.plp-card-wrapper").get_attribute("href")
            except Exception as e:
                print(f"❌ Product {idx+1}: Failed to get URL:", e)
                url = None
            try:
                name = item.find_element(By.CSS_SELECTOR, "div.plp-card-details-name").text
            except Exception as e:
                print(f"❌ Product {idx+1}: Failed to get name:", e)
                name = None
            try:
                price_text = item.find_element(By.CSS_SELECTOR, "div.plp-card-details-price span.jm-heading-xxs").text
                price = price_text.replace("₹", "").strip()
            except Exception as e:
                print(f"❌ Product {idx+1}: Failed to get price:", e)
                price = None
            try:
                img_elem = item.find_element(By.CSS_SELECTOR, "div.plp-card-image img")
                img = img_elem.get_attribute("src")
                if not img or img.strip() == "":
                    img = img_elem.get_attribute("data-src")
            except Exception as e:
                print(f"❌ Product {idx+1}: Failed to get image:", e)
                img = None
            try:
                delivery_time = item.find_element(By.CSS_SELECTOR, "span.jm-body-xxs-bold.qc-card-tag").text
            except Exception as e:
                print(f"❌ Product {idx+1}: Failed to get delivery time:", e)
                delivery_time = None

            products.append({
                "name": name,
                "price": price,
                "image": img,
                "product_url": url,
                "delivery_time": delivery_time,
                "source": "jiomart",
                "location": location,
                "scraped_at": datetime.now()
            })

    except Exception as e:
        print("❌ JioMart scraping failed:", e)
        driver.save_screenshot("jiomart_scrape_fail.png")
    finally:
        driver.quit()

    return products
