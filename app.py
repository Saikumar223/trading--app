import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import os

st.set_page_config(page_title="Trading App", layout="wide")

st.title("📊 Smart Trading App (₹1000 Strategy)")

# =========================
# FILE FOR TRADE TRACKING
# =========================
TRADE_FILE = "trades.csv"

if not os.path.exists(TRADE_FILE):
    pd.DataFrame(columns=[
        "Stock","Entry","Target","Stoploss","Status","Exit","PnL"
    ]).to_csv(TRADE_FILE, index=False)

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
        volume = data["Volume"][stock]

        latest = float(close.iloc[-1])
        old = float(close.iloc[-12])

        change = ((latest - old) / old) * 100

        if latest > 500:
            continue

        if change > 0.4:
            entry = latest
            target = round(entry * 1.015,2)
            stoploss = round(entry * 0.992,2)

            volume_ratio = float(volume.iloc[-1]) / float(volume.mean())
            score = (change * 0.6) + (volume_ratio * 0.4)

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
# OUTPUT
# =========================
if results:
    df = pd.DataFrame(results)
    best = df.sort_values(by="Score", ascending=False).iloc[0]

    st.subheader("🏆 Best Trade")

    st.success(best.to_dict())

    # =========================
    # SAVE TRADE (NEW)
    # =========================
    trades = pd.read_csv(TRADE_FILE)

    if not ((trades["Stock"] == best["Stock"]) & (trades["Status"] == "OPEN")).any():
        new_trade = pd.DataFrame([{
            "Stock": best["Stock"],
            "Entry": best["Entry"],
            "Target": best["Target"],
            "Stoploss": best["Stoploss"],
            "Status": "OPEN",
            "Exit": 0,
            "PnL": 0
        }])

        trades = pd.concat([trades, new_trade])
        trades.to_csv(TRADE_FILE, index=False)

    # =========================
    # UPDATE TRADES
    # =========================
    for i, row in trades.iterrows():
        if row["Status"] == "OPEN":
            data = yf.download(row["Stock"], period="1d", interval="5m", progress=False)

            if not data.empty:
                price = float(data["Close"][row["Stock"]].iloc[-1])

                if price >= row["Target"]:
                    trades.at[i, "Status"] = "WIN"
                    trades.at[i, "Exit"] = price
                    trades.at[i, "PnL"] = price - row["Entry"]

                elif price <= row["Stoploss"]:
                    trades.at[i, "Status"] = "LOSS"
                    trades.at[i, "Exit"] = price
                    trades.at[i, "PnL"] = price - row["Entry"]

    trades.to_csv(TRADE_FILE, index=False)

    # =========================
    # STATS
    # =========================
    total = len(trades)
    wins = len(trades[trades["Status"] == "WIN"])
    losses = len(trades[trades["Status"] == "LOSS"])
    pnl = trades["PnL"].sum()

    accuracy = (wins / total * 100) if total > 0 else 0

    st.subheader("📊 Performance")

    st.write(f"Total Trades: {total}")
    st.write(f"Wins: {wins}")
    st.write(f"Losses: {losses}")
    st.write(f"Accuracy: {round(accuracy,2)}%")
    st.write(f"Total PnL: ₹{round(pnl,2)}")

    st.subheader("📋 Trade History")
    st.dataframe(trades)

else:
    st.warning("No trades found")
