import os
import streamlit as st
import pandas as pd
import time
import random
import re

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - optional dependency
    OpenAI = None

st.set_page_config(
    page_title="Pan de Staku AI",
    page_icon="🥐",
    layout="wide"
)

# ------------------------------------------------
# PREMIUM CAFE STYLE UI
# ------------------------------------------------
st.markdown("""
<style>

.stApp{
background:
radial-gradient(circle at 20% 20%, rgba(255,224,178,0.35), transparent 40%),
linear-gradient(135deg,#3E2723,#6D4C41,#D7A86E);
background-attachment:fixed;
}

h1,h2,h3,p{
color:white;
}

.chat-card{
background: rgba(255,255,255,0.12);
padding:18px;
border-radius:15px;
backdrop-filter: blur(8px);
box-shadow:0 5px 25px rgba(0,0,0,0.3);
}

.menu-card{
background: rgba(255,255,255,0.18);
padding:20px;
border-radius:15px;
}

.stChatMessage{
border-radius:12px;
}

</style>
""", unsafe_allow_html=True)

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:wght@600;700&family=Space+Grotesk:wght@400;500;600&display=swap');

:root {
  --bg-dark: #2a1a14;
  --bg-mid: #6a4a3c;
  --bg-light: #d7b07d;
  --cream: #f6efe6;
  --accent: #f2c97d;
  --card: rgba(255, 248, 236, 0.10);
  --card-strong: rgba(255, 248, 236, 0.16);
  --border: rgba(255, 248, 236, 0.18);
  --shadow: 0 10px 28px rgba(0, 0, 0, 0.28);
}

.stApp {
  color: var(--cream);
  font-family: "Space Grotesk", sans-serif;
}

h1, h2, h3, p, li {
  color: var(--cream);
}

h1, h2, h3 {
  font-family: "Fraunces", serif;
  letter-spacing: 0.5px;
}

@keyframes riseIn {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}

.chat-card, .menu-card, .recipe-card {
  background: var(--card);
  border: 1px solid var(--border);
  padding: 18px;
  border-radius: 16px;
  box-shadow: var(--shadow);
  backdrop-filter: blur(8px);
  animation: riseIn 0.5s ease;
}

.menu-card {
  background: var(--card-strong);
}

