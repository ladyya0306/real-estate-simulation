
import logging
import os
import shutil

from config.config_loader import SimulationConfig
from simulation_runner import SimulationRunner

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def run_verification():
    print("=== Starting Verification Simulation (Programmatic) ===")

    # 1. Setup Project
    proj_name = "test_run_batch_match_v2"
    proj_dir = os.path.join("results", proj_name)

    if os.path.exists(proj_dir):
        try:
            shutil.rmtree(proj_dir)
        except:
            pass
    if not os.path.exists(proj_dir):
        os.makedirs(proj_dir)

    # 2. Config
    config_path = "config/baseline.yaml"
    config = SimulationConfig(config_path)

    # Override for testing
    agent_count = 50
    months = 2

    config.update('simulation.agent_count', agent_count)
    config.update('simulation.months', months)

    # Save user config
    user_config_path = os.path.join(proj_dir, "user_config.yaml")
    config.save(user_config_path)

    # 3. DB Path
    db_path = os.path.join(proj_dir, "simulation.db")

    # 4. Instantiate Runner (Correct Signature)
    # def __init__(self, agent_count=50, months=12, seed=42, resume=False, config=None, db_path=None):
    runner = SimulationRunner(
        agent_count=agent_count,
        months=months,
        seed=42,
        resume=False,
        config=config,
        db_path=db_path
    )

    # 5. Run
    try:
        runner.run()
        print(f"\n=== Simulation Complete: {proj_dir} ===")
    except Exception as e:
        print(f"\n❌ Simulation Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_verification()
