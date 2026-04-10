import yfinance as yf
import pandas as pd
import requests
import os
from ml_model import predict
from engine import stock_ranking

TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg}
        )
    except:
        pass

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

stocks = [
    "RELIANCE.NS","TCS.NS","INFY.NS",
    "HDFCBANK.NS","ICICIBANK.NS","SBIN.NS"
]

rankings = stock_ranking()
results = []

# =========================
# MARKET CHECK
# =========================
nifty = yf.download("^NSEI", period="1d", interval="5m", progress=False)

if nifty.empty:
    send("⚠️ Market data unavailable")
    exit()

close = nifty["Close"]
if isinstance(close, pd.DataFrame):
    close = close.iloc[:, 0]

if len(close) < 12:
    exit()

change = ((close.iloc[-1] - close.iloc[-12]) / close.iloc[-12]) * 100

if change <= 0:
    send("⚠️ Market is weak. No trades.")
    exit()

# =========================
# SCAN
# =========================
for stock in stocks:
    try:
        if not higher_tf(stock):
            continue

        data = yf.download(stock, period="1d", interval="5m", progress=False)
        if data.empty:
            continue

        close = data["Close"]
        volume = data["Volume"]

        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
            volume = volume.iloc[:, 0]

        latest = float(close.iloc[-1])
        old = float(close.iloc[-12])

        change = ((latest-old)/old)*100
        vol = float(volume.iloc[-1]) / float(volume.mean())
        r = rsi(close).iloc[-1]

        ema20 = ema(close,20).iloc[-1]
        ema50 = ema(close,50).iloc[-1]

        if not (latest > ema20 > ema50):
            continue

        if r > 65 or r < 40:
            continue

        support, resistance = sr(close)

        if latest < resistance * 0.995:
            continue

        confidence = predict(change, vol, r, "AUTO", "Bullish")
        winrate = rankings.get(stock, 0.5)

        score = confidence + (winrate * 100)

        results.append((stock, resistance, support, score))

    except:
        continue

# =========================
# FINAL SIGNAL
# =========================
if not results:
    send("⚠️ No high-quality trades found")
else:
    best = sorted(results, key=lambda x: x[3], reverse=True)[0]

    msg = f"""
🚀 AUTO TRADE SIGNAL

Stock: {best[0]}
Entry: ₹{round(best[1],2)}
Target: ₹{round(best[1]*1.015,2)}
SL: ₹{round(best[2],2)}
"""

    send(msg)
