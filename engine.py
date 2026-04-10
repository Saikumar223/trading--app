import pandas as pd
import yfinance as yf
import os

FILE = "trades.csv"

# =========================
# SAFE READ CSV
# =========================
def read_file():
    try:
        df = pd.read_csv(FILE)
        if df.empty or len(df.columns) == 0:
            raise ValueError("Empty file")
        return df
    except:
        df = pd.DataFrame(columns=[
            "Stock","Entry","Target","SL","Status","Exit","PnL"
        ])
        df.to_csv(FILE, index=False)
        return df

# =========================
# SAVE TRADE
# =========================
def save_trade(stock, entry, target, sl):
    df = read_file()

    # avoid duplicate open trades
    if not ((df["Stock"] == stock) & (df["Status"] == "OPEN")).any():

        new_trade = pd.DataFrame([{
            "Stock": stock,
            "Entry": entry,
            "Target": target,
            "SL": sl,
            "Status": "OPEN",
            "Exit": 0,
            "PnL": 0
        }])

        df = pd.concat([df, new_trade], ignore_index=True)
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

                price = float(data["Close"][row["Stock"]].iloc[-1])

                if price >= row["Target"]:
                    df.at[i, "Status"] = "WIN"
                    df.at[i, "Exit"] = price
                    df.at[i, "PnL"] = price - row["Entry"]

                elif price <= row["SL"]:
                    df.at[i, "Status"] = "LOSS"
                    df.at[i, "Exit"] = price
                    df.at[i, "PnL"] = price - row["Entry"]

            except:
                continue

    df.to_csv(FILE, index=False)
    return df

# =========================
# BACKTEST
# =========================
def backtest(stock):
    try:
        data = yf.download(stock, period="5d", interval="5m", progress=False)

        if data.empty:
            return 0, 0

        close = data["Close"][stock]

        wins = 0
        total = 0

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

        acc = (wins / total * 100) if total > 0 else 0

        return round(acc,2), total

    except:
        return 0, 0
