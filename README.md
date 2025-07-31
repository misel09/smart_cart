# 🛒 SMART CART

A full-stack web application that helps users compare grocery prices across multiple platforms (Blinkit, Zepto, Instamart, JioMart, BigBasket). It fetches live data using headless Selenium scrapers and displays results in a unified, user-friendly interface.

---

## 🌐 Tech Stack

### Backend:

* **Python**
* **Flask**
* **Selenium** with `undetected_chromedriver`
* **MongoDB** via `pymongo`

### Frontend:

* **Python**, **Django** (or custom styling)

---

## 🔧 Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/misel09/smart_cart.git
cd grocery-comparator
```

### 2. Set Up Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate for Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure MongoDB

* Make sure MongoDB is running.
* Edit `mongo_config.py` to match your connection string.

### 5. Run the Application

```bash
python app.py
```

Navigate to `http://localhost:5000`

---
## 📹 Demo Video

https://github.com/misel09/smart_cart/blob/main/assets/smart_cart.mp4

---

## 🔍 Features

* 🔎 Search products by name and location
* ⚡ Compare prices, delivery time, quantity, and rating
* 💾 Store results in MongoDB
* 📊 Filter & sort results

---

## 📜 License

[MIT](https://choosealicense.com/licenses/mit/)

---

## 💡 Future Enhancements

* Power BI dashboard integration
* Authentication system
  
---

Happy Scraping! 🕷️
