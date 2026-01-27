
import sys
import os
import sqlite3

# Add project root to path
sys.path.append(os.getcwd())

from simulation_runner import SimulationRunner

def verify_p0():
    print("Verifying P0 Changes...")
    try:
        # Test Init with Seed
        runner = SimulationRunner(agent_count=10, months=1, seed=42)
        runner.initialize() # This drops and recreates tables
        print("Initialize successful.")
        
        # Check DB Schema
        conn = sqlite3.connect('real_estate_stage2.db')
        cursor = conn.cursor()
        
        # Check agents table
        cursor.execute("PRAGMA table_info(agents)")
        cols = [row[1] for row in cursor.fetchall()]
        if 'role' not in cols: 
            raise Exception("Missing 'role' in agents")
        if 'role_duration' not in cols: 
            raise Exception("Missing 'role_duration' in agents")
        print("✅ Agents table schema verified (role, role_duration present).")
        
        # Check properties table
        cursor.execute("PRAGMA table_info(properties)")
        cols = [row[1] for row in cursor.fetchall()]
        if 'bedrooms' in cols: 
            raise Exception("'bedrooms' still in properties")
        print("✅ Properties table schema verified ('bedrooms' removed).")
        
        # Check Indexes
        cursor.execute("PRAGMA index_list(agents)")
        indexes = [row[1] for row in cursor.fetchall()]
        if 'idx_agents_role' not in indexes: print("⚠️ idx_agents_role missing")
        else: print("✅ idx_agents_role present.")
        
        cursor.execute("PRAGMA index_list(properties)")
        indexes = [row[1] for row in cursor.fetchall()]
        if 'idx_properties_owner' not in indexes: print("⚠️ idx_properties_owner missing")
        else: print("✅ idx_properties_owner present.")

        # Test Run Month (Basic) - this exercises transaction engine without bedrooms
        print("Running Month 1 simulation...")
        runner.run_month(1)
        print("✅ Run Month 1 successful.")
        
        conn.close()
        print("\n🎉 ALL P0 VERIFICATIONS PASSED")
        
    except Exception as e:
        print(f"\n❌ P0 VERIFICATION FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_p0()
