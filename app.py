import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import requests
import hashlib
from ml_model import predict
from engine import save_trade, update_trades, stock_ranking

st.set_page_config(layout="wide")

st.title("📊 AI Trading Dashboard")

mode = st.selectbox("Mode", ["Intraday", "Swing"])
capital = st.number_input("💰 Capital (₹)", value=1000)

# =========================
# TELEGRAM ALERT
# =========================
def send_telegram_alert(best):
    try:
        TOKEN = st.secrets["TOKEN"]
        CHAT_ID = st.secrets["CHAT_ID"]

        trade_id = hashlib.md5(
            f"{best['Stock']}{best['Entry']}{best['Target']}".encode()
        ).hexdigest()

        if "last_trade_id" not in st.session_state:
            st.session_state.last_trade_id = ""

        if st.session_state.last_trade_id != trade_id:

            msg = f"""
🚀 BEST TRADE

{best['Stock']}
Entry: ₹{best['Entry']}
Target: ₹{best['Target']}
SL: ₹{best['StopLoss']}
Qty: {best['Qty']}
Confidence: {best['Confidence %']}%
"""

            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                data={"chat_id": CHAT_ID, "text": msg}
            )

            st.session_state.last_trade_id = trade_id

    except:
        pass

# =========================
# POSITION SIZE
# =========================
def calculate_position(entry, sl, capital):
    risk = capital * 0.02
    risk_per_share = abs(entry - sl)
    if risk_per_share == 0:
        return 0, 0
    qty = int(risk / risk_per_share)
    return qty, qty * entry

# =========================
# MARKET CHECK
# =========================
nifty = yf.download("^NSEI", period="1d", interval="5m", progress=False)

if nifty.empty:
    st.stop()

close = nifty["Close"]
if isinstance(close, pd.DataFrame):
    close = close.iloc[:, 0]

if len(close) < 12:
    st.stop()

change = ((close.iloc[-1] - close.iloc[-12]) / close.iloc[-12]) * 100

st.write(f"NIFTY Trend: {round(change,2)}%")

if change <= 0:
    st.warning("Market weak")
    st.stop()

# =========================
# FUNCTIONS
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
    c = data["Close"]
    if isinstance(c, pd.DataFrame):
        c = c.iloc[:, 0]
    return c.iloc[-1] > ema(c,20).iloc[-1] > ema(c,50).iloc[-1]

stocks = ["RELIANCE.NS","TCS.NS","INFY.NS","HDFCBANK.NS","SBIN.NS"]

rankings = stock_ranking()
results = []

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

        entry = resistance
        target = entry * (1.03 if mode=="Swing" else 1.015)
        sl = support

        confidence = predict(change, vol, r, "AUTO", "Bullish")

        if confidence != 50 and confidence < 60:
            continue

        qty, investment = calculate_position(entry, sl, capital)
        if qty == 0:
            continue

        winrate = rankings.get(stock, 0.5)*100

        results.append({
            "Stock": stock,
            "Entry": round(entry,2),
            "Target": round(target,2),
            "StopLoss": round(sl,2),
            "Qty": qty,
            "Investment": round(investment,2),
            "Confidence %": confidence,
            "WinRate": round(winrate,2)
        })

    except:
        continue

df = pd.DataFrame(results)

if df.empty:
    st.warning("No trades found")
    st.stop()

df = df.sort_values(by=["Confidence %","WinRate"], ascending=False).head(3)

st.dataframe(df)

best = df.iloc[0]

st.success(f"""
BEST TRADE

{best['Stock']}
Entry: ₹{best['Entry']}
Target: ₹{best['Target']}
SL: ₹{best['StopLoss']}
Qty: {best['Qty']}
Confidence: {best['Confidence %']}%
""")

send_telegram_alert(best)

save_trade(
    best["Stock"], best["Entry"], best["Target"], best["StopLoss"],
    0,0,50,"AUTO","Bullish"
)

# =========================
# CHART
# =========================
chart = yf.download(best["Stock"], period="1d", interval="5m", progress=False)

if not chart.empty:
    if isinstance(chart.columns, pd.MultiIndex):
        chart.columns = chart.columns.get_level_values(0)

    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=chart.index,
        open=chart["Open"],
        high=chart["High"],
        low=chart["Low"],
        close=chart["Close"]
    ))

    fig.add_hline(y=best["Entry"], line_color="green")
    fig.add_hline(y=best["Target"], line_color="blue")
    fig.add_hline(y=best["StopLoss"], line_color="red")

    fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False)

    st.plotly_chart(fig)
