# database.py
import sqlite3

DB = "hedgebot.db"

def init_db():
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()

    # Create thresholds table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS thresholds (
            user_id INTEGER PRIMARY KEY,
            threshold REAL NOT NULL
        )
    """)

    # Create hedges table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hedges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            asset TEXT,
            size REAL,
            price REAL,
            reason TEXT,
            time TEXT
        )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS auto_hedge_jobs (
        user_id INTEGER PRIMARY KEY,
        asset TEXT NOT NULL,
        size REAL NOT NULL
    )
""")

    # MIGRATION: Ensure positions table has PRIMARY KEY(user_id, asset)
    cursor.execute("PRAGMA table_info(positions)")
    columns = cursor.fetchall()
    column_names = [col[1] for col in columns]

    if columns:
        cursor.execute("SELECT sql FROM sqlite_master WHERE name='positions'")
        existing_schema = cursor.fetchone()[0]
        if "PRIMARY KEY" not in existing_schema or "user_id, asset" not in existing_schema:
            print("🔧 Recreating 'positions' table with proper PRIMARY KEY...")
            cursor.execute("ALTER TABLE positions RENAME TO positions_old")

            # Recreate correct schema
            cursor.execute("""
                CREATE TABLE positions (
                    user_id INTEGER,
                    asset TEXT,
                    size REAL,
                    price REAL,
                    PRIMARY KEY (user_id, asset)
                )
            """)

            # Copy old data (if any)
            try:
                cursor.execute("""
                    INSERT INTO positions (user_id, asset, size, price)
                    SELECT user_id, asset, size, price FROM positions_old
                """)
            except Exception as e:
                print(f"⚠️ Data migration failed: {e}")

            cursor.execute("DROP TABLE positions_old")

    else:
        # If table didn't exist at all
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                user_id INTEGER,
                asset TEXT,
                size REAL,
                price REAL,
                PRIMARY KEY (user_id, asset)
            )
        """)

    conn.commit()
    conn.close()
