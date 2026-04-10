import yfinance as yf
import requests

TOKEN = "YOUR_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"

def send(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

stocks = ["IRFC.NS","NBCC.NS","PNB.NS","IDFCFIRSTB.NS"]

best_stock = None
best_score = 0

for stock in stocks:
    try:
        data = yf.download(stock, period="1d", interval="5m", progress=False)
        if data.empty:
            continue

        close = data["Close"][stock]

        latest = float(close.iloc[-1])
        old = float(close.iloc[-12])

        change = ((latest - old) / old) * 100

        if change > best_score:
            best_score = change
            best_stock = (stock, latest)

    except:
        continue

if best_stock:
    msg = f"""
📊 AUTO TRADE ALERT

Stock: {best_stock[0]}
Price: ₹{round(best_stock[1],2)}
Move: {round(best_score,2)}%
"""
    send(msg)
