# 🥐 Pan de Staku - Enterprise Bakery & Coffee Management System with AI Chatbot 🤖

**Pan de Staku** is a **French-inspired bakery and coffee management system** built with **Streamlit** ☕.

The app provides a **complete digital bakery platform** that combines:

🍞 Customer ordering system
📊 Business analytics dashboard
🏬 Multi-branch architecture
🤖 AI-powered chatbot assistant (**DoughBot**)

It simulates a **modern smart bakery platform** capable of handling:

* 🛒 Orders
* 📦 Inventory
* 📈 Analytics
* 💬 AI customer assistance

---

# 🤖 AI Chatbot - DoughBot

The system includes an **AI bakery assistant** called **DoughBot**.

DoughBot helps customers interact with the bakery using **natural conversation**.

## 🧠 Capabilities

* 🍞 Answer questions about **menu items and prices**
* ☕ Recommend **bread and coffee combinations**
* 🚚 Provide **delivery and branch information**
* 💳 Explain **payment steps (GCash and Maya flow)**
* 🛍 Guide users through **order and checkout steps**

---

## 💬 Example Interaction

**User**

```text
Hi
```

**DoughBot**

```text
Bonjour! I am DoughBot. Looking for bread, coffee, or a combo today?
```

**User**

```text
Recommend breakfast
```

**DoughBot**

```text
My recommendation: Croissant with Latte.
```

---

# ✨ Features

## 🛒 Customer Side

* 🔐 Register and login securely
* 🥖 Browse breads and coffee
* 🛍 Add items to cart
* 🌏 Branch-based ordering

  * Manila
  * Cebu
  * Davao
* 🔢 OTP-style payment validation simulation
* 🤖 DoughBot chat assistance

---

# 🤖 AI Chatbot Features

DoughBot supports:

* 💬 Conversational menu browsing
* 🥐 Product recommendations
* ☕ Coffee and bread pairing suggestions
* 🚚 Delivery and branch FAQs
* 🛍 Ordering and payment guidance

The chatbot is built using **rule-based, prompt-driven conversational logic**.

---

# 🧑‍💼 Admin Dashboard

Admin features include:

* 🔐 Secure admin login
* 💰 Total sales monitoring
* 📈 Total profit monitoring
* 📋 Full orders table view
* 📦 Inventory table view

---

# 🏢 Enterprise System Features

The system includes **enterprise-style functionality**:

* 🌍 **Multi-branch support**

  * 🏙 Manila
  * 🌆 Cebu
  * 🌃 Davao

* 🗄 SQLite database persistence

* 📦 Inventory auto-deduction when items are sold

* 💵 Profit calculation based on product cost

* 📊 Real-time metrics in dashboard

* 🤖 AI chatbot integration

---

# 📑 Added Content Tabs

The app now includes **business information tabs** for:

🏠 **Home** – Pan de Staku concept explanation
🥖 **Product** – Bread and coffee offerings
🛎 **Service** – Service scope and commitments
📞 **Contact** – Support channels and branch details

---

# ⚙️ Installation & Setup

## 1️⃣ Install Python

Install **Python 3.10 or higher**:

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

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### Mac / Linux

```bash
python -m venv venv
source venv/bin/activate
```

---

## 4️⃣ Install Dependencies

```bash
pip install streamlit pandas
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

# 🔑 Default Accounts

| Role        | Username        | Password |
| ----------- | --------------- | -------- |
| 👑 Admin    | admin           | admin123 |
| 👤 Customer | Register in app | N/A      |

---

# 🗄 Database Structure (SQLite)

The system uses **SQLite** for persistent storage.

## 👤 `users`

Stores account information.

```
id
username
password
role
```

---

## 📦 `inventory`

Tracks stock levels and cost basis.

```
item
stock
cost
```

---

## 🧾 `orders`

Logs confirmed checkout transactions.

```
id
username
branch
total
profit
payment
timestamp
```

---

# 💳 Payment Simulation

The app includes a **digital payment simulation** with:

* 📱 **GCash or Maya selection**
* ☎️ **11-digit phone validation**
* 🔐 **6-digit OTP validation**
* 🧾 **Transaction logging into orders table**

---

# 🧪 Prompt Testing (Chatbot Testing)

You can test **DoughBot behavior** using sample prompts.

### 🧪 Test 1 – Greeting

Input:

```text
Hello
```

Expected:

```text
A greeting response from DoughBot.
```

---

### 🧪 Test 2 – Menu Inquiry

Input:

```text
What breads do you have?
```

Expected:

```text
A list of available bread items.
```

---

### 🧪 Test 3 – Recommendation

Input:

```text
Recommend a coffee and bread combo
```

Expected:

```text
A pairing recommendation such as Croissant with Latte.
```

---

### 🧪 Test 4 – Delivery

Input:

```text
Do you offer delivery?
```

Expected:

```text
Delivery availability and base fee information.
```

---

# 🚀 Deployment Guide

## ☁️ Streamlit Community Cloud

1. Push the repository to **GitHub**.
2. Open:

```
https://share.streamlit.io
```

3. Connect your **GitHub repository**.
4. Select `app.py`.
5. Deploy.

---

## 🖥 Alternative Deployment Options

### VPS

```bash
streamlit run app.py --server.port=8501
```

### 🐳 Docker

Containerize the app for **scalable deployment across branches**.

---

# 🏗 System Architecture

The system follows a **multi-layer structure**:

1️⃣ **Customer Layer** – UI for browsing and placing orders
2️⃣ **AI Layer** – DoughBot conversational assistance
3️⃣ **Branch Layer** – Branch-aware ordering system
4️⃣ **Admin Layer** – Dashboard analytics and inventory visibility
5️⃣ **Database Layer** – SQLite storage for users, inventory, and orders

---

# 🧰 Technology Stack

| Component    | Technology         |
| ------------ | ------------------ |
| 🎨 Frontend  | Streamlit          |
| ⚙️ Backend   | Python             |
| 🗄 Database  | SQLite             |
| 📊 Analytics | Pandas             |
| 🤖 AI Logic  | Rule-based chatbot |

---

# 🔮 Future Improvements

Possible upgrades:

* 🧠 Real **LLM integration** (OpenAI or local models)
* 🎤 **Voice ordering workflow**
* 📱 Mobile-first responsive UI refinement
* 💳 Real **payment gateway integration** (GCash, Maya, Stripe)
* 📈 **AI-based inventory demand forecasting**

---

# 📜 License

MIT License.

✅ Free to **use, modify, and deploy** for:

* 🎓 Educational projects
* 🧑‍💻 Personal development
* 🏢 Commercial bakery applications

---
