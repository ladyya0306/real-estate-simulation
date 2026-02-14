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
import datetime
import os
import shutil

RESULTS_DIR = "results"

def list_projects():
    if not os.path.exists(RESULTS_DIR):
        return []
    projects = [os.path.join(RESULTS_DIR, d) for d in os.listdir(RESULTS_DIR) if os.path.isdir(os.path.join(RESULTS_DIR, d))]
    return sorted(projects)

def load_project_paths(project_dir):
    config_path = os.path.join(project_dir, "config.yaml")
    # Find DB file
    if not os.path.exists(project_dir):
        return config_path, os.path.join(project_dir, "simulation.db")

    db_files = [f for f in os.listdir(project_dir) if f.endswith(".db")]
    db_path = os.path.join(project_dir, db_files[0]) if db_files else os.path.join(project_dir, "simulation.db")
    return config_path, db_path

def create_new_project(template_config_path):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    proj_dir = os.path.join(RESULTS_DIR, f"run_{timestamp}")
    os.makedirs(proj_dir, exist_ok=True)

    # Copy config
    new_config_path = os.path.join(proj_dir, "config.yaml")
    if os.path.exists(template_config_path):
        shutil.copy(template_config_path, new_config_path)
    else:
        # Try finding baseline in default location if template not found
        default_baseline = "config/baseline.yaml"
        if os.path.exists(default_baseline):
             shutil.copy(default_baseline, new_config_path)
        else:
            with open(new_config_path, 'w') as f:
                f.write("# Empty Config")

    db_path = os.path.join(proj_dir, "simulation.db")
    return proj_dir, new_config_path, db_path
