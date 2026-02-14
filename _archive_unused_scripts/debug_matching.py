import sqlite3
import os

db_path = r'd:\GitProj\oasis-main\results\run_20260208_171858\simulation.db'

print(f"Connecting to {db_path}...")
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check Agent 27 (Buyer) details in active_participants and agents_finance
    print("\n--- Agent 27 (Buyer?) ---")
    cursor.execute("SELECT * FROM active_participants WHERE agent_id = 27")
    ap_cols = [description[0] for description in cursor.description]
    rows = cursor.fetchall()
    if rows:
        for row in rows:
            print("Active Participant Data:")
            for col, val in zip(ap_cols, row):
                print(f"  {col}: {val}")
    else:
        print("Agent 27 not found in active_participants")

    cursor.execute("SELECT * FROM agents_finance WHERE agent_id = 27")
    af_cols = [description[0] for description in cursor.description]
    rows = cursor.fetchall()
    for row in rows:
        print("Finance Data:")
        for col, val in zip(af_cols, row):
            print(f"  {col}: {val}")

    # Check Agent 10 (Seller) and Property 47
    print("\n--- Agent 10 (Seller?) & Property 47 ---")
    cursor.execute("SELECT * FROM active_participants WHERE agent_id = 10")
    rows = cursor.fetchall()
    if rows:
        for row in rows:
            print("Active Participant Data (Agent 10):")
            for col, val in zip(ap_cols, row):
                print(f"  {col}: {val}")
    else:
         print("Agent 10 not found in active_participants")

    print("\n--- Property 47 (Market Data) ---")
    cursor.execute("SELECT * FROM properties_market WHERE property_id IN (46, 47, 48)")
    pm_cols = [description[0] for description in cursor.description]
    rows = cursor.fetchall()
    for row in rows:
        print(f"Property {row[0]}:")
        for col, val in zip(pm_cols, row):
            print(f"  {col}: {val}")

    conn.close()

except Exception as e:
    print(f"Error: {e}")

