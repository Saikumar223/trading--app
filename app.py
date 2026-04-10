import yfinance as yf
import requests
import json
import os

TOKEN = "YOUR_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"

FILE = "last_alert.json"

# =========================
# TELEGRAM FUNCTION
# =========================
def send(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# =========================
# LOAD LAST ALERT
# =========================
def load_last():
    if os.path.exists(FILE):
        with open(FILE, "r") as f:
            return json.load(f)
    return {}

# =========================
# SAVE ALERT
# =========================
def save_last(data):
    with open(FILE, "w") as f:
        json.dump(data, f)

# =========================
# STOCK SCAN
# =========================
stocks = ["IRFC.NS","NBCC.NS","PNB.NS","IDFCFIRSTB.NS"]

best_stock = None
best_score = 0
best_data = {}

for stock in stocks:
    try:
        data = yf.download(stock, period="1d", interval="5m", progress=False)

        if data.empty:
            continue

        close = data["Close"][stock]

        latest = float(close.iloc[-1])
        old = float(close.iloc[-12])

        change = ((latest - old) / old) * 100

        if latest > 500:
            continue

        if change > best_score:
            best_score = change

            entry = round(latest,2)
            target = round(entry * 1.015,2)
            stoploss = round(entry * 0.992,2)

            best_data = {
                "Stock": stock,
                "Entry": entry,
                "Target": target,
                "Stoploss": stoploss
            }

    except:
        continue

# =========================
# DUPLICATE CHECK
# =========================
last = load_last()

if best_data:

    if best_data != last:
        # NEW ALERT
        msg = f"""
📈 NEW TRADE ALERT

Stock: {best_data['Stock']}
Entry: ₹{best_data['Entry']}
Target: ₹{best_data['Target']}
StopLoss: ₹{best_data['Stoploss']}
"""

        send(msg)
        save_last(best_data)

    else:
        print("Duplicate alert skipped")

else:
    print("No trade found")
