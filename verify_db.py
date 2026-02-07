import sqlite3
import glob
import os

try:
    # Find latest results dir
    list_of_files = glob.glob('results/run_*')
    if not list_of_files:
        print("No run results found.")
        exit()
    latest_file = max(list_of_files, key=os.path.getctime)
    db_path = os.path.join(latest_file, "simulation.db")
    print(f"Checking DB: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("-" * 30)
    print(">>> 1. Checking Life Events (Phase 4.3)...")
    try:
        cursor.execute("SELECT count(*) FROM decision_logs WHERE event_type='LIFE_EVENT'")
        count = cursor.fetchone()[0]
        print(f"Life Events Found: {count}")
        if count > 0:
            cursor.execute("SELECT decision, reason FROM decision_logs WHERE event_type='LIFE_EVENT' LIMIT 3")
            for row in cursor.fetchall():
                print(f"  - {row[0]}: {row[1]}")
    except Exception as e:
        print(f"Life Event Check Failed: {e}")

    print("-" * 30)
    print(">>> 2. Checking Multi-Property Listings (Phase 4.4)...")
    try:
        cursor.execute("""
            SELECT seller_id, created_month, count(*) as count 
            FROM property_listings 
            GROUP BY seller_id, created_month 
            HAVING count > 1
        """)
        rows = cursor.fetchall()
        if rows:
            print(f"FOUND {len(rows)} agents listing multiple properties:")
            for row in rows:
                print(f"  - Seller {row[0]} listed {row[2]} properties in Month {row[1]}")
        else:
            print("No multi-property listings found yet.")
    except Exception as e:
        print(f"Multi-Property Check Failed: {e}")

    print("-" * 30)
    print(">>> 3. Checking Total Stats...")
    try:
        cursor.execute("SELECT count(*) FROM property_listings")
        total_listings = cursor.fetchone()[0]
        cursor.execute("SELECT count(*) FROM property_listings") # duplicate query in original snippet? No, checking decision_logs
        # Oops, my ReplacementContent logic should follow my instruction logic.
        # I will fix the query in my instruction below.
        
        cursor.execute("SELECT count(*) FROM property_listings")
        total_listings = cursor.fetchone()[0]
        cursor.execute("SELECT count(*) FROM decision_logs")
        total_decisions = cursor.fetchone()[0]
        print(f"Total Listings: {total_listings}")
        print(f"Total Decisions: {total_decisions}")
    except:
        pass

except Exception as e:
    print(f"Error: {e}")
