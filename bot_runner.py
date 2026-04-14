import yfinance as yf
import requests
import os
import json
from datetime import datetime, timedelta
from ml_model import auto_train, predict
from engine import stock_ranking

TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

STATE_FILE = "trade_state.json"

CAPITAL = 1000
MAX_DAILY_LOSS = CAPITAL * 0.02
MAX_TRADES = 3
MAX_CONSECUTIVE_LOSS = 2

# =========================
# TELEGRAM
# =========================
def send(msg):
    try:
        res = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg}
        )
        print("STATUS:", res.status_code)
        print("RESPONSE:", res.text)
    except Exception as e:
        print("ERROR:", str(e))

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
# AUTO TRAIN
# =========================
auto_train()

# =========================
# IST TIME
# =========================
ist_time = datetime.utcnow() + timedelta(hours=5, minutes=30)
hour = ist_time.hour
minute = ist_time.minute

print("IST TIME:", ist_time)

# =========================
# 🔥 SMART TIME WINDOWS (FIXED)
# =========================
if 9 <= hour < 12:
    phase = "OPEN"
elif 12 <= hour < 14:
    phase = "MID"
elif 14 <= hour < 16:
    phase = "CLOSE"
else:
    send(f"⏭️ Skipped → IST {hour}:{minute} (outside trading hours)")
    exit()

# Always confirm run
send(f"🚀 BOT RUNNING | IST: {hour}:{minute} | Phase: {phase}")

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
# 🌅 OPEN PHASE
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

# =========================
# 🌞 MID PHASE
# =========================
elif phase == "MID":

    trades = state.get("trades", [])

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

            if price > trade["entry"] * 1.01:
                new_tsl = price * 0.995
                if new_tsl > trade["tsl"]:
                    trade["tsl"] = new_tsl

            action = "HOLD" if price > trade["tsl"] else "EXIT 🔒"

            msg += f"{trade['stock']} → ₹{round(price,2)} | PnL ₹{round(pnl,2)} → {action}\n"

        except:
            continue

    send(msg)

# =========================
# 🌆 CLOSE PHASE
# =========================
else:
    send("🌆 Market closed — no action")
