import os
import shutil
import datetime

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

