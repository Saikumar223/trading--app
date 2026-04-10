import streamlit as st
from engine import performance_summary

st.set_page_config(layout="wide")
st.title("📊 AI Trading Dashboard")

st.subheader("📈 Performance")

perf = performance_summary()

st.write(f"💰 Total PnL: ₹{perf['PnL']}")
st.write(f"🎯 Accuracy: {perf['Accuracy']}%")

st.info("Bot is running via automation. Check Telegram for signals.")
