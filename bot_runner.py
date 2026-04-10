import yfinance as yf
import requests
import os
import json
from datetime import datetime
from ml_model import auto_train, predict
from engine import stock_ranking

TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

STATE_FILE = "trade_state.json"

CAPITAL = 1000
MAX_DAILY_LOSS = CAPITAL * 0.03  # 3%

# =========================
# TELEGRAM
# =========================
def send(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg}
        )
    except:
        pass

# =========================
# STATE
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
# AUTO TRAIN ML DAILY
# =========================
auto_train()

# =========================
# TIME PHASE
# =========================
hour = datetime.utcnow().hour

if hour < 5:
    phase = "OPEN"
elif hour < 9:
    phase = "MID"
else:
    phase = "CLOSE"

# =========================
# HELPERS
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
    if hasattr(close, "columns"):
        close = close.iloc[:, 0]

    return close.iloc[-1] > ema(close,20).iloc[-1] > ema(close,50).iloc[-1]

def position_size(entry, sl):
    risk_per_trade = CAPITAL * 0.02
    risk_per_share = abs(entry - sl)

    if risk_per_share == 0:
        return 0

    return int(risk_per_trade / risk_per_share)

stocks = [
    "RELIANCE.NS","TCS.NS","INFY.NS",
    "HDFCBANK.NS","ICICIBANK.NS","SBIN.NS"
]

rankings = stock_ranking()

# =========================
# 🌅 MORNING (PORTFOLIO BUILD)
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
            volume = data["Volume"]

            if hasattr(close, "columns"):
                close = close.iloc[:, 0]
                volume = volume.iloc[:, 0]

            latest = float(close.iloc[-1])
            old = float(close.iloc[-12])

            change = ((latest-old)/old)*100
            vol = float(volume.iloc[-1]) / float(volume.mean())
            r = rsi(close).iloc[-1]

            support, resistance = sr(close)

            confidence = predict(change, vol, r, "AUTO", "Bullish")
            winrate = rankings.get(stock, 0.5)

            score = confidence + (winrate * 100)

            results.append((stock, resistance, support, score))

        except:
            continue

    if not results:
        send("⚠️ No trades today")
    else:
        top = sorted(results, key=lambda x: x[3], reverse=True)[:3]

        trades = []
        msg = "🌅 MORNING PORTFOLIO\n\n"

        for t in top:
            qty = position_size(t[1], t[2])

            if qty == 0:
                continue

            trades.append({
                "stock": t[0],
                "entry": t[1],
                "sl": t[2],
                "qty": qty,
                "tsl": t[2]  # initialize trailing SL
            })

            msg += f"{t[0]} → Buy ₹{round(t[1],2)} | SL ₹{round(t[2],2)} | Qty {qty}\n"

        state["trades"] = trades
        state["daily_loss"] = 0

        save_state(state)
        send(msg)

# =========================
# 🌞 MIDDAY (LIVE DECISIONS + TRAILING SL)
# =========================
elif phase == "MID":

    trades = state.get("trades", [])
    daily_loss = state.get("daily_loss", 0)

    if not trades:
        send("⚠️ No active trades")
        exit()

    msg = "🌞 MIDDAY UPDATE\n\n"

    for trade in trades:
        try:
            data = yf.download(trade["stock"], period="1d", interval="5m", progress=False)
            if data.empty:
                continue

            close = data["Close"]
            if hasattr(close, "columns"):
                close = close.iloc[:, 0]

            price = float(close.iloc[-1])

            pnl = (price - trade["entry"]) * trade["qty"]

            if pnl < 0:
                daily_loss += abs(pnl)

            # =========================
            # 🔥 TRAILING STOPLOSS
            # =========================
            if price > trade["entry"] * 1.01:
                new_tsl = price * 0.995
                if new_tsl > trade["tsl"]:
                    trade["tsl"] = new_tsl

            if price < trade["tsl"]:
                action = "EXIT (TSL HIT) 🔒"
            elif daily_loss >= MAX_DAILY_LOSS:
                action = "STOP TRADING 🛑"
            elif price > trade["entry"] * 1.01:
                action = "HOLD ✅ (TSL Active)"
            elif price < trade["entry"]:
                action = "EXIT ❌"
            else:
                action = "WAIT ⏳"

            msg += f"{trade['stock']} → ₹{round(price,2)} | PnL ₹{round(pnl,2)} | TSL ₹{round(trade['tsl'],2)} → {action}\n"

        except:
            continue

    state["daily_loss"] = daily_loss
    save_state(state)

    msg += f"\nTotal Loss Today: ₹{round(daily_loss,2)}"
    send(msg)

# =========================
# 🌆 CLOSE (FINAL SUMMARY)
# =========================
else:

    trades = state.get("trades", [])

    if not trades:
        send("📊 No trades today")
        exit()

    msg = "🌆 FINAL SUMMARY\n\n"
    total_pnl = 0

    for trade in trades:
        try:
            data = yf.download(trade["stock"], period="1d", interval="5m", progress=False)
            if data.empty:
                continue

            close = data["Close"]
            if hasattr(close, "columns"):
                close = close.iloc[:, 0]

            price = float(close.iloc[-1])

            pnl = (price - trade["entry"]) * trade["qty"]
            total_pnl += pnl

            msg += f"{trade['stock']} → PnL ₹{round(pnl,2)}\n"

        except:
            continue

    msg += f"\n💰 Total Portfolio PnL: ₹{round(total_pnl,2)}"

    send(msg)

    state.clear()
    save_state(state)