.stChatMessage {
  border-radius: 14px;
}
</style>
""",
    unsafe_allow_html=True,
)

# ------------------------------------------------
# CHATBOT NAME
# ------------------------------------------------
CHATBOT_NAME = "DoughBot"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"
BRANCHES = ["Manila", "Cebu", "Davao", "Iloilo", "General Santos", "Baguio"]
BRANCH_LIST_TEXT = ", ".join(BRANCHES)
SIGNUP_BONUS = 300
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
OPENAI_MAX_HISTORY = int(os.getenv("OPENAI_MAX_HISTORY", "12"))
OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))

# ------------------------------------------------
# MENU DATA
# ------------------------------------------------
menu_items = {
    "🥐 Croissant":120,
    "🍞 Baguette":100,
    "🥖 Brioche":150,
    "🥯 Pain au Chocolat":140,
    "☕ Espresso":90,
    "☕ Latte":130,
    "☕ Cappuccino":120
}

menu_items.update({
    "Fougasse": 130,
    "Sourdough": 160,
    "Danish": 135,
    "Americano": 100,
    "Mocha": 140,
    "Macchiato": 115,
    "Flat White": 125,
})

# ------------------------------------------------
# SESSION STATE
# ------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "conversation_context" not in st.session_state:
    st.session_state.conversation_context = {}

if "last_response" not in st.session_state:
    st.session_state.last_response = None

if "pending_recipe_prompt" not in st.session_state:
    st.session_state.pending_recipe_prompt = None

if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

# ------------------------------------------------
# OPENAI HELPERS
# ------------------------------------------------
def _get_openai_api_key() -> str | None:
    key = os.getenv("OPENAI_API_KEY")
    if key:
        return key
    try:
        return st.secrets.get("OPENAI_API_KEY")
    except Exception:
        return None


@st.cache_resource(show_spinner=False)
def _get_openai_client():
    if OpenAI is None:
        return None
    api_key = _get_openai_api_key()
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


def _build_system_prompt() -> str:
    menu_lines = "\n".join([f"- {item}: PHP {price}" for item, price in menu_items.items()])
    return (
        "You are DoughBot, a friendly bakery assistant for Pan de Staku. "
        "Be warm, concise, and helpful. Use only the menu and prices provided below. "
        "If a user asks for an item not listed, say you do not see it and suggest a close alternative. "
        "You can recommend pairings and simple recipes when asked.\n"
        f"Signup bonus: new customers get PHP {SIGNUP_BONUS} wallet credit after registering.\n\n"
        f"Branches: {BRANCH_LIST_TEXT}\n"
        "Payment methods: GCash, Maya, Cash. GCash/Maya require mobile number + OTP. Cash requires mobile number only.\n"
        "Menu and prices:\n"
        f"{menu_lines}"
    )


def _build_openai_messages() -> list[dict[str, str]]:
    messages: list[dict[str, str]] = [{"role": "system", "content": _build_system_prompt()}]
    history = st.session_state.messages[-OPENAI_MAX_HISTORY:]
    for msg in history:
        role = msg.get("role")
        content = msg.get("content")
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": str(content)})
    return messages


def _extract_output_text(response) -> str | None:
    try:
        output = getattr(response, "output", None) or []
        for item in output:
            for content in getattr(item, "content", []) or []:
                if getattr(content, "type", "") == "output_text":
                    return getattr(content, "text", None)
    except Exception:
        return None
    return None


def _openai_reply() -> str | None:
    client = _get_openai_client()
    if not client:
        return None
    try:
        response = client.responses.create(
            model=OPENAI_MODEL,
            input=_build_openai_messages(),
            temperature=OPENAI_TEMPERATURE,
        )
        text = getattr(response, "output_text", None) or _extract_output_text(response)
        return text.strip() if text else None
    except Exception:
        return None

# ------------------------------------------------
# HEADER
# ------------------------------------------------
with st.sidebar:
    st.subheader("Admin Login")
    if st.session_state.admin_logged_in:
        st.success("Logged in as admin.")
        if st.button("Logout Admin"):
            st.session_state.admin_logged_in = False
    else:
        admin_user = st.text_input("Admin Username", key="admin_user")
        admin_pass = st.text_input("Admin Password", type="password", key="admin_pass")
        if st.button("Login as Admin"):
            if admin_user == ADMIN_USERNAME and admin_pass == ADMIN_PASSWORD:
                st.session_state.admin_logged_in = True
                st.success("Admin login successful.")
            else:
                st.error("Invalid admin credentials.")

    if st.session_state.admin_logged_in:
        st.markdown("### Admin Panel")
        st.caption("Quick monitoring snapshot")
        st.metric("Chat Messages", len(st.session_state.messages))
        if st.button("Clear Chat History"):
            st.session_state.messages = []
            st.success("Chat history cleared.")

    st.divider()
    st.subheader("OpenAI Status")
    if _get_openai_client():
        st.success("OpenAI connected")
        st.caption(f"Model: {OPENAI_MODEL}")
    elif OpenAI is None:
        st.warning("OpenAI SDK not installed")
        st.caption("Install with: pip install openai")
    else:
        st.warning("OpenAI API key not set")
        st.caption("Set OPENAI_API_KEY or add it to Streamlit secrets.")

st.markdown("Tip: Try asking `Give me a recipe for chicken, garlic, onion`.")
st.title("🥐 Pan de Staku Smart Bakery")
st.subheader("AI Powered Bakery Assistant")

st.markdown("""
Welcome to **Pan de Staku**.

Chat with **DoughBot 🤖** to:

• Discover artisan breads  
• Get coffee pairings  
• Ask bakery questions  
• Get menu recommendations  
""")

# ------------------------------------------------
# LAYOUT
# ------------------------------------------------
col1, col2 = st.columns([1,1.2])

# ------------------------------------------------
# MENU DISPLAY
# ------------------------------------------------
with col1:

    st.markdown('<div class="menu-card">', unsafe_allow_html=True)
    st.markdown("### 📋 Bakery Menu")

    df = pd.DataFrame(menu_items.items(), columns=["Item","Price"])
    df["Price"] = df["Price"].apply(lambda x: f"₱{x}")

    df["Price"] = df["Price"].apply(lambda x: f"PHP {x}")
    st.dataframe(df, width="stretch")

    st.markdown("### ⭐ Popular Combo")

    st.info("""
