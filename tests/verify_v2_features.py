import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import shutil
from simulation_runner import SimulationRunner
import scripts.export_results as exporter

def main():
    print("🧪 Starting Verification Test...")
    
    # 1. Clean DB (optional, but good for test)
    if os.path.exists('real_estate_stage2.db'):
        os.remove('real_estate_stage2.db')
        
    # 2. Run New Simulation (Month 1-2)
    print("Step 1: Running New Simulation (Months 1-2)")
    config = {'volatility': 0.0, 'shock_prob': 0.0, 'shock_mag': 0.0} # Stable
    runner = SimulationRunner(agent_count=20, months=2, resume=False, config=config)
    runner.run()
    
    # 3. Export
    print("Step 2: Exporting Results")
    exporter.export_data()
    
    # 4. Resume Simulation (Month 3-4)
    print("Step 3: Resuming Simulation (Months 3-4)")
    runner2 = SimulationRunner(agent_count=0, months=2, resume=True, config=config) # agent_count ignored
    runner2.run()
    
    print("✅ Verification Script Completed without Error.")

if __name__ == "__main__":
    main()
