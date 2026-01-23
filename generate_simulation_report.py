import sqlite3
import json
import os
import csv
from datetime import datetime

# Default Constants
DB_PATH = 'real_estate_stage2.db'
REPORT_DIR = 'reports'

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

# --- CSV Export Functions ---
def export_legacy_csvs(results_dir):
    ensure_dir(results_dir)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. agents.csv
    print(f"Exporting agents.csv to {results_dir}...")
    cursor.execute("SELECT * FROM agents")
    rows = cursor.fetchall()
    if rows:
        with open(f"{results_dir}/agents.csv", "w", newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            for row in rows:
                writer.writerow(dict(row))
                
    # 2. thoughts.csv (Mapped from decision_logs)
    print("Exporting thoughts.csv...")
    cursor.execute("SELECT month, agent_id, decision as step_type, reason as content, thought_process FROM decision_logs")
    rows = cursor.fetchall()
    if rows:
        with open(f"{results_dir}/thoughts.csv", "w", newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            for row in rows:
                writer.writerow(dict(row))

    # 3. properties.csv
    print("Exporting properties.csv...")
    cursor.execute("SELECT * FROM properties")
    rows = cursor.fetchall()
    if rows:
        with open(f"{results_dir}/properties.csv", "w", newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            for row in rows:
                writer.writerow(dict(row))
                
    # 4. trans.csv (transactions)
    print("Exporting trans.csv...")
    try:
        cursor.execute("SELECT * FROM transactions")
        rows = cursor.fetchall()
        if rows:
            with open(f"{results_dir}/trans.csv", "w", newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                for row in rows:
                    writer.writerow(dict(row))
        else:
            # Create empty file with header if no transactions
            with open(f"{results_dir}/trans.csv", "w", newline='', encoding='utf-8') as f:
                f.write("transaction_id,buyer_id,seller_id,board_id,price,date\n")
    except Exception as e:
        print(f"Error exporting trans.csv: {e}")
        
    # 5. console_log.txt (Copy current log)
    print("Copying console_log.txt...")
    try:
        if os.path.exists("simulation_run.log"):
            with open("simulation_run.log", "r", encoding='utf-8') as src:
                content = src.read()
            with open(f"{results_dir}/console_log.txt", "w", encoding='utf-8') as dst:
                dst.write(content)
    except Exception as e:
        print(f"Error copying log: {e}")

    conn.close()
    print(f"Legacy CSVs exported to {results_dir}/")

# --- Metric Reports (Markdown) ---
def generate_agent_personas(report_dir=REPORT_DIR):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT agent_id, name, age, occupation, background_story, housing_need, selling_motivation FROM agents")
    
    content = "# Agent Personas Report\n\n"
    for row in cursor.fetchall():
        content += f"## Agent {row[0]}: {row[1]} ({row[2]}岁)\n"
        content += f"- **Occupation**: {row[3]}\n"
        content += f"- **Background**: {row[4]}\n"
        content += f"- **Housing Need**: {row[5]}\n"
        content += f"- **Selling Motivation**: {row[6]}\n"
        content += "---\n"
        
    with open(f"{report_dir}/agent_personas.md", "w", encoding='utf-8') as f:
        f.write(content)
    print(f"Generated {report_dir}/agent_personas.md")
    conn.close()

def generate_negotiations(report_dir=REPORT_DIR):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT negotiation_id, buyer_id, seller_id, property_id, success, log, final_price FROM negotiations")
    
    content = "# Negotiation Logs\n\n"
    for row in cursor.fetchall():
        status = "✅ SUCCESS" if row[4] else "❌ FAILED"
        price = f"${row[6]:,.0f}" if row[6] else "N/A"
        content += f"## Negotiation #{row[0]} ({status})\n"
        content += f"**Buyer**: {row[1]} | **Seller**: {row[2]} | **Property**: {row[3]} | **Final Price**: {price}\n\n"
        content += "### Dialogue History\n"
        
        try:
            logs = json.loads(row[5])
            for entry in logs:
                party = entry.get('party', 'UNKNOWN').upper()
                action = entry.get('action', 'Unknown')
                price_call = entry.get('price', 0)
                reason = entry.get('content', '') or entry.get('reason', '')
                
                content += f"- **{party}** ({action} @ ${price_call:,.0f}): {reason}\n"
        except:
             content += f"Raw Log: {row[5]}\n"
        
        content += "\n---\n"

    with open(f"{report_dir}/negotiations.md", "w", encoding='utf-8') as f:
        f.write(content)
    print(f"Generated {report_dir}/negotiations.md")
    conn.close()

def generate_decisions(report_dir=REPORT_DIR):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT month, agent_id, decision, reason, thought_process FROM decision_logs ORDER BY month, agent_id")
    
    content = "# Decision Logs (Thoughts)\n\n"
    current_month = -1
    for row in cursor.fetchall():
        if row[0] != current_month:
            content += f"\n## Month {row[0]}\n"
            current_month = row[0]
            
        content += f"### Agent {row[1]} -> {row[2]}\n"
        content += f"**Reasoning**: {row[3]}\n"
        content += "\n"

    with open(f"{report_dir}/decisions.md", "w", encoding='utf-8') as f:
        f.write(content)
    print(f"Generated {report_dir}/decisions.md")
    conn.close()

def generate_market_report(report_dir=REPORT_DIR):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    content = "# Market Report\n\n"
    
    # Overview
    cursor.execute("SELECT COUNT(*), AVG(base_value) FROM properties")
    row = cursor.fetchone()
    content += f"## Overview\n"
    val = row[1] if row[1] else 0
    content += f"- Total Properties: {row[0]}\n"
    content += f"- Avg Value: ${val:,.0f}\n\n"
    
    # Listings
    cursor.execute("SELECT COUNT(*), AVG(listed_price) FROM property_listings WHERE status='active'")
    row = cursor.fetchone()
    price = row[1] if row[1] else 0
    content += f"## Active Listings\n"
    content += f"- Count: {row[0]}\n"
    content += f"- Avg List Price: ${price:,.0f}\n\n"
    
    # Transactions
    try:
        cursor.execute("SELECT * FROM transactions")
        txs = cursor.fetchall()
        content += f"## Transactions ({len(txs)})\n"
        for tx in txs:
            content += f"- {tx}\n"
    except:
        content += "No transactions table found (or empty).\n"

    with open(f"{report_dir}/market_report.md", "w", encoding='utf-8') as f:
        f.write(content)
    print(f"Generated {report_dir}/market_report.md")
    conn.close()

def generate_all_reports():
    """Main entry point for report generation."""
    print("Generating Reports & Exports...")
    
    # 1. Setup Timestamps
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = f"results/result_{timestamp}"
    ensure_dir(results_dir)
    ensure_dir(REPORT_DIR)
    
    # 2. Generate Reports
    generate_agent_personas(REPORT_DIR)
    generate_negotiations(REPORT_DIR)
    generate_decisions(REPORT_DIR)
    generate_market_report(REPORT_DIR)
    
    # 3. Export CSVs
    export_legacy_csvs(results_dir)
    
    print(f"Done! Reports saved in {REPORT_DIR}/ and Data in {results_dir}/")

if __name__ == "__main__":
    generate_all_reports()