🥐 Croissant + ☕ Latte  
Perfect buttery breakfast combo.
""")

    st.markdown("### Recipe Helper")
    ingredients_input = st.text_input("Ingredients or dish name", key="ingredients_input")
    if st.button("Generate Recipe"):
        if ingredients_input.strip():
            st.session_state.pending_recipe_prompt = f"Give me a recipe for {ingredients_input.strip()}."

    st.markdown("</div>", unsafe_allow_html=True)

# ------------------------------------------------
# DOUGHBOT AI ENGINE
# ------------------------------------------------
def doughbot_ai(prompt):

    text = prompt.lower()

    greetings = ["hello","hi","hey","good morning","good evening"]
    thanks = ["thanks","thank you"]
    recommend = ["recommend","suggest","best"]
    coffee = ["coffee","espresso","latte","cappuccino"]
    bread = ["bread","croissant","baguette","brioche"]
    delivery = ["delivery","deliver"]
    price = ["price","cost","how much"]

    # Greeting
    if any(x in text for x in greetings):
        return random.choice([
            "Bonjour! I'm **DoughBot**, your bakery assistant 🥐",
            "Hello! Welcome to **Pan de Staku**. What would you like today?",
            "Hi there! Looking for fresh bread or coffee?"
        ])

    # Recommendation
    if any(x in text for x in recommend):
        return """
I recommend this combo:

🥐 **Croissant**  
☕ **Latte**

It’s our **most loved breakfast pair**.
"""

    # Coffee
    if any(x in text for x in coffee):
        return """
Our coffee selection includes:

☕ Espresso  
☕ Latte  
☕ Cappuccino

Best pairing: **Brioche + Cappuccino**
"""

    # Bread
    if any(x in text for x in bread):
        return """
Our artisan breads:

🥐 Croissant  
🍞 Baguette  
🥖 Brioche  
🥯 Pain au Chocolat
"""

    # Price
    if any(x in text for x in price):
        return "Our items range between **₱90 and ₱150**."

    # Delivery
    if any(x in text for x in delivery):
        return "Yes! We deliver within the city for **₱40 delivery fee 🚚**."

    # Thanks
    if any(x in text for x in thanks):
        return "You're welcome! Enjoy Pan de Staku 🥐"

    # Menu direct question
    if "menu" in text:
        items = ", ".join(menu_items.keys())
        return f"Our menu includes: {items}"

    # fallback
    return """
I'm **DoughBot 🤖**

Try asking me things like:

