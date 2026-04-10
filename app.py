import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
from ml_model import predict
from engine import save_trade, update_trades, backtest

st.set_page_config(layout="wide")

st.title("📊 AI Trading Dashboard")

# =========================
# DARK UI
# =========================
st.markdown("""
<style>
body {
    background-color: #0e1117;
    color: white;
}
</style>
""", unsafe_allow_html=True)

# =========================
# REFRESH
# =========================
if st.button("🔄 Refresh"):
    st.rerun()

# =========================
# MARKET STATUS
# =========================
nifty = yf.download("^NSEI", period="1d", interval="5m", progress=False)

if nifty is None or nifty.empty:
    st.error("Market data not available")
    st.stop()

close = nifty["Close"]
if isinstance(close, pd.DataFrame):
    close = close.iloc[:, 0]

if len(close) < 12:
    st.warning("Not enough market data")
    st.stop()

latest = float(close.iloc[-1])
old = float(close.iloc[-12])
change = ((latest - old) / old) * 100

col1, col2, col3 = st.columns(3)
col1.metric("NIFTY Trend", f"{round(change,2)}%")
col2.metric("Market Status", "Bullish" if change > 0 else "Weak")
col3.metric("Strategy", "Active" if change > 0 else "Paused")

if change <= 0:
    st.warning("Market weak — avoid trading")
    st.stop()

# =========================
# RSI FUNCTION
# =========================
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = -delta.clip(upper=0).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# =========================
# STOCK LIST
# =========================
stocks = [
    "RELIANCE.NS","TCS.NS","INFY.NS","HDFCBANK.NS","ICICIBANK.NS",
    "SBIN.NS","ITC.NS","LT.NS","AXISBANK.NS","KOTAKBANK.NS",
    "JSWSTEEL.NS","TATASTEEL.NS","WIPRO.NS","TECHM.NS"
]

results = []

# =========================
# SCAN MARKET
# =========================
for stock in stocks:
    try:
        data = yf.download(stock, period="1d", interval="5m", progress=False)

        if data is None or data.empty or len(data) < 20:
            continue

        close = data["Close"][stock]
        volume = data["Volume"][stock]

        latest = float(close.iloc[-1])
        old = float(close.iloc[-12])

        price_change = ((latest - old) / old) * 100
        vol_ratio = float(volume.iloc[-1]) / float(volume.mean())
        rsi = calculate_rsi(close).iloc[-1]

        if price_change > 0.5 and vol_ratio > 1.5 and 40 < rsi < 70:

            recent_high = float(close.tail(10).max())
            recent_low = float(close.tail(10).min())

            if latest > recent_high * 0.995:
                entry_type = "Breakout 🚀"
                entry = recent_high
            else:
                entry_type = "Pullback 🔁"
                entry = recent_low

            target = round(entry * 1.015, 2)
            stoploss = round(entry * 0.992, 2)

            confidence = predict(
                price_change,
                vol_ratio,
                rsi,
                entry_type,
                "Bullish"
            )

            if confidence < 60:
                continue

            score = price_change + vol_ratio + (confidence / 10)

            results.append({
                "Stock": stock,
                "Entry": round(entry,2),
                "Target": target,
                "StopLoss": stoploss,
                "RSI": round(rsi,2),
                "Confidence %": confidence,
                "Type": entry_type,
                "Score": round(score,2),
                "Change": price_change,
                "Volume": vol_ratio
            })

    except:
        continue

df = pd.DataFrame(results)

if df.empty:
    st.warning("No high-quality trades found")
    st.stop()

df = df.sort_values(by="Score", ascending=False).head(5)

st.subheader("📈 Top AI Trade Setups")
st.dataframe(df)

best = df.iloc[0]

st.subheader("🏆 Best Trade")
st.success(f"""
Stock: {best['Stock']}
Entry: ₹{best['Entry']}
Target: ₹{best['Target']}
StopLoss: ₹{best['StopLoss']}
Confidence: {best['Confidence %']}%
Type: {best['Type']}
""")

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
    best["RSI"],
    best["Type"],
    "Bullish"
)

# =========================
# PERFORMANCE
# =========================
st.subheader("📊 Trade Performance")
trades = update_trades()

if not trades.empty:
    st.dataframe(trades)

# =========================
# PnL GRAPH
# =========================
st.subheader("📈 PnL Trend")

if not trades.empty:
    trades["Cumulative PnL"] = trades["PnL"].cumsum()
    fig = px.line(trades, y="Cumulative PnL")
    st.plotly_chart(fig)

# =========================
# BACKTEST
# =========================
st.subheader("🧠 Backtest")

acc, count = backtest(best["Stock"])
st.write(f"Accuracy: {acc}% | Trades: {count}")
