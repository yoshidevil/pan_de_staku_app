import base64
import importlib.util
import hashlib
import random
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

DB_PATH = "pan_de_staku.db"
ADMIN_USERNAME = "admin"
ADMIN_DEFAULT_PASSWORD = "admin123"
HAS_PDF_VIEWER = importlib.util.find_spec("streamlit_pdf") is not None
SIGNUP_BONUS = 300
BRANCH_DETAILS = {
    "Manila": {
        "address": "Ayala Avenue, Makati",
        "hours": "7:00 AM - 9:00 PM",
        "best_pair": "Croissant + Latte",
    },
    "Cebu": {
        "address": "IT Park, Cebu City",
        "hours": "7:00 AM - 9:00 PM",
        "best_pair": "Pandesal + Americano",
    },
    "Davao": {
        "address": "Lanang, Davao City",
        "hours": "7:00 AM - 9:00 PM",
        "best_pair": "Ube + Mocha",
    },
    "Iloilo": {
        "address": "Festive Walk, Mandurriao, Iloilo City",
        "hours": "7:00 AM - 9:00 PM",
        "best_pair": "Brioche + Flat White",
    },
    "General Santos": {
        "address": "J. Catolico Avenue, General Santos City",
        "hours": "7:00 AM - 9:00 PM",
        "best_pair": "Loaf Bread + Cappuccino",
    },
    "Baguio": {
        "address": "Session Road, Baguio City",
        "hours": "7:00 AM - 9:00 PM",
        "best_pair": "Pain au Chocolat + Latte",
    },
}
BRANCHES = list(BRANCH_DETAILS.keys())
BRANCH_LIST_TEXT = ", ".join(BRANCHES)

bread_menu = {
    "Croissant": 120,
    "Baguette": 100,
    "Brioche": 150,
    "Pain au Chocolat": 140,
    "Fougasse": 130,
    "Sourdough": 160,
    "Danish": 135,
}

local_bakes_menu = {
    "Banana Cake": 95,
    "Pandesal": 25,
    "Loaf Bread": 85,
    "Choco Bread": 60,
    "Yoyo": 30,
    "Ube": 70,
}

coffee_menu = {
    "Espresso": 90,
    "Americano": 100,
    "Cappuccino": 120,
    "Latte": 130,
    "Mocha": 140,
    "Macchiato": 115,
    "Flat White": 125,
}

drinks_menu = {
    "Soda": 35,
    "Juice": 45,
    "Coke": 45,
    "Royal": 45,
    "Sprite": 45,
    "MUG Beer": 55,
    "Lipton": 50,
}

all_menu = {**bread_menu, **local_bakes_menu, **coffee_menu, **drinks_menu}

NAV_DEFINITIONS = {
    "Home": "Brand overview, highlights, and vision.",
    "Login": "Sign in to place orders and access your account.",
    "Presentation": "View, download, and preview the Pan de Staku presentation deck.",
    "Register": "Create a new customer account.",
    "Branch": "Choose your branch and view local details.",
    "Menu List": "Full menu with updated prices.",
    "Order": "Build multi-item orders and add to cart.",
    "Cart": "Review items and complete payment.",
    "DoughBot Chat": "Chat support for menu, prices, and recommendations.",
    "Product": "Product lineup and pricing.",
    "Service": "Service flow, payment, and support commitments.",
    "Contact": "Reach the team for help or partnerships.",
    "Admin Dashboard": "Admin-only sales and inventory monitoring.",
}


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


