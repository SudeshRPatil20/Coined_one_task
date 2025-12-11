import streamlit as st
import requests

API_CHAT = "https://coined-one-task.onrender.com/chat"
API_CALC = "https://coined-one-task.onrender.com/calculate"


st.set_page_config(page_title="AI Mortgage Assistant", page_icon="🏠", layout="wide")

st.title("🏠 AI Mortgage Smart Advisor (UAE)")
st.markdown(
    """
    Chat with an AI-powered UAE mortgage advisor or instantly calculate **Buy vs Rent**.
    """
)


st.subheader("💬 Chat with Mortgage Assistant")

chat_container = st.container()

if "messages" not in st.session_state:
    st.session_state.messages = []

with chat_container:
    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).write(msg["content"])

user_input = st.chat_input("Ask anything about mortgage, EMI, LTV, or buy vs rent...")

if user_input:
    # Add user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)

    # API call
    try:
        res = requests.post(API_CHAT, json={"messages": st.session_state.messages})
        reply = res.json().get("reply", "No reply received.")
    except Exception as e:
        reply = f"⚠️ Server error: {e}"

    # Show assistant message
    st.session_state.messages.append({"role": "assistant", "content": reply})
    st.chat_message("assistant").write(reply)


st.divider()
st.subheader("📊 Quick Buy vs Rent Calculator")

with st.form("calculator"):
    col1, col2 = st.columns(2)

    with col1:
        price = st.number_input("🏢 Property Price (AED)", value=1500000)
        dp = st.number_input("💰 Down Payment (AED)", value=300000)
        tenure = st.slider("📅 Mortgage Tenure (years)", 1, 25, 25)

    with col2:
        stay = st.slider("⏳ Years You Plan To Stay", 1, 20, 5)
        rent = st.number_input("🏠 Monthly Rent (AED)", value=7000)
        income = st.number_input("💵 Monthly Income (AED)", value=20000)

    submitted = st.form_submit_button("Calculate 📈")

if submitted:
    payload = {
        "property_price": price,
        "down_payment": dp,
        "tenure_years": tenure,
        "years_planned": stay,
        "monthly_rent": rent,
        "monthly_income": income
    }

    try:
        result = requests.post(API_CALC, json=payload).json()

        st.success("Here is your calculation:")
        st.json(result)

        st.success(f"🏁 Final Recommendation: **{result['recommendation'].upper()}**")

    except Exception as e:
        st.error(f"Error contacting backend: {e}")
