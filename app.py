import hashlib
import random
import re
import sqlite3
from datetime import datetime

import pandas as pd
import streamlit as st

DB_PATH = "pan_de_staku.db"
ADMIN_USERNAME = "admin"
ADMIN_DEFAULT_PASSWORD = "admin123"
BRANCHES = ["Manila", "Cebu", "Davao"]

bread_menu = {
    "Croissant": 120,
    "Baguette": 100,
    "Brioche": 150,
    "Pain au Chocolat": 140,
    "Fougasse": 130,
    "Sourdough": 160,
    "Danish": 135,
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

all_menu = {**bread_menu, **coffee_menu}


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
    if db_hash == hash_password(password):
        return {"username": db_username, "role": db_role}
    return None


def create_user(conn: sqlite3.Connection, username: str, password: str) -> tuple[bool, str]:
    if not re.fullmatch(r"[A-Za-z0-9_]{3,20}", username):
        return False, "Username must be 3-20 chars and contain only letters, numbers, or underscore."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."

    try:
        conn.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            (username.strip(), hash_password(password), "customer"),
        )
        conn.commit()
        return True, "Account created successfully."
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


def get_stock(conn: sqlite3.Connection, item: str) -> int:
    row = conn.execute("SELECT stock FROM inventory WHERE item = ?", (item,)).fetchone()
    return int(row[0]) if row else 0


def add_to_cart(item: str, qty: int, price: float) -> None:
    for entry in st.session_state.cart:
        if entry["item"] == item:
            entry["qty"] += qty
            return
    st.session_state.cart.append({"item": item, "qty": qty, "price": price})


