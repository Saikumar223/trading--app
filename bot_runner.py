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
MAX_DAILY_LOSS = CAPITAL * 0.02   # 2%
MAX_TRADES = 3
MAX_CONSECUTIVE_LOSS = 2

# =========================
# TELEGRAM
# =========================

send("🚀 BOT STARTED SUCCESSFULLY")


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
# AUTO TRAIN ML
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

def position_size(entry, sl):
    risk = CAPITAL * 0.02
    risk_per_share = abs(entry - sl)
    return int(risk / risk_per_share) if risk_per_share != 0 else 0

def market_trend():
    data = yf.download("^NSEI", period="1d", interval="5m", progress=False)
    if data.empty:
        return "UNKNOWN", 0

    close = data["Close"]
    if hasattr(close, "columns"):
        close = close.iloc[:, 0]

    ema20 = ema(close,20).iloc[-1]
    ema50 = ema(close,50).iloc[-1]
    price = close.iloc[-1]

    if price > ema20 > ema50:
        return "BULLISH", price
    elif price < ema20 < ema50:
        return "BEARISH", price
    else:
        return "SIDEWAYS", price

stocks = ["RELIANCE.NS","TCS.NS","INFY.NS","HDFCBANK.NS","SBIN.NS"]
rankings = stock_ranking()

# =========================
# 🌅 MORNING
# =========================
if phase == "OPEN":

    trend, index_price = market_trend()

    results = []

    for stock in stocks:
        try:
            data = yf.download(stock, period="1d", interval="5m", progress=False)
            if data.empty:
                continue

            close = data["Close"]
            volume = data["Volume"]

            if hasattr(close, "columns"):
                close = close.iloc[:, 0]
                volume = volume.iloc[:, 0]

            latest = close.iloc[-1]
            old = close.iloc[-12]

            change = ((latest-old)/old)*100
            vol_ratio = volume.iloc[-1] / volume.mean()
            r = rsi(close).iloc[-1]

            ema20 = ema(close,20).iloc[-1]
            ema50 = ema(close,50).iloc[-1]

            # 🔥 STRICT FILTERS
            if not (latest > ema20 > ema50):
                continue
            if vol_ratio < 1.3:
                continue
            if not (45 < r < 65):
                continue

            confidence = predict(change, vol_ratio, r, "AUTO", trend)
            if confidence < 70:
                continue

            support, resistance = sr(close)

            qty = position_size(resistance, support)
            if qty == 0:
                continue

            score = confidence + (rankings.get(stock, 0.5) * 100)

            results.append((stock, resistance, support, qty, score))

        except:
            continue

    if not results:
        send("⚠️ No high-quality equity trades today")
    else:
        top = sorted(results, key=lambda x: x[4], reverse=True)[:MAX_TRADES]

        trades = []
        msg = "🌅 EQUITY TRADES\n\n"

        for t in top:
            trades.append({
                "stock": t[0],
                "entry": t[1],
                "sl": t[2],
                "qty": t[3],
                "tsl": t[2],
                "loss": False
            })

            msg += f"{t[0]} → ₹{round(t[1],2)} | SL ₹{round(t[2],2)} | Qty {t[3]}\n"

        state["trades"] = trades
        state["daily_loss"] = 0
        state["consecutive_loss"] = 0

        save_state(state)
        send(msg)

    # 🔥 OPTIONS SIGNAL (only strong trend)
    if trend in ["BULLISH", "BEARISH"]:
        strike = round(index_price / 100) * 100

        option = f"NIFTY {strike} CE" if trend=="BULLISH" else f"NIFTY {strike} PE"

        send(f"""
🚀 OPTIONS TRADE

Trend: {trend}
Trade: {option}

SL: 20%
Target: 40%+
""")

# =========================
# 🌞 MIDDAY
# =========================
elif phase == "MID":

    trades = state.get("trades", [])
    daily_loss = state.get("daily_loss", 0)
    consecutive_loss = state.get("consecutive_loss", 0)

    if not trades:
        send("⚠️ No trades running")
        exit()

    msg = "🌞 MIDDAY UPDATE\n\n"

    for trade in trades:
        try:
            data = yf.download(trade["stock"], period="1d", interval="5m", progress=False)
            close = data["Close"]

            if hasattr(close, "columns"):
                close = close.iloc[:, 0]

            price = close.iloc[-1]

            pnl = (price - trade["entry"]) * trade["qty"]

            if pnl < 0:
                daily_loss += abs(pnl)

            # TSL
            if price > trade["entry"] * 1.01:
                new_tsl = price * 0.995
                if new_tsl > trade["tsl"]:
                    trade["tsl"] = new_tsl

            if price < trade["tsl"]:
                action = "EXIT 🔒"
                if not trade["loss"]:
                    consecutive_loss += 1
                    trade["loss"] = True
            else:
                action = "HOLD"

            msg += f"{trade['stock']} → ₹{round(price,2)} | PnL ₹{round(pnl,2)} → {action}\n"

        except:
            continue

    state["daily_loss"] = daily_loss
    state["consecutive_loss"] = consecutive_loss

    save_state(state)

    if daily_loss >= MAX_DAILY_LOSS or consecutive_loss >= MAX_CONSECUTIVE_LOSS:
        send("🛑 STOP TRADING FOR TODAY")

    send(msg)

# =========================
# 🌆 CLOSE
# =========================
else:

    trades = state.get("trades", [])

    if not trades:
        send("📊 No trades today")
        exit()

    total_pnl = 0
    msg = "🌆 FINAL REPORT\n\n"

    for trade in trades:
        try:
            data = yf.download(trade["stock"], period="1d", interval="5m", progress=False)
            close = data["Close"]

            if hasattr(close, "columns"):
                close = close.iloc[:, 0]

            price = close.iloc[-1]

            pnl = (price - trade["entry"]) * trade["qty"]
            total_pnl += pnl

            msg += f"{trade['stock']} → ₹{round(pnl,2)}\n"

        except:
            continue

    msg += f"\n💰 TOTAL PnL: ₹{round(total_pnl,2)}"

    send(msg)

    state.clear()
    save_state(state)
