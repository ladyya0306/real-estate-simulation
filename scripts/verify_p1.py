
import sys
import os
import sqlite3
import pandas as pd
from collections import Counter

sys.path.append(os.getcwd())

from simulation_runner import SimulationRunner
from config.agent_tiers import AGENT_TIER_CONFIG

def verify_p1():
    print("Verifying P1 (Batch Initialization)...")
    
    # Init with 1000 agents to check distribution
    runner = SimulationRunner(agent_count=1000, months=1, seed=42)
    runner.initialize()
    
    conn = sqlite3.connect('real_estate_stage2.db')
    
    # 1. Check Roles
    df_agents = pd.read_sql_query("SELECT * FROM agents", conn)
    role_counts = df_agents['role'].value_counts()
    print("\nRole Distribution:")
    print(role_counts)
    
    if len(role_counts) != 1 or 'OBSERVER' not in role_counts:
        print("❌ FAILED: Not all agents are OBSERVERs")
    else:
        print("✅ PASS: All agents are OBSERVERs")
        
    # 2. Check Use of Chinese Names
    names = df_agents['name'].tolist()
    chinese_char_count = sum(1 for n in names if any('\u4e00' <= char <= '\u9fff' for char in n))
    print(f"\nChinese Names: {chinese_char_count}/{len(names)}")
    if chinese_char_count < len(names) * 0.9:
         print("❌ FAILED: Names do not appear to be Chinese")
    else:
         print("✅ PASS: Chinese Name Generator working")
         
    # 3. Check Property Distribution (Rich get houses)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.monthly_income, COUNT(p.property_id) as prop_count
        FROM agents a
        LEFT JOIN properties p ON a.agent_id = p.owner_id
        GROUP BY a.agent_id
    """)
    data = cursor.fetchall()
    
    # Segment by income to approximate tiers
    rich_props = [row[1] for row in data if row[0] >= 500000/12] # High income
    poor_props = [row[1] for row in data if row[0] < 100000/12] # Low income
    
    avg_rich_props = sum(rich_props) / max(len(rich_props), 1)
    avg_poor_props = sum(poor_props) / max(len(poor_props), 1)
    
    print(f"\nAvg Props (Rich): {avg_rich_props:.2f}")
    print(f"Avg Props (Poor): {avg_poor_props:.2f}")
    
    if avg_rich_props > avg_poor_props:
        print("✅ PASS: Rich agents have more properties")
    else:
        print("❌ FAILED: Property distribution issue")

    # 4. Check Templates Applied
    print("\nSample Occupations:")
    print(df_agents['occupation'].value_counts().head(5))
    
    expected_occupations = ["上市公司高管", "互联网大厂P8", "公务员", "工厂技工"]
    found = any(occ in df_agents['occupation'].values for occ in expected_occupations)
    if found:
        print("✅ PASS: Templates applied (found expected occupations)")
    else:
        print("❌ FAILED: Templates no applied")
        
    conn.close()

if __name__ == "__main__":
    verify_p1()
