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

# ✅ IMPORTANT FUNCTION (MISSING BEFORE)
def stock_ranking():
    df = read_file()

    df = df[df["Status"].isin(["WIN", "LOSS"])]

    if df.empty:
        return {}

    summary = df.groupby("Stock")["Status"].value_counts().unstack().fillna(0)

    summary["WinRate"] = summary.get("WIN", 0) / summary.sum(axis=1)

    return summary["WinRate"].to_dict()

def update_trades():
    df = read_file()

    for i, row in df.iterrows():
        if row["Status"] == "OPEN":
            try:
                data = yf.download(row["Stock"], period="1d", interval="5m", progress=False)

                if data.empty:
                    continue

                close = data["Close"]

                if isinstance(close, pd.DataFrame):
                    close = close.iloc[:, 0]

                price = float(close.iloc[-1])

                if price >= row["Target"]:
                    df.at[i,"Status"]="WIN"
                    df.at[i,"PnL"]=price-row["Entry"]

                elif price <= row["SL"]:
                    df.at[i,"Status"]="LOSS"
                    df.at[i,"PnL"]=price-row["Entry"]

            except:
                continue

    df.to_csv(FILE,index=False)
    return df
