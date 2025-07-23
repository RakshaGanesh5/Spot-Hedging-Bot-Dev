# portfolio.py

import sqlite3
from market_data import fetch_spot_price
from risk_engine import calculate_delta, calculate_var
from database import DB

def get_portfolio_status(user_id):

    conn = sqlite3.connect(DB)
    cursor = conn.cursor()

    # ❗️ Removed user_id filter for now
    cursor.execute("SELECT asset, size FROM positions WHERE user_id = ?", (user_id,))

    positions = cursor.fetchall()
    conn.close()

    if not positions:
        return [], 0, 0

    summary = []
    total_delta = 0
    total_var = 0

    for asset, size in positions:
        price = fetch_spot_price(asset, "bybit")
        if price is None:
            continue

        # Simulate historical prices for VaR
        history = [price - 30, price, price + 20, price - 10, price + 5]

        delta = calculate_delta(size)
        var = calculate_var(history)

        total_delta += delta
        total_var += var

        summary.append({
            "asset": asset,
            "size": size,
            "price": price,
            "delta": delta,
            "var": var
        })

    avg_var = total_var / len(summary) if summary else 0
    return summary, total_delta, avg_var
