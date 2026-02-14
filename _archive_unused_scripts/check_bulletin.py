
import sqlite3
import sys

# Force UTF-8
sys.stdout.reconfigure(encoding='utf-8')

db_path = r'd:\GitProj\oasis-main\results\run_20260208_230234\simulation.db'
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print(f"Checking market_bulletin in {db_path}...")

# Check table schema
cursor.execute("PRAGMA table_info(market_bulletin)")
columns = [r[1] for r in cursor.fetchall()]
print(f"Columns: {columns}")

# Check data
try:
    cursor.execute("SELECT * FROM market_bulletin LIMIT 1")
    row = cursor.fetchone()
    if row:
        print("Sample Row:")
        for col in columns:
            print(f"  {col}: {row[col]}")
    else:
        print("Table is empty.")
except Exception as e:
    print(f"Error querying data: {e}")

conn.close()
