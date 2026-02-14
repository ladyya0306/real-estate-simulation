import glob
import os
import sqlite3

# Find latest run
results_dir = 'd:/GitProj/oasis-main/results'
folders = [f for f in glob.glob(os.path.join(results_dir, 'run_*')) if os.path.isdir(f)]
if not folders:
    print("No run folders found.")
    exit()

latest_folder = max(folders, key=os.path.getmtime)
db_path = os.path.join(latest_folder, 'simulation.db')
print(f"Checking database: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    with open('verify_report.txt', 'w', encoding='utf-8') as f:
        f.write(f"Checking database: {db_path}\n")
        f.write("\n--- Checking agents_finance Persistence ---\n")

        # Check active participants first
        cursor.execute("SELECT role, COUNT(*) FROM active_participants GROUP BY role")
        roles = cursor.fetchall()
        f.write(f"Active Participants Roles: {roles}\n")

        cursor.execute("""
            SELECT COUNT(*), AVG(psychological_price), AVG(max_affordable_price), AVG(net_cashflow)
            FROM agents_finance
            WHERE psychological_price > 0 OR max_affordable_price > 0
        """)
        row = cursor.fetchone()
        count = row[0]
        avg_psych = row[1] or 0
        avg_afford = row[2] or 0
        avg_cashflow = row[3] or 0

        f.write(f"Rows with Tier 6 data: {count}\n")
        f.write(f"Avg Psycho Price: {avg_psych:,.2f}\n")
        f.write(f"Avg Max Afford: {avg_afford:,.2f}\n")
        f.write(f"Avg Net Cashflow: {avg_cashflow:,.2f}\n")

        if count > 0 and avg_psych > 0:
            f.write("✅ SUCCESS: Tier 6 financial data is being persisted!\n")
        else:
            f.write("❌ FAILURE: Persistence failed or data is zero.\n")

        f.write("\n--- Checking decision_logs Schema ---\n")
        cursor.execute("PRAGMA table_info(decision_logs)")
        columns = [r[1] for r in cursor.fetchall()]
        f.write(f"Columns: {columns}\n")

        required = ['event_type', 'decision', 'thought_process']
        if all(c in columns for c in required):
            f.write(f"✅ SUCCESS: decision_logs has {required}\n")
        else:
            f.write(f"❌ FAILURE: decision_logs missing columns. Have: {columns}\n")

    conn.close()

except Exception as e:
    with open('verify_report.txt', 'w', encoding='utf-8') as f:
        f.write(f"Error: {e}")
