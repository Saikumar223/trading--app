import pandas as pd
import os
from sklearn.ensemble import RandomForestClassifier

FILE = "trades.csv"

model = None

def train():
    global model

    if not os.path.exists(FILE):
        return None

    df = pd.read_csv(FILE)
    df = df[df["Status"].isin(["WIN","LOSS"])]

    if len(df) < 20:
        return None

    df["result"] = df["Status"].apply(lambda x: 1 if x=="WIN" else 0)

    # Safe features (fallback if missing)
    df["Change"] = df.get("Change", 0)
    df["Volume"] = df.get("Volume", 1)
    df["RSI"] = df.get("RSI", 50)

    X = df[["Change","Volume","RSI"]]
    y = df["result"]

    model = RandomForestClassifier(n_estimators=100, max_depth=5)
    model.fit(X,y)

def predict(change, vol, rsi, *_):
    global model

    if model is None:
        train()

    if model is None:
        return 50.0

    prob = model.predict_proba([[change, vol, rsi]])[0][1]
    return round(prob*100,2)

def auto_train():
    try:
        train()
    except:
        pass
