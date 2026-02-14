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
