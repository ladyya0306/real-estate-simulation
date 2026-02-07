from simulation_runner import SimulationRunner
from database_v2 import init_db
from config.config_loader import SimulationConfig
import os
import sqlite3
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

db_path = os.path.abspath("test_v2_gen.db")
if os.path.exists(db_path): os.remove(db_path)

print(f"Initializing V2 DB at {db_path}...")
# Init V2 Schema
init_db(db_path)

print("Initializing Runner...")
# Create a dummy config
config = SimulationConfig("config/baseline.yaml") # Assumes this file exists
runner = SimulationRunner(agent_count=20, months=1, config=config)
# Force db_path override (usually done via config passing in real app, strictly handled in init)
# We need to make sure runner uses THIS db_path.
# In modified runner, self.db_path = getattr(config, 'db_path', ...)
# So we update config object
runner.db_path = db_path

print("Running Initialize (Generation)...")
runner.initialize()

# Verify
conn = sqlite3.connect(db_path)
c = conn.cursor()

print("\n--- Verification ---")
c.execute("SELECT count(*) FROM agents_static")
count_static = c.fetchone()[0]
print("agents_static count:", count_static)

c.execute("SELECT count(*) FROM agents_finance")
count_finance = c.fetchone()[0]
print("agents_finance count:", count_finance)

if count_static == 20 and count_finance == 20:
    print("SUCCESS: Agent counts match.")
else:
    print("FAILURE: Agent counts mismatch.")

c.execute("SELECT * FROM agents_static LIMIT 1")
row = c.fetchone()
print(f"Agent Static Sample: {row}")

# Check investment_style
if len(row) >= 8: # index 7 is investment_style
    print(f"Investment Style: {row[7]}")
else:
    print("Investment Style column index issue?")

# Check properties (V1 table populated?)
c.execute("SELECT count(*) FROM properties") # V1 table created in runner
count_props = c.fetchone()[0]
print("properties (V1) count:", count_props)

conn.close()

# Cleanup
# if os.path.exists(db_path): os.remove(db_path)
