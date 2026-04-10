import streamlit as st
import pandas as pd
import yfinance as yf
from ml_model import predict
from engine import save_trade, update_trades, backtest

st.set_page_config(layout="wide")

st.title("📊 AI Trading Dashboard")

# =========================
# REFRESH
# =========================
if st.button("🔄 Refresh"):
    st.rerun()

# =========================
# MARKET STATUS (SAFE)
# =========================
nifty = yf.download("^NSEI", period="1d", interval="5m", progress=False)

if nifty is None or nifty.empty:
    st.error("Market data not available")
    st.stop()

close = nifty["Close"]

if isinstance(close, pd.DataFrame):
    close = close.iloc[:, 0]

if close is None or len(close) < 12:
    st.warning("Not enough market data yet. Try after some time.")
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
    "BAJFINANCE.NS","BHARTIARTL.NS","ASIANPAINT.NS","MARUTI.NS",
    "TITAN.NS","SUNPHARMA.NS","ONGC.NS","NTPC.NS","POWERGRID.NS",
    "COALINDIA.NS","JSWSTEEL.NS","TATASTEEL.NS","WIPRO.NS",
    "TECHM.NS","HCLTECH.NS","DRREDDY.NS","CIPLA.NS"
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

        # 🔥 FILTERS
        if price_change > 0.5 and vol_ratio > 1.5 and 40 < rsi < 70:

            confidence = predict(price_change, vol_ratio, rsi)

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

            score = price_change + vol_ratio + (confidence / 10)

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

df = pd.DataFrame(results)

if df.empty:
    st.warning("No high-quality trades found")
    st.stop()

df = df.sort_values(by="Score", ascending=False).head(5)

# =========================
# DISPLAY TRADES
# =========================
st.subheader("📈 Top AI Trade Setups")
st.dataframe(df)

# =========================
# BEST TRADE
# =========================
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
# SAVE TRADE
# =========================
save_trade(best["Stock"], best["Entry"], best["Target"], best["StopLoss"])

# =========================
# PORTFOLIO
# =========================
st.subheader("💼 Portfolio Allocation")

capital = 1000
risk_per_trade = 0.02

portfolio = []

for i, row in df.iterrows():
    try:
        risk_amt = capital * risk_per_trade
        risk_per_share = abs(row["Entry"] - row["StopLoss"])

        if risk_per_share == 0:
            continue

        qty = int(risk_amt / risk_per_share)

        portfolio.append({
            "Stock": row["Stock"],
            "Qty": qty,
            "Investment": round(qty * row["Entry"], 2)
        })

    except:
        continue

portfolio_df = pd.DataFrame(portfolio)

st.dataframe(portfolio_df)

# =========================
# TRADE PERFORMANCE
# =========================
st.subheader("📊 Trade Performance")

trades = update_trades()

if not trades.empty:
    total = len(trades)
    wins = len(trades[trades["Status"] == "WIN"])
    losses = len(trades[trades["Status"] == "LOSS"])
    pnl = trades["PnL"].sum()

    accuracy = (wins / total * 100) if total > 0 else 0

    st.write(f"Total Trades: {total}")
    st.write(f"Wins: {wins}")
    st.write(f"Losses: {losses}")
    st.write(f"Accuracy: {round(accuracy,2)}%")
    st.write(f"Total PnL: ₹{round(pnl,2)}")

    st.dataframe(trades)

# =========================
# BACKTEST
# =========================
st.subheader("🧠 Backtest Result")

acc, count = backtest(best["Stock"])

st.write(f"Backtest Accuracy: {acc}%")
st.write(f"Trades Tested: {count}")
