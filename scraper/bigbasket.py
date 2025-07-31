from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime
import time


def scrape_bigbasket(query, location):
    options = Options()
    options.headless = True
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 8)
    products = []
    seen_urls = set()

    try:
        driver.get("https://www.bigbasket.com/")
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        driver.execute_script("document.querySelector('header')?.remove();")

        location_btn = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[.//span[contains(text(), 'Select Location')]]"))
        )
        try:
            ActionChains(driver).move_to_element(location_btn).click().perform()
        except:
            driver.execute_script("arguments[0].click();", location_btn)

        location_input = wait.until(
            EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Search for area or street name']"))
        )
        location_input.clear()
        location_input.send_keys(location)

        suggestions = wait.until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "ul.overscroll-contain > li"))
        )
        driver.execute_script("arguments[0].click();", suggestions[0])

        time.sleep(2)
        search_input = wait.until(
            EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Search for Products...']"))
        )
        ActionChains(driver).move_to_element(search_input).click().perform()
        search_input.clear()
        search_input.send_keys(query)
        search_input.send_keys(Keys.ENTER)

        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.z-10")))

        # Fastest possible scrolling
        def scroll_to_bottom():
            for _ in range(5):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(0.5)

        last_items_count = -1
        same_count_retries = 0

        while len(products) < 15 and same_count_retries < 3:
            scroll_to_bottom()

            items = driver.find_elements(By.CSS_SELECTOR, "div.SKUDeck___StyledDiv-sc-1e5d9gk-0")

            if len(items) == last_items_count:
                same_count_retries += 1
            else:
                same_count_retries = 0

            last_items_count = len(items)

            for item in items:
                if len(products) >= 15:
                    break
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", item)

                    url = item.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
                    if not url or url in seen_urls:
                        continue
                    seen_urls.add(url)

                    brand = ""
                    pname = ""
                    quantity = ""
                    price = None
                    image = None
                    rating = None
                    delivery_time = None

                    try:
                        brand = item.find_element(By.CSS_SELECTOR, "span[class*='BrandName']").text.strip()
                    except:
                        pass

                    try:
                        pname = item.find_element(By.CSS_SELECTOR, "h3.block.m-0.line-clamp-2").text.strip()
                    except:
                        pass

                    try:
                        quantity = item.find_element(By.CSS_SELECTOR, "span[class*='PackSelector']").text.strip()
                    except:
                        try:
                            quantity = item.find_element(By.CSS_SELECTOR, "span[class*='PackChanger']").text.strip()
                        except:
                            quantity = ""

                    try:
                        price = item.find_element(By.XPATH, ".//span[contains(text(), '₹')]").text.replace("₹",
                                                                                                           "").strip()
                    except:
                        pass

                    try:
                        img_el = item.find_element(By.CSS_SELECTOR, "img")
                        image = img_el.get_attribute("src") or img_el.get_attribute("data-src")
                    except:
                        pass

                    try:
                        delivery_elem = item.find_element(
                            By.XPATH,
                            './/div[contains(text(), "hrs") or contains(text(), "mins") or contains(text(),"days")]'
                        )
                        delivery_time = delivery_elem.text.strip().lower()
                    except:
                        delivery_time = None

                    try:
                        rating_elems = item.find_elements(
                            By.CSS_SELECTOR,
                            ".Label-sc-15v1nk5-0.gJxZPQ"
                        )
                        for elem in rating_elems:
                            text = elem.text.strip()
                            if text.replace('.', '', 1).isdigit():
                                rating = text
                                break
                    except:
                        rating = None

                    products.append({
                        "name": brand + " " + pname,
                        "quantity": quantity,
                        "price": price,
                        "image": image,
                        "product_url": url,
                        "rating": rating,
                        "delivery_time": delivery_time,
                        "source": "BigBasket",
                        "scraped_at": datetime.now()
                    })

                except Exception as e:
                    print("❌ Failed to extract item:", e)

    except Exception as e:
        print("❌ Error:", e)
        driver.save_screenshot("scraping_error.png")
    finally:
        driver.quit()

    return products