import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Trading App", layout="wide")

st.title("📊 Smart Trading App (₹1000 Strategy)")

# Refresh
if st.button("🔄 Refresh"):
    st.rerun()

st.write("Running market analysis...\n")

# =========================
# MARKET CHECK
# =========================
nifty = yf.download("^NSEI", period="1d", interval="5m", progress=False)

market_ok = False
market_reason = ""

if nifty is not None and not nifty.empty:
    close = nifty["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]

    latest = float(close.iloc[-1])
    old = float(close.iloc[-12])

    change = ((latest - old) / old) * 100

    st.write(f"📉 NIFTY Trend (1hr): {round(change,2)}%")

    if change > 0:
        st.success("Market is Bullish ✅")
        market_ok = True
        market_reason = "Market is trending upward"
    else:
        st.warning("Market is Weak ⚠️")
        market_reason = "Market is weak"

if not market_ok:
    st.error("🚫 No trades due to weak market")
    st.stop()

# =========================
# STOCK SCAN
# =========================
stocks = ["IRFC.NS","NBCC.NS","PNB.NS","IDFCFIRSTB.NS"]

results = []

for stock in stocks:
    try:
        data = yf.download(stock, period="1d", interval="5m", progress=False)

        if data is None or data.empty:
            continue

        close = data["Close"][stock]
        volume = data["Volume"][stock]

        latest_close = float(close.iloc[-1])
        old_close = float(close.iloc[-12])

        latest_volume = float(volume.iloc[-1])
        avg_volume = float(volume.mean())

        price_change = ((latest_close - old_close) / old_close) * 100

        if latest_close > 500:
            continue

        if price_change > 0.4:

            volume_ratio = latest_volume / avg_volume
            score = (price_change * 0.6) + (volume_ratio * 0.4)

            # Entry Logic
            recent_high = float(close.tail(10).max())
            recent_low = float(close.tail(10).min())

            if volume_ratio > 5:
                entry_type = "Wait ⚠️"
                entry_msg = "High volume spike – avoid immediate entry"
            elif latest_close > recent_high * 0.995:
                entry_type = "Breakout 🚀"
                entry_msg = f"Buy above ₹{round(recent_high,2)}"
            else:
                entry_type = "Pullback 🔁"
                entry_msg = f"Buy near ₹{round(recent_low,2)}"

            results.append({
                "Stock": stock,
                "Price": round(latest_close,2),
                "Score": round(score,2),
                "Entry": entry_type,
                "Note": entry_msg
            })

    except:
        continue

# =========================
# OUTPUT
# =========================
if results:
    df = pd.DataFrame(results)
    best = df.sort_values(by="Score", ascending=False).iloc[0]

    st.subheader("🏆 Best Trade")
    st.success(best.to_dict())

    st.subheader("📊 All Trades")
    st.dataframe(df)

else:
    st.warning("No strong trades found")
