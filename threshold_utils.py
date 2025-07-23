# threshold_utils.py
import sqlite3
from database import DB


DB = "hedgebot.db"

def set_user_threshold(user_id, threshold):
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO thresholds (user_id, threshold)
        VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET threshold=excluded.threshold
    """, (user_id, threshold))
    conn.commit()
    conn.close()

def get_user_threshold(user_id):
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("SELECT threshold FROM thresholds WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 1.0  # default threshold if not set
