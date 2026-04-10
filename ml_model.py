import pandas as pd
from sklearn.ensemble import RandomForestClassifier

def train_model():
    # Dummy training data (we improve later)
    data = pd.DataFrame({
        "change": [0.5, 0.8, 1.2, 0.3, 0.7, 1.5, 0.2],
        "volume": [1.2, 2.0, 3.0, 1.1, 1.8, 3.5, 1.0],
        "rsi": [45, 50, 60, 35, 55, 65, 30],
        "target": [1, 1, 1, 0, 1, 1, 0]
    })

    X = data[["change","volume","rsi"]]
    y = data["target"]

    model = RandomForestClassifier()
    model.fit(X, y)

    return model

model = train_model()

def predict(change, volume, rsi):
    prob = model.predict_proba([[change, volume, rsi]])[0][1]
    return round(prob * 100, 2)
