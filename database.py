import sqlite3
from datetime import datetime

DB = "trading.db"

# =========================
# CONNECT
# =========================
def connect():

    return sqlite3.connect(DB)

# =========================
# INIT DB
# =========================
def init_db():

    conn = connect()

    cur = conn.cursor()

    # TRADES
    cur.execute("""
    CREATE TABLE IF NOT EXISTS trades (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        stock TEXT,
        entry REAL,
        sl REAL,
        target REAL,
        qty INTEGER,

        status TEXT,

        entry_time TEXT,
        exit_time TEXT,

        exit_price REAL,
        pnl REAL
    )
    """)

    # SESSIONS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sessions (

        day TEXT,
        phase TEXT
    )
    """)

    # CAPITAL
    cur.execute("""
    CREATE TABLE IF NOT EXISTS capital (

        amount REAL
    )
    """)

    conn.commit()

    # INITIAL CAPITAL
    cur.execute("SELECT * FROM capital")

    if not cur.fetchone():

        cur.execute(
            "INSERT INTO capital VALUES (?)",
            (1000,)
        )

    conn.commit()

    conn.close()

# =========================
# CAPITAL
# =========================
def get_capital():

    conn = connect()

    cur = conn.cursor()

    cur.execute("SELECT amount FROM capital")

    capital = cur.fetchone()[0]

    conn.close()

    return capital

def update_capital(new_amount):

    conn = connect()

    cur = conn.cursor()

    cur.execute(
        "UPDATE capital SET amount=?",
        (new_amount,)
    )

    conn.commit()

    conn.close()

# =========================
# SESSION CONTROL
# =========================
def session_done(day, phase):

    conn = connect()

    cur = conn.cursor()

    cur.execute(
        """
        SELECT * FROM sessions
        WHERE day=? AND phase=?
        """,
        (day, phase)
    )

    result = cur.fetchone()

    conn.close()

    return result is not None

def mark_session(day, phase):

    conn = connect()

    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO sessions
        VALUES (?,?)
        """,
        (day, phase)
    )

    conn.commit()

    conn.close()

# =========================
# TRADES
# =========================
def add_trade(stock, entry, sl, qty):

    conn = connect()

    cur = conn.cursor()

    risk = abs(entry - sl)

    target = entry + (risk * 2)

    cur.execute("""
    INSERT INTO trades (

        stock,
        entry,
        sl,
        target,
        qty,

        status,

        entry_time,

        exit_time,
        exit_price,
        pnl

    )

    VALUES (?,?,?,?,?,?,?,?,?,?)
    """,

    (
        stock,
        round(entry,2),
        round(sl,2),
        round(target,2),
        qty,

        "OPEN",

        str(datetime.now()),

        None,
        None,
        0
    ))

    conn.commit()

    conn.close()

# =========================
# ACTIVE TRADES
# =========================
def get_active_trades():

    conn = connect()

    cur = conn.cursor()

    cur.execute("""
    SELECT
    stock,
    entry,
    sl,
    target,
    qty
    FROM trades
    WHERE status='OPEN'
    """)

    rows = cur.fetchall()

    conn.close()

    trades = []

    for r in rows:

        trades.append({
            "stock": r[0],
            "entry": r[1],
            "sl": r[2],
            "target": r[3],
            "qty": r[4]
        })

    return trades

# =========================
# UPDATE SL
# =========================
def update_sl(stock, sl):

    conn = connect()

    cur = conn.cursor()

    cur.execute("""
    UPDATE trades
    SET sl=?
    WHERE stock=?
    AND status='OPEN'
    """,

    (
        round(sl,2),
        stock
    ))

    conn.commit()

    conn.close()

# =========================
# CLOSE TRADE
# =========================
def close_trade(stock, price):

    conn = connect()

    cur = conn.cursor()

    cur.execute("""
    SELECT
    entry,
    qty
    FROM trades
    WHERE stock=?
    AND status='OPEN'
    """,

    (stock,)
    )

    row = cur.fetchone()

    if not row:
        conn.close()
        return 0

    entry = row[0]
    qty = row[1]

    pnl = (
        (price - entry)
        * qty
    )

    cur.execute("""
    UPDATE trades

    SET
    status='CLOSED',
    exit_price=?,
    exit_time=?,
    pnl=?

    WHERE stock=?
    AND status='OPEN'
    """,

    (
        round(price,2),
        str(datetime.now()),
        round(pnl,2),
        stock
    ))

    conn.commit()

    conn.close()

    return pnl
