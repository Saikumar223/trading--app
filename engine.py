import pandas as pd
import os

FILE = "trades.csv"

def log_trade(stock, entry, exit_price, pnl):

    result = "WIN" if pnl > 0 else "LOSS"

    new = pd.DataFrame([{
        "Stock": stock,
        "Entry": entry,
        "Exit": exit_price,
        "PnL": pnl,
        "Status": result
    }])

    if not os.path.exists(FILE):
        new.to_csv(FILE, index=False)
    else:
        df = pd.read_csv(FILE)
        df = pd.concat([df, new], ignore_index=True)
        df.to_csv(FILE, index=False)

def stock_ranking():
    if not os.path.exists(FILE):
        return {}

    df = pd.read_csv(FILE)
    df = df[df["Status"].isin(["WIN","LOSS"])]

    if df.empty:
        return {}

    summary = df.groupby("Stock")["Status"].value_counts().unstack().fillna(0)
    summary["WinRate"] = summary.get("WIN",0)/summary.sum(axis=1)

    return summary["WinRate"].to_dict()
