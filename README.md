# 🥐 Pan de Staku – Enterprise Bakery & Coffee Management System with AI Chatbot

**Pan de Staku** is a premium **French-inspired bakery and coffee management system** built with **Streamlit**.

The application provides a **complete digital bakery platform** that combines:

* 🛒 Customer ordering system
* 📊 Business analytics dashboard
* 🏪 Multi-branch architecture
* 🤖 AI-powered chatbot assistant (**DoughBot**)

It is designed to simulate a **modern smart bakery management platform** capable of handling **orders, inventory, analytics, and AI customer assistance**.

---

# 🤖 AI Chatbot – DoughBot

The system includes an AI bakery assistant called **DoughBot**.

**DoughBot** helps customers interact with the bakery using natural conversation.

### Capabilities

* Answer questions about the menu
* Recommend bread and coffee combinations
* Provide delivery information
* Help customers explore the bakery
* Simulate an AI ordering assistant

### Example Interaction

**User**

```
Hi
```

**DoughBot**

```
Bonjour! I'm DoughBot, your Pan de Staku bakery assistant 🥐
How can I help you today?
```

**User**

```
Recommend breakfast
```

**DoughBot**

```
I recommend our buttery Croissant with a Latte ☕
It’s our most popular breakfast combo!
```

---

# 🚀 Features

## 🛒 Customer Side

* Register and login securely
* Browse breads and coffee
* Add items to cart
* Apply promo codes (example: `SAVE10`)
* Checkout with delivery fee
* GCash-style payment simulation
* Order history tracking
* AI chatbot assistance

---

## 🤖 AI Chatbot Features

DoughBot supports:

* Conversational menu browsing
* Product recommendations
* Coffee & bread pairing suggestions
* Delivery information
* Bakery FAQ assistance

The chatbot is built using **prompt-based logic and conversational flow**, simulating a **smart bakery ordering assistant**.

---

## 📊 Admin Dashboard

Admin features include:

* Secure admin login
* Business analytics dashboard
* Total sales monitoring
* Total order tracking
* Best-selling product detection
* Profit calculation
* Inventory monitoring
* Order history export (CSV)

---

## 🏪 Enterprise System Features

The system includes **enterprise-style functionality**:

* Multi-branch support

  * Manila
  * Cebu
  * Davao

* SQLite database persistence

* Inventory auto-deduction when items are sold

* Profit calculation based on product cost

* Real-time analytics dashboard

* Exportable sales reports

* AI chatbot integration

---

# 🛠 Installation & Setup

## 1️⃣ Install Python

Install **Python 3.10 or higher**

Download from:

```
https://www.python.org/downloads/
```

---

## 2️⃣ Clone the Repository

```bash
git clone https://github.com/yourusername/pan-de-staku.git

cd pan-de-staku
```

---

## 3️⃣ Create Virtual Environment (Recommended)

Windows

```bash
python -m venv venv
venv\Scripts\activate
```

Mac / Linux

```bash
python -m venv venv
source venv/bin/activate
```

---

## 4️⃣ Install Dependencies

```bash
pip install streamlit pandas sqlite3
```

Optional AI libraries (future expansion)

```bash
pip install openai langchain
```

---

## 5️⃣ Run the Application

```bash
streamlit run app.py
```

Then open:

```
http://localhost:8501
```

---

# 👤 Default Accounts

| Role     | Username        | Password |
| -------- | --------------- | -------- |
| Admin    | admin           | admin123 |
| Customer | Register in app | N/A      |

---

# 📦 Database Structure (SQLite)

The system uses **SQLite for persistent storage**.

### Tables

### users

Stores account information

```
id
username
password_hash
role
```

### inventory

Tracks stock levels

```
item_name
stock
cost
price
```

### orders

Logs all orders

```
order_id
timestamp
items
total_price
branch
customer
```

### profits

Tracks profit per order

```
order_id
profit
cost
revenue
```

---

# 💳 Payment Simulation

The system includes a **GCash-style payment simulation**.

Features include:

* Delivery fee calculation
* Promo code discount
* Dynamic order totals
* Payment confirmation
* Transaction logging

---

# 🧪 Prompt Testing (Chatbot Testing)

The chatbot behavior is tested through **sample prompt interactions**.

Example tests include:

### Test 1 – Greeting

Input

```
Hello
```

Expected Output

```
Bonjour! I'm DoughBot, your bakery assistant.
```

---

### Test 2 – Menu Inquiry

Input

```
What breads do you have?
```

Expected Output

```
We offer Croissant, Baguette, Brioche, and Pain au Chocolat.
```

---

### Test 3 – Recommendation

Input

```
Recommend a coffee and bread combo
```

Expected Output

```
Try our Croissant with a Latte ☕
```

---

### Test 4 – Delivery

Input

```
Do you offer delivery?
```

Expected Output

```
Yes! Delivery is available within the city for ₱40.
```

---

# 🌐 Deployment Guide

## Streamlit Cloud

1. Push the repository to GitHub
2. Open

```
https://share.streamlit.io
```

3. Connect GitHub repository
4. Select `app.py`
5. Deploy

---

## Alternative Deployment Options

### VPS

```
streamlit run app.py --server.port=8501
```

### Docker

Containerize the app for scalable deployment across bakery branches.

### Heroku

Deploy using a **Procfile** and requirements.txt.

---

# 🏗 System Architecture

The system follows a **multi-layer architecture**.

### 1️⃣ Customer Layer

User interface for browsing menu and placing orders.

### 2️⃣ AI Layer

DoughBot chatbot handles conversational assistance.

### 3️⃣ Branch Layer

Manages inventory and sales for each branch.

### 4️⃣ Admin Layer

Dashboard analytics and business insights.

### 5️⃣ Database Layer

SQLite handles persistent storage for:

* users
* inventory
* orders
* profits

---

# 🎨 Technology Stack

| Component | Technology           |
| --------- | -------------------- |
| Frontend  | Streamlit            |
| Backend   | Python               |
| Database  | SQLite               |
| Analytics | Pandas               |
| AI Logic  | Prompt-based chatbot |

---

# 🔮 Future Improvements

Possible future upgrades include:

* Real AI model integration (OpenAI / LLM)

* Voice ordering system

* Mobile-friendly UI

* Real payment gateway integration

  * GCash
  * PayMaya
  * Stripe

* Smart inventory prediction using AI

---

# ⚡ License

MIT License

Free to use, modify, and deploy for **educational, personal, or commercial bakery applications**.

---
