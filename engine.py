import pandas as pd
import yfinance as yf
import os
import requests
import streamlit as st

FILE = "trades.csv"

def read_file():
    try:
        df = pd.read_csv(FILE)
        if df.empty:
            raise Exception
        return df
    except:
        df = pd.DataFrame(columns=[
            "Stock","Entry","Target","SL",
            "Change","Volume","RSI","Type","MarketTrend",
            "Status","Exit","PnL"
        ])
        df.to_csv(FILE, index=False)
        return df

def save_trade(stock, entry, target, sl, change, volume, rsi, entry_type, market_trend):
    df = read_file()

    new = pd.DataFrame([{
        "Stock": stock,
        "Entry": entry,
        "Target": target,
        "SL": sl,
        "Change": change,
        "Volume": volume,
        "RSI": rsi,
        "Type": entry_type,
        "MarketTrend": market_trend,
        "Status": "OPEN",
        "Exit": 0,
        "PnL": 0
    }])

    df = pd.concat([df, new], ignore_index=True)
    df.to_csv(FILE, index=False)

# =========================
# 🔔 TELEGRAM EXIT ALERT
# =========================
def send_exit_alert(stock, status, entry, exit_price, pnl):
    try:
        TOKEN = st.secrets["TOKEN"]
        CHAT_ID = st.secrets["CHAT_ID"]

        msg = f"""
📊 TRADE CLOSED

{stock}
Status: {status}
Entry: ₹{entry}
Exit: ₹{exit_price}
PnL: ₹{round(pnl,2)}
"""

        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg}
        )
    except:
        pass

# =========================
# UPDATE TRADES
# =========================
def update_trades():
    df = read_file()

    for i, row in df.iterrows():
        if row["Status"] == "OPEN":
            try:
                data = yf.download(row["Stock"], period="1d", interval="5m", progress=False)

                if data.empty:
                    continue

                close_data = data["Close"]

                if isinstance(close_data, pd.DataFrame):
                    close_data = close_data.iloc[:, 0]

                price = float(close_data.iloc[-1])

                # 🎯 TARGET HIT
                if price >= row["Target"]:
                    df.at[i,"Status"]="WIN"
                    df.at[i,"Exit"]=price
                    df.at[i,"PnL"]=price-row["Entry"]

                    send_exit_alert(
                        row["Stock"],
                        "TARGET HIT 🎯",
                        row["Entry"],
                        price,
                        price-row["Entry"]
                    )

                # 🛑 STOPLOSS HIT
                elif price <= row["SL"]:
                    df.at[i,"Status"]="LOSS"
                    df.at[i,"Exit"]=price
                    df.at[i,"PnL"]=price-row["Entry"]

                    send_exit_alert(
                        row["Stock"],
                        "STOPLOSS HIT 🛑",
                        row["Entry"],
                        price,
                        price-row["Entry"]
                    )

            except:
                continue

    df.to_csv(FILE,index=False)
    return df

def backtest(stock):
    return 60, 50
