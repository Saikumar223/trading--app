import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import os

FILE = "trades.csv"

model = None

def train_model():
    global model

    if not os.path.exists(FILE):
        return None

    df = pd.read_csv(FILE)

    df = df[df["Status"].isin(["WIN","LOSS"])]

    if len(df) < 10:
        return None

    # Encode categorical
    df["Type"] = df["Type"].map({"Breakout 🚀":1, "Pullback 🔁":0})
    df["MarketTrend"] = df["MarketTrend"].map({"Bullish":1, "Bearish":0})

    df["result"] = df["Status"].apply(lambda x: 1 if x == "WIN" else 0)

    X = df[["Change","Volume","RSI","Type","MarketTrend"]]
    y = df["result"]

    model = RandomForestClassifier(n_estimators=200)
    model.fit(X, y)

    return model

def predict(change, volume, rsi, entry_type, market_trend):
    global model

    if model is None:
        model = train_model()

    if model is None:
        return 50.0

    type_val = 1 if "Breakout" in entry_type else 0
    trend_val = 1 if market_trend == "Bullish" else 0

    prob = model.predict_proba([[change, volume, rsi, type_val, trend_val]])[0][1]

    return round(prob * 100, 2)
