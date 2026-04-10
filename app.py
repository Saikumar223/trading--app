import streamlit as st
import pandas as pd
import yfinance as yf
from ml_model import predict

st.set_page_config(layout="wide")

st.title("📊 AI Trading Dashboard")

# =========================
# REFRESH
# =========================
if st.button("🔄 Refresh"):
    st.rerun()

# =========================
# MARKET STATUS
# =========================
nifty = yf.download("^NSEI", period="1d", interval="5m", progress=False)

close = nifty["Close"]
if isinstance(close, pd.DataFrame):
    close = close.iloc[:,0]

change = ((close.iloc[-1] - close.iloc[-12]) / close.iloc[-12]) * 100

col1, col2, col3 = st.columns(3)

col1.metric("NIFTY Trend", f"{round(change,2)}%")
col2.metric("Market Status", "Bullish" if change > 0 else "Weak")
col3.metric("Strategy", "Active" if change > 0 else "Paused")

if change <= 0:
    st.warning("Market weak — avoid trading")
    st.stop()

# =========================
# STOCK SCAN
# =========================
stocks = [
    "RELIANCE.NS","TCS.NS","INFY.NS","HDFCBANK.NS","ICICIBANK.NS",
    "SBIN.NS","ITC.NS","LT.NS","AXISBANK.NS"
]

results = []

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = -delta.clip(upper=0).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

for stock in stocks:
    try:
        data = yf.download(stock, period="1d", interval="5m", progress=False)

        if data.empty or len(data) < 20:
            continue

        close = data["Close"][stock]
        volume = data["Volume"][stock]

        latest = float(close.iloc[-1])
        old = float(close.iloc[-12])

        price_change = ((latest - old) / old) * 100
        vol_ratio = float(volume.iloc[-1]) / float(volume.mean())

        rsi = calculate_rsi(close).iloc[-1]

        if price_change > 0.5 and vol_ratio > 1.5 and 40 < rsi < 70:

            # ML prediction
            confidence = predict(price_change, vol_ratio, rsi)

            # Entry logic
            recent_high = float(close.tail(10).max())
            recent_low = float(close.tail(10).min())

            if latest > recent_high * 0.995:
                entry_type = "Breakout 🚀"
                entry = recent_high
            else:
                entry_type = "Pullback 🔁"
                entry = recent_low

            target = round(entry * 1.015,2)
            stoploss = round(entry * 0.992,2)

            score = price_change + vol_ratio + confidence/10

            results.append({
                "Stock": stock,
                "Entry": round(entry,2),
                "Target": target,
                "StopLoss": stoploss,
                "RSI": round(rsi,2),
                "Confidence %": confidence,
                "Type": entry_type,
                "Score": round(score,2)
            })

    except:
        continue

df = pd.DataFrame(results).sort_values(by="Score", ascending=False).head(5)

# =========================
# DISPLAY TRADES
# =========================
st.subheader("📈 Top AI Trade Setups")
st.dataframe(df)

# =========================
# BEST TRADE HIGHLIGHT
# =========================
if not df.empty:
    best = df.iloc[0]

    st.subheader("🏆 Best Trade")

    st.success(
        f"""
Stock: {best['Stock']}

Entry: ₹{best['Entry']}
Target: ₹{best['Target']}
StopLoss: ₹{best['StopLoss']}

Confidence: {best['Confidence %']}%
Type: {best['Type']}
"""
    )

# =========================
# PORTFOLIO
# =========================
st.subheader("💼 Portfolio")

capital = 1000
risk = 0.02

portfolio_data = []

for i, row in df.iterrows():
    risk_amt = capital * risk
    qty = int(risk_amt / (row["Entry"] - row["StopLoss"]))

    portfolio_data.append({
        "Stock": row["Stock"],
        "Qty": qty,
        "Investment": round(qty * row["Entry"],2)
    })

portfolio_df = pd.DataFrame(portfolio_data)

st.dataframe(portfolio_df)
