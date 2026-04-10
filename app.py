import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

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

if nifty is not None and not nifty.empty:
    close = nifty["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]

    latest = float(close.iloc[-1])
    old = float(close.iloc[-12])

    change = ((latest - old) / old) * 100

    st.write(f"📉 NIFTY Trend (1hr): {round(change,2)}%")

    if change
