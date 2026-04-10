import pandas as pd
import yfinance as yf
import os

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

def update_trades():
    df = read_file()

    for i, row in df.iterrows():
        if row["Status"] == "OPEN":
            try:
                data = yf.download(row["Stock"], period="1d", interval="5m", progress=False)

                if data.empty:
                    continue

                # ✅ FIXED: handle both single & multi-column
                close_data = data["Close"]

                if isinstance(close_data, pd.DataFrame):
                    close_data = close_data.iloc[:, 0]

                price = float(close_data.iloc[-1])

                if price >= row["Target"]:
                    df.at[i,"Status"]="WIN"
                    df.at[i,"PnL"]=price-row["Entry"]
                    df.at[i,"Exit"]=price

                elif price <= row["SL"]:
                    df.at[i,"Status"]="LOSS"
                    df.at[i,"PnL"]=price-row["Entry"]
                    df.at[i,"Exit"]=price

            except:
                continue

    df.to_csv(FILE,index=False)
    return df

def backtest(stock):
    return 60, 50
