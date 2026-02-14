
import sqlite3
import sys

# Force UTF-8
sys.stdout.reconfigure(encoding='utf-8')

db_path = r'd:\GitProj\oasis-main\results\run_20260208_233238\simulation.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print(f"Checking agents_finance in {db_path}...")

# Check total agents
cursor.execute("SELECT COUNT(*) FROM agents_finance")
total = cursor.fetchone()[0]
print(f"Total agents in finance table: {total}")

# Check how many pass the filter
cursor.execute("SELECT COUNT(*) FROM agents_finance WHERE cash > 300000")
rich_cash = cursor.fetchone()[0]
print(f"Agents with Cash > 300,000: {rich_cash}")

cursor.execute("SELECT COUNT(*) FROM agents_finance WHERE monthly_income > 20000")
rich_income = cursor.fetchone()[0]
print(f"Agents with Income > 20,000: {rich_income}")

# Sample some agents
print("\nSample Agent Finances:")
cursor.execute("SELECT agent_id, cash, monthly_income FROM agents_finance LIMIT 10")
for r in cursor.fetchall():
    print(f"Agent {r[0]}: Cash={r[1]:,.0f}, Income={r[2]:,.0f}")

conn.close()
