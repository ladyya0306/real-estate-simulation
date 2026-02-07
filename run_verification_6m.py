
import sys
import os
import logging
from config.config_loader import SimulationConfig
from simulation_runner import SimulationRunner
import project_manager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', encoding='utf-8')

def main():
    print("Starting 6-Month Verification Run...")
    
    # 1. Setup Project
    proj_dir, config_path, db_path = project_manager.create_new_project("config/baseline.yaml")
    print(f"Project Created: {proj_dir}")
    
    # 2. Configure
    config = SimulationConfig(config_path)
    config.update('simulation.random_seed', 42) # Fixed seed
    config.save()
    
    # 3. Initialize Runner (6 Months)
    runner = SimulationRunner(config=config, months=6)
    
    # 4. Run
    runner.run()
    
    print("Simulation Complete.")

if __name__ == "__main__":
    main()