• "Recommend a breakfast combo"
• "What breads do you have?"
• "Do you offer delivery?"
• "What coffee goes with croissant?"
"""

def _primary_doughbot_ai(prompt):
    text = prompt.lower().strip()

    greetings = ["hello", "hi", "hey", "good morning", "good evening", "good afternoon"]
    thanks = ["thanks", "thank you", "appreciate", "ty"]
    recommend = ["recommend", "suggest", "best", "favorite", "fave"]
    coffee = ["coffee", "espresso", "latte", "cappuccino", "americano", "mocha", "macchiato", "flat white"]
    bread = ["bread", "croissant", "baguette", "brioche", "sourdough", "danish", "fougasse"]
    delivery = ["delivery", "deliver", "shipping"]
    branch = ["branch", "branches", "location", "store", "stores", "where are you", "where located"]
    price = ["price", "cost", "how much", "rates"]
    signup = ["signup", "sign up", "register", "registration", "welcome bonus", "signup bonus", "free 300", "p300"]
    payment = ["payment", "gcash", "maya", "otp", "cash"]

    combos = [
        ("Croissant", "Latte"),
        ("Brioche", "Cappuccino"),
        ("Pain au Chocolat", "Mocha"),
        ("Sourdough", "Flat White"),
    ]
    combo = random.choice(combos)
    menu_list = ", ".join(menu_items.keys())
    price_min = min(menu_items.values())
    price_max = max(menu_items.values())

    if any(x in text for x in greetings):
        return [
            "Hello! I'm DoughBot. Want bread, coffee, or a combo today?",
            "Hi there. I can recommend items or answer menu questions.",
            "Welcome to Pan de Staku. What are you in the mood for?",
        ]

    if any(x in text for x in recommend):
        return [
            f"My pick: {combo[0]} with {combo[1]}. Balanced and popular.",
            f"Try {combo[0]} + {combo[1]}. Great for mornings.",
            "If you want something rich, go Brioche with Cappuccino.",
            "For a lighter start, Croissant with Latte is a solid choice.",
        ]

    if any(x in text for x in coffee):
        return [
            "Coffee options: Espresso, Americano, Cappuccino, Latte, Mocha, Macchiato, Flat White.",
            "Want something strong? Espresso or Americano. Prefer smooth? Latte or Flat White.",
            "Cappuccino pairs nicely with Brioche. Mocha pairs well with Pain au Chocolat.",
        ]

    if any(x in text for x in bread):
        return [
            "Breads: Croissant, Baguette, Brioche, Pain au Chocolat, Fougasse, Sourdough, Danish.",
            "Looking for a classic? Croissant and Baguette are favorites.",
            "If you want something hearty, Sourdough is a great pick.",
        ]

    if any(x in text for x in price):
        return [
            f"Our items range between PHP {price_min} and PHP {price_max}.",
            "Tell me the item and I can give the exact price.",
        ]

    if any(x in text for x in delivery):
        return [
            "Yes, delivery is available. Fees depend on distance.",
            "We can deliver locally. Share your area and I will estimate.",
        ]

    if any(x in text for x in branch):
        return [
            f"Our branches are in {BRANCH_LIST_TEXT}.",
            f"You can visit us in {BRANCH_LIST_TEXT}.",
        ]

    if any(x in text for x in thanks):
        return [
            "You're welcome. Want another suggestion?",
            "Happy to help. Ask me anytime.",
            "Anytime. I can recommend a combo if you want.",
        ]

    if any(x in text for x in signup):
        return [
            f"New customers get PHP {SIGNUP_BONUS} wallet credit after registering.",
            f"Signup bonus: PHP {SIGNUP_BONUS} credit added to your wallet right after registration.",
            "Register an account and the bonus applies automatically at checkout.",
        ]

    if any(x in text for x in payment):
        return [
            "Payment options: GCash, Maya, and Cash.",
            "GCash/Maya need your mobile number and OTP. Cash only needs your mobile number.",
        ]

    if "menu" in text:
        return [
            f"Our menu includes: {menu_list}.",
            "We serve artisan breads and coffee. Ask about any item.",
        ]

    return [
        "Tell me what you are craving and I will suggest a combo.",
        "Ask about menu items, prices, or pairings, and I will help.",
        "If you want a recipe, say: Give me a recipe for chicken, garlic, onion.",
    ]


def _parse_ingredients(text: str) -> list[str]:
    parts = re.split(r"[,\n;]+", text)
    return [p.strip() for p in parts if p.strip()]


def _generate_recipe(query: str) -> str:
    ingredients = _parse_ingredients(query)
    if not ingredients:
        return "Tell me the ingredients or dish name and I will build a recipe."
    style_titles = ["Skillet", "Saute", "One-Pan", "Quick Bowl"]
    flavor_tips = [
        "Add a squeeze of citrus for brightness.",
        "Finish with fresh herbs if you have them.",
        "A splash of broth makes it richer.",
        "A little butter at the end makes it silky.",
    ]
    if len(ingredients) == 1:
        dish = ingredients[0].title()
        tip = random.choice(flavor_tips)
        steps = [
            "Prep and season the main ingredient.",
            "Warm oil in a pan over medium heat.",
            "Cook until browned, then reduce heat and finish gently.",
            "Taste and adjust seasoning.",
            "Serve hot with a simple side.",
        ]
        step_lines = "\n".join([f"{idx}. {step}" for idx, step in enumerate(steps, start=1)])
        return f"""Recipe idea: {dish}

Ingredients:
- {dish}
- salt
- pepper
- oil

Steps:
{step_lines}

