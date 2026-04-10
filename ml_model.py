import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import os

FILE = "trades.csv"

model = None

# =========================
# TRAIN MODEL
# =========================
def train_model():
    global model

    if not os.path.exists(FILE):
        return None

    df = pd.read_csv(FILE)

    df = df[df["Status"].isin(["WIN","LOSS"])]

    if len(df) < 10:
        return None

    # 🔥 ADVANCED FEATURES
    df["change"] = (df["Target"] - df["Entry"]) / df["Entry"] * 100
    df["risk"] = (df["Entry"] - df["SL"]) / df["Entry"] * 100
    df["rr"] = df["change"] / df["risk"]

    # simulate extra signals
    df["volume"] = 1.5  # placeholder
    df["rsi"] = 50      # placeholder

    df["result"] = df["Status"].apply(lambda x: 1 if x == "WIN" else 0)

    X = df[["change","risk","rr","volume","rsi"]]
    y = df["result"]

    model = RandomForestClassifier(n_estimators=100)
    model.fit(X, y)

    return model

# =========================
# PREDICT
# =========================
def predict(change, volume, rsi):
    global model

    if model is None:
        model = train_model()

    if model is None:
        return 50.0

    risk = 0.8
    rr = change / risk if risk != 0 else 1

    prob = model.predict_proba([[change, risk, rr, volume, rsi]])[0][1]

    return round(prob * 100, 2)
