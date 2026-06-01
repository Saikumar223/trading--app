import yfinance as yf
import requests
import os
from datetime import datetime
import pytz

from database import (
    init_db,
    get_capital,
    add_trade,
    get_active_trades,
    close_trade
)

# Initialize local SQLite database
init_db()

# Secure credentials from GitHub Secrets
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")  # Add this to your GitHub Secrets
MAX_TRADES = 3

def send(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg}
        )
    except:
        pass

def fetch_news_sentiment(company_name):
    """
    Fetches live headlines and calculates a weight-based sentiment score.
    """
    if not NEWS_API_KEY:
        return 0  # Neutral if no API key is provided
        
    try:
        # Fetching recent news headlines matching the company name
        url = f"https://newsapi.org/v2/everything?q={company_name}&sortBy=publishedAt&pageSize=3&apiKey={NEWS_API_KEY}"
        response = requests.get(url, timeout=5).json()
        articles = response.get("articles", [])
        
        score = 0
        heavy_negative = ["fraud", "probe", "lawsuit", "investigation", "scam"]
        mild_negative = ["deficit", "drop", "fall", "missed"]
        positive_words = ["profit", "growth", "expansion", "record", "win"]
        
        for art in articles:
            title = art.get("title", "").lower()
            # ⚠️ Heavy negative news blocks the trade (-2 points)
            if any(w in title for w in heavy_negative):
                score -= 2
            # 📉 Mild negative news lowers the score (-1 point)
            elif any(w in title for w in mild_negative):
                score -= 1
            # 📈 Positive news boosts the score (+1 point)
            elif any(w in title for w in positive_words):
                score += 1
        return score
    except:
        return 0  # Fallback to neutral if API fails

def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def qty(entry, sl):
    capital = get_capital()
    allocated_cash = capital * 0.25
    return int(allocated_cash / entry)

# Track using Indian Standard Time (IST)
ist = datetime.now(pytz.timezone("Asia/Kolkata"))
hour = ist.hour

# Watchlist mapped to search terms for the News API
WATCHLIST = {
    "SBIN.NS": "State Bank of India",
    "INFY.NS": "Infosys",
    "HDFCBANK.NS": "HDFC Bank",
    "RELIANCE.NS": "Reliance Industries"
}

# ==========================================
# 🌅 PHASE 1: OPENING ANALYSIS (9:00 AM - 12:00 PM)
# ==========================================
if 9 <= hour < 12:
    send("🌅 Bot starting morning analysis with live news verification...")
    active_trades = get_active_trades()
    active_stocks = [t["stock"] for t in active_trades]
    
    results = []
    for s, search_name in WATCHLIST.items():
        if s in active_stocks:
            continue
            
        try:
            d = yf.download(s, period="1d", interval="5m", progress=False)
            if d.empty:
                continue
                
            c = d["Close"]
            v = d["Volume"]
            if hasattr(c, "columns"):
                c = c.iloc[:, 0]
                v = v.iloc[:, 0]
                
            latest = c.iloc[-1]
            vr = v.iloc[-1] / v.mean()
            r = rsi(c).iloc[-1]
            e20 = ema(c, 20).iloc[-1]
            
            # --- WEIGHT-BASED SCORING ENGINE ---
            trading_score = 0
            
            # 1. Technical Chart Check (+2 Points for finding a dip)
            recent_low = c.tail(15).min()
            if (latest < e20) and (recent_low <= latest <= (recent_low * 1.01)):
                trading_score += 2
                
            # 2. Volume & RSI Filters
            if vr < 1.1 or not (35 < r < 75):
                continue
                
            # 3. Live News Sentiment Check
            news_score = fetch_news_sentiment(search_name)
            trading_score += news_score
            
            # 🎯 Execution Threshold: Must score 1 or higher to buy
            if trading_score >= 1:
                stop_loss = latest * 0.98
                q = qty(latest, stop_loss)
                
                if q > 0:
                    results.append((s, latest, stop_loss, q, trading_score))
                    if len(results) + len(active_trades) >= MAX_TRADES:
                        break
        except:
            continue
            
    for s, entry, sl, q, score in results:
        add_trade(s, entry, sl, q)
        send(f"🚀 MULTI-DAY BUY: {s}\n📊 Total Score: {score}\n💰 Entry: ₹{round(entry, 2)}\n🛡️ SL (2%): ₹{round(sl, 2)}\n🎯 Target Range (6%-10%): ₹{round(entry * 1.06, 2)} - ₹{round(entry * 1.10, 2)}")

# ==========================================
# 📈 PHASE 2: MID-DAY MONITORING (12:00 PM - 2:00 PM)
# ==========================================
elif 12 <= hour < 14:
    trades = get_active_trades()
    for t in trades:
        try:
            d = yf.download(t["stock"], period="1d", interval="5m", progress=False)
            c = d["Close"]
            if hasattr(c, "columns"):
                c = c.iloc[:, 0]
            latest = c.iloc[-1]
            
            # Check Stop Loss (2%)
            if latest <= t["sl"]:
                close_trade(t["stock"], latest)
                send(f"🛑 STOP LOSS HIT: Sold {t['stock']} at ₹{round(latest, 2)}")
            
            # Check Trailing Profit Range (6% to 10%)
            elif latest >= (t["entry"] * 1.06):
                close_trade(t["stock"], latest)
                profit_pct = ((latest - t["entry"]) / t["entry"]) * 100
                send(f"🎯 TARGET REACHED: Profit locked in for {t['stock']} at ₹{round(latest, 2)} (+{round(profit_pct, 2)}%)")
        except:
            continue

# ==========================================
# 🌆 PHASE 3: PORTFOLIO SUMMARY (2:00 PM onwards)
# ==========================================
else:
    trades = get_active_trades()
    if not trades:
        send("🌆 No active positions to report today.")
        exit()
        
    msg = "🌆 DAILY PORTFOLIO SUMMARY (Holding Overnight)\n\n"
    for t in trades:
        try:
            d = yf.download(t["stock"], period="1d", interval="5m", progress=False)
            c = d["Close"]
            if hasattr(c, "columns"):
                c = c.iloc[:, 0]
            latest = c.iloc[-1]
            pnl = ((latest - t["entry"]) / t["entry"]) * 100
            msg += f"📦 {t['stock']}\n  • Entry: ₹{round(t['entry'], 2)}\n  • Current: ₹{round(latest, 2)}\n  • Current Return: {round(pnl, 2)}%\n\n"
        except:
            continue
    send(msg)
