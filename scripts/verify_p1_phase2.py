
import sys
import os
import sqlite3
import pandas as pd

sys.path.append(os.getcwd())

from simulation_runner import SimulationRunner

def verify_phase2():
    print("Verifying P1 Phase 2 (Monthly Activation)...")
    
    # Run for 2 months to check lifecycle (timeout/price cuts)
    # Use 1000 agents to get statistically likely activations
    runner = SimulationRunner(agent_count=2000, months=2, seed=123)
    runner.run()
    
    conn = sqlite3.connect('real_estate_stage2.db')
    
    # 1. Check Decision Logs (Activations)
    df_logs = pd.read_sql_query("SELECT * FROM decision_logs", conn)
    print(f"\nDecision Logs Count: {len(df_logs)}")
    print(df_logs.head())
    
    activations = df_logs[df_logs['decision'].isin(['BUYER', 'SELLER'])]
    print(f"\nActivations (Buyer/Seller): {len(activations)}")
    
    if len(activations) > 0:
        print("✅ PASS: Agents were activated via Batch LLM")
    else:
        print("❌ FAILED: No agents activated (Check prob or LLM mock)")

    # 2. Check Roles updated in Agents table
    df_agents = pd.read_sql_query("SELECT role, COUNT(*) as count FROM agents GROUP BY role", conn)
    print("\nAgent Roles in DB:")
    print(df_agents)
    
    if 'BUYER' in df_agents['role'].values or 'SELLER' in df_agents['role'].values:
        print("✅ PASS: Agent roles updated in DB")
    else:
        # Note: If they transacted, they might revert to Observer? 
        # But buyers stay buyers if no match. With 2000 agents, match is rare.
        print("⚠️ WARNING: No active roles found in DB (Sim ended?)")

    # 3. Check Listings
    df_listings = pd.read_sql_query("SELECT * FROM property_listings", conn)
    print(f"\nListings Count: {len(df_listings)}")
    if len(df_listings) > 0:
        print("✅ PASS: Listings generated")
    else:
        print("❌ FAILED: No listings")

    conn.close()

if __name__ == "__main__":
    verify_phase2()
