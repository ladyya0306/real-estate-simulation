
import sqlite3
import pandas as pd
import glob
import os
import json

def find_latest_db():
    dbs = glob.glob(os.path.join("results", "run_*", "simulation.db")) + ["simulation.db"]
    dbs.sort(key=os.path.getmtime, reverse=True)
    return dbs[0] if dbs else None

def analyze():
    db_path = find_latest_db()
    if not db_path:
        print("No DB found.")
        return

    print(f"📂 Analyzing DB: {db_path}")
    conn = sqlite3.connect(db_path)

    # 1. Supply vs Demand (based on Roles)
    print("\n--- 1. Supply vs Demand (By Role) ---")
    try:
        roles_df = pd.read_sql_query("SELECT month, decision as role, COUNT(*) as count FROM decision_logs WHERE event_type='ROLE_DECISION' GROUP BY month, decision", conn)
        print(roles_df)
    except Exception as e:
        print(f"Error reading roles: {e}")

    # 2. Bidding Intensity
    print("\n--- 2. Bidding Intensity ---")
    try:
        # Assuming we can parse 'BID' events or infer from logs
        # Or look at transaction prices vs listed prices?
        # Actually, let's look at `transactions` table
        tx_df = pd.read_sql_query("SELECT * FROM transactions", conn)
        if not tx_df.empty:
            print(f"Total Transactions: {len(tx_df)}")
            print(tx_df[['month', 'property_id', 'buyer_id', 'price', 'event_type']].head())
        else:
            print("No Transactions found yet.")
    except Exception as e:
        print(f"Error reading transactions: {e}")

    # 3. Buyer Frustration / Reasoning
    print("\n--- 3. Buyer Reasoning (Why not buying?) ---")
    try:
        # Look for buyers who DID NOT buy (if possible to track?)
        # Or look for 'BID' events that failed?
        # Let's look for keywords in decision_logs for BUYER role
        query = "SELECT agent_id, reason FROM decision_logs WHERE event_type='ROLE_DECISION' AND decision='BUYER' LIMIT 10"
        buyers = pd.read_sql_query(query, conn)
        print("Sample Buyer Reasoning:")
        for r in buyers['reason']:
            print(f"- {r[:50]}...")
            
    except Exception as e:
        print(f"Error: {e}")

    conn.close()

if __name__ == "__main__":
    analyze()