def validate_payment(phone: str, otp: str) -> bool:
    return bool(re.fullmatch(r"\d{11}", phone) and re.fullmatch(r"\d{6}", otp))


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
    }
    pairings = {
        "Croissant": "Latte",
        "Baguette": "Americano",
        "Brioche": "Cappuccino",
        "Pain au Chocolat": "Mocha",
        "Fougasse": "Espresso",
        "Sourdough": "Flat White",
        "Danish": "Macchiato",
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

    if "who" in words and "you" in words:
        return signed_reply(
            "about",
            "I am DoughBot, your Pan de Staku assistant for menu guidance, smart recommendations, and checkout support.",
        )

    if matches(menu_words):
        bread_list = ", ".join([f"{item} (PHP {price})" for item, price in bread_menu.items()])
        coffee_list = ", ".join([f"{item} (PHP {price})" for item, price in coffee_menu.items()])
        return signed_reply("menu", f"Bread:\n{bread_list}\n\nCoffee:\n{coffee_list}")

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
        return signed_reply("branch", f"Branches: Manila, Cebu, Davao. Your current selected branch is {current_branch}.")

    if matches(payment_words):
        return signed_reply(
            "payment",
            "We accept GCash and Maya. Provide an 11-digit mobile number and 6-digit OTP to confirm payment.",
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

st.markdown(
    f"""
<style>
@keyframes fadeIn {{
    from {{ opacity: 0; transform: translateY(20px); }}
    to {{ opacity: 1; transform: translateY(0); }}
}}

.stApp {{
    animation: fadeIn 0.8s ease-in-out;
    background: {app_background};
    color: {text_color};
}}

section[data-testid="stSidebar"] {{
    background: {sidebar_background};
    border-right: none;
    box-shadow: 8px 0 24px rgba(0, 0, 0, 0.18);
}}

section[data-testid="stSidebar"] * {{
    color: {nav_text_color} !important;
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
    background: rgba(255, 244, 231, 0.24);
    border-left-color: rgba(255, 244, 231, 0.7);
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
    border: none;
    border-radius: 18px;
    padding: 1.4rem 1.2rem;
    backdrop-filter: blur(2px);
}}

h1, h2, h3, .stTitle {{
    color: {title_color};
}}

p {{
    color: {text_color};
}}
</style>
""",
    unsafe_allow_html=True,
)

cart_count = sum(entry["qty"] for entry in st.session_state.cart)
current_user = st.session_state.user or "Guest"
st.sidebar.caption(f"User: {current_user} | Branch: {st.session_state.branch}")

menu = st.sidebar.radio(
    f"Navigation Cart({cart_count})",
    [
        "Home",
        "Login",
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
    ],
)

if menu == "Home":
    st.title("Pan de Staku")
    st.subheader("Enterprise French Bakery and Coffee Management System")

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

elif menu == "Product":
    st.header("Products")
    st.write(
        "Our product line is designed for customers who want high-quality baked goods and coffee with predictable taste, "
        "freshness, and value."
    )

    st.subheader("Signature Bread Collection")
    for item, price in bread_menu.items():
        st.write(f"- {item}: PHP {price}")

    st.subheader("Coffee Program")
    for item, price in coffee_menu.items():
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
        """
- In-store and branch-based ordering for walk-in and local fulfillment.
- Digital cart and checkout flow for fast order placement.
- GCash and Maya payment support with verification flow.
- Multi-branch coverage in Manila, Cebu, and Davao.
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
        """
**Head Office Email:** support@pandestaku.com  
**Customer Hotline:** +63 917 555 0123  
**Business Hours:** Monday to Sunday, 7:00 AM - 9:00 PM  
**Main Branches:** Manila, Cebu, Davao
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
            st.success("Login successful.")
        else:
            st.error("Invalid credentials.")

elif menu == "Register":
    st.header("Register")
    new_user = st.text_input("Username")
    new_pass = st.text_input("Password", type="password")
    if st.button("Create Account"):
        ok, message = create_user(conn, new_user, new_pass)
        if ok:
            st.success(message)
        else:
            st.error(message)

elif menu == "Branch":
    branch = st.selectbox("Select Branch", BRANCHES, index=BRANCHES.index(st.session_state.branch))
    st.session_state.branch = branch
    st.success(f"Branch set to {branch}.")

elif menu == "Menu List":
    st.header("Full Menu")
    df = pd.DataFrame(list(all_menu.items()), columns=["Item", "Price"])
    st.dataframe(df, use_container_width=True)

elif menu == "Order":
    if not st.session_state.user:
        st.warning("Login first.")
    else:
        st.header("Add to Cart")
        item = st.selectbox("Item", list(all_menu.keys()))
        available_stock = get_stock(conn, item)
        st.caption(f"Available stock: {available_stock}")
        qty = st.number_input("Quantity", min_value=1, max_value=20, value=1)
        if st.button("Add to Cart"):
            if qty > available_stock:
                st.error("Not enough stock for this item.")
            else:
                add_to_cart(item, int(qty), all_menu[item])
                st.success("Added to cart.")

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

        st.subheader(f"Total: PHP {total:.2f}")
        st.subheader("Payment Method")
        payment_method = st.selectbox("Choose Payment", ["GCash", "Maya"])
        phone = st.text_input("Mobile Number (11 digits)")
        otp = st.text_input("OTP (6 digits)")

        if unavailable_items:
            st.error("Insufficient stock: " + "; ".join(unavailable_items))

        if st.button("Confirm Payment"):
            if unavailable_items:
                st.error("Please adjust cart quantities before checkout.")
            elif not validate_payment(phone, otp):
                st.error("Invalid payment details.")
            else:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                conn.execute(
                    """
                    INSERT INTO orders (username, branch, total, profit, payment, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        st.session_state.user,
                        st.session_state.branch,
                        total,
                        profit_total,
                        payment_method,
                        timestamp,
                    ),
                )
                for entry in st.session_state.cart:
                    conn.execute(
                        "UPDATE inventory SET stock = stock - ? WHERE item = ?",
                        (entry["qty"], entry["item"]),
                    )
                conn.commit()
                st.session_state.cart.clear()
                st.success(f"{payment_method} payment successful.")

elif menu == "DoughBot Chat":
    st.title("DoughBot Assistant")
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
    st.header("Admin Panel")
    if not st.session_state.user:
        st.warning("Login as admin to view this page.")
    elif st.session_state.role != "admin":
        st.error("Admin access required.")
    else:
        df_orders = pd.read_sql_query("SELECT * FROM orders", conn)
        df_inventory = pd.read_sql_query("SELECT * FROM inventory", conn)

        total_sales = int(df_orders["total"].sum()) if not df_orders.empty else 0
        total_profit = int(df_orders["profit"].sum()) if not df_orders.empty else 0

        st.subheader("Total Sales")
        st.metric("PHP", total_sales)

        st.subheader("Total Profit")
        st.metric("PHP", total_profit)

        st.subheader("Orders")
        st.dataframe(df_orders, use_container_width=True)

        st.subheader("Inventory")
        st.dataframe(df_inventory, use_container_width=True)



