
import logging
import os
import shutil

from config.config_loader import SimulationConfig
from database import init_db
from simulation_runner import SimulationRunner

# Configure logging
logging.basicConfig(level=logging.INFO)


def run_auto():
    # Setup paths
    proj_dir = "v2_project_auto_test"
    if os.path.exists(proj_dir):
        shutil.rmtree(proj_dir)
    os.makedirs(proj_dir)

    config_path = os.path.join(proj_dir, "config.yaml")
    db_path = os.path.join(proj_dir, "simulation.db")

    # Copy baseline config
    if os.path.exists("config/baseline.yaml"):
        shutil.copy("config/baseline.yaml", config_path)
    else:
        print("Warning: config/baseline.yaml not found, creating empty config")
        with open(config_path, "w") as f:
            f.write("")

    # Initialize DB (This triggers migration)
    print(f"Initializing DB at {db_path}...")
    init_db(db_path)

    # Load Config
    config = SimulationConfig(config_path)

    # Initialize Runner
    runner = SimulationRunner(
        agent_count=50,  # Small count for speed
        months=2,
        seed=42,
        resume=False,
        config=config,
        db_path=db_path
    )

    # Run
    print("Starting simulation run...")
    runner.run()
    print("Simulation run complete.")


if __name__ == "__main__":
    run_auto()
