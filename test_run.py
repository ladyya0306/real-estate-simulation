from simulation_runner import SimulationRunner
from config.config_loader import SimulationConfig
import project_manager
import logging
import sys

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

try:
    # Setup
    proj_dir, config_path, db_path = project_manager.create_new_project("config/baseline.yaml")
    print(f"Project Created: {proj_dir}")

    config = SimulationConfig(config_path)

    # Run Simulation
    print("Starting Runner...")
    runner = SimulationRunner(
        agent_count=50, 
        months=2, 
        seed=42, 
        resume=False, 
        config=config, 
        db_path=db_path
    )
    runner.run()
    print("Run Complete.")

except Exception as e:
    import traceback
    traceback.print_exc()
    sys.exit(1)
