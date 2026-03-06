# 🥐 Pan de Staku – Enterprise Bakery & Coffee Management System

**Pan de Staku** is a premium French-inspired bakery and coffee Streamlit application. It is designed for both customer-facing ordering and admin-level business analytics, providing an **end-to-end bakery management solution**.

The app includes:

* Multi-branch support (e.g., Manila, Cebu, Davao)
* Customer login and registration with secure password hashing
* Admin login with full dashboard analytics
* SQLite database storage for users, orders, inventory, and profits
* Real-time profit calculation for each order
* Inventory management (auto deduction when items are sold)
* Promo code and discount system
* GCash-style payment simulation
* Animated, premium UI
* Exportable sales reports in CSV

---

## 🚀 Features

### **Customer Side**

* Register/Login securely
* Browse breads and coffee
* Add items to cart with quantity selection
* Apply promo codes (e.g., `SAVE10` for discounts)
* Checkout with delivery fee and payment simulation
* View order history

### **Admin Side**

* Secure password-protected login
* Dashboard showing:

  * Total sales
  * Total orders
  * Best-selling items
  * Profit calculation
  * Inventory levels
* Order history table with CSV export
* Reset sales/orders with one click
* Multi-branch overview

### **Enterprise Enhancements**

* Multi-branch architecture
* Real profit and inventory tracking
* SQLite database integration for persistence
* Animated UI for better UX
* Ready for cloud deployment

---

## 🛠 Installation & Setup

### 1️⃣ Install Python

Ensure Python ≥ 3.10 is installed. Download from [python.org](https://www.python.org/downloads/).

---

### 2️⃣ Clone the Repository

```bash
git clone https://github.com/yourusername/pan-de-staku.git
cd pan-de-staku
```

---

### 3️⃣ Create a Virtual Environment (Recommended)

```bash
python -m venv venv
# Activate
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

---

### 4️⃣ Install Dependencies

```bash
pip install streamlit pandas sqlite3
```

---

### 5️⃣ Run the App

```bash
streamlit run app.py
```

The app should open in your browser at: `http://localhost:8501`

---

## 👤 Default Accounts

| Role     | Username        | Password |
| -------- | --------------- | -------- |
| Admin    | admin           | admin123 |
| Customer | Register in-app | N/A      |

---

## 📦 Database Structure (SQLite)

* **users:** Stores admin and customer accounts
* **inventory:** Tracks stock levels and item costs
* **orders:** Logs all orders including branch, items, totals, and profits
* **profits:** Tracks profit per sale after cost deduction

---

## 💳 Payment Simulation

* Customers can "pay" with a simulated GCash-style interface
* Promo codes automatically applied
* Order totals, discounts, and delivery fees are calculated dynamically

---

## 🌐 Deployment Guide

### Streamlit Cloud

1. Push repository to GitHub
2. Connect GitHub repository to [Streamlit Cloud](https://share.streamlit.io/)
3. Select `app.py` as the main file
4. Streamlit Cloud installs dependencies from `requirements.txt` automatically

### Other Deployment Options

* **Heroku:** Use `Procfile` and push the repository
* **VPS / Digital Ocean:** Run `streamlit run app.py --server.port=8501`
* **Docker (optional):** Containerize the app for multi-branch scaling

---

## 📈 Business Architecture

1. **Customer Layer:** UI for ordering, cart management, payment simulation
2. **Branch Layer:** Inventory and sales tracking per branch
3. **Admin Layer:** Centralized dashboard with analytics, profit, and export
4. **Database Layer:** SQLite for storing persistent user, inventory, and order data

---

## 🔧 Next Steps / Improvements

* Integrate real payment gateways (GCash, PayMaya, Stripe)
* Multi-language support for international customers
* Cloud-based multi-branch analytics
* Advanced UI animations and transitions

---

## ⚡ License

MIT License – Free to use, modify, and deploy for personal or commercial bakery applications.

---
