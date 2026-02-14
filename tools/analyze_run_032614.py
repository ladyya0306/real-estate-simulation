import sqlite3
import json
import random
import os

DB_PATH = r"d:\GitProj\oasis-main\results\run_20260214_032614\simulation.db"
REPORT_PATH = r"d:\GitProj\oasis-main\analysis_report_032614.md"

def analyze_run():
    if not os.path.exists(DB_PATH):
        print(f"Error: DB not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("# Simulation Analysis Report (Run 032614)\n\n")

        # --- 1. Market Bulletin Analysis ---
        f.write("## 1. Market Bulletin Analysis\n\n")
        try:
            cursor.execute("SELECT month, avg_price, trend_signal, llm_analysis FROM market_bulletin ORDER BY month")
            bulletins = cursor.fetchall()
            if not bulletins:
                f.write("*No market bulletins found.*\n")
            else:
                for b in bulletins:
                    f.write(f"### Month {b['month']}\n")
                    f.write(f"- **Avg Price**: {b['avg_price']:,.0f}\n")
                    f.write(f"- **Trend**: {b['trend_signal']}\n")
                    analysis = b['llm_analysis']
                    # Parse if JSON, otherwise print nicely
                    try:
                        import ast
                        if analysis.startswith("```json"):
                            analysis = analysis.replace("```json", "").replace("```", "")
                        
                        analysis_dict = ast.literal_eval(analysis)
                        if isinstance(analysis_dict, dict):
                            f.write(f"- **Core View**: {analysis_dict.get('核心观点', 'N/A')}\n")
                            f.write(f"- **Interpretation**: {analysis_dict.get('环境解读', 'N/A')}\n")
                        else:
                            f.write(f"- **Analysis (Raw)**: {analysis}\n")
                    except Exception as e:
                        f.write(f"- **Analysis (Raw - Parse Error)**: {analysis} (Error: {e})\n")
                    f.write("\n")
        except Exception as e:
            f.write(f"Error reading bulletins: {e}\n")

        # --- 2. Agent Profiles ---
        f.write("\n## 2. Agent Profiles (Random Sample of 30)\n\n")
        
        try:
            # Get all agent IDs
            cursor.execute("SELECT agent_id FROM agents_static")
            all_ids = [r['agent_id'] for r in cursor.fetchall()]
            
            sample_size = min(len(all_ids), 30)
            selected_ids = random.sample(all_ids, sample_size)
            selected_ids.sort()

            for agent_id in selected_ids:
                try:
                    f.write(f"### Agent {agent_id}\n")
                    
                    # Identity
                    cursor.execute("SELECT * FROM agents_static WHERE agent_id=?", (agent_id,))
                    static = cursor.fetchone()
                    if static:
                        age = 2024 - static['birth_year'] if static['birth_year'] else "N/A"
                        f.write(f"**Identity**: {static['name']} ({age}), {static['occupation']}\n")
                        f.write(f"**Style**: {static['investment_style']}\n")
                    
                    # Financials
                    cursor.execute("SELECT * FROM agents_finance WHERE agent_id=?", (agent_id,))
                    finance = cursor.fetchone()
                    if finance:
                        f.write(f"**Financials**: Cash: {finance['cash']:,.0f}, Net Worth: {finance['total_assets']:,.0f}, Debt: {finance['total_debt']:,.0f}, Cashflow: {finance['net_cashflow']:,.0f}\n")
                    
                    # Transaction History
                    cursor.execute("SELECT * FROM transactions WHERE buyer_id=? OR seller_id=?", (agent_id, agent_id))
                    txs = cursor.fetchall()
                    if txs:
                        f.write("**Transactions**:\n")
                        for tx in txs:
                            role = "Buyer" if tx['buyer_id'] == agent_id else "Seller"
                            f.write(f"- Month {tx['month']}: {role} for Property {tx['property_id']} @ {tx['final_price']:,.0f}\n")
                    else:
                        f.write("**Transactions**: None\n")
                        
                    # Bidding History (Ghost Transaction Check)
                    try:
                        cursor.execute("SELECT * FROM property_buyer_matches WHERE buyer_id=?", (agent_id,))
                        bids = cursor.fetchall()
                        if bids:
                            f.write(f"**Bidding Activity**: Matched {len(bids)} times.\n")
                    except:
                        f.write("**Bidding Activity**: table not found (check DB version)\n")

                    # Thought Process (First, Transaction-related, Last)
                    f.write("**Thought Process Snippets**:\n")
                    cursor.execute("SELECT month, event_type, decision, reason, context_metrics, thought_process FROM decision_logs WHERE agent_id=? ORDER BY month", (agent_id,))
                    logs = cursor.fetchall()
                    
                    if not logs:
                        f.write("- No decision logs.\n")
                    else:
                        # Show first
                        first = logs[0]
                        f.write(f"- [Month {first['month']} {first['event_type']}] {first['decision']}: {first['reason']}\n")
                        
                        # Show any transaction related
                        important_logs = [l for l in logs if l['event_type'] in ('BID', 'LIST_PROPERTY', 'NEGOTIATION', 'ACCEPT_OFFER')]
                        for l in important_logs:
                            f.write(f"- [Month {l['month']} {l['event_type']}] {l['decision']}: {l['reason']}\n")

                        # Show last if different
                        last = logs[-1]
                        if last['log_id'] != first['log_id'] and last not in important_logs:
                            f.write(f"- [Month {last['month']} {last['event_type']}] {last['decision']}: {last['reason']}\n")
                    
                    f.write("\n---\n\n")
                except Exception as e:
                    f.write(f"Error analyzing agent {agent_id}: {e}\n")

        except Exception as e:
            f.write(f"Error querying agents: {e}\n")

        # --- 3. Rental Check ---
        f.write("\n## 3. Rental Logic Check\n")
        try:
            cursor.execute("SELECT COUNT(*) FROM rental_transactions")
            count = cursor.fetchone()[0]
            f.write(f"Rental Transactions Table Count: {count}\n")
            f.write("Note: Rental transactions are currently abstract and modify `agents_finance` directly without creating transaction records.\n")
        except Exception as e:
            f.write(f"Error checking rental table: {e}\n")

    conn.close()
    print(f"Report written to {REPORT_PATH}")

if __name__ == "__main__":
    analyze_run()
