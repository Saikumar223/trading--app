import streamlit as st
import yfinance as yf
import pandas as pd
import requests

st.set_page_config(page_title="Trading App", layout="wide")

st.title("📊 Smart Trading App (₹1000 Strategy)")

# =========================
# TELEGRAM FUNCTION
# =========================
def send_telegram(msg):
    token = st.secrets["TELEGRAM_TOKEN"]
    chat_id = st.secrets["CHAT_ID"]

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {"chat_id": chat_id, "text": msg}

    try:
        requests.post(url, data=data)
    except:
        pass

# =========================
# REFRESH
# =========================
if st.button("🔄 Refresh"):
    st.rerun()

# =========================
# MARKET CHECK
# =========================
nifty = yf.download("^NSEI", period="1d", interval="5m", progress=False)

market_ok = False

if not nifty.empty:
    close = nifty["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:,0]

    change = ((close.iloc[-1] - close.iloc[-12]) / close.iloc[-12]) * 100

    st.write(f"📉 NIFTY Trend: {round(change,2)}%")

    if change > 0:
        st.success("Market Bullish ✅")
        market_ok = True
    else:
        st.warning("Market Weak ⚠️")

if not market_ok:
    st.stop()

# =========================
# STOCK SCAN
# =========================
stocks = ["IRFC.NS","NBCC.NS","PNB.NS","IDFCFIRSTB.NS"]

results = []

for stock in stocks:
    try:
        data = yf.download(stock, period="1d", interval="5m", progress=False)

        if data.empty:
            continue

        close = data["Close"][stock]

        latest = float(close.iloc[-1])
        old = float(close.iloc[-12])

        change = ((latest - old) / old) * 100

        if latest > 500:
            continue

        if change > 0.4:
            entry = round(latest,2)
            target = round(entry * 1.015,2)
            stoploss = round(entry * 0.992,2)

            score = change

            results.append({
                "Stock": stock,
                "Entry": entry,
                "Target": target,
                "Stoploss": stoploss,
                "Score": round(score,2)
            })

    except:
        continue

# =========================
# OUTPUT + ALERT
# =========================
if results:
    df = pd.DataFrame(results)
    best = df.sort_values(by="Score", ascending=False).iloc[0]

    st.subheader("🏆 Best Trade")
    st.success(best.to_dict())

    # 🔥 SEND TELEGRAM ALERT
    msg = f"""
📈 NEW TRADE ALERT

Stock: {best['Stock']}
Entry: ₹{best['Entry']}
Target: ₹{best['Target']}
StopLoss: ₹{best['Stoploss']}
"""

    send_telegram(msg)

    st.subheader("📊 All Trades")
    st.dataframe(df)

else:
    st.warning("No trades found")
