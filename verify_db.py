import sqlite3

DB = "hedgebot.db"

def show_tables_and_rows():
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()

    # Show tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print("📋 Tables in DB:")
    for table in tables:
        print(" -", table[0])

    print("\n📊 Sample data from each table:")

    for table_name in ["thresholds", "hedges", "positions"]:
        print(f"\n📌 {table_name.upper()} ----------------------")
        try:
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
            rows = cursor.fetchall()
            if rows:
                for row in rows:
                    print(row)
            else:
                print("No data.")
        except Exception as e:
            print(f"⚠️ Could not query {table_name}: {e}")

    conn.close()

if __name__ == "__main__":
    show_tables_and_rows()
