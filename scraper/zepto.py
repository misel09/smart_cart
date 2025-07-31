from pymongo import MongoClient
from dotenv import load_dotenv
import os
from datetime import datetime
def scrape(query, location):
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.common.keys import Keys
    import time
    import re

    products = []
    delivery_time = None

    options = Options()
    options.headless = True
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--start-maximized")
    # Disable images for faster loading
    prefs = {"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 8)

    try:
        driver.get("https://www.zeptonow.com/")
        time.sleep(1)
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Select Location"]'))).click()

        # Input location
        location_input = wait.until(EC.presence_of_element_located((By.XPATH, '//input[@placeholder="Search a new address"]')))
        location_input.clear()
        location_input.send_keys(location)
        time.sleep(1)
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'div[data-testid="address-search-item"]'))).click()
        time.sleep(1)
        try:
            wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-testid="location-confirm-btn"]'))).click()
            time.sleep(1)
        except Exception:
            pass

        # Get delivery time
        try:
            delivery_time_elem = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, '//*[contains(@data-testid, "delivery-time")]//span[contains(@class,"font-extrabold")]')
                )
            )
            delivery_time = delivery_time_elem.text.strip()
        except Exception:
            delivery_time = None

        # Open search bar
        wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, r'div.z-\[9999999\]')))
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'a[data-testid="search-bar-icon"], a[href="/search"]'))).click()
        time.sleep(0.5)

        # Search for the product
        try:
            search_box = wait.until(EC.presence_of_element_located((By.XPATH, '//input[contains(@placeholder, "Search for")]')))
        except:
            search_box = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="search"]')))
        search_box.click()
        search_box.clear()
        search_box.send_keys(query)
        search_box.send_keys(Keys.ENTER)
        wait.until(EC.presence_of_all_elements_located((By.XPATH, '//a[div[contains(@class,"container_lg_c1j8m_26")]]')))
        time.sleep(2)

        # Wait for overlays to disappear
        try:
            wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, r'div.z-\[9999999\]')))
        except:
            pass
        try:
            wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, 'div[class*="loading"], div[class*="spinner"]')))
        except:
            pass

        # Scrape products
        try:
            grid = driver.find_element(By.CSS_SELECTOR, 'div.pb-20')
            items = grid.find_elements(By.XPATH, './/a[div[contains(@class,"container_lg_c1j8m_26")]]')
        except:
            items = []

        for i in range(min(15, len(items))):  # Only scrape first 15 products
            try:
                item = grid.find_elements(By.XPATH, './/a[div[contains(@class,"container_lg_c1j8m_26")]]')[i]
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", item)
                time.sleep(0.1)

                # Skip out-of-stock
                try:
                    container = item.find_element(By.XPATH, './/div[contains(@class,"container_lg_c1j8m_26")]')
                    is_out_of_stock = container.get_attribute("data-is-out-of-stock")
                    if is_out_of_stock and is_out_of_stock.lower() == "true":
                        continue
                except:
                    continue

                url = item.get_attribute("href") or None
                name = None
                try:
                    name = item.find_element(
                        By.XPATH,
                        './/div[contains(@data-slot-id,"ProductName")]//span'
                    ).text
                except:
                    pass

                price = None
                try:
                    price_text = item.find_element(
                        By.XPATH,
                        './/div[contains(@class,"price-and-discount-attribute")]//p[contains(@class,"price_ljyvk_11")]'
                    ).text
                    price_digits = re.sub(r"[^\d]", "", price_text)
                    price = int(price_digits) if price_digits else None
                except:
                    pass

                quantity = None
                try:
                    quantity = item.find_element(
                        By.XPATH,
                        './/div[contains(@data-slot-id,"PackSize")]//span'
                    ).text
                except:
                    pass

                rating = None
                try:
                    rating = item.find_element(
                        By.XPATH,
                        './/span[contains(@class,"rating_1dpeb_1")]'
                    ).text
                except:
                    pass

                image = None
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", item)
                    time.sleep(0.1)
                    img_elem = item.find_element(By.TAG_NAME, 'img')
                    image = img_elem.get_attribute('src') or img_elem.get_attribute('data-src')
                except:
                    pass

                products.append({
                    'name': name,
                    'price': price,
                    'image': image,
                    'quantity': quantity,
                    'rating': rating,
                    'delivery_time': delivery_time,
                    'product_url': url,
                    'source': 'Zepto',
                    'scraped_at': datetime.now()
                })
            except Exception:
                continue

    except Exception as e:
        print("❌ Zepto scraping error:", e)
    finally:
        driver.quit()

    return products