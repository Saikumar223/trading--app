import yfinance as yf
import requests
import os
import json
from datetime import datetime
import pytz
from ml_model import auto_train, predict
from engine import log_trade, update_capital

TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

STATE_FILE = "trade_state.json"

# =========================
# STATE
# =========================
def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    return json.load(open(STATE_FILE))

def save_state(data):
    json.dump(data, open(STATE_FILE, "w"))

state = load_state()

CAPITAL = state.get("capital", 1000)
MAX_DAILY_LOSS = CAPITAL * 0.02
MAX_TRADES = 3
MAX_CONSECUTIVE_LOSS = 2

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
# AUTO TRAIN
# =========================
auto_train()

# =========================
# IST TIME
# =========================
ist = datetime.now(pytz.timezone("Asia/Kolkata"))
hour = ist.hour
minute = ist.minute

print("IST:", ist)

# =========================
# PHASE
# =========================
if 9 <= hour < 12:
    phase = "OPEN"
elif 12 <= hour < 14:
    phase = "MID"
elif 14 <= hour < 16:
    phase = "CLOSE"
else:
    send(f"⏭️ Skipped {hour}")
    exit()

send(f"🚀 RUN | {hour}:{minute} | {phase}")

# =========================
# HELPERS
# =========================
def ema(x, n): return x.ewm(span=n).mean()

def rsi(x):
    d = x.diff()
    g = d.clip(lower=0).rolling(14).mean()
    l = -d.clip(upper=0).rolling(14).mean()
    rs = g/l
    return 100 - (100/(1+rs))

def sr(x): return float(x.tail(20).min()), float(x.tail(20).max())

def qty(entry, sl):
    risk = CAPITAL * 0.02
    r = abs(entry - sl)
    return int(risk / r) if r else 0

def trend():
    d = yf.download("^NSEI", period="1d", interval="5m", progress=False)
    c = d["Close"]
    if hasattr(c,"columns"): c = c.iloc[:,0]
    e20,e50 = ema(c,20).iloc[-1], ema(c,50).iloc[-1]
    p = c.iloc[-1]
    if p > e20 > e50: return "BULL"
    if p < e20 < e50: return "BEAR"
    return "SIDE"

# =========================
# EDGE FUNCTIONS (RELAXED)
# =========================
def breakout(c):
    recent_high = c.tail(15).max()
    return c.iloc[-1] >= recent_high * 0.995

def momentum(c):
    return c.iloc[-1] >= c.iloc[-5]

stocks = ["RELIANCE.NS","TCS.NS","INFY.NS","HDFCBANK.NS","SBIN.NS"]

# =========================
# CONFIDENCE
# =========================
base_conf = 60
if state.get("loss_streak",0) >= 2:
    base_conf = 70

# =========================
# OPEN PHASE
# =========================
if phase == "OPEN":

    if state.get("daily_loss",0) >= MAX_DAILY_LOSS:
        send("❌ Max loss hit")
        exit()

    if state.get("loss_streak",0) >= MAX_CONSECUTIVE_LOSS:
        send("❌ Loss streak stop")
        exit()

    t = trend()
    results = []

    for s in stocks:
        try:
            d = yf.download(s, period="1d", interval="5m", progress=False)
            if d.empty:
                continue

            c,v = d["Close"], d["Volume"]
            if hasattr(c,"columns"):
                c,v = c.iloc[:,0], v.iloc[:,0]

            latest = c.iloc[-1]
            old = c.iloc[-12]

            change = (latest-old)/old*100
            vr = v.iloc[-1]/v.mean()
            r = rsi(c).iloc[-1]

            e20,e50 = ema(c,20).iloc[-1], ema(c,50).iloc[-1]

            # TREND
            if not(latest > e20 > e50):
                continue

            # RELAXED EDGE
            if not breakout(c):
                continue

            if not momentum(c):
                continue

            # BASIC FILTERS
            if vr < 1.1:
                continue

            if not(35 < r < 75):
                continue

            conf = predict(change, vr, r, "AUTO", t)

            if conf < base_conf:
                continue

            support,_ = sr(c)
            q = qty(latest, support)

            if q == 0:
                continue

            results.append((s, latest, support, q, conf))

            if len(results) >= MAX_TRADES:
                break

        except:
            continue

    # 🔥 FALLBACK (CRITICAL FIX)
    if not results:
        for s in stocks:
            try:
                d = yf.download(s, period="1d", interval="5m", progress=False)
                c = d["Close"]
                if hasattr(c,"columns"): c = c.iloc[:,0]

                latest = c.iloc[-1]
                e20 = ema(c,20).iloc[-1]

                if latest > e20:
                    support,_ = sr(c)
                    q = qty(latest, support)

                    if q > 0:
                        results.append((s, latest, support, q, 50))
                        break
            except:
                continue

    if not results:
        send("⚠️ No trades today")
    else:
        state["trades"] = []
        msg = "🌅 TRADES\n\n"

        for r in results:
            state["trades"].append({
                "stock": r[0],
                "entry": r[1],
                "sl": r[2],
                "qty": r[3],
                "status": "OPEN"
            })

            msg += f"{r[0]} ₹{round(r[1],2)} SL {round(r[2],2)} Q {r[3]}\n"

        state["daily_loss"] = 0
        state["loss_streak"] = 0

        save_state(state)
        send(msg)

# =========================
# MID
# =========================
elif phase == "MID":

    trades = state.get("trades", [])

    if not trades:
        send("⚠️ No active trades")
        exit()

    msg = "🌞 UPDATE\n\n"

    for t in trades:
        try:
            d = yf.download(t["stock"], period="1d", interval="5m", progress=False)
            c = d["Close"]
            if hasattr(c,"columns"): c = c.iloc[:,0]

            price = c.iloc[-1]
            pnl = (price - t["entry"]) * t["qty"]

            if price <= t["sl"]:
                t["status"] = "LOSS"
                state["daily_loss"] += abs(pnl)
                state["loss_streak"] += 1
                log_trade(t["stock"], t["entry"], price, pnl)

            elif price > t["entry"] * 1.01:
                t["sl"] = price * 0.995
                t["status"] = "PROFIT"

            msg += f"{t['stock']} ₹{round(price,2)} | PnL ₹{round(pnl,2)} → {t['status']}\n"

        except:
            continue

    save_state(state)
    send(msg)

# =========================
# CLOSE
# =========================
else:

    trades = state.get("trades", [])

    if not trades:
        send("🌆 No trades executed today")
        exit()

    total = 0
    wins = 0

    for t in trades:
        try:
            d = yf.download(t["stock"], period="1d", interval="5m", progress=False)
            c = d["Close"]
            if hasattr(c,"columns"): c = c.iloc[:,0]

            price = c.iloc[-1]
            pnl = (price - t["entry"]) * t["qty"]

            total += pnl
            if pnl > 0:
                wins += 1

            log_trade(t["stock"], t["entry"], price, pnl)

        except:
            continue

    update_capital(total)

    new_capital = CAPITAL + total
    state["capital"] = new_capital
    state["daily_loss"] = 0
    state["loss_streak"] = 0

    save_state(state)

    acc = (wins / len(trades) * 100) if trades else 0

    send(f"🌆 REPORT\n💰 Capital ₹{round(new_capital,2)}\nPnL ₹{round(total,2)}\nAccuracy {round(acc,2)}%")
