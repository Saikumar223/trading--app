import pandas as pd
import yfinance as yf
import os

FILE = "trades.csv"

def read_file():
    if not os.path.exists(FILE):
        df = pd.DataFrame(columns=[
            "Stock","Entry","Target","SL",
            "Status","Exit","PnL"
        ])
        df.to_csv(FILE, index=False)
        return df

    try:
        df = pd.read_csv(FILE)
        return df
    except:
        return pd.DataFrame()

# =========================
# SAVE TRADE
# =========================
def save_trade(stock, entry, target, sl):
    df = read_file()

    new = pd.DataFrame([{
        "Stock": stock,
        "Entry": entry,
        "Target": target,
        "SL": sl,
        "Status": "OPEN",
        "Exit": 0,
        "PnL": 0
    }])

    df = pd.concat([df, new], ignore_index=True)
    df.to_csv(FILE, index=False)

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

                close = data["Close"]
                if hasattr(close, "columns"):
                    close = close.iloc[:, 0]

                price = float(close.iloc[-1])

                if price >= row["Target"]:
                    df.at[i,"Status"]="WIN"
                    df.at[i,"Exit"]=price
                    df.at[i,"PnL"]=price-row["Entry"]

                elif price <= row["SL"]:
                    df.at[i,"Status"]="LOSS"
                    df.at[i,"Exit"]=price
                    df.at[i,"PnL"]=price-row["Entry"]

            except:
                continue

    df.to_csv(FILE,index=False)
    return df

# =========================
# STOCK RANKING
# =========================
def stock_ranking():
    df = read_file()
    df = df[df["Status"].isin(["WIN","LOSS"])]

    if df.empty:
        return {}

    summary = df.groupby("Stock")["Status"].value_counts().unstack().fillna(0)
    summary["WinRate"] = summary.get("WIN",0) / summary.sum(axis=1)

    return summary["WinRate"].to_dict()

# =========================
# PERFORMANCE
# =========================
def performance_summary():
    df = read_file()
    closed = df[df["Status"].isin(["WIN","LOSS"])]

    if closed.empty:
        return {"PnL":0, "Accuracy":0}

    pnl = closed["PnL"].sum()
    acc = (closed["Status"]=="WIN").mean()*100

    return {
        "PnL": round(pnl,2),
        "Accuracy": round(acc,2)
    }
