import sqlite3
import os

db_path = "results/run_20260203_233305/simulation.db"

if not os.path.exists(db_path):
    print(f"Error: DB not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("--- Verifying Bug #1: Property Count ---")
try:
    cursor.execute("SELECT COUNT(*) FROM properties_static")
    count = cursor.fetchone()[0]
    print(f"Total Properties (properties_static): {count}")
    if count == 50:
        print("✅ PASS: Property count is 50")
    else:
        print(f"❌ FAIL: Property count is {count}, expected 50")
except Exception as e:
    print(f"Error querying properties: {e}")

print("\n--- Debug: Market Activity ---")
try:
    cursor.execute("SELECT COUNT(*) FROM property_listings")
    l_count = cursor.fetchone()[0]
    print(f"Total Listings: {l_count}")
    
    cursor.execute("SELECT COUNT(*) FROM transactions")
    t_count = cursor.fetchone()[0]
    print(f"Total Transactions: {t_count}")
except Exception as e:
    print(f"Error querying activity: {e}")

print("\n--- Verifying Bug #2: Negotiation Reasons ---")
try:
    # check if column exists
    cursor.execute("PRAGMA table_info(negotiations)")
    cols = [r[1] for r in cursor.fetchall()]
    if 'reason' not in cols:
        print("❌ FAIL: 'reason' column missing in negotiations table")
    else:
        print("✅ PASS: 'reason' column exists")
        
        cursor.execute("SELECT reason, success, count(*) FROM negotiations GROUP BY reason, success")
        rows = cursor.fetchall()
        print("\nNegotiation Reasons Summary:")
        for r in rows:
            reason = r[0]
            success = r[1]
            count = r[2]
            status = "Success" if success else "Failed"
            print(f"[{status}] Reason: '{reason}' | Count: {count}")
            
        # Check if we have failures with non-null reasons
        cursor.execute("SELECT COUNT(*) FROM negotiations WHERE success=0 AND (reason IS NULL OR reason = '')")
        empty_reasons = cursor.fetchone()[0]
        if empty_reasons == 0:
            print("✅ PASS: All failed negotiations have reasons")
        else:
            print(f"❌ FAIL: {empty_reasons} failed negotiations obtain reason")

except Exception as e:
    print(f"Error querying negotiations: {e}")

conn.close()
