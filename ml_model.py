import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import os

FILE = "trades.csv"

model = None

# =========================
# TRAIN MODEL FROM TRADES
# =========================
def train_model():
    global model

    if not os.path.exists(FILE):
        return None

    df = pd.read_csv(FILE)

    # Only completed trades
    df = df[df["Status"].isin(["WIN","LOSS"])]

    if len(df) < 5:
        return None  # not enough data yet

    # Create simple features
    df["change"] = (df["Target"] - df["Entry"]) / df["Entry"] * 100
    df["risk"] = (df["Entry"] - df["SL"]) / df["Entry"] * 100

    df["result"] = df["Status"].apply(lambda x: 1 if x == "WIN" else 0)

    X = df[["change","risk"]]
    y = df["result"]

    model = RandomForestClassifier()
    model.fit(X, y)

    return model

# =========================
# PREDICT
# =========================
def predict(change, volume, rsi):
    global model

    if model is None:
        model = train_model()

    # fallback if no model
    if model is None:
        return 50.0

    risk = 0.8  # approximate fallback

    prob = model.predict_proba([[change, risk]])[0][1]

    return round(prob * 100, 2)
