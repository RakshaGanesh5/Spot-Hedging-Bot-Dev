import sqlite3
from datetime import datetime
from database import DB

def log_hedge(asset, size, price, reason, user_id):
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO hedges (user_id, asset, size, price, reason, time)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        asset,
        size,
        price,
        reason,
        datetime.utcnow().isoformat()
    ))
    conn.commit()
    conn.close()
