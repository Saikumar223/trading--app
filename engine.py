import pandas as pd
import os

TRADES_FILE = "trades.csv"
CAPITAL_FILE = "capital.csv"

def log_trade(stock, entry, exit_price, pnl):

    result = "WIN" if pnl > 0 else "LOSS"

    new = pd.DataFrame([{
        "Stock": stock,
        "Entry": entry,
        "Exit": exit_price,
        "PnL": pnl,
        "Status": result
    }])

    if not os.path.exists(TRADES_FILE):
        new.to_csv(TRADES_FILE, index=False)
    else:
        df = pd.read_csv(TRADES_FILE)
        df = pd.concat([df, new], ignore_index=True)
        df.to_csv(TRADES_FILE, index=False)

def update_capital(pnl):

    today = pd.Timestamp.today().date()

    if not os.path.exists(CAPITAL_FILE):
        df = pd.DataFrame([{"Date": today, "Capital": 1000 + pnl}])
    else:
        df = pd.read_csv(CAPITAL_FILE)
        last_cap = df.iloc[-1]["Capital"]
        df = pd.concat([df, pd.DataFrame([{"Date": today, "Capital": last_cap + pnl}])])

    df.to_csv(CAPITAL_FILE, index=False)

def stock_ranking():
    return {}
