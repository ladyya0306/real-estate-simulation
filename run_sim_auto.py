# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========

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
        with open(config_path, "w") as f: f.write("")

    # Initialize DB (This triggers migration)
    print(f"Initializing DB at {db_path}...")
    init_db(db_path)

    # Load Config
    config = SimulationConfig(config_path)

    # Initialize Runner
    runner = SimulationRunner(
        agent_count=50, # Small count for speed
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
