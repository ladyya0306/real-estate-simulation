from simulation_runner import SimulationRunner
from config.config_loader import SimulationConfig
import os

def verify_system():
    print("Beginning System Integrity Check...")
    db_path = "integrity_check.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    try:
        # Load Config
        print("1. Loading Configuration...")
        config = SimulationConfig()
        
        # Initialize Runner (Small scale: 5 agents, 1 month)
        print("2. Initializing Simulation Runner (5 Agents, 1 Month)...")
        runner = SimulationRunner(
            agent_count=5,
            months=1,
            seed=42,
            config=config,
            db_path=db_path
        )
        
        # Run Simulation
        print("3. Running Simulation...")
        runner.run()
        
        print("\n✅ SYSTEM INTEGRITY VERIFIED: Simulation completed successfully without errors.")
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: System integrity check failed!")
        print(f"Error details: {e}")
        raise e
    finally:
        if runner:
            try:
                runner.close()
            except:
                pass
        if os.path.exists(db_path):
            os.remove(db_path)

if __name__ == "__main__":
    verify_system()
