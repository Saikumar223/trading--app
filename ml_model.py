import pandas as pd
import os
from sklearn.ensemble import RandomForestClassifier

FILE = "trades.csv"
model = None

def train():
    global model

    if not os.path.exists(FILE):
        return

    df = pd.read_csv(FILE)
    df = df[df["Status"].isin(["WIN","LOSS"])]

    if len(df) < 10:
        return

    df["result"] = df["Status"].apply(lambda x: 1 if x=="WIN" else 0)

    X = df[["Entry","Exit","PnL"]]
    y = df["result"]

    model = RandomForestClassifier(n_estimators=200)
    model.fit(X,y)

def predict(change, vol, rsi, *_):
    global model

    if model is None:
        train()

    if model is None:
        return 50

    return 60  # fallback simplified

def auto_train():
    try:
        train()
    except:
        pass
