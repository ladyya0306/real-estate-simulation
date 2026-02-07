
import sqlite3
import json
import logging

def analyze():
    conn = sqlite3.connect('real_estate_stage2.db')
    cursor = conn.cursor()
    
    print("\n=== Simulation Analysis Report (6 Months) ===\n")
    
    # 1. Transactions
    cursor.execute("SELECT COUNT(*), AVG(price), SUM(price) FROM transactions")
    tx_stats = cursor.fetchone()
    print(f"Total Transactions: {tx_stats[0]}")
    print(f"Average Price: {tx_stats[1]:,.0f}")
    print(f"Total Volume: {tx_stats[2]:,.0f}\n")
    
    # 2. Negotiations Overview
    cursor.execute("SELECT COUNT(*), SUM(CASE WHEN success THEN 1 ELSE 0 END) FROM negotiations")
    neg_stats = cursor.fetchone()
    print(f"Total Negotiations: {neg_stats[0]}")
    print(f"Successful: {neg_stats[1]}")
    print(f"Success Rate: {neg_stats[1]/neg_stats[0]:.1%}" if neg_stats[0] else "Success Rate: 0%\n")
    
    # 3. Mode Analysis
    # We look inside the LOG column for keywords
    modes = {
        "Classic": 0,
        "Batch": 0,
        "Flash": 0
    }
    
    cursor.execute("SELECT log FROM negotiations")
    logs = cursor.fetchall()
    
    for row in logs:
        log_json = row[0]
        # Heuristic check
        if "WIN_BID" in log_json:
            modes["Batch"] += 1
        elif "FLASH_ACCEPT" in log_json:
            modes["Flash"] += 1
        else:
            modes["Classic"] += 1
            
    print("Negotiation Modes Used:")
    for m, c in modes.items():
        print(f"  - {m}: {c}")
        
    print("\n=== End of Report ===")
    conn.close()

if __name__ == "__main__":
    analyze()
