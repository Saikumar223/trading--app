import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import requests
import hashlib
from ml_model import predict
from engine import save_trade, update_trades, backtest

st.set_page_config(layout="wide")

st.title("📊 AI Trading Dashboard")

mode = st.selectbox("Select Mode", ["Intraday", "Swing"])

# =========================
# REFRESH
# =========================
if st.button("🔄 Refresh"):
    st.rerun()

# =========================
# TELEGRAM ALERT FUNCTION
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
            st.success("📩 Alert Sent")

    except:
        pass

# =========================
# MARKET STATUS
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

col1, col2, col3 = st.columns(3)
col1.metric("NIFTY Trend", f"{round(change,2)}%")
col2.metric("Market", "Bullish" if change > 0 else "Weak")
col3.metric("Mode", mode)

if change <= 0:
    st.warning("Market weak — avoid trading")
    st.stop()

# =========================
# RSI + EMA
# =========================
def calculate_rsi(series):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / loss
    return 100 - (100/(1+rs))

def ema(series):
    return series.ewm(span=20).mean()

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

        close = data["Close"][stock]
        volume = data["Volume"][stock]

        latest = float(close.iloc[-1])
        old = float(close.iloc[-12])

        price_change = ((latest-old)/old)*100
        vol_ratio = float(volume.iloc[-1]) / float(volume.mean())
        rsi = calculate_rsi(close).iloc[-1]

        if latest < ema(close).iloc[-1]:
            continue

        if price_change < 0.7 or vol_ratio < 1.5 or not (40 < rsi < 70):
            continue

        entry = float(close.tail(10).max())
        entry_type = "Breakout 🚀"

        if mode == "Swing":
            target = entry * 1.03
            stoploss = entry * 0.97
        else:
            target = entry * 1.015
            stoploss = entry * 0.992

        confidence = predict(
            price_change,
            vol_ratio,
            rsi,
            entry_type,
            "Bullish"
        )

        # smart filter
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
    st.warning("No trades found")
    st.stop()

df = df.sort_values(by="Confidence %", ascending=False).head(3)

st.subheader("📈 Trade Setups")
st.dataframe(df)

# =========================
# BEST TRADE
# =========================
best = df.iloc[0]

st.subheader("🏆 Best Trade")

st.success(f"""
📌 {best['Stock']}

Entry: ₹{best['Entry']}
Target: ₹{best['Target']}
StopLoss: ₹{best['StopLoss']}

Confidence: {best['Confidence %']}%
""")

# =========================
# TELEGRAM AUTO ALERT
# =========================
send_telegram_alert(best)

# =========================
# SAVE TRADE
# =========================
save_trade(
    best["Stock"],
    best["Entry"],
    best["Target"],
    best["StopLoss"],
    best["Change"],
    best["Volume"],
    50,
    "Breakout 🚀",
    "Bullish"
)

# =========================
# LIVE CHART
# =========================
st.subheader("📊 Live Chart")

chart = yf.download(best["Stock"], period="1d", interval="5m", progress=False)

if not chart.empty:

    close_data = chart["Close"]

    if isinstance(close_data, pd.DataFrame):
        close_data = close_data.iloc[:, 0]

    chart_df = close_data.reset_index()
    chart_df.columns = ["Time", "Price"]

    fig = px.line(chart_df, x="Time", y="Price", title=best["Stock"])

    # ✅ ADD IT HERE
    fig.update_layout(template="plotly_dark")

    st.plotly_chart(fig, use_container_width=True)

# =========================
# PERFORMANCE
# =========================
st.subheader("📊 Performance")

trades = update_trades()

if not trades.empty:
    st.dataframe(trades)

# =========================
# PNL GRAPH
# =========================
st.subheader("📈 PnL Trend")

if not trades.empty:
    trades["Cumulative PnL"] = trades["PnL"].cumsum()
    fig = px.line(trades, y="Cumulative PnL", title="Profit Curve")
    st.plotly_chart(fig)

# =========================
# BACKTEST
# =========================
st.subheader("🧠 Backtest")

acc, count = backtest(best["Stock"])
st.write(f"Accuracy: {acc}% | Trades: {count}")
