from flask import Flask, render_template, request
from pymongo import MongoClient
from datetime import datetime

from scraper import jiomart
from scraper.zepto import scrape as scrape_zepto
from scraper.blinkit import scrape as scrape_blinkit
from scraper.instamart import scrape_instamart
from scraper.bigbasket import scrape_bigbasket
from scraper.jiomart import scrape_jiomart
import os
from dotenv import load_dotenv
from concurrent.futures import ProcessPoolExecutor, as_completed
import time

app = Flask(__name__, static_url_path='/static')

# Load Mongo URI from .env
load_dotenv()
mongo_uri = os.getenv("MONGO_URI")
client = MongoClient(mongo_uri)
db = client['grocery_db']
products_collection = db['products']


@app.route('/')
def home():
    return render_template('index.html', results=[], request=request)


@app.route('/search', methods=['POST'])
def search():
    location = request.form.get('location', '').strip()
    query = request.form.get('product', '').strip()
    if not location or not query:
        return "Please enter both location and product.", 400

    results = []
    scrapers = {
        "instamart": scrape_instamart,
        # "jiomart": scrape_jiomart,
        # "zepto": scrape_zepto,
        # "blinkit": scrape_blinkit,
        # "bigbasket": scrape_bigbasket
    }

    # Use ProcessPoolExecutor for multiprocessing
    with ProcessPoolExecutor(max_workers=2) as executor:
        future_to_source = {
            executor.submit(func, query, location): source
            for source, func in scrapers.items()
        }
        for future in as_completed(future_to_source):
            source = future_to_source[future]
            try:
                data = future.result()
                if data:
                    for item in data:
                        item['source'] = source
                        item['scraped_at'] = datetime.now()
                    results.extend(data)
            except Exception as e:
                import traceback
                print(f"❌ {source} scraping failed:", e)
                traceback.print_exc()

    # Store all results in MongoDB (using the already-open client)
    if results:
        try:
            products_collection.insert_many(results)
        except Exception as e:
            print("❌ MongoDB insert error:", e)

    return render_template('index.html', results=results, request=request)


if __name__ == '__main__':
    app.run(debug=False, use_reloader=False)
