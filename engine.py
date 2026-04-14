import pandas as pd
import os

TRADES_FILE = "trades.csv"
CAPITAL_FILE = "capital.csv"

# =========================
# TRADE LOG
# =========================
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

# =========================
# CAPITAL TRACKING
# =========================
def update_capital(pnl):

    today = pd.Timestamp.today().date()

    if not os.path.exists(CAPITAL_FILE):
        df = pd.DataFrame([{
            "Date": today,
            "Capital": 1000 + pnl
        }])
    else:
        df = pd.read_csv(CAPITAL_FILE)
        last_cap = df.iloc[-1]["Capital"]

        new_row = pd.DataFrame([{
            "Date": today,
            "Capital": last_cap + pnl
        }])

        df = pd.concat([df, new_row], ignore_index=True)

    df.to_csv(CAPITAL_FILE, index=False)

# =========================
# STOCK RANKING (SAFE)
# =========================
def stock_ranking():
    return {}

# =========================
# PERFORMANCE SUMMARY
# =========================
def performance_summary():

    if not os.path.exists(TRADES_FILE):
        return {
            "PnL": 0,
            "Wins": 0,
            "Losses": 0,
            "Accuracy": 0,
            "Total Trades": 0
        }

    df = pd.read_csv(TRADES_FILE)

    if df.empty:
        return {
            "PnL": 0,
            "Wins": 0,
            "Losses": 0,
            "Accuracy": 0,
            "Total Trades": 0
        }

    wins = len(df[df["Status"] == "WIN"])
    losses = len(df[df["Status"] == "LOSS"])
    total = len(df)

    accuracy = (wins / total * 100) if total else 0
    total_pnl = df["PnL"].sum()

    return {
        "PnL": round(total_pnl, 2),
        "Wins": wins,
        "Losses": losses,
        "Accuracy": round(accuracy, 2),
        "Total Trades": total
    }
