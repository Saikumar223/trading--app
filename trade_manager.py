import json
import os
from datetime import datetime

STATE_FILE = "trade_state.json"
JOURNAL_FILE = "journal.json"

# =========================
# LOAD STATE
# =========================
def load_state():

    if not os.path.exists(STATE_FILE):
        return {
            "capital": 1000,
            "daily_loss": 0,
            "loss_streak": 0,
            "trades": []
        }

    with open(STATE_FILE, "r") as f:
        return json.load(f)

# =========================
# SAVE STATE
# =========================
def save_state(state):

    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)

# =========================
# ADD TRADE
# =========================
def add_trade(stock, entry, sl, qty):

    state = load_state()

    risk = abs(entry - sl)

    trade = {
        "stock": stock,
        "entry": round(entry, 2),
        "sl": round(sl, 2),
        "target": round(entry + (risk * 2), 2),
        "qty": qty,
        "status": "OPEN",
        "entry_time": str(datetime.now()),
        "exit_time": None,
        "exit_price": None,
        "pnl": 0
    }

    state["trades"].append(trade)

    save_state(state)

# =========================
# GET ACTIVE TRADES
# =========================
def get_active_trades():

    state = load_state()

    return [
        t for t in state["trades"]
        if t["status"] == "OPEN"
    ]

# =========================
# UPDATE TRADE
# =========================
def update_trade(stock, updates):

    state = load_state()

    for t in state["trades"]:

        if t["stock"] == stock and t["status"] == "OPEN":

            for k, v in updates.items():
                t[k] = v

    save_state(state)

# =========================
# CLOSE TRADE
# =========================
def close_trade(stock, exit_price):

    state = load_state()

    closed_trade = None

    for t in state["trades"]:

        if t["stock"] == stock and t["status"] == "OPEN":

            pnl = (
                (exit_price - t["entry"])
                * t["qty"]
            )

            t["status"] = "CLOSED"
            t["exit_price"] = round(exit_price, 2)
            t["exit_time"] = str(datetime.now())
            t["pnl"] = round(pnl, 2)

            state["capital"] += pnl

            if pnl < 0:
                state["daily_loss"] += abs(pnl)
                state["loss_streak"] += 1
            else:
                state["loss_streak"] = 0

            closed_trade = t

    save_state(state)

    if closed_trade:
        log_journal(closed_trade)

# =========================
# JOURNAL
# =========================
def log_journal(trade):

    data = []

    if os.path.exists(JOURNAL_FILE):

        with open(JOURNAL_FILE, "r") as f:
            data = json.load(f)

    data.append(trade)

    with open(JOURNAL_FILE, "w") as f:
        json.dump(data, f, indent=4)