@st.cache_resource
def get_db_connection() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS inventory (
            item TEXT PRIMARY KEY,
            stock INTEGER,
            cost REAL
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            branch TEXT,
            total REAL,
            profit REAL,
            payment TEXT,
            timestamp TEXT
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS wallets (
            username TEXT PRIMARY KEY,
            balance REAL,
            created_at TEXT
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS wallet_awards (
            username TEXT,
            amount REAL,
            reason TEXT,
            granted_at TEXT,
            PRIMARY KEY (username, reason)
        )
        """
    )
    ensure_orders_schema(conn)
    conn.commit()


def seed_default_admin(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM users WHERE username = ?", (ADMIN_USERNAME,))
    if cursor.fetchone():
        return
    cursor.execute(
        "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
        (ADMIN_USERNAME, hash_password(ADMIN_DEFAULT_PASSWORD), "admin"),
    )
    conn.commit()


def seed_inventory(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    for item, price in all_menu.items():
        cursor.execute(
            "INSERT OR IGNORE INTO inventory (item, stock, cost) VALUES (?, ?, ?)",
            (item, 50, round(price * 0.6, 2)),
        )
    conn.commit()


def authenticate_user(conn: sqlite3.Connection, username: str, password: str):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT username, role, password FROM users WHERE username = ?",
        (username.strip(),),
    )
    row = cursor.fetchone()
    if not row:
        return None
    db_username, db_role, db_hash = row
    incoming_hash = hash_password(password)
    if db_hash == incoming_hash:
        return {"username": db_username, "role": db_role}
    if db_hash == password:
        # Migrate legacy plain-text passwords to hashed storage.
        cursor.execute(
            "UPDATE users SET password = ? WHERE username = ?",
            (incoming_hash, db_username),
        )
        conn.commit()
        return {"username": db_username, "role": db_role}
    return None


def create_user(conn: sqlite3.Connection, username: str, password: str) -> tuple[bool, str]:
    if not re.fullmatch(r"[A-Za-z0-9_]{3,20}", username):
        return False, "Username must be 3-20 chars and contain only letters, numbers, or underscore."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."

    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            (username.strip(), hash_password(password), "customer"),
        )
        conn.execute(
            "INSERT INTO wallets (username, balance, created_at) VALUES (?, ?, ?)",
            (username.strip(), SIGNUP_BONUS, now),
        )
        conn.execute(
            "INSERT INTO wallet_awards (username, amount, reason, granted_at) VALUES (?, ?, ?, ?)",
            (username.strip(), SIGNUP_BONUS, "signup_bonus", now),
        )
        conn.commit()
        return True, f"Account created. You received PHP {SIGNUP_BONUS} signup credit."
    except sqlite3.IntegrityError:
        return False, "Username already exists."


def init_session_state() -> None:
    st.session_state.setdefault("cart", [])
    st.session_state.setdefault("user", None)
    st.session_state.setdefault("role", None)
    st.session_state.setdefault("branch", BRANCHES[0])
    st.session_state.setdefault("appearance", "Light")
    st.session_state.setdefault("chat_messages", [])
    st.session_state.setdefault("doughbot_last_item", None)
    st.session_state.setdefault("doughbot_last_intent", None)
    st.session_state.setdefault("doughbot_user_name", None)
    st.session_state.setdefault("doughbot_last_topic", None)
    st.session_state.setdefault("doughbot_last_response", None)


def ensure_orders_schema(conn: sqlite3.Connection) -> None:
    existing_cols = {
        row[1] for row in conn.execute("PRAGMA table_info(orders)").fetchall()
    }
    if "payment" not in existing_cols:
        conn.execute("ALTER TABLE orders ADD COLUMN payment TEXT")


def get_stock(conn: sqlite3.Connection, item: str) -> int:
    row = conn.execute("SELECT stock FROM inventory WHERE item = ?", (item,)).fetchone()
    return int(row[0]) if row else 0


def ensure_wallet(conn: sqlite3.Connection, username: str) -> None:
    if not username:
        return
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "INSERT OR IGNORE INTO wallets (username, balance, created_at) VALUES (?, ?, ?)",
        (username, 0, now),
    )
    conn.commit()


def get_wallet_balance(conn: sqlite3.Connection, username: str) -> float:
    if not username:
        return 0.0
    row = conn.execute("SELECT balance FROM wallets WHERE username = ?", (username,)).fetchone()
    if row is None:
        ensure_wallet(conn, username)
        return 0.0
    return float(row[0] or 0)


def grant_signup_bonus_to_existing_users(conn: sqlite3.Connection) -> int:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    users = conn.execute("SELECT username FROM users WHERE role != 'admin'").fetchall()
    granted = 0
    for (username,) in users:
        award_exists = conn.execute(
            "SELECT 1 FROM wallet_awards WHERE username = ? AND reason = ?",
            (username, "signup_bonus"),
        ).fetchone()
        if award_exists:
            continue
        conn.execute(
            "INSERT OR IGNORE INTO wallets (username, balance, created_at) VALUES (?, ?, ?)",
            (username, 0, now),
        )
        conn.execute(
            "UPDATE wallets SET balance = balance + ? WHERE username = ?",
            (SIGNUP_BONUS, username),
        )
        conn.execute(
            "INSERT INTO wallet_awards (username, amount, reason, granted_at) VALUES (?, ?, ?, ?)",
            (username, SIGNUP_BONUS, "signup_bonus", now),
        )
        granted += 1
    if granted:
        conn.commit()
    return granted


def add_to_cart(item: str, qty: int, price: float) -> None:
    for entry in st.session_state.cart:
        if entry["item"] == item:
            entry["qty"] += qty
            return
    st.session_state.cart.append({"item": item, "qty": qty, "price": price})


def validate_payment(phone: str, otp: str, method: str) -> bool:
    if method == "Cash":
        return bool(re.fullmatch(r"\d{11}", phone))
    return bool(re.fullmatch(r"\d{11}", phone) and re.fullmatch(r"\d{6}", otp))


def render_menu_section(title: str, subtitle: str, items: dict[str, int]) -> None:
    st.subheader(title)
    st.caption(subtitle)

    item_lines = [f"{item} — PHP {price}" for item, price in items.items()]
    split_index = (len(item_lines) + 1) // 2
    left_items = item_lines[:split_index]
    right_items = item_lines[split_index:]

    cols = st.columns(2)
    with cols[0]:
        if left_items:
            st.markdown("\n".join([f"- {line}" for line in left_items]))
    with cols[1]:
        if right_items:
            st.markdown("\n".join([f"- {line}" for line in right_items]))


def get_presentation_paths() -> tuple[Path | None, Path | None]:
    pptx_candidates = [Path("assets/Pan de Staku.pptx"), Path("Pan de Staku.pptx")]
    pptx_path = next((candidate for candidate in pptx_candidates if candidate.exists()), None)

    pdf_candidates = [Path("assets/Pan de Staku.pdf"), Path("Pan de Staku.pdf")]
    if pptx_path:
        pdf_candidates.insert(0, pptx_path.with_suffix(".pdf"))
    pdf_path = next((candidate for candidate in pdf_candidates if candidate.exists()), None)
    return pptx_path, pdf_path


@st.cache_data(show_spinner=False)
def load_binary_file(path: Path) -> bytes:
    return path.read_bytes()


def extract_presentation_outline(pptx_path: Path) -> list[str]:
    try:
        with ZipFile(pptx_path) as pptx_zip:
            slide_files = []
            for file_name in pptx_zip.namelist():
                match = re.fullmatch(r"ppt/slides/slide(\d+)\.xml", file_name)
                if match:
                    slide_files.append((int(match.group(1)), file_name))
            slide_files.sort(key=lambda item: item[0])

            namespace = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
            outlines: list[str] = []
            for slide_no, file_name in slide_files:
                root = ET.fromstring(pptx_zip.read(file_name))
                texts = [
                    node.text.strip()
                    for node in root.findall(".//a:t", namespace)
                    if node.text and node.text.strip()
                ]
                first_text = texts[0] if texts else "No visible title text found."
                outlines.append(f"Slide {slide_no}: {first_text}")
            return outlines
    except Exception:
        return []


def render_pdf_embed(pdf_bytes: bytes, height: int = 720) -> None:
    if HAS_PDF_VIEWER and hasattr(st, "pdf"):
        st.pdf(pdf_bytes, height=height)
        return

    pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
    viewer_html = f"""
<style>
  .presentation-frame {{
    width: 100%;
    height: {height}px;
    border: 1px solid rgba(0, 0, 0, 0.12);
    border-radius: 18px;
    box-shadow: 0 18px 36px rgba(0, 0, 0, 0.18);
  }}
</style>
<iframe
  class="presentation-frame"
  src="data:application/pdf;base64,{pdf_base64}"
  type="application/pdf">
</iframe>
"""
    components.html(viewer_html, height=height + 24, scrolling=True)


def doughbot_response(prompt: str, conn: sqlite3.Connection = None) -> str:
    prompt_clean = " ".join(prompt.strip().split())
    p = prompt_clean.lower()
    words = set(re.findall(r"[a-z]+", p))

    item_aliases = {
        "croissant": "Croissant",
        "baguette": "Baguette",
        "brioche": "Brioche",
        "pain au chocolat": "Pain au Chocolat",
        "pain au choc": "Pain au Chocolat",
        "chocolate croissant": "Pain au Chocolat",
        "fougasse": "Fougasse",
        "sourdough": "Sourdough",
        "danish": "Danish",
        "banana cake": "Banana Cake",
        "pandesal": "Pandesal",
        "loaf bread": "Loaf Bread",
        "loaf": "Loaf Bread",
        "choco bread": "Choco Bread",
        "chocolate bread": "Choco Bread",
        "yoyo": "Yoyo",
        "ube": "Ube",
        "espresso": "Espresso",
        "americano": "Americano",
        "cappuccino": "Cappuccino",
        "capuccino": "Cappuccino",
        "latte": "Latte",
        "cafe latte": "Latte",
        "mocha": "Mocha",
        "macchiato": "Macchiato",
        "flat white": "Flat White",
        "flatwhite": "Flat White",
        "soda": "Soda",
        "juice": "Juice",
        "coke": "Coke",
        "coca cola": "Coke",
        "royal": "Royal",
        "sprite": "Sprite",
        "mug beer": "MUG Beer",
        "mug": "MUG Beer",
        "lipton": "Lipton",
        "iced tea": "Lipton",
    }
    pairings = {
        "Croissant": "Latte",
        "Baguette": "Americano",
        "Brioche": "Cappuccino",
        "Pain au Chocolat": "Mocha",
        "Fougasse": "Espresso",
        "Sourdough": "Flat White",
        "Danish": "Macchiato",
        "Banana Cake": "Latte",
        "Pandesal": "Americano",
        "Loaf Bread": "Cappuccino",
        "Choco Bread": "Mocha",
        "Yoyo": "Espresso",
        "Ube": "Flat White",
    }
    personas = [
        ("Aiah", "<3"),
        ("Colet", "<3"),
        ("Maloi", "<3"),
        ("Gwen", "<3"),
        ("Stacey", "<3"),
        ("Mikha", "<3"),
        ("Jhoanna", "<3"),
        ("Sheena", "<3"),
        ("Alex Gaskarth", "<3"),
        ("Jack Barakat", "<3"),
        ("Rian", "<3"),
        ("Zack", "<3"),
    ]
    greet_words = {
        "hi",
        "hello",
        "hey",
        "bonjour",
        "goodmorning",
        "goodafternoon",
        "goodnight",
        "morning",
        "evening",
        "greetings",
        "sup",
        "yo",
        "hiya",
        "good morning",
        "good afternoon",
        "good evening",
    }
    thanks_words = {"thanks", "thank", "thankyou", "salamat", "appreciate", "grateful", "ty", "thx"}
    price_words = {"price", "cost", "rate", "rates", "php"}
    recommend_words = {
        "recommend",
        "suggest",
        "best",
        "suggestion",
        "recommendation",
        "what should",
        "what do you recommend",
        "got any",
        "any suggestion",
    }
    order_words = {"order", "buy", "checkout", "cart", "purchase", "ordering", "place order", "shop", "add to cart"}
    delivery_words = {"delivery", "deliver", "ship", "shipping", "delivered", "shipping fee"}
    branch_words = {"branch", "location", "store", "branches", "addresses", "where are you", "where are you located", "where is your store"}
    payment_words = {"payment", "gcash", "maya", "otp", "pay", "how to pay", "payment method", "mode of payment", "credit", "debit"}
    hours_words = {"hours", "open", "close", "operating", "schedule", "timing", "opening", "closing"}
    breakfast_words = {"breakfast", "morning", "morning meal", "early", "sunrise", "dawn"}
    budget_words = {"cheap", "budget", "affordable", "lowest", "low", "pricey", "expensive", "under", "less than", "below", "value", "deal", "promo", "discount"}
    stock_words = {"stock", "available", "availability", "in stock", "out of stock", "do you have", "do you sell", "can i get", "left", "remaining"}
    compare_words = {"compare", "difference", "vs", "versus", "between", "better", "worse", "different"}
    help_words = {"help", "assist", "support", "guide", "what can you do", "capabilities"}
    signup_words = {
        "signup",
        "sign up",
        "sign-up",
        "register",
        "registration",
        "welcome bonus",
        "signup bonus",
        "sign up bonus",
        "new account",
        "new user",
        "starter credit",
        "first time",
    }
    follow_up_words = {"it", "that", "this", "one", "same", "these", "those", "them"}
    menu_words = {"menu", "list", "items", "products", "what do you sell", "sell", "offer", "catalogue"}
    bye_words = {"bye", "goodbye", "see you", "later", "farewell", "take care", "cya", "peace"}
    smalltalk_phrases = {"how are you", "how's it going", "hows it going", "what's up", "whats up", "how do you feel"}
    question_words = {"what", "why", "how", "when", "where", "who", "which", "can", "do", "does", "is", "are", "should", "could", "would", "will"}
    positive_words = {"love", "great", "good", "amazing", "awesome", "nice", "cool", "perfect", "yay", "happy", "excited"}
    negative_words = {"bad", "terrible", "awful", "hate", "worst", "sucks", "sad", "angry", "upset", "annoyed", "disappointed"}
    hunger_words = {"hungry", "craving", "crave", "starving", "famished"}
    sweet_words = {"sweet", "dessert", "chocolate", "sugary"}
    savory_words = {"savory", "salty"}
    caffeine_words = {"caffeine", "coffee", "energize", "energy", "awake", "wake", "sleepy"}
    joke_words = {"joke", "funny", "laugh"}
    complaint_words = {"complain", "complaint", "refund", "cancel", "wrong", "issue", "problem", "late", "cold", "stale"}
    ingredient_words = {"ingredient", "ingredients", "allergen", "allergens", "gluten", "nuts", "nut", "dairy", "vegan", "vegetarian"}
    custom_words = {"custom", "customize", "size", "sizes", "sugar", "milk", "decaf", "less sugar", "extra", "hot", "iced", "ice"}
    order_status_words = {"order status", "track my order", "tracking", "where is my order"}
    refund_words = {"refund", "cancel order", "return", "chargeback"}
    name_reset_phrases = {"forget my name", "reset my name", "clear my name"}

    def signed_reply(intent: str, message: str) -> str:
        st.session_state.doughbot_last_intent = intent
        st.session_state.doughbot_last_topic = intent
        persona_name, heart = random.choice(personas)
        response = f"{message}\n\n{persona_name} {heart}"
        last = st.session_state.get("doughbot_last_response")
        if last == response:
            followups = [
                "Want a different suggestion?",
                "I can tailor that by budget or taste.",
                "Tell me your mood and I will personalize it.",
            ]
            response = f"{message}\n\n{random.choice(followups)}\n\n{persona_name} {heart}"
        st.session_state.doughbot_last_response = response
        return response

    def matches(candidates: set[str]) -> bool:
        for cand in candidates:
            if " " in cand:
                if cand in p:
                    return True
            elif cand in words:
                return True
        return False

    def extract_name(text: str) -> str | None:
        patterns = [
            r"\bmy name is\s+([A-Za-z][A-Za-z0-9_ -]{1,24})",
            r"\bcall me\s+([A-Za-z][A-Za-z0-9_ -]{1,24})",
            r"\bi am\s+([A-Za-z][A-Za-z0-9_ -]{1,24})",
            r"\bi'm\s+([A-Za-z][A-Za-z0-9_ -]{1,24})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def alias_in_text(alias: str, text_lower: str) -> bool:
        if " " in alias:
            return alias in text_lower
        return re.search(rf"\b{re.escape(alias)}s?\b", text_lower) is not None

    def detect_items(text_lower: str) -> list[str]:
        found = []
        for alias, canonical in item_aliases.items():
            if alias_in_text(alias, text_lower) and canonical not in found:
                found.append(canonical)
        return found

    def extract_item_qty(text_lower: str) -> tuple[dict[str, int], bool]:
        requested: dict[str, int] = {}
        explicit_qty = False
        number_words = {
            "a": 1,
            "an": 1,
            "one": 1,
            "two": 2,
            "three": 3,
            "four": 4,
            "five": 5,
            "six": 6,
            "seven": 7,
            "eight": 8,
            "nine": 9,
            "ten": 10,
        }
        for alias, canonical in item_aliases.items():
            alias_pattern = re.escape(alias) + r"s?"
            digit_patterns = [
                rf"\b(\d+)\s*x?\s+{alias_pattern}\b",
                rf"\b{alias_pattern}\s*x?\s*(\d+)\b",
            ]
            matched = False
            for pattern in digit_patterns:
                match = re.search(pattern, text_lower)
                if match:
                    requested[canonical] = requested.get(canonical, 0) + int(match.group(1))
                    explicit_qty = True
                    matched = True
                    break
            if matched:
                continue
            for word, qty in number_words.items():
                if re.search(rf"\b{word}\s+{alias_pattern}\b", text_lower):
                    requested[canonical] = requested.get(canonical, 0) + qty
                    explicit_qty = True
                    matched = True
                    break
            if not matched and alias_in_text(alias, text_lower):
                requested[canonical] = requested.get(canonical, 0) + 1
        return requested, explicit_qty

    def get_stock_safe(item: str) -> int:
        if conn is None:
            return 50
        try:
            row = conn.execute("SELECT stock FROM inventory WHERE item = ?", (item,)).fetchone()
            return int(row[0]) if row else 0
        except:
            return 50

    if not p:
        return signed_reply("fallback", "Ask me about menu items, prices, pairings, stock, or order steps.")

    if any(phrase in p for phrase in name_reset_phrases):
        st.session_state.doughbot_user_name = None
        return signed_reply("name", "Okay, I will forget your name. How can I help?")

    name = extract_name(prompt_clean)
    if name:
        st.session_state.doughbot_user_name = name
        return signed_reply("name", f"Nice to meet you, {name}. How can I help today?")

    if "my" in words and "name" in words and ("what" in words or "remember" in words):
        remembered = st.session_state.get("doughbot_user_name")
        if remembered:
            return signed_reply("name", f"Your name is {remembered}.")
        return signed_reply("name", "I do not know your name yet. Tell me with 'my name is ...'.")

    if "your" in words and "name" in words:
        return signed_reply("about", "I am DoughBot, your Pan de Staku assistant.")

    if matches(bye_words):
        return signed_reply("bye", "Thanks for chatting. Come back anytime for bread or coffee.")

    if matches(greet_words):
        return signed_reply(
            "greeting",
            random.choice(
                [
                    "Bonjour! I am DoughBot. Looking for bread, coffee, or a combo today?",
                    "Welcome to Pan de Staku. I can suggest items, prices, pairings, and best picks.",
                    "Hi! Tell me your mood and budget, and I will suggest something.",
                ]
            ),
        )

    if any(phrase in p for phrase in smalltalk_phrases) or ("how" in words and "you" in words):
        return signed_reply(
            "smalltalk",
            "I am doing well and ready to help. Want a recommendation, price check, or stock update?",
        )

    if matches(help_words):
        return signed_reply(
            "help",
            "I can help with menu, prices, stock checks, pairings, branch info, delivery, and checkout steps. "
            "Try: 'recommend breakfast under 250', 'compare latte vs cappuccino', or '2 croissant and 1 latte'.",
        )

    if matches(thanks_words):
        return signed_reply(
            "thanks",
            random.choice(
                [
                    "You are welcome. Enjoy your order.",
                    "Happy to help. I can suggest another combo anytime.",
                    "Anytime. Ask me for a custom combo by mood or budget.",
                ]
            ),
        )

    if matches(signup_words):
        return signed_reply(
            "signup_bonus",
            f"New customers receive PHP {SIGNUP_BONUS} wallet credit after registering. It applies automatically at checkout.",
        )

    if "who" in words and "you" in words:
        return signed_reply(
            "about",
            "I am DoughBot, your Pan de Staku assistant for menu guidance, smart recommendations, and checkout support.",
        )

    if matches(menu_words):
        artisan_list = ", ".join([f"{item} (PHP {price})" for item, price in bread_menu.items()])
        local_list = ", ".join([f"{item} (PHP {price})" for item, price in local_bakes_menu.items()])
        coffee_list = ", ".join([f"{item} (PHP {price})" for item, price in coffee_menu.items()])
        drink_list = ", ".join([f"{item} (PHP {price})" for item, price in drinks_menu.items()])
        return signed_reply(
            "menu",
            "Artisan Bread:\n"
            + artisan_list
            + "\n\nLocal Bakes:\n"
            + local_list
            + "\n\nCoffee:\n"
            + coffee_list
            + "\n\nDrinks:\n"
            + drink_list,
        )

    mentioned_items = detect_items(p)
    detected_item = mentioned_items[0] if mentioned_items else None

    if not detected_item and st.session_state.get("doughbot_last_item") and words.intersection(follow_up_words):
        detected_item = st.session_state.doughbot_last_item
        mentioned_items = [detected_item]

    if detected_item:
        st.session_state.doughbot_last_item = detected_item

    if matches(compare_words) and len(mentioned_items) >= 2:
        a, b = mentioned_items[0], mentioned_items[1]
        pa, pb = all_menu[a], all_menu[b]
        diff = abs(pa - pb)
        if pa == pb:
            msg = f"{a} and {b} are both PHP {pa}. Choose by taste preference."
        elif pa > pb:
            msg = f"{a} (PHP {pa}) is PHP {diff} more than {b} (PHP {pb})."
        else:
            msg = f"{b} (PHP {pb}) is PHP {diff} more than {a} (PHP {pa})."
        return signed_reply("compare", msg)

    if matches(stock_words):
        if mentioned_items:
            lines = []
            for item in mentioned_items:
                stock = get_stock_safe(item)
                if stock > 10:
                    lines.append(f"- {item}: available ({stock})")
                elif stock > 0:
                    lines.append(f"- {item}: limited ({stock})")
                else:
                    lines.append(f"- {item}: out of stock")
            return signed_reply("stock", "Stock update:\n" + "\n".join(lines))
        return signed_reply("stock", "Which item should I check stock for?")

    if matches(order_status_words):
        return signed_reply("order_status", "Order tracking is handled in your account or with the branch. Share your order details and branch.")

    if matches(refund_words):
        return signed_reply("refund", "For refunds or cancellations, please contact your branch with order details.")

    requested, explicit_qty = extract_item_qty(p)
    if requested and (matches(order_words) or explicit_qty or "total" in words or "estimate" in words):
        lines = []
        total = 0
        for item, qty in requested.items():
            subtotal = all_menu[item] * qty
            lines.append(f"- {item} x{qty}: PHP {subtotal}")
            total += subtotal
        return signed_reply(
            "order_estimate",
            "Estimated order total:\n"
            + "\n".join(lines)
            + f"\nTotal estimate: PHP {total}\n\nTo complete: login -> Order page -> add items -> Cart -> payment.",
        )

    if matches(recommend_words) or matches(breakfast_words) or words.intersection(hunger_words) or words.intersection(caffeine_words):
        picks = [
            "Croissant with Latte",
            "Brioche with Cappuccino",
            "Pain au Chocolat with Mocha",
            "Sourdough with Flat White",
        ]
        if words.intersection(sweet_words):
            return signed_reply("recommend", "Sweet craving pick: Pain au Chocolat with Mocha.")
        if words.intersection(savory_words):
            return signed_reply("recommend", "Savory pick: Fougasse with Espresso.")
        if words.intersection(caffeine_words):
            return signed_reply("recommend", "Need energy? Espresso or Americano are strong, or try a Latte for balance.")
        if matches(breakfast_words):
            return signed_reply("recommend", "Breakfast pick: Croissant with Latte. It is balanced, light, and popular in the morning.")
        budget_picks = [pick for pick in picks if all_menu[pick.split(" with ")[0]] + all_menu[pick.split(" with ")[1]] <= 270]
        if matches(budget_words) and budget_picks:
            return signed_reply("recommend", f"Budget-friendly combo: {random.choice(budget_picks)}.")
        return signed_reply("recommend", f"My recommendation: {random.choice(picks)}.")

    if matches(budget_words):
        amounts = [int(n) for n in re.findall(r"\d+", p)]
        budget = min(amounts) if amounts else None
        if budget is not None:
            combos = []
            for bread, coffee in pairings.items():
                total = all_menu[bread] + all_menu[coffee]
                if total <= budget:
                    combos.append(f"{bread} with {coffee} (PHP {total})")
            singles = [f"{item} (PHP {price})" for item, price in all_menu.items() if price <= budget]
            if combos:
                return signed_reply("price", "Combos within budget:\n" + "\n".join(combos[:4]))
            if singles:
                return signed_reply("price", "Items within budget:\n" + ", ".join(singles[:6]))
            cheapest_item = min(all_menu, key=all_menu.get)
            return signed_reply("price", f"Cheapest item is {cheapest_item} at PHP {all_menu[cheapest_item]}.")
        sorted_items = sorted(all_menu.items(), key=lambda x: x[1])
        cheapest = ", ".join([f"{item} (PHP {price})" for item, price in sorted_items[:3]])
        premium = ", ".join([f"{item} (PHP {price})" for item, price in sorted_items[-3:]])
        if {"expensive", "pricey"}.intersection(words):
            return signed_reply("price", f"Premium picks: {premium}.")
        return signed_reply("price", f"Best budget picks: {cheapest}.")

    if detected_item and ("pair" in words or "with" in words or "goes" in words):
        paired = pairings.get(detected_item, "a coffee of your choice")
        return signed_reply("pairing", f"{detected_item} pairs well with {paired}.")

    how_much = "how much" in p
    if detected_item and (matches(price_words) or how_much):
        price = all_menu.get(detected_item)
        if price is not None:
            return signed_reply("price", f"{detected_item} is PHP {price}.")

    if matches(price_words) or how_much:
        min_item = min(all_menu, key=all_menu.get)
        max_item = max(all_menu, key=all_menu.get)
        return signed_reply(
            "price",
            f"Prices range from PHP {all_menu[min_item]} ({min_item}) to PHP {all_menu[max_item]} ({max_item}).",
        )

    if matches(delivery_words):
        return signed_reply(
            "delivery",
            random.choice(
                [
                    "Delivery fee starts at PHP 40, depending on distance.",
                    "Yes, delivery is available. Base fee is PHP 40.",
                    "We support local delivery. Final fee depends on branch distance.",
                ]
            ),
        )

    if matches(branch_words):
        current_branch = st.session_state.get("branch", BRANCHES[0])
        return signed_reply("branch", f"Branches: {BRANCH_LIST_TEXT}. Your current selected branch is {current_branch}.")

    if matches(payment_words):
        return signed_reply(
            "payment",
            "We accept GCash, Maya, and Cash. GCash/Maya require an 11-digit mobile number and 6-digit OTP. "
            "Cash only needs your mobile number.",
        )

    if matches(hours_words):
        return signed_reply(
            "hours",
            "Store hours are managed per branch. Select your branch and check latest branch announcements.",
        )

    if matches(ingredient_words):
        return signed_reply(
            "ingredients",
            "For allergens or dietary needs, please check with staff or ingredient labels. Tell me the item and I can guide you.",
        )

    if matches(custom_words):
        return signed_reply(
            "custom",
            "Some customizations are available depending on branch. Tell me your preference and I will note it.",
        )

    if matches(joke_words):
        return signed_reply("smalltalk", "Bakery joke: Why did the baguette get promoted? It always rose to the occasion.")

    if matches(complaint_words):
        return signed_reply("support", "Sorry about the trouble. Tell me the branch, item, and what happened so I can help.")

    if detected_item:
        if detected_item in drinks_menu:
            paired = "a fresh bread of your choice"
        else:
            paired = pairings.get(detected_item, "a coffee of your choice")
        price = all_menu.get(detected_item)
        stock = get_stock_safe(detected_item)
        if price is not None:
            stock_note = "in stock" if stock > 0 else "currently unavailable"
            return signed_reply(
                "item_info",
                f"{detected_item} is PHP {price}, usually pairs with {paired}, and is {stock_note}.",
            )

    if words.intersection(positive_words):
        return signed_reply("smalltalk", "Glad to hear that. Want a matching bread and coffee combo?")

    if words.intersection(negative_words):
        return signed_reply("smalltalk", "Sorry you are feeling that way. Want a comfort pick?")

    if "?" in prompt_clean or words.intersection(question_words):
        return signed_reply(
            "fallback",
            "Good question. I focus on Pan de Staku menu, prices, and ordering help. "
            "If you want that, tell me the item, mood, or budget.",
        )

    short_echo = prompt_clean if len(prompt_clean) <= 140 else prompt_clean[:137] + "..."
    return signed_reply(
        "fallback",
        f"Thanks for sharing: \"{short_echo}\". "
        "I can help with menu, prices, pairings, stock checks, delivery, payment, branches, and order estimates. "
        "Try: 'recommend breakfast', 'compare latte vs cappuccino', or 'is brioche available?'.",
    )
st.set_page_config(page_title="Pan de Staku", page_icon=":croissant:", layout="wide")

conn = get_db_connection()
init_db(conn)
seed_default_admin(conn)
seed_inventory(conn)
grant_signup_bonus_to_existing_users(conn)
init_session_state()

appearance_choice = st.sidebar.radio(
    "Appearance",
    ["Light", "Dark", "Coffee", "Cheese"],
    index=["Light", "Dark", "Coffee", "Cheese"].index(st.session_state.appearance)
    if st.session_state.appearance in ["Light", "Dark", "Coffee", "Cheese"]
    else 0,
    horizontal=True,
)
st.session_state.appearance = appearance_choice

if st.session_state.appearance == "Dark":
    app_background = (
        "radial-gradient(circle at 12% 12%, rgba(201, 150, 90, 0.20), transparent 38%),"
        "radial-gradient(circle at 86% 12%, rgba(143, 110, 99, 0.28), transparent 36%),"
        "linear-gradient(150deg, #2f1f18 0%, #4e342e 44%, #8d6e63 73%, #c9965a 100%)"
    )
    sidebar_background = "linear-gradient(170deg, #2b1b15 0%, #4e342e 36%, #7a4e35 66%, #c9965a 100%)"
    block_background = "linear-gradient(160deg, rgba(74, 50, 37, 0.78), rgba(40, 27, 21, 0.52))"
    block_border = "rgba(222, 185, 135, 0.22)"
    title_color = "#fff3e0"
    text_color = "#f5dfc4"
    nav_text_color = "#fff8ec"
    nav_hover = "rgba(255, 248, 236, 0.18)"
    nav_card = "rgba(255, 248, 236, 0.08)"
    accent_color = "#f3c27a"
    accent_soft = "rgba(243, 194, 122, 0.18)"
    glow_color = "rgba(243, 194, 122, 0.35)"
    shadow_color = "rgba(12, 8, 6, 0.55)"
elif st.session_state.appearance == "Coffee":
    app_background = (
        "radial-gradient(circle at 14% 12%, rgba(210, 180, 140, 0.25), transparent 36%),"
        "radial-gradient(circle at 84% 14%, rgba(111, 78, 55, 0.28), transparent 34%),"
        "linear-gradient(150deg, #3b2a22 0%, #5c4033 34%, #8b5e3c 64%, #b07d4f 100%)"
    )
    sidebar_background = "linear-gradient(170deg, #2f221d 0%, #4b352b 34%, #6f4e37 67%, #b07d4f 100%)"
    block_background = "linear-gradient(160deg, rgba(80, 56, 42, 0.76), rgba(46, 32, 25, 0.54))"
    block_border = "rgba(226, 198, 165, 0.24)"
    title_color = "#f9ead7"
    text_color = "#f0dcc3"
    nav_text_color = "#fff4e7"
    nav_hover = "rgba(255, 244, 231, 0.16)"
    nav_card = "rgba(255, 244, 231, 0.08)"
    accent_color = "#f0b66a"
    accent_soft = "rgba(240, 182, 106, 0.2)"
    glow_color = "rgba(240, 182, 106, 0.35)"
    shadow_color = "rgba(18, 12, 9, 0.55)"
elif st.session_state.appearance == "Cheese":
    app_background = (
        "radial-gradient(circle at 12% 16%, rgba(255, 250, 220, 0.42), transparent 38%),"
        "radial-gradient(circle at 86% 12%, rgba(255, 213, 128, 0.34), transparent 34%),"
        "linear-gradient(145deg, #fff6d9 0%, #ffe8a8 33%, #ffd166 62%, #d6a651 80%, #8f5e2e 100%)"
    )
    sidebar_background = "linear-gradient(165deg, #fff3cc 0%, #ffe08a 30%, #f2c261 58%, #c9965a 80%, #7f4f24 100%)"
    block_background = "linear-gradient(160deg, rgba(255, 251, 231, 0.76), rgba(255, 236, 184, 0.40))"
    block_border = "rgba(143, 94, 46, 0.24)"
    title_color = "#3f250f"
    text_color = "#503116"
    nav_text_color = "#1d1208"
    nav_hover = "rgba(79, 49, 22, 0.12)"
    nav_card = "rgba(255, 247, 218, 0.48)"
    accent_color = "#b56a1f"
    accent_soft = "rgba(181, 106, 31, 0.16)"
    glow_color = "rgba(181, 106, 31, 0.28)"
    shadow_color = "rgba(94, 58, 24, 0.3)"
else:
    app_background = (
        "radial-gradient(circle at 12% 14%, rgba(255, 248, 236, 0.92), transparent 40%),"
        "radial-gradient(circle at 88% 10%, rgba(250, 224, 184, 0.45), transparent 38%),"
        "linear-gradient(145deg, #fff8ec 0%, #f6e7ce 36%, #d9b078 63%, #c9965a 82%, #8a5a3b 100%)"
    )
    sidebar_background = "linear-gradient(165deg, #fff9ef 0%, #f1dec1 30%, #ddb785 58%, #c9965a 80%, #8a5a3b 100%)"
    block_background = "linear-gradient(160deg, rgba(255, 250, 240, 0.74), rgba(255, 245, 228, 0.36))"
    block_border = "rgba(124, 83, 57, 0.20)"
    title_color = "#3a2618"
    text_color = "#4b3324"
    nav_text_color = "#16100b"
    nav_hover = "rgba(78, 52, 46, 0.12)"
    nav_card = "rgba(255, 248, 236, 0.34)"
    accent_color = "#c7762f"
    accent_soft = "rgba(199, 118, 47, 0.16)"
    glow_color = "rgba(199, 118, 47, 0.28)"
    shadow_color = "rgba(82, 52, 32, 0.3)"

st.markdown(
    f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;700&family=Space+Grotesk:wght@400;500;600&display=swap');

:root {{
    --accent: {accent_color};
    --accent-soft: {accent_soft};
    --glow: {glow_color};
    --shadow: {shadow_color};
    --card-radius: 18px;
}}

@keyframes fadeIn {{
    from {{ opacity: 0; transform: translateY(20px); }}
    to {{ opacity: 1; transform: translateY(0); }}
}}

.stApp {{
    animation: fadeIn 0.8s ease-in-out;
    background: {app_background};
    color: {text_color};
    font-family: 'Space Grotesk', 'Segoe UI', sans-serif;
}}

section[data-testid="stSidebar"] {{
    background: {sidebar_background};
    border-right: none;
    box-shadow: 8px 0 24px rgba(0, 0, 0, 0.18);
}}

section[data-testid="stSidebar"] * {{
    color: {nav_text_color} !important;
    font-family: 'Space Grotesk', 'Segoe UI', sans-serif;
}}

.sidebar-brand {{
    font-family: 'Fraunces', 'Times New Roman', serif;
    font-size: 1.6rem;
    letter-spacing: 0.04em;
    margin-bottom: 0.2rem;
}}

.sidebar-tag {{
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.25em;
    color: var(--accent);
    margin-bottom: 0.9rem;
}}

section[data-testid="stSidebar"] [data-baseweb="radio"] {{
    background: {nav_card};
    border: none;
    border-radius: 12px;
    padding: 10px 12px;
    box-shadow: none;
}}

section[data-testid="stSidebar"] [data-baseweb="radio"] label {{
    margin-bottom: 4px;
    border-radius: 10px;
    padding: 6px 10px;
    border-left: 3px solid transparent;
    transition: background 0.2s ease, transform 0.2s ease, border-color 0.2s ease;
}}

section[data-testid="stSidebar"] [data-baseweb="radio"] label:hover {{
    background: {nav_hover};
    transform: translateX(2px);
}}

section[data-testid="stSidebar"] [data-baseweb="radio"] label[data-checked="true"],
section[data-testid="stSidebar"] [data-baseweb="radio"] label:has(input:checked),
section[data-testid="stSidebar"] [data-baseweb="radio"] input:checked + div {{
    background: var(--accent-soft);
    border-left-color: var(--accent);
    font-weight: 600;
}}

section[data-testid="stSidebar"] .stRadio > label {{
    font-size: 0.85rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin-bottom: 6px;
    display: block;
}}

[data-testid="stHeader"] {{
    background: transparent;
}}

[data-testid="stToolbar"] {{
    right: 1rem;
}}

.block-container {{
    background: {block_background};
    border: 1px solid {block_border};
    border-radius: var(--card-radius);
    padding: 1.6rem 1.4rem;
    backdrop-filter: blur(2px);
    box-shadow: 0 18px 45px var(--shadow);
}}

h1, h2, h3, .stTitle {{
    color: {title_color};
    font-family: 'Fraunces', 'Times New Roman', serif;
    letter-spacing: 0.01em;
}}

p, li, label, span, div {{
    color: {text_color};
    font-family: 'Space Grotesk', 'Segoe UI', sans-serif;
}}

.stButton > button {{
    background: linear-gradient(135deg, var(--accent), #ffe1b3);
    color: #2a1a0f;
    border: none;
    border-radius: 999px;
    padding: 0.6rem 1.4rem;
    font-weight: 600;
    box-shadow: 0 10px 24px var(--glow);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}}

.stButton > button:hover {{
    transform: translateY(-2px);
    box-shadow: 0 14px 32px var(--glow);
}}

.hero-card {{
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.16), rgba(255, 255, 255, 0.04));
    border: 1px solid {block_border};
    border-radius: 22px;
    padding: 1.8rem 2rem;
    box-shadow: 0 20px 40px var(--shadow);
    backdrop-filter: blur(6px);
}}

.hero-eyebrow {{
    text-transform: uppercase;
    letter-spacing: 0.25em;
    color: var(--accent);
    font-size: 0.75rem;
    font-weight: 600;
}}

.hero-title {{
    font-size: 2.4rem;
    margin: 0.25rem 0 0.6rem 0;
}}

.hero-subtitle {{
    font-size: 1rem;
    max-width: 650px;
}}

.hero-badges {{
    display: flex;
    gap: 0.6rem;
    flex-wrap: wrap;
    margin-top: 1.1rem;
}}

.hero-badge {{
    background: var(--accent-soft);
    color: {title_color};
    padding: 0.35rem 0.8rem;
    border-radius: 999px;
    font-weight: 600;
    font-size: 0.75rem;
    border: 1px solid {block_border};
}}

.presentation-card {{
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.16), rgba(255, 255, 255, 0.04));
    border: 1px solid {block_border};
    border-radius: 20px;
    padding: 1.3rem 1.4rem;
    box-shadow: 0 18px 36px var(--shadow);
    margin-bottom: 0.9rem;
}}

.presentation-title {{
    font-family: 'Fraunces', 'Times New Roman', serif;
    font-size: 1.4rem;
    margin-bottom: 0.45rem;
}}

.presentation-meta {{
    font-size: 0.9rem;
    opacity: 0.95;
}}

.presentation-outline {{
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid {block_border};
    border-radius: 16px;
    padding: 0.9rem 1rem;
}}

.presentation-frame {{
    border: 1px solid {block_border};
    border-radius: 18px;
    box-shadow: 0 18px 36px var(--shadow);
}}

.menu-section {{
    margin-top: 1.6rem;
}}

.menu-header {{
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    margin-bottom: 0.8rem;
    gap: 1rem;
}}

.menu-title {{
    font-size: 1.4rem;
    font-weight: 600;
    color: {title_color};
    font-family: 'Fraunces', 'Times New Roman', serif;
}}

.menu-subtitle {{
    font-size: 0.9rem;
    opacity: 0.9;
}}

.menu-shell {{
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.12), rgba(255, 255, 255, 0.03));
    border: 1px solid {block_border};
    border-radius: 22px;
    padding: 1.2rem 1.4rem;
    box-shadow: 0 18px 40px var(--shadow);
    backdrop-filter: blur(8px);
}}

.menu-count {{
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--accent);
    letter-spacing: 0.08em;
    text-transform: uppercase;
}}

.menu-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 14px;
}}

.menu-card {{
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid {block_border};
    border-radius: 16px;
    padding: 0.9rem 1rem;
    box-shadow: 0 12px 30px var(--shadow);
    position: relative;
    overflow: hidden;
    transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}}

.menu-card::before {{
    content: "";
    position: absolute;
    inset: -1px;
    background: radial-gradient(circle at top left, var(--accent-soft), transparent 65%);
    opacity: 0.9;
}}

.menu-card:hover {{
    transform: translateY(-4px);
    border-color: var(--accent);
    box-shadow: 0 18px 36px var(--shadow);
}}

.menu-name {{
    position: relative;
    font-weight: 600;
    margin-bottom: 0.35rem;
}}

.menu-price {{
    position: relative;
    color: var(--accent);
    font-weight: 600;
    display: inline-block;
    background: var(--accent-soft);
    padding: 0.2rem 0.6rem;
    border-radius: 999px;
    border: 1px solid {block_border};
}}

.menu-list {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 0.6rem 1.4rem;
}}

.menu-line {{
    display: flex;
    align-items: baseline;
    gap: 0.6rem;
    padding: 0.4rem 0.2rem;
    border-bottom: 1px dashed rgba(255, 255, 255, 0.1);
}}

.menu-line-name {{
    font-weight: 600;
}}

.menu-line-dots {{
    flex: 1;
    border-bottom: 1px dotted rgba(255, 255, 255, 0.35);
    transform: translateY(-4px);
}}

.menu-line-price {{
    color: var(--accent);
    font-weight: 600;
    white-space: nowrap;
}}

.menu-banner {{
    border-radius: 24px;
    padding: 1.6rem 2rem;
    border: 1px solid {block_border};
    background: linear-gradient(135deg, rgba(255, 246, 214, 0.22), rgba(255, 255, 255, 0.04));
    box-shadow: 0 20px 42px var(--shadow);
    margin-bottom: 1.4rem;
}}

.menu-banner-title {{
    font-size: 1.9rem;
    font-weight: 700;
    color: {title_color};
    font-family: 'Fraunces', 'Times New Roman', serif;
}}

.menu-banner-subtitle {{
    font-size: 1rem;
    max-width: 620px;
}}

.menu-banner-pill {{
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    margin-top: 0.8rem;
    padding: 0.35rem 0.8rem;
    border-radius: 999px;
    border: 1px solid {block_border};
    background: var(--accent-soft);
    font-weight: 600;
}}

.order-card {{
    border-radius: 22px;
    padding: 1.6rem 1.8rem;
    border: 1px solid {block_border};
    background: linear-gradient(135deg, rgba(255, 250, 240, 0.18), rgba(255, 255, 255, 0.04));
    box-shadow: 0 18px 40px var(--shadow);
    margin-bottom: 1.2rem;
}}

.order-title {{
    font-size: 1.5rem;
    font-weight: 700;
    color: {title_color};
    font-family: 'Fraunces', 'Times New Roman', serif;
}}

.order-subtitle {{
    font-size: 0.95rem;
    opacity: 0.95;
    max-width: 620px;
}}

.order-badges {{
    display: flex;
    gap: 0.6rem;
    flex-wrap: wrap;
    margin-top: 0.9rem;
}}

.order-badge {{
    background: var(--accent-soft);
    color: {title_color};
    padding: 0.3rem 0.8rem;
    border-radius: 999px;
    font-weight: 600;
    font-size: 0.75rem;
    border: 1px solid {block_border};
}}

.order-panel {{
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid {block_border};
    border-radius: 18px;
    padding: 1.2rem 1.3rem;
    box-shadow: 0 14px 32px var(--shadow);
}}

.nav-guide {{
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid {block_border};
    border-radius: 14px;
    padding: 0.8rem 0.9rem;
    margin-top: 0.8rem;
}}

.nav-guide-title {{
    font-size: 0.7rem;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--accent);
    font-weight: 700;
    margin-bottom: 0.35rem;
}}

.nav-guide-text {{
    font-size: 0.85rem;
}}

.nav-all {{
    margin-top: 0.7rem;
    padding: 0.6rem 0.7rem;
    border-radius: 12px;
    border: 1px solid {block_border};
    background: rgba(255, 255, 255, 0.06);
    max-height: 220px;
    overflow-y: auto;
}}

.nav-all-item {{
    font-size: 0.78rem;
    line-height: 1.35;
    margin-bottom: 0.45rem;
}}

.nav-all-item b {{
    color: {title_color};
}}

.top-nav {{
    position: sticky;
    top: 0;
    z-index: 10;
    padding: 0.8rem 1rem;
    margin-bottom: 1rem;
    border-radius: 18px;
    border: 1px solid {block_border};
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.18), rgba(255, 255, 255, 0.04));
    box-shadow: 0 16px 34px var(--shadow);
}}

.top-nav [data-baseweb="radio"] {{
    background: transparent;
    border: none;
    padding: 0;
}}

.top-nav [data-baseweb="radio"] > div {{
    display: flex;
    flex-wrap: wrap;
    gap: 0.55rem;
}}

.top-nav [data-baseweb="radio"] label {{
    background: rgba(255, 255, 255, 0.12);
    border: 1px solid {block_border};
    border-radius: 999px;
    padding: 0.35rem 0.85rem;
    font-weight: 600;
    transition: transform 0.2s ease, border-color 0.2s ease, background 0.2s ease;
}}

.top-nav [data-baseweb="radio"] label:hover {{
    transform: translateY(-1px);
    border-color: var(--accent);
}}

.top-nav [data-baseweb="radio"] label[data-checked="true"],
.top-nav [data-baseweb="radio"] label:has(input:checked),
.top-nav [data-baseweb="radio"] input:checked + div {{
    background: var(--accent-soft);
    border-color: var(--accent);
}}

.page-definition {{
    border-radius: 18px;
    padding: 1rem 1.2rem;
    border: 1px solid {block_border};
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.12), rgba(255, 255, 255, 0.04));
    box-shadow: 0 14px 30px var(--shadow);
    margin-bottom: 1rem;
}}

.page-definition-title {{
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.22em;
    color: var(--accent);
    font-weight: 700;
}}

.page-definition-text {{
    font-size: 0.95rem;
    margin-top: 0.3rem;
}}

div[data-baseweb="select"] > div {{
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid {block_border};
    border-radius: 999px;
    box-shadow: 0 10px 24px var(--shadow);
}}

div[data-baseweb="select"] > div:hover {{
    border-color: var(--accent);
}}

div[data-baseweb="select"] svg {{
    color: var(--accent);
}}

.branch-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 14px;
    margin-top: 1rem;
}}

.branch-card {{
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid {block_border};
    border-radius: 16px;
    padding: 1rem 1.1rem;
    box-shadow: 0 12px 30px var(--shadow);
}}

.branch-card.selected {{
    border-color: var(--accent);
    box-shadow: 0 0 0 1px var(--accent) inset, 0 18px 36px var(--shadow);
}}

.branch-title {{
    font-family: 'Fraunces', 'Times New Roman', serif;
    font-size: 1.2rem;
    margin-bottom: 0.4rem;
}}

.branch-meta {{
    font-size: 0.85rem;
    opacity: 0.9;
}}

.chat-panel {{
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid {block_border};
    border-radius: 18px;
    padding: 1.2rem 1.4rem;
    box-shadow: 0 14px 32px var(--shadow);
    margin-bottom: 1rem;
}}

.chat-badges {{
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
    margin-top: 0.8rem;
}}

.chat-badge {{
    background: var(--accent-soft);
    color: {title_color};
    padding: 0.28rem 0.7rem;
    border-radius: 999px;
    font-weight: 600;
    font-size: 0.72rem;
    border: 1px solid {block_border};
}}
</style>
""",
    unsafe_allow_html=True,
)

cart_count = sum(entry["qty"] for entry in st.session_state.cart)
current_user = st.session_state.user or "Guest"
st.sidebar.markdown(
    """
<div class="sidebar-brand">Pan de Staku</div>
<div class="sidebar-tag">Artisan Bakery</div>
""",
    unsafe_allow_html=True,
)
st.sidebar.caption(f"User: {current_user} | Branch: {st.session_state.branch}")
st.sidebar.divider()
nav_items = [
    "Home",
    "Login",
    "Presentation",
    "Register",
    "Branch",
    "Menu List",
    "Order",
    "Cart",
    "DoughBot Chat",
    "Product",
    "Service",
    "Contact",
    "Admin Dashboard",
]
if "nav" not in st.session_state:
    st.session_state.nav = nav_items[0]
if "pending_nav" in st.session_state:
    st.session_state.nav = st.session_state.pop("pending_nav")

st.markdown('<div class="top-nav">', unsafe_allow_html=True)
menu = st.radio(
    "Navigation",
    nav_items,
    key="nav",
    horizontal=True,
    label_visibility="collapsed",
)
st.markdown("</div>", unsafe_allow_html=True)

page_definition = NAV_DEFINITIONS.get(menu, "")
if page_definition:
    st.markdown(
        f"""
<div class="page-definition">
  <div class="page-definition-title">{menu}</div>
  <div class="page-definition-text">{page_definition}</div>
</div>
""",
        unsafe_allow_html=True,
    )

nav_definition = NAV_DEFINITIONS.get(menu, "")
if nav_definition:
    st.sidebar.markdown(
        f"""
<div class="nav-guide">
  <div class="nav-guide-title">Navigation</div>
  <div class="nav-guide-text">{nav_definition}</div>
</div>
""",
        unsafe_allow_html=True,
    )

all_defs = "".join(
    [
        f'<div class="nav-all-item"><b>{item}</b>: {NAV_DEFINITIONS.get(item, "")}</div>'
        for item in nav_items
    ]
)
st.sidebar.markdown(
    f"""
<div class="nav-all">
  {all_defs}
</div>
""",
    unsafe_allow_html=True,
)

if menu == "Home":
    st.markdown(
        """
<div class="hero-card">
  <div class="hero-eyebrow">Pan de Staku</div>
  <div class="hero-title">Freshly Baked. Brightly Served.</div>
  <div class="hero-subtitle">
    Enterprise French bakery and coffee management with local favorites, glow-up visuals,
    and a refreshed drink bar for every branch.
  </div>
  <div class="hero-badges">
    <span class="hero-badge">Artisan Breads</span>
    <span class="hero-badge">Local Bakes</span>
    <span class="hero-badge">Coffee + Drinks</span>
    <span class="hero-badge">Smart Ordering</span>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown(
        """
Pan de Staku is a modern bakery and coffee concept built around a simple promise: deliver artisan-quality bread,
carefully brewed coffee, and reliable digital service in one connected experience. The name represents a fusion of
traditional baking roots and smart operations. "Pan" points to bread craftsmanship, while "Staku" reflects structured,
technology-assisted business flow for daily bakery operations.

At its core, Pan de Staku is both a customer-facing food brand and an internal management platform. For customers,
it provides a consistent way to browse products, place orders, pay digitally, and receive support through an assistant.
For the business team, it supports inventory visibility, branch-level control, and operational decision making through
real sales and profit records.

The long-term vision of Pan de Staku is to create a bakery ecosystem where quality and convenience are not separate.
Each branch follows the same product standards and service approach while still serving local demand efficiently.
From handcrafted croissants to classic espresso drinks, every menu item is positioned to maintain premium value,
balanced pricing, and customer trust.

Pan de Staku also emphasizes sustainability in operations: reducing waste through stock tracking, improving fulfillment
accuracy through branch assignment, and enabling repeatable service standards through guided digital workflows. The goal
is not only to sell bakery products, but to establish a dependable food-and-service system that can scale across cities
without losing the feel of a neighborhood bakery.
"""
    )

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Brand Definition")
        st.write(
            "Pan de Staku is an integrated bakery management model that combines artisan baking, specialty coffee, "
            "and branch-based digital commerce into one operational platform."
        )
    with col2:
        st.subheader("Why It Matters")
        st.write(
            "It improves customer convenience while giving the business better control over stock, sales, and service "
            "quality across multiple locations."
        )

    image_candidates = [Path("pan_de_staku.png"), Path("assets/pan_de_staku.png")]
    home_image = next((candidate for candidate in image_candidates if candidate.exists()), None)
    if home_image:
        left_col, center_col, right_col = st.columns([1, 2, 1])
        with center_col:
            st.image(str(home_image), width="stretch")
            st.markdown(
                """
<div style="text-align: center; margin-top: 0.55rem; font-weight: 600;">
  Pan de Staku: Freshly baked every day, warmly served for every moment.
</div>
""",
                unsafe_allow_html=True,
            )

elif menu == "Product":
    st.header("Products")
    st.write(
        "Our product line is designed for customers who want high-quality baked goods and coffee with predictable taste, "
        "freshness, and value."
    )

    st.subheader("Signature Bread Collection")
    for item, price in bread_menu.items():
        st.write(f"- {item}: PHP {price}")

    st.subheader("Local Favorite Bakes")
    for item, price in local_bakes_menu.items():
        st.write(f"- {item}: PHP {price}")

    st.subheader("Coffee Program")
    for item, price in coffee_menu.items():
        st.write(f"- {item}: PHP {price}")

    st.subheader("Drink Bar")
    for item, price in drinks_menu.items():
        st.write(f"- {item}: PHP {price}")

    st.subheader("Product Direction")
    st.write(
        "Pan de Staku products focus on daily freshness, balanced flavor profiles, and curated bread-and-coffee pairings "
        "to improve customer satisfaction and repeat purchases."
    )

elif menu == "Service":
    st.header("Services")
    st.write("Pan de Staku provides a complete service flow from product discovery to post-order assistance.")

    st.markdown(
        f"""
- In-store and branch-based ordering for walk-in and local fulfillment.
- Digital cart and checkout flow for fast order placement.
- GCash and Maya payment support with verification flow.
- Multi-branch coverage in {BRANCH_LIST_TEXT}.
- DoughBot support for menu guidance, pairings, prices, and ordering steps.
- Inventory-aware ordering to reduce out-of-stock frustration.
"""
    )

    st.subheader("Service Commitment")
    st.write(
        "We aim to deliver accurate orders, transparent pricing, and responsive customer support while continuously "
        "improving branch-level performance."
    )

elif menu == "Contact":
    st.header("Contact Us")
    st.write("Reach Pan de Staku for orders, partnerships, branch concerns, or customer support.")

    st.markdown(
        f"""
**Head Office Email:** support@pandestaku.com  
**Customer Hotline:** +63 917 555 0123  
**Business Hours:** Monday to Sunday, 7:00 AM - 9:00 PM  
**Main Branches:** {BRANCH_LIST_TEXT}
"""
    )

    st.subheader("Contact Channels")
    st.write("- General Inquiries: support@pandestaku.com")
    st.write("- Franchise and Partnerships: partnerships@pandestaku.com")
    st.write("- Billing and Payments: billing@pandestaku.com")
    st.write("- Branch Operations: operations@pandestaku.com")

elif menu == "Login":
    st.header("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        user = authenticate_user(conn, username, password)
        if user:
            st.session_state.user = user["username"]
            st.session_state.role = user["role"]
            if user["role"] == "admin":
                st.session_state.pending_nav = "Admin Dashboard"
                st.success("Login successful. Redirecting to Admin Dashboard...")
                st.rerun()
            st.success("Login successful.")
        else:
            st.error("Invalid credentials.")

elif menu == "Presentation":
    st.header("Presentation")
    st.write("Access the latest Pan de Staku deck with download options and in-app preview.")

    pptx_path, pdf_path = get_presentation_paths()
    if not pptx_path and not pdf_path:
        st.error("Presentation file not found. Add `Pan de Staku.pptx` or `Pan de Staku.pdf` in the `assets` folder.")
    else:
        primary_path = pptx_path or pdf_path
        file_info = primary_path.stat()
        file_size_mb = file_info.st_size / (1024 * 1024)
        modified_time = datetime.fromtimestamp(file_info.st_mtime).strftime("%B %d, %Y %I:%M %p")

        available_files = []
        if pptx_path:
            available_files.append("PPTX")
        if pdf_path:
            available_files.append("PDF")
        available_label = ", ".join(available_files) if available_files else "None"

        st.markdown(
            f"""
<div class="presentation-card">
  <div class="presentation-title">Pan de Staku Presentation Deck</div>
  <div class="presentation-meta"><b>Available Files:</b> {available_label}</div>
  <div class="presentation-meta"><b>Primary File:</b> {primary_path.name}</div>
  <div class="presentation-meta"><b>Primary File Size:</b> {file_size_mb:.2f} MB</div>
  <div class="presentation-meta"><b>Last Updated:</b> {modified_time}</div>
</div>
""",
            unsafe_allow_html=True,
        )

        pptx_bytes = load_binary_file(pptx_path) if pptx_path else None
        pdf_bytes = load_binary_file(pdf_path) if pdf_path else None

        download_col_1, download_col_2 = st.columns(2)
        with download_col_1:
            if pptx_path:
                st.download_button(
                    "Download PPTX",
                    data=pptx_bytes,
                    file_name=pptx_path.name,
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                )
        with download_col_2:
            if pdf_path:
                st.download_button(
                    "Download PDF",
                    data=pdf_bytes,
                    file_name=pdf_path.name,
                    mime="application/pdf",
                )

        outline = extract_presentation_outline(pptx_path) if pptx_path else []
        if outline:
            st.subheader("Slide Outline")
            st.markdown('<div class="presentation-outline">', unsafe_allow_html=True)
            st.caption(f"Detected slides: {len(outline)}")
            for line in outline:
                st.write(f"- {line}")
            st.markdown("</div>", unsafe_allow_html=True)
        elif pptx_path:
            st.caption("Slide outline not detected from the current PPTX file.")

        st.subheader("Presentation Viewer")
        if pdf_path and pdf_bytes:
            render_pdf_embed(pdf_bytes, height=780)
            st.caption(f"Displaying PDF preview from `{pdf_path}`.")
        else:
            st.warning("PDF preview is unavailable. Add `Pan de Staku.pdf` in `assets/` for in-app viewing.")

elif menu == "Register":
    st.header("Register")
    st.markdown(
        f"""
<div class="presentation-card">
  <div class="presentation-title">Welcome Bonus</div>
  <div class="presentation-meta">
    New customers receive <b>PHP {SIGNUP_BONUS}</b> in wallet credit right after signup.
  </div>
  <div class="presentation-meta">
    Your credit can be used automatically during checkout.
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
    new_user = st.text_input("Username")
    new_pass = st.text_input("Password", type="password")
    if st.button("Create Account"):
        ok, message = create_user(conn, new_user, new_pass)
        if ok:
            st.success(message)
        else:
            st.error(message)

elif menu == "Branch":
    st.header("Branch Selection")
    if st.session_state.branch not in BRANCHES:
        st.session_state.branch = BRANCHES[0]
    branch = st.selectbox("Select Branch", BRANCHES, index=BRANCHES.index(st.session_state.branch))
    st.session_state.branch = branch
    st.success(f"Branch set to {branch}.")
    branch_cards = []
    for name, details in BRANCH_DETAILS.items():
        selected_class = " selected" if name == branch else ""
        branch_cards.append(
            f"""
<div class="branch-card{selected_class}">
  <div class="branch-title">{name} Branch</div>
  <div class="branch-meta"><b>Address:</b> {details["address"]}</div>
  <div class="branch-meta"><b>Hours:</b> {details["hours"]}</div>
  <div class="branch-meta"><b>Best Pair:</b> {details["best_pair"]}</div>
</div>
"""
        )
    st.markdown(f'<div class="branch-grid">{"".join(branch_cards)}</div>', unsafe_allow_html=True)

elif menu == "Menu List":
    st.header("Menu List")
    st.markdown(
        """
<div class="menu-banner">
  <div class="menu-banner-title">Curated Menu, Freshly Updated</div>
  <div class="menu-banner-subtitle">
    Explore artisan breads, local favorites, coffee classics, and a refreshed drink bar.
    All prices are updated for quick ordering.
  </div>
  <div class="menu-banner-pill">Glow-Up Menu Board</div>
</div>
""",
        unsafe_allow_html=True,
    )

    render_menu_section(
        "Signature Bread Collection",
        "Buttery layers and artisan loaves baked daily.",
        bread_menu,
    )
    st.divider()
    render_menu_section(
        "Local Favorite Bakes",
        "Classic Filipino staples and sweet treats.",
        local_bakes_menu,
    )
    st.divider()
    render_menu_section(
        "Coffee Program",
        "Espresso-based drinks crafted to order.",
        coffee_menu,
    )
    st.divider()
    render_menu_section(
        "Drink Bar",
        "Cold refreshers and bottled favorites.",
        drinks_menu,
    )

elif menu == "Order":
    if not st.session_state.user:
        st.warning("Login first.")
    else:
        st.header("Order Builder")
        st.markdown(
            f"""
<div class="order-card">
  <div class="order-title">Build Your Order Faster</div>
  <div class="order-subtitle">
    Add multiple items in one go. Mix breads, local bakes, coffee, and drinks in the same order.
  </div>
  <div class="order-badges">
    <span class="order-badge">Multi-Item Add</span>
    <span class="order-badge">Food + Drink Combo</span>
    <span class="order-badge">Stock Aware</span>
    <span class="order-badge">Cart Items: {cart_count}</span>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

        food_menu = {**bread_menu, **local_bakes_menu}
        drink_menu = {**coffee_menu, **drinks_menu}

        left_col, right_col = st.columns([1.05, 1])

        with left_col:
            st.markdown('<div class="order-panel">', unsafe_allow_html=True)
            st.subheader("Quick Combo")
            st.caption("Add a food item and a drink in one click.")
            with st.form("combo_form", clear_on_submit=True):
                food_item = st.selectbox("Food item", list(food_menu.keys()), key="combo_food_item")
                food_qty = st.number_input(
                    "Food quantity",
                    min_value=1,
                    max_value=20,
                    value=1,
                    key="combo_food_qty",
                )
                st.caption(f"Food stock: {get_stock(conn, food_item)}")
                drink_item = st.selectbox("Drink item", list(drink_menu.keys()), key="combo_drink_item")
                drink_qty = st.number_input(
                    "Drink quantity",
                    min_value=1,
                    max_value=20,
                    value=1,
                    key="combo_drink_qty",
                )
                st.caption(f"Drink stock: {get_stock(conn, drink_item)}")
                combo_submit = st.form_submit_button("Add Combo to Cart")

            if combo_submit:
                added = []
                errors = []
                for item, qty in [(food_item, food_qty), (drink_item, drink_qty)]:
                    stock = get_stock(conn, item)
                    if qty > stock:
                        errors.append(f"{item} (requested {qty}, stock {stock})")
                    else:
                        add_to_cart(item, int(qty), all_menu[item])
                        added.append(f"{item} x{qty}")

                if errors:
                    st.error("Not enough stock for: " + "; ".join(errors))
                if added:
                    st.success("Added: " + ", ".join(added))

            st.markdown("</div>", unsafe_allow_html=True)

        with right_col:
            st.markdown('<div class="order-panel">', unsafe_allow_html=True)
            st.subheader("Multi-Item Order")
            st.caption("Add up to three items at once.")
            item_options = ["-- Select item --"] + list(all_menu.keys())

            with st.form("multi_item_form", clear_on_submit=True):
                selections = []
                for idx in range(1, 4):
                    row = st.columns([3, 1])
                    with row[0]:
                        item = st.selectbox(f"Item {idx}", item_options, key=f"multi_item_{idx}")
                    with row[1]:
                        qty = st.number_input(
                            "Qty",
                            min_value=1,
                            max_value=20,
                            value=1,
                            key=f"multi_qty_{idx}",
                        )
                    selections.append((item, qty))
                multi_submit = st.form_submit_button("Add Selected Items")

            if multi_submit:
                added = []
                errors = []
                for item, qty in selections:
                    if item == "-- Select item --":
                        continue
                    stock = get_stock(conn, item)
                    if qty > stock:
                        errors.append(f"{item} (requested {qty}, stock {stock})")
                    else:
                        add_to_cart(item, int(qty), all_menu[item])
                        added.append(f"{item} x{qty}")

                if errors:
                    st.error("Not enough stock for: " + "; ".join(errors))
                if added:
                    st.success("Added: " + ", ".join(added))
                if not added and not errors:
                    st.info("Select at least one item to add.")

            st.markdown("</div>", unsafe_allow_html=True)

elif menu == "Cart":
    if not st.session_state.cart:
        st.info("Cart is empty.")
    elif not st.session_state.user:
        st.warning("Login first.")
    else:
        total = 0.0
        profit_total = 0.0
        unavailable_items = []

        for entry in st.session_state.cart:
            item = entry["item"]
            qty = entry["qty"]
            price = entry["price"]
            stock = get_stock(conn, item)

            if qty > stock:
                unavailable_items.append(f"{item} (requested {qty}, stock {stock})")

            subtotal = qty * price
            total += subtotal

            row = conn.execute("SELECT cost FROM inventory WHERE item = ?", (item,)).fetchone()
            cost = float(row[0]) if row else 0.0
            profit_total += (price - cost) * qty

            st.write(f"{item} x{qty} = PHP {subtotal:.2f}")

        wallet_balance = get_wallet_balance(conn, st.session_state.user)
        use_wallet = False
        if wallet_balance > 0:
            use_wallet = st.checkbox(
                f"Apply wallet credit (PHP {wallet_balance:.2f})",
                value=True,
            )
        credit_applied = min(wallet_balance, total) if use_wallet else 0.0
        payable_total = max(total - credit_applied, 0.0)
        profit_after_credit = profit_total - credit_applied

        st.subheader(f"Order Total: PHP {total:.2f}")
        if credit_applied > 0:
            st.write(f"Wallet Credit Applied: -PHP {credit_applied:.2f}")
        st.subheader(f"Payable Total: PHP {payable_total:.2f}")

        if payable_total > 0:
            st.subheader("Payment Method")
            payment_method = st.selectbox("Choose Payment", ["GCash", "Maya", "Cash"])
            phone = st.text_input("Mobile Number (11 digits)")
            if payment_method == "Cash":
                otp = ""
                st.caption("Cash payment only requires your mobile number.")
            else:
                otp = st.text_input("OTP (6 digits)")
        else:
            payment_method = "Wallet Credit"
            phone = ""
            otp = ""
            st.success("Your wallet credit covers this order. No payment needed.")

        if unavailable_items:
            st.error("Insufficient stock: " + "; ".join(unavailable_items))

        if st.button("Confirm Payment"):
            if unavailable_items:
                st.error("Please adjust cart quantities before checkout.")
            elif payable_total > 0 and not validate_payment(phone, otp, payment_method):
                st.error("Invalid payment details.")
            else:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                payment_label = payment_method
                if credit_applied > 0 and payable_total > 0:
                    payment_label = f"Wallet + {payment_method}"
                conn.execute(
                    """
                    INSERT INTO orders (username, branch, total, profit, payment, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        st.session_state.user,
                        st.session_state.branch,
                        payable_total,
                        profit_after_credit,
                        payment_label,
                        timestamp,
                    ),
                )
                for entry in st.session_state.cart:
                    conn.execute(
                        "UPDATE inventory SET stock = stock - ? WHERE item = ?",
                        (entry["qty"], entry["item"]),
                    )
                if credit_applied > 0:
                    conn.execute(
                        "UPDATE wallets SET balance = MAX(balance - ?, 0) WHERE username = ?",
                        (credit_applied, st.session_state.user),
                    )
                conn.commit()
                st.session_state.cart.clear()
                if payment_label == "Wallet Credit":
                    st.success("Order confirmed using wallet credit.")
                else:
                    st.success(f"{payment_method} payment successful.")

elif menu == "DoughBot Chat":
    st.title("DoughBot Assistant")
    st.markdown(
        """
<div class="chat-panel">
  <div class="menu-title">How can we help today?</div>
  <div class="menu-subtitle">
    Ask about prices, stock availability, pairings, or quick recommendations.
  </div>
  <div class="chat-badges">
    <span class="chat-badge">Price Check</span>
    <span class="chat-badge">Stock Status</span>
    <span class="chat-badge">Best Pairings</span>
    <span class="chat-badge">Order Guidance</span>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    prompt = st.chat_input("Ask DoughBot something...")
    if prompt:
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
        response = doughbot_response(prompt, conn)
        with st.chat_message("assistant"):
            st.write(response)
        st.session_state.chat_messages.append({"role": "assistant", "content": response})

elif menu == "Admin Dashboard":
    st.header("Admin Monitoring Dashboard")
    if not st.session_state.user:
        st.warning("Login as admin to view this page.")
    elif st.session_state.role != "admin":
        st.error("Admin access required.")
    else:
        df_orders = pd.read_sql_query("SELECT * FROM orders", conn)
        df_inventory = pd.read_sql_query("SELECT * FROM inventory", conn)
        df_users = pd.read_sql_query("SELECT id, username, role FROM users", conn)

        total_sales = int(df_orders["total"].sum()) if not df_orders.empty else 0
        total_profit = int(df_orders["profit"].sum()) if not df_orders.empty else 0
        total_users = int(df_users.shape[0]) if not df_users.empty else 0

        metric_col1, metric_col2, metric_col3 = st.columns(3)
        metric_col1.metric("Total Sales (PHP)", total_sales)
        metric_col2.metric("Total Profit (PHP)", total_profit)
        metric_col3.metric("Total Users", total_users)

        st.subheader("Users")
        st.dataframe(df_users, width="stretch")

        st.subheader("Orders")
        st.dataframe(df_orders, width="stretch")

        st.subheader("Inventory")
        st.dataframe(df_inventory, width="stretch")
