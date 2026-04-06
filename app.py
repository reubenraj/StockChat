import streamlit as st
import yfinance as yf
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage


def get_llm():
    return ChatGroq(
        api_key=st.secrets["GROQ_API_KEY"],
        model="llama-3.3-70b-versatile",
        temperature=0.7
    )


def extract_ticker(user_message: str) -> str | None:
    extraction_prompt = f"""
You are a financial assistant. Your only job right now is to extract a stock ticker symbol from the user's message.

Rules:
- If the message mentions a company or stock, return ONLY the ticker symbol in uppercase. Nothing else.
- If no stock or company is mentioned, return ONLY the word: NONE
- Do not explain. Do not add punctuation. Just the ticker or NONE.

Examples:
User: How is Apple doing today?       → AAPL
User: What is the price of Tesla?     → TSLA
User: Tell me about Microsoft stock   → MSFT
User: What is 2 + 2?                  → NONE
User: How are you?                    → NONE

User message: {user_message}
""".strip()

    llm = get_llm()
    try:
        response = llm.invoke([HumanMessage(content=extraction_prompt)])
        result = response.content.strip().upper()
        if result == "NONE" or not result.isalpha() or len(result) > 6:
            return None
        return result
    except Exception as e:
        st.error(f"Error extracting ticker: {e}")
        return None


def get_stock_data(ticker: str) -> str:
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        name        = info.get("longName", ticker)
        price       = info.get("currentPrice") or info.get("regularMarketPrice")
        change_pct  = info.get("regularMarketChangePercent")
        week52_high = info.get("fiftyTwoWeekHigh")
        week52_low  = info.get("fiftyTwoWeekLow")
        market_cap  = info.get("marketCap")
        volume      = info.get("regularMarketVolume")

        if market_cap:
            if market_cap >= 1_000_000_000_000:
                market_cap_str = f"${market_cap / 1_000_000_000_000:.2f}T"
            elif market_cap >= 1_000_000_000:
                market_cap_str = f"${market_cap / 1_000_000_000:.2f}B"
            else:
                market_cap_str = f"${market_cap / 1_000_000:.2f}M"
        else:
            market_cap_str = "N/A"

        # ✅ Fixed: return is now OUTSIDE the if/else, always executes
        return f"""
📊 **{name} ({ticker.upper()})**
- 💵 Current price:   ${price:.2f}
- 📈 Change today:    {change_pct:.2f}%
- 🔺 52-week high:    ${week52_high:.2f}
- 🔻 52-week low:     ${week52_low:.2f}
- 🏦 Market cap:      {market_cap_str}
- 📦 Volume:          {volume:,}
""".strip()

    except Exception as e:
        return f"⚠️ Could not fetch data for **{ticker}**: {str(e)}"


def get_ai_response(user_message: str) -> str:
    # ✅ Fixed: llm is now properly created inside the function
    llm = get_llm()

    ticker = extract_ticker(user_message)

    # ✅ Fixed: variable name was stock_content before, now consistently stock_context
    stock_context = ""
    if ticker:
        stock_data = get_stock_data(ticker)
        stock_context = f"""
Here is the latest real-time stock data for {ticker}:
{stock_data}

Use this data to answer the user's question accurately.
"""

    system_prompt = f"""You are a friendly and knowledgeable stock market assistant.
You help users understand stocks, market trends, and financial data in plain English.
You remember the full conversation history and refer back to it naturally when relevant.
If you don't know something or data is unavailable, say so honestly.
{stock_context}"""

    messages = [SystemMessage(content=system_prompt)]

    # ✅ Fixed: reading chat_history from session_state, not a bare variable
    for msg in st.session_state.chat_history:
        messages.append(msg)

    messages.append(HumanMessage(content=user_message))

    try:
        response = llm.invoke(messages)
        ai_response = response.content
    except Exception as e:
        ai_response = f"⚠️ Sorry, I ran into an error: {str(e)}"

    # ✅ Fixed: manual memory save, replaces the old save_context call
    st.session_state.chat_history.append(HumanMessage(content=user_message))
    st.session_state.chat_history.append(AIMessage(content=ai_response))

    return ai_response


def main():
    st.set_page_config(page_title="Stock Market Chatbot", layout="wide")
    st.title("📈 Stock Market Chatbot")
    st.caption("Ask about stock market. Eg. How's Apple doing today?")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # ✅ Fixed: moved up before the chat loop so it's always initialized
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask me about stocks!"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.spinner("Thinking..."):
            response = get_ai_response(prompt)

        st.session_state.messages.append({"role": "assistant", "content": response})
        with st.chat_message("assistant"):
            st.markdown(response)


main()