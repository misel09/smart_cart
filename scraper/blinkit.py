import os
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime

def slugify(name):
    # Remove brackets
    name = re.sub(r"[\(\)\[\]\{\}]", "", name)
    # Replace all non-alphanumeric characters (except '-') with '-'
    name = re.sub(r"[^a-zA-Z0-9\-]", "-", name)
    # Replace multiple '-' with single '-'
    name = re.sub(r"-+", "-", name)
    # Strip leading/trailing '-'
    return name.strip("-").lower()

def scrape(query, location):
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    options.headless = True
    options.add_argument("--disable-gpu")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 8)  # Slightly lower wait

    results = []

    try:
        driver.get("https://www.blinkit.com/")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='search delivery location']")))

        loc_input = driver.find_element(By.CSS_SELECTOR, "input[placeholder='search delivery location']")
        loc_input.clear()
        loc_input.send_keys(location)

        # Remove sleep, rely on explicit wait
        first_suggestion = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "div.LocationSearchList__LocationDetails-sc-93rfr7-3"))
        )
        first_suggestion.click()

        placeholder = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "SearchBar__PlaceholderContainer-sc-16lps2d-0")))
        driver.execute_script("arguments[0].click();", placeholder)

        search_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[class^='SearchBarContainer__Input']")))
        search_input.clear()
        search_input.send_keys(query)
        search_input.send_keys(Keys.ENTER)

        wait.until(EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@class, 'tw-w-full tw-px-3')]")))

        product_cards = driver.find_elements(By.XPATH, "//div[contains(@class, 'tw-w-full tw-px-3')]")

        for card in product_cards[:15]:  # Limit to 15 products
            try:
                # Remove per-item scroll and sleep for speed

                name = card.find_element(By.XPATH, ".//div[contains(@class, 'tw-line-clamp-2')]").text.strip()
                if name.lower().startswith("showing results for") or name.lower().startswith("showing related products"):
                    continue

                try:
                    price_element = card.find_element(By.XPATH, ".//div[contains(@class,'tw-font-semibold') and contains(text(),'₹')]")
                    price = price_element.text.replace("₹", "").replace(",", "").strip()
                except:
                    price = None

                try:
                    quantity = card.find_element(By.XPATH, ".//div[contains(@class,'tw-font-medium')]").text.strip()
                except:
                    quantity = "N/A"

                try:
                    delivery_time = card.find_element(By.XPATH, ".//div[contains(text(), 'mins') or contains(text(), 'MINS')]").text.strip()
                except:
                    delivery_time = "N/A"

                try:
                    parent = card.find_element(By.XPATH, "..")
                    image_container = parent.find_element(By.XPATH, ".//div[contains(@class, 'tw-relative') and contains(@class, 'tw-overflow-hidden')]")
                    img_elem = image_container.find_element(By.TAG_NAME, "img")
                    image = img_elem.get_attribute("src")
                    if image and image.startswith("//"):
                        image = "https:" + image
                except:
                    image = None

                try:
                    parent_div = card.find_element(By.XPATH, "..")
                    product_id = parent_div.get_attribute("id")
                    if not product_id:
                        product_id = card.get_attribute("id")
                except Exception as e:
                    product_id = card.get_attribute("id") if card.get_attribute("id") else None

                if name and product_id:
                    product_slug = slugify(name)
                    product_url = f"https://blinkit.com/prn/{product_slug}/prid/{product_id}"
                else:
                    product_url = None

                results.append({
                    "name": name,
                    "price": float(price) if price else None,
                    "quantity": quantity,
                    "image": image,
                    "delivery_time": delivery_time,
                    "product_url": product_url,
                    "source": "Blinkit",
                    "search_query": query,
                    "location": location,
                    "scraped_at": datetime.now()
                })

            except Exception:
                continue

    except Exception:
        driver.save_screenshot("fail_debug.png")

    finally:
        driver.quit()

    return results
