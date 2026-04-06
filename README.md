# 📈 Stock Market Chatbot

An AI-powered stock market assistant built with Groq, LangChain, yfinance, and Streamlit. Ask questions in plain English — the app automatically extracts the stock ticker, fetches live data from Yahoo Finance, and responds conversationally with full memory of your chat history.

---

## Live Demo

Deployed on Streamlit Cloud: https://stockchat-r.streamlit.app/

---

## What It Does

- **Natural language queries** — Ask "How is Apple doing today?" and the app figures out you mean `AAPL`
- **Real-time stock data** — Fetches current price, % change, 52-week high/low, market cap, and volume via yfinance
- **Conversation memory** — Remembers your full chat history so follow-up questions like "How does that compare to its 52-week low?" work seamlessly
- **Graceful fallback** — If no stock is mentioned, the AI responds using general financial knowledge without crashing
- **Zero cost** — Groq free tier + yfinance (no API key) + Streamlit Cloud free hosting

---

## Tech Stack

| Tool | Purpose |
|---|---|
| [Groq API](https://groq.com) | LLM inference — Llama 3.3 70B |
| [LangChain](https://langchain.com) | Message schema (`HumanMessage`, `AIMessage`, `SystemMessage`) |
| [yfinance](https://pypi.org/project/yfinance/) | Real-time stock data from Yahoo Finance |
| [Streamlit](https://streamlit.io) | Chat UI and cloud deployment |
| Python 3.10+ | Core language |

---

## Project Structure

```
stock-chatbot/
├── .streamlit/
│   └── secrets.toml        # Local secrets — never committed to Git
├── venv/                   # Virtual environment — never committed to Git
├── app.py                  # Main application file
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/your-username/stock-chatbot.git
cd stock-chatbot
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
venv\Scripts\activate
```

Your terminal prompt should change to show `(venv)` — this means you are inside the isolated environment.

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure your API key

Create the secrets file:

```bash
mkdir .streamlit
```

Create `.streamlit/secrets.toml` and add:

```toml
GROQ_API_KEY = "your_groq_api_key_here"
```

Get your free Groq API key at [console.groq.com](https://console.groq.com).

> **Important:** Never commit `secrets.toml` to Git. It is already listed in `.gitignore`.

### 5. Run the app

```bash
streamlit run app.py
```

Your browser will open automatically at `http://localhost:8501`.

---

## Deploying to Streamlit Cloud

1. Push your code to a public GitHub repository (make sure `secrets.toml` is in `.gitignore`)
2. Go to [share.streamlit.io](https://share.streamlit.io) and connect your GitHub repo
3. In the Streamlit Cloud dashboard, go to **Settings → Secrets** and add:

```toml
GROQ_API_KEY = "your_groq_api_key_here"
```

4. Click **Deploy** — your app will be live in under a minute

---

## Requirements

```
streamlit
langchain
langchain-groq
langchain-core
yfinance
```

Generate a fresh `requirements.txt` anytime with:

```bash
pip freeze > requirements.txt
```

---

## Code Walkthrough

### `get_llm()`

```python
def get_llm():
    return ChatGroq(
        api_key=st.secrets["GROQ_API_KEY"],
        model="llama-3.3-70b-versatile",
        temperature=0.7
    )
```

Creates and returns a `ChatGroq` LLM client. Called as a function (rather than a global variable) so a fresh client is created each time it is needed — this avoids Streamlit re-run issues. `temperature=0.7` balances creativity and consistency. The API key is read from Streamlit secrets, never hardcoded.

---

### `extract_ticker(user_message)`

```python
def extract_ticker(user_message: str) -> str | None:
```

Uses the Groq LLM to extract a stock ticker symbol from the user's natural language message. This is called **smart extraction** — instead of keyword matching, the LLM reads the sentence and infers the correct ticker.

The function uses **few-shot prompting** — it provides 5 examples of inputs and expected outputs before asking the LLM to process the real message. This dramatically improves accuracy.

**Safety checks on the result:**
- If the LLM returns `"NONE"`, the function returns `None` — no ticker found
- `len(result) > 6` — real tickers are 1–5 characters; longer strings are rejected
- `not result.isalpha()` — tickers are letters only; anything with numbers or symbols is rejected

If anything fails (network error, API issue), the function catches the exception and returns `None` instead of crashing the app.

---

### `get_stock_data(ticker)`

```python
def get_stock_data(ticker: str) -> str:
```

Fetches live stock data from Yahoo Finance using the `yfinance` library. No API key is required — yfinance is free.

**Fields fetched:**

| Field | yfinance key |
|---|---|
| Company name | `longName` |
| Current price | `currentPrice` or `regularMarketPrice` |
| % change today | `regularMarketChangePercent` |
| 52-week high | `fiftyTwoWeekHigh` |
| 52-week low | `fiftyTwoWeekLow` |
| Market cap | `marketCap` |
| Volume | `regularMarketVolume` |

Market cap is formatted into human-readable strings: `$2.98T`, `$45.2B`, or `$320.5M` depending on the magnitude.

The `return` statement sits **outside** the `if/else` block for market cap — this is intentional. The market cap formatting block only decides the string representation; the return always executes regardless.

Returns a formatted markdown string ready to be injected into the AI prompt.

---

### `get_ai_response(user_message)`

```python
def get_ai_response(user_message: str) -> str:
```

The main orchestrator function. Runs these steps in sequence:

**Step 1 — Extract ticker**
Calls `extract_ticker()`. If a company is mentioned, `ticker` holds something like `"AAPL"`. Otherwise it is `None`.

**Step 2 — Fetch stock data**
If a ticker was found, calls `get_stock_data()` and wraps the result in a context block that instructs the AI to use it. If no ticker was found, `stock_context` stays as an empty string.

**Step 3 — Build the system prompt**
Constructs the AI's "identity card" — its personality, instructions, and the stock data context injected at the bottom. The system prompt is rebuilt on every call so fresh stock data is always included.

**Step 4 — Load conversation memory**
Reads `st.session_state.chat_history` — a list of `HumanMessage` and `AIMessage` objects accumulated across the conversation.

**Step 5 — Assemble the message list**
Builds the full message list sent to Groq:
```
[SystemMessage] → [past HumanMessage] → [past AIMessage] → ... → [current HumanMessage]
```

**Step 6 — Call Groq**
Sends the assembled message list to Groq's Llama 3.3 70B. The response is extracted with `.content`.

**Step 7 — Save to memory**
Appends the current exchange (user message + AI response) to `st.session_state.chat_history` so it is available in the next turn.

---

### `main()`

```python
def main():
```

The Streamlit UI layer. Runs on every browser interaction because Streamlit re-executes the entire script each time the user does anything.

**Session state keys used:**

| Key | Type | Purpose |
|---|---|---|
| `messages` | `list[dict]` | Stores `{"role": ..., "content": ...}` dicts for rendering chat bubbles |
| `chat_history` | `list[BaseMessage]` | Stores `HumanMessage`/`AIMessage` objects for LLM memory injection |

Two separate lists are maintained deliberately:
- `messages` is what Streamlit's `st.chat_message()` needs to render the UI
- `chat_history` is what the LLM needs as structured message objects

The `if "key" not in st.session_state` guards ensure lists are created only once — not reset on every re-run.

---

## Example Conversations

```
You:       How is Apple doing today?
Assistant: Apple (AAPL) is trading at $213.49, down 0.8% today...

You:       How does that compare to its 52-week high?
Assistant: Apple's current price of $213.49 is about 18% below its
           52-week high of $260.10, reached earlier this year...

You:       What about Microsoft?
Assistant: Microsoft (MSFT) is currently at $415.20, up 1.2% today...

You:       Which one has the higher market cap?
Assistant: Microsoft has the higher market cap at $3.09T compared
           to Apple's $3.21T — actually Apple edges it out slightly...
```

---

## Known Limitations

- **Market hours** — yfinance data may be delayed or show previous close price outside of market hours (9:30am–4:00pm ET weekdays)
- **Ticker ambiguity** — Very generic company names (e.g. "the bank") may extract the wrong ticker. Being specific ("JPMorgan" vs "the bank") gives better results
- **Memory length** — The full conversation history is sent to Groq on every turn. Very long conversations may approach token limits. A future improvement would be to cap history at the last N turns
- **Rate limits** — Groq's free tier has rate limits. Very rapid back-to-back messages may trigger a temporary limit error

---

## License

MIT License — free to use, modify, and distribute.

---

*Part of a 5-project AI portfolio series. Projects: Local Sentiment Analyzer · PDF RAG Chat · Customer Churn Predictor · **Stock Market Chatbot** · Smart Document Summarizer*
