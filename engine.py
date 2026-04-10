import pandas as pd
import yfinance as yf
import os

FILE = "trades.csv"

# =========================
# SAVE TRADE
# =========================
def save_trade(stock, entry, target, sl):
    trade = pd.DataFrame([{
        "Stock": stock,
        "Entry": entry,
        "Target": target,
        "SL": sl,
        "Status": "OPEN",
        "Exit": 0,
        "PnL": 0
    }])

    if os.path.exists(FILE):
        df = pd.read_csv(FILE)
        df = pd.concat([df, trade])
    else:
        df = trade

    df.to_csv(FILE, index=False)

# =========================
# UPDATE TRADES
# =========================
def update_trades():
    if not os.path.exists(FILE):
        return pd.DataFrame()

    df = pd.read_csv(FILE)

    for i, row in df.iterrows():
        if row["Status"] == "OPEN":
            data = yf.download(row["Stock"], period="1d", interval="5m", progress=False)

            if data.empty:
                continue

            price = float(data["Close"][row["Stock"]].iloc[-1])

            if price >= row["Target"]:
                df.at[i, "Status"] = "WIN"
                df.at[i, "Exit"] = price
                df.at[i, "PnL"] = price - row["Entry"]

            elif price <= row["SL"]:
                df.at[i, "Status"] = "LOSS"
                df.at[i, "Exit"] = price
                df.at[i, "PnL"] = price - row["Entry"]

    df.to_csv(FILE, index=False)
    return df

# =========================
# BACKTEST
# =========================
def backtest(stock):
    data = yf.download(stock, period="5d", interval="5m", progress=False)

    if data.empty:
        return 0,0

    wins = 0
    total = 0

    close = data["Close"][stock]

    for i in range(20, len(close)-5):
        entry = close.iloc[i]
        target = entry * 1.015
        sl = entry * 0.992

        future = close.iloc[i:i+5]

        if future.max() >= target:
            wins += 1
        elif future.min() <= sl:
            pass

        total += 1

    accuracy = (wins / total * 100) if total > 0 else 0

    return round(accuracy,2), total
