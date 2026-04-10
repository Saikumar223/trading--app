import yfinance as yf
import pandas as pd
import requests
import os
import json
from datetime import datetime
from ml_model import predict
from engine import stock_ranking

TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

STATE_FILE = "trade_state.json"

def send(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg}
        )
    except:
        pass

# =========================
# STATE MANAGEMENT
# =========================
def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, "r") as f:
        return json.load(f)

def save_state(data):
    with open(STATE_FILE, "w") as f:
        json.dump(data, f)

state = load_state()

# =========================
# TIME PHASE DETECTION
# =========================
hour = datetime.utcnow().hour  # UTC

if hour < 5:
    phase = "OPEN"
elif hour < 9:
    phase = "MID"
else:
    phase = "CLOSE"

# =========================
# COMMON FUNCTIONS
# =========================
def ema(series, span):
    return series.ewm(span=span).mean()

def rsi(series):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / loss
    return 100 - (100/(1+rs))

def sr(series):
    return float(series.tail(20).min()), float(series.tail(20).max())

def higher_tf(stock):
    data = yf.download(stock, period="2d", interval="15m", progress=False)
    if data.empty:
        return False

    close = data["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]

    return close.iloc[-1] > ema(close,20).iloc[-1] > ema(close,50).iloc[-1]

stocks = ["RELIANCE.NS","TCS.NS","INFY.NS","HDFCBANK.NS","SBIN.NS"]
rankings = stock_ranking()

# =========================
# 🌅 MORNING LOGIC
# =========================
if phase == "OPEN":

    results = []

    for stock in stocks:
        try:
            if not higher_tf(stock):
                continue

            data = yf.download(stock, period="1d", interval="5m", progress=False)
            if data.empty:
                continue

            close = data["Close"]
            if isinstance(close, pd.DataFrame):
                close = close.iloc[:, 0]

            support, resistance = sr(close)

            score = rankings.get(stock, 0.5)

            results.append((stock, resistance, support, score))

        except:
            continue

    if not results:
        send("⚠️ No trades today")
    else:
        best = sorted(results, key=lambda x: x[3], reverse=True)[0]

        state["trade"] = {
            "stock": best[0],
            "entry": best[1],
            "sl": best[2]
        }

        save_state(state)

        send(f"""
🌅 MORNING TRADE

Stock: {best[0]}
Buy above: ₹{round(best[1],2)}
SL: ₹{round(best[2],2)}
""")

# =========================
# 🌞 MIDDAY LOGIC
# =========================
elif phase == "MID":

    trade = state.get("trade")

    if not trade:
        send("⚠️ No active trade")
        exit()

    data = yf.download(trade["stock"], period="1d", interval="5m", progress=False)

    if data.empty:
        exit()

    close = data["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]

    price = float(close.iloc[-1])

    if price > trade["entry"] * 1.01:
        action = "HOLD ✅ (Strong)"
    elif price < trade["entry"]:
        action = "EXIT ❌ (Weak)"
    else:
        action = "WAIT ⏳"

    send(f"""
🌞 MIDDAY UPDATE

{trade['stock']}
Current: ₹{round(price,2)}

Action: {action}
""")

# =========================
# 🌆 CLOSING LOGIC
# =========================
else:

    trade = state.get("trade")

    if not trade:
        send("📊 No trades today")
        exit()

    data = yf.download(trade["stock"], period="1d", interval="5m", progress=False)

    if data.empty:
        exit()

    close = data["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]

    price = float(close.iloc[-1])

    pnl = price - trade["entry"]

    send(f"""
🌆 MARKET CLOSE

{trade['stock']}
Close: ₹{round(price,2)}

PnL: ₹{round(pnl,2)}

Action:
{"BOOK PROFIT ✅" if pnl > 0 else "STOPLOSS HIT ❌"}
""")

    state.clear()
    save_state(state)
