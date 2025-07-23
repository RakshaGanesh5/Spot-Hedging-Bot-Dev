import sqlite3

conn = sqlite3.connect("hedgebot.db")
cursor = conn.cursor()

cursor.execute("DROP TABLE IF EXISTS positions")
conn.commit()
conn.close()

print("✅ Old positions table dropped. Now restart the bot to recreate it.")
