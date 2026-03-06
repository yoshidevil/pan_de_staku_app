import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Pan de Staku AI",
    page_icon="🥐",
    layout="wide"
)

# -----------------------------
# CHATBOT NAME
# -----------------------------
CHATBOT_NAME = "DoughBot"

# -----------------------------
# MENU DATA
# -----------------------------
menu_items = {
    "🥐 Croissant":120,
    "🍞 Baguette":100,
    "🥖 Brioche":150,
    "🥯 Pain au Chocolat":140,
    "☕ Espresso":90,
    "☕ Latte":130,
    "☕ Cappuccino":120
}

# -----------------------------
# SESSION STATE
# -----------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

# -----------------------------
# PAGE HEADER
# -----------------------------
st.title("🥐 Pan de Staku Smart Bakery")
st.subheader("AI Powered Ordering Assistant")

st.markdown(
"""
Welcome to **Pan de Staku**.

Chat with **DoughBot** to:
- Discover breads
- Get coffee recommendations
- Place orders
"""
)

# -----------------------------
# LAYOUT
# -----------------------------
col1, col2 = st.columns([1,1])

# -----------------------------
# MENU SECTION
# -----------------------------
with col1:
    st.header("📋 Menu")

    df = pd.DataFrame(
        menu_items.items(),
        columns=["Item","Price"]
    )

    df["Price"] = df["Price"].apply(lambda x: f"₱{x}")
    st.dataframe(df)

# -----------------------------
# CHATBOT UI
# -----------------------------
with col2:
    st.header(f"🤖 Chat with {CHATBOT_NAME}")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    prompt = st.chat_input("Ask DoughBot something...")

    if prompt:

        st.session_state.messages.append(
            {"role":"user","content":prompt}
        )

        with st.chat_message("user"):
            st.write(prompt)

        # Simple AI logic (draft version)
        response = ""

        if "recommend" in prompt.lower():
            response = "I recommend our buttery Croissant with a Latte ☕"

        elif "menu" in prompt.lower():
            response = "You can check our menu on the left side!"

        elif "coffee" in prompt.lower():
            response = "Our Cappuccino pairs perfectly with Brioche."

        elif "delivery" in prompt.lower():
            response = "We offer delivery within the city for ₱40."

        else:
            response = "I'm DoughBot! Ask me about our breads, coffee, or delivery."

        with st.chat_message("assistant"):
            st.write(response)

        st.session_state.messages.append(
            {"role":"assistant","content":response}
        )