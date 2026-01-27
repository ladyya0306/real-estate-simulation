
import sys
import os
import time

sys.path.append(os.getcwd())

from simulation_runner import SimulationRunner

def run_demo():
    print("🚀 Starting Final End-to-End Simulation Demo")
    print("===========================================")
    
    # Configuration
    AGENT_COUNT = 10000  # Large enough to see patterns, small enough for quick demo
    MONTHS = 12
    SEED = 2026
    
    print(f"👥 Agents: {AGENT_COUNT}")
    print(f"📅 Duration: {MONTHS} Months")
    print(f"🎲 Seed: {SEED}")
    print("-------------------------------------------")
    
    start_time = time.time()
    
    runner = SimulationRunner(agent_count=AGENT_COUNT, months=MONTHS, seed=SEED)
    runner.run()
    
    duration = time.time() - start_time
    print("\n===========================================")
    print(f"🎉 Simulation Completed in {duration:.2f} seconds")
    print(f"📂 Results saved to 'results/' directory")
    print("Please check the generated 'wealth_distribution.png' and markdown reports.")

if __name__ == "__main__":
    run_demo()
