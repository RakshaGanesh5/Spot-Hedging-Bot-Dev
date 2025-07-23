import sqlite3

conn = sqlite3.connect("hedgebot.db")
cursor = conn.cursor()

# Drop the old table
cursor.execute("DROP TABLE IF EXISTS positions")

# Recreate with correct schema
cursor.execute("""
    CREATE TABLE positions (
        user_id INTEGER,
        asset TEXT,
        size REAL,
        price REAL,
        PRIMARY KEY (user_id, asset)
    )
""")

conn.commit()
conn.close()
print("✅ positions table reset with PRIMARY KEY (user_id, asset)")
