import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import requests
import hashlib
from ml_model import predict
from engine import save_trade, update_trades, backtest

st.set_page_config(layout="wide")

st.title("📊 AI Trading Dashboard")

mode = st.selectbox("Mode", ["Intraday", "Swing"])

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
# MARKET
# =========================
nifty = yf.download("^NSEI", period="1d", interval="5m", progress=False)

if nifty.empty:
    st.stop()

close = nifty["Close"]
if isinstance(close, pd.DataFrame):
    close = close.iloc[:, 0]

if len(close) < 12:
    st.stop()

latest = float(close.iloc[-1])
old = float(close.iloc[-12])
change = ((latest - old) / old) * 100

st.write(f"NIFTY Trend: {round(change,2)}%")

if change <= 0:
    st.warning("Market weak")
    st.stop()

# =========================
# FUNCTIONS
# =========================
def calculate_rsi(series):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / loss
    return 100 - (100/(1+rs))

def ema(series, span):
    return series.ewm(span=span).mean()

stocks = [
    "RELIANCE.NS","TCS.NS","INFY.NS",
    "HDFCBANK.NS","ICICIBANK.NS",
    "SBIN.NS","ITC.NS","LT.NS",
    "JSWSTEEL.NS","TATASTEEL.NS"
]

results = []

# =========================
# SCAN
# =========================
for stock in stocks:
    try:
        data = yf.download(stock, period="1d", interval="5m", progress=False)

        if data.empty or len(data) < 20:
            continue

        close = data["Close"]
        volume = data["Volume"]

        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
            volume = volume.iloc[:, 0]

        latest = float(close.iloc[-1])
        old = float(close.iloc[-12])

        price_change = ((latest-old)/old)*100
        vol_ratio = float(volume.iloc[-1]) / float(volume.mean())
        rsi = calculate_rsi(close).iloc[-1]

        # =========================
        # 🔥 NEW: TREND CONFIRMATION
        # =========================
        ema20 = ema(close, 20).iloc[-1]
        ema50 = ema(close, 50).iloc[-1]

        if not (latest > ema20 > ema50):
            continue

        # =========================
        # 🔥 NEW: RSI FILTER
        # =========================
        if rsi > 65:   # avoid overbought
            continue

        # =========================
        # EXISTING FILTER
        # =========================
        if price_change < 0.7 or vol_ratio < 1.5 or rsi < 40:
            continue

        recent_high = float(close.tail(10).max())

        # 🔥 avoid weak breakout
        if latest < recent_high * 0.998:
            continue

        entry = recent_high
        entry_type = "Strong Breakout 🚀"

        if mode == "Swing":
            target = entry * 1.03
            stoploss = entry * 0.97
        else:
            target = entry * 1.015
            stoploss = entry * 0.992

        confidence = predict(price_change, vol_ratio, rsi, entry_type, "Bullish")

        if confidence != 50 and confidence < 60:
            continue

        results.append({
            "Stock": stock,
            "Entry": round(entry,2),
            "Target": round(target,2),
            "StopLoss": round(stoploss,2),
            "Confidence %": confidence,
            "Change": price_change,
            "Volume": vol_ratio
        })

    except:
        continue

df = pd.DataFrame(results)

if df.empty:
    st.warning("No high-quality trades")
    st.stop()

df = df.sort_values(by="Confidence %", ascending=False).head(3)

st.dataframe(df)

best = df.iloc[0]

st.success(f"""
BEST TRADE

{best['Stock']}
Entry: ₹{best['Entry']}
Target: ₹{best['Target']}
SL: ₹{best['StopLoss']}
Confidence: {best['Confidence %']}%
""")

send_telegram_alert(best)

save_trade(
    best["Stock"],
    best["Entry"],
    best["Target"],
    best["StopLoss"],
    best["Change"],
    best["Volume"],
    50,
    "Strong Breakout 🚀",
    "Bullish"
)

# =========================
# CHART
# =========================
st.subheader("📊 Candlestick Chart")

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

    st.plotly_chart(fig, use_container_width=True)

# =========================
# PERFORMANCE
# =========================
trades = update_trades()

if not trades.empty:
    st.dataframe(trades)
