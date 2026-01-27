
import sys
import os
import re

sys.path.append(os.getcwd())

from simulation_runner import SimulationRunner

def verify_macro():
    print("Verifying P2 (Dynamic Macro Sentiment)...")
    
    # Run for 3 months to see transition from Stable (M1-2) to Optimistic (M3)
    runner = SimulationRunner(agent_count=100, months=3, seed=123)
    runner.run()
    
    # Check log file content
    try:
        with open("simulation_run.log", "r", encoding="utf-8") as f:
            content = f.read()
            
        print("\n--- Log Scan ---")
        
        # Check Month 1 Stable
        m1 = re.search(r"Month 1 \[STABLE\]", content)
        if m1: print("✅ Month 1 is STABLE")
        else: print("❌ Month 1 sentiment missing/wrong")
        
        # Check Month 3 Optimistic
        m3 = re.search(r"Month 3 \[OPTIMISTIC\]", content)
        if m3: print("✅ Month 3 is OPTIMISTIC")
        else: print("❌ Month 3 sentiment missing/wrong")
        
        # Check Prompt Context in Agent Behavior (Harder to check in log unless we debug log it)
        # But if log has 'Macro: ...' it means it fetched correctly.
        
    except FileNotFoundError:
        print("❌ Log file not found")

if __name__ == "__main__":
    verify_macro()