Tip: {tip}"""

    title = ingredients[0].title()
    pantry = ["salt", "pepper", "oil"]
    ingredient_lines = "\n".join([f"- {item}" for item in ingredients + pantry])
    steps = [
        "Prep and chop all ingredients.",
        "Warm oil in a pan and cook aromatics first.",
        "Add the main ingredients and cook until tender.",
        "Season, stir, and let flavors combine for a few minutes.",
        "Taste, adjust, and serve hot.",
    ]
    if random.choice([True, False]):
        steps = [
            "Prep and portion ingredients.",
            "Sear the main ingredients for color.",
            "Add the rest and cook until fragrant.",
            "Lower heat and let flavors meld.",
            "Finish and serve.",
        ]
    step_lines = "\n".join([f"{idx}. {step}" for idx, step in enumerate(steps, start=1)])
    style = random.choice(style_titles)
    tip = random.choice(flavor_tips)
    return f"""Recipe: Simple {title} {style}

Ingredients:
{ingredient_lines}

Steps:
{step_lines}

Tip: {tip}"""


def _avoid_repeat(response) -> str:
    last = st.session_state.get("last_response")
    if isinstance(response, list):
        choices = response[:]
        if last in choices and len(choices) > 1:
            choices = [item for item in choices if item != last]
        response = random.choice(choices)
    if last and response == last:
        followups = [
            "Want a faster version or a baked version instead?",
            "Tell me your dietary preference and I will adapt it.",
            "If you want a different flavor, give me 2 to 3 ingredients.",
        ]
        response = response + "\n\n" + random.choice(followups)
    st.session_state.last_response = response
    return response


def _recipe_query(text: str) -> str | None:
    match = re.search(r"recipe\s+(?:for|with)\s+(.+)", text)
    if match:
        return match.group(1).strip(" .")
    if "ingredients:" in text:
        return text.split("ingredients:", 1)[1].strip()
    if "recipe" in text:
        cleaned = text.replace("recipe", "").strip(" .")
        return cleaned if cleaned else None
    return None


_base_doughbot_ai = _primary_doughbot_ai


def doughbot_ai(prompt):
    text = prompt.lower().strip()
    recipe_query = _recipe_query(text)
    if recipe_query:
        return _avoid_repeat(_generate_recipe(recipe_query))
    if "recipe" in text and not recipe_query:
        return _avoid_repeat(
            [
                "Tell me the ingredients or dish name and I will build a recipe.",
                "Share ingredients or a dish name and I will create a recipe.",
                "Give me ingredients and I will make a quick recipe.",
            ]
        )
    if "menu" in text or "list" in text:
        items = ", ".join(menu_items.keys())
        return _avoid_repeat(
            [
                f"Our menu includes: {items}.",
                "We serve artisan breads and coffee. Ask about any item.",
            ]
        )
    response = _base_doughbot_ai(prompt)
    return _avoid_repeat(response)


def generate_response(prompt: str) -> str:
    openai_text = _openai_reply()
    if openai_text:
        return openai_text
    return doughbot_ai(prompt)


if st.session_state.pending_recipe_prompt:
    prompt_text = st.session_state.pending_recipe_prompt
    st.session_state.pending_recipe_prompt = None
    st.session_state.messages.append({"role": "user", "content": prompt_text})
    recipe_response = generate_response(prompt_text)
    st.session_state.messages.append({"role": "assistant", "content": recipe_response})

# ------------------------------------------------
# CHAT UI
# ------------------------------------------------
with col2:

    st.markdown('<div class="chat-card">', unsafe_allow_html=True)
    st.markdown(f"### 🤖 Chat with {CHATBOT_NAME}")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    user_prompt = st.chat_input("Ask DoughBot something...")

    if user_prompt:

        st.session_state.messages.append({
            "role":"user",
            "content":user_prompt
        })

        with st.chat_message("user"):
            st.write(user_prompt)

        with st.chat_message("assistant"):

            with st.spinner("DoughBot is thinking..."):
                time.sleep(1)

                response = generate_response(user_prompt)

                st.write(response)

        st.session_state.messages.append({
            "role":"assistant",
            "content":response
        })

    st.markdown("</div>", unsafe_allow_html=True)
