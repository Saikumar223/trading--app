import yfinance as yf
import requests
import os
from datetime import datetime
import pytz

from ml_model import auto_train, predict

from trade_manager import (
    load_state,
    save_state,
    add_trade,
    get_active_trades,
    update_trade,
    close_trade
)

TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# =========================
# LOAD STATE
# =========================
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
            data={
                "chat_id": CHAT_ID,
                "text": msg
            }
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
ist = datetime.now(
    pytz.timezone("Asia/Kolkata")
)

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
def ema(x, n):
    return x.ewm(span=n).mean()

def rsi(x):

    d = x.diff()

    g = d.clip(lower=0).rolling(14).mean()

    l = -d.clip(upper=0).rolling(14).mean()

    rs = g / l

    return 100 - (100 / (1 + rs))

def sr(x):

    return (
        float(x.tail(20).min()),
        float(x.tail(20).max())
    )

def qty(entry, sl):

    risk = CAPITAL * 0.02

    r = abs(entry - sl)

    return int(risk / r) if r else 0

def trend():

    d = yf.download(
        "^NSEI",
        period="1d",
        interval="5m",
        progress=False
    )

    c = d["Close"]

    if hasattr(c, "columns"):
        c = c.iloc[:, 0]

    e20 = ema(c, 20).iloc[-1]
    e50 = ema(c, 50).iloc[-1]

    p = c.iloc[-1]

    if p > e20 > e50:
        return "BULL"

    if p < e20 < e50:
        return "BEAR"

    return "SIDE"

# =========================
# EDGE FUNCTIONS
# =========================
def breakout(c):

    recent_high = c.tail(15).max()

    return c.iloc[-1] >= recent_high * 0.995

def momentum(c):

    return c.iloc[-1] >= c.iloc[-5]

stocks = [
    "RELIANCE.NS",
    "TCS.NS",
    "INFY.NS",
    "HDFCBANK.NS",
    "SBIN.NS"
]

# =========================
# CONFIDENCE
# =========================
base_conf = 60

if state.get("loss_streak", 0) >= 2:
    base_conf = 70

# =========================
# OPEN
# =========================
if phase == "OPEN":

    if state.get("daily_loss", 0) >= MAX_DAILY_LOSS:
        send("❌ Max loss hit")
        exit()

    if state.get("loss_streak", 0) >= MAX_CONSECUTIVE_LOSS:
        send("❌ Loss streak stop")
        exit()

    t = trend()

    results = []

    for s in stocks:

        try:

            d = yf.download(
                s,
                period="1d",
                interval="5m",
                progress=False
            )

            if d.empty:
                continue

            c = d["Close"]
            v = d["Volume"]

            if hasattr(c, "columns"):
                c = c.iloc[:, 0]
                v = v.iloc[:, 0]

            latest = c.iloc[-1]
            old = c.iloc[-12]

            change = (
                (latest - old) / old
            ) * 100

            vr = v.iloc[-1] / v.mean()

            r = rsi(c).iloc[-1]

            e20 = ema(c, 20).iloc[-1]
            e50 = ema(c, 50).iloc[-1]

            # TREND
            if not (latest > e20 > e50):
                continue

            # EDGE
            if not breakout(c):
                continue

            if not momentum(c):
                continue

            # FILTERS
            if vr < 1.1:
                continue

            if not (35 < r < 75):
                continue

            conf = predict(
                change,
                vr,
                r,
                "AUTO",
                t
            )

            if conf < base_conf:
                continue

            support, _ = sr(c)

            q = qty(latest, support)

            if q == 0:
                continue

            results.append(
                (
                    s,
                    latest,
                    support,
                    q
                )
            )

            if len(results) >= MAX_TRADES:
                break

        except:
            continue

    # FALLBACK
    if not results:

        for s in stocks:

            try:

                d = yf.download(
                    s,
                    period="1d",
                    interval="5m",
                    progress=False
                )

                c = d["Close"]

                if hasattr(c, "columns"):
                    c = c.iloc[:, 0]

                latest = c.iloc[-1]

                e20 = ema(c, 20).iloc[-1]

                if latest > e20:

                    support, _ = sr(c)

                    q = qty(latest, support)

                    if q > 0:

                        results.append(
                            (
                                s,
                                latest,
                                support,
                                q
                            )
                        )

                        break

            except:
                continue

    if not results:

        send("⚠️ No trades today")

    else:

        msg = "🌅 TRADES\n\n"

        for r in results:

            add_trade(
                r[0],
                r[1],
                r[2],
                r[3]
            )

            msg += (
                f"{r[0]} "
                f"₹{round(r[1],2)} "
                f"SL {round(r[2],2)} "
                f"Q {r[3]}\n"
            )

        send(msg)

# =========================
# MID
# =========================
elif phase == "MID":

    trades = get_active_trades()

    if not trades:

        send("⚠️ No active trades")
        exit()

    msg = "🌞 UPDATE\n\n"

    for t in trades:

        try:

            d = yf.download(
                t["stock"],
                period="1d",
                interval="5m",
                progress=False
            )

            c = d["Close"]

            if hasattr(c, "columns"):
                c = c.iloc[:, 0]

            price = c.iloc[-1]

            pnl = (
                (price - t["entry"])
                * t["qty"]
            )

            status = "HOLD"

            # SL HIT
            if price <= t["sl"]:

                close_trade(
                    t["stock"],
                    price
                )

                status = "SL HIT ❌"

            # TARGET HIT
            elif price >= t["target"]:

                close_trade(
                    t["stock"],
                    price
                )

                status = "TARGET 🎯"

            # TRAILING SL
            elif price > t["entry"] * 1.01:

                new_sl = round(
                    price * 0.995,
                    2
                )

                update_trade(
                    t["stock"],
                    {
                        "sl": new_sl
                    }
                )

                status = "TRAILING 🔥"

            msg += (
                f"{t['stock']} "
                f"₹{round(price,2)} "
                f"| PnL ₹{round(pnl,2)} "
                f"| {status}\n"
            )

        except:
            continue

    send(msg)

# =========================
# CLOSE
# =========================
else:

    trades = get_active_trades()

    if not trades:

        send("🌆 No trades executed today")
        exit()

    total = 0
    wins = 0

    for t in trades:

        try:

            d = yf.download(
                t["stock"],
                period="1d",
                interval="5m",
                progress=False
            )

            c = d["Close"]

            if hasattr(c, "columns"):
                c = c.iloc[:, 0]

            price = c.iloc[-1]

            pnl = (
                (price - t["entry"])
                * t["qty"]
            )

            total += pnl

            if pnl > 0:
                wins += 1

            close_trade(
                t["stock"],
                price
            )

        except:
            continue

    state = load_state()

    capital = state.get("capital", 1000)

    acc = (
        (wins / len(trades)) * 100
    ) if trades else 0

    send(
        f"🌆 REPORT\n"
        f"💰 Capital ₹{round(capital,2)}\n"
        f"PnL ₹{round(total,2)}\n"
        f"Accuracy {round(acc,2)}%"
    )
