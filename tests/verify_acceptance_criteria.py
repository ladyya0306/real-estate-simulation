import sqlite3
import sys
import os
import json

# Add parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = 'real_estate_stage2.db'

def check_db_schema():
    print(">>> 1. Checking Database Schema")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check properties table schema
    cursor.execute("PRAGMA table_info(properties)")
    columns = {row[1]: row for row in cursor.fetchall()}
    
    required_fields = ['base_value', 'zone', 'listed_price']
    missing = [f for f in required_fields if f not in columns]
    
    if missing:
        print(f"❌ FAILED: Missing columns: {missing}")
    else:
        print("✅ PASS: Schema contains base_value, zone, listed_price")
        
    # Check for NULL base_value
    cursor.execute("SELECT COUNT(*) FROM properties WHERE base_value IS NULL")
    null_count = cursor.fetchone()[0]
    if null_count > 0:
        print(f"❌ FAILED: Found {null_count} properties with NULL base_value")
    else:
        print("✅ PASS: No NULL base_value")
        
    conn.close()

def check_property_init():
    print("\n>>> 2. Checking Property Initialization")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check counts
    cursor.execute("SELECT zone, COUNT(*) FROM properties GROUP BY zone")
    counts = dict(cursor.fetchall())
    
    print(f"Counts: {counts}")
    if counts.get('A') == 100 and counts.get('B') == 200:
        print("✅ PASS: Zone counts A:100, B:200")
    else:
        print("❌ FAILED: Incorrect zone distribution")
        
    # Check ownership (Are there any owners?)
    cursor.execute("SELECT COUNT(*) FROM properties WHERE owner_id IS NOT NULL")
    owned_count = cursor.fetchone()[0]
    print(f"Owned Properties: {owned_count}")
    
    if owned_count > 0:
        print("✅ PASS: Properties are owned")
    else:
        print("⚠️ WARNING: No properties are owned by agents (All System Owned?)")
        
    conn.close()

def check_logs():
    print("\n>>> 3. Checking Decision Logs")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check triggers
    cursor.execute("SELECT content FROM agent_decision_logs WHERE metadata LIKE '%\"llm_called\": true%' LIMIT 5")
    logs = cursor.fetchall()
    
    print(f"Found {len(logs)} LLM logs sample.")
    
    # Check granularity (Do we have multiple steps per agent/month?)
    cursor.execute("""
        SELECT agent_id, month, COUNT(*) as steps 
        FROM agent_decision_logs 
        GROUP BY agent_id, month 
        HAVING steps > 1
        LIMIT 5
    """)
    multi_step = cursor.fetchall()
    
    if len(multi_step) > 0:
        print("✅ PASS: Found multi-step logs for single decision")
    else:
        print("⚠️ WARNING: Only found 1 log entry per decision. (Expect 4 for LLM?)")
        
    conn.close()

if __name__ == "__main__":
    check_db_schema()
    check_property_init()
    check_logs()
