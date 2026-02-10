
import sqlite3
import sys

# Force UTF-8
sys.stdout.reconfigure(encoding='utf-8')

db_path = r'd:\GitProj\oasis-main\results\run_20260209_000256\simulation.db'
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print(f"Analyzing {db_path}...")

# 1. Check Role Decisions
cursor.execute("SELECT decision, COUNT(*) FROM decision_logs WHERE event_type='ROLE_DECISION' GROUP BY decision")
role_stats = dict(cursor.fetchall())
print(f"Role Decisions: {role_stats}")

# 2. Check Market Bulletin
print("\nMarket Bulletin Check:")
try:
    cursor.execute("SELECT month, policy_news, llm_analysis FROM market_bulletin ORDER BY month DESC LIMIT 2")
    bulletins = cursor.fetchall()
    if bulletins:
        for b in bulletins:
            print(f"Bulletin Month {b['month']}:")
            p_news = b['policy_news']
            l_analysis = b['llm_analysis']
            print(f"  Policy News: {p_news[:50]}..." if p_news else "  Policy News: EMPTY")
            print(f"  LLM Analysis: {l_analysis[:100]}..." if l_analysis else "  LLM Analysis: EMPTY")
    else:
        print("No Market Bulletin found.")
except Exception as e:
    print(f"Error checking bulletin: {e}")

# 3. Check Transactions & Negotiations
cursor.execute("SELECT COUNT(*) FROM transactions")
tx_count = cursor.fetchone()[0]
print(f"\nTransaction Count: {tx_count}")

cursor.execute("SELECT success, COUNT(*) FROM negotiations GROUP BY success")
neg_stats = dict(cursor.fetchall())
print(f"Negotiations: {neg_stats}")

# 4. Analyze Failed Negotiations
print("\nFailed Negotiations (Sample):")
cursor.execute("SELECT negotiation_id, buyer_id, seller_id, final_price, reason, log FROM negotiations WHERE success=0 LIMIT 3")
failed_negs = cursor.fetchall()
for neg in failed_negs:
    print(f"NegID: {neg['negotiation_id']}, Buyer: {neg['buyer_id']}, Seller: {neg['seller_id']}")
    print(f"  Final Price: {neg['final_price']}")
    print(f"  Reason: {neg['reason']}")
    # print(f"  Log: {neg['log']}") # Too verbose maybe

conn.close()
