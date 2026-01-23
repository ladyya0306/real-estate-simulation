"""Quick debug script to test property matching"""
import sys
sys.path.insert(0, 'd:\\GitProj\\oasis-main')

from simulation_runner import SimulationRunner

runner = SimulationRunner(agent_count=10, months=1)
runner.initialize()

# Check properties
print(f"Total properties in market: {len(runner.market.properties)}")
print(f"First 3 property IDs: {[p['property_id'] for p in runner.market.properties[:3]]}")

# Check owned properties
owned_count = sum(len(a.owned_properties) for a in runner.agents)
print(f"\nTotal owned properties: {owned_count}")
for agent in runner.agents[:3]:
    if agent.owned_properties:
        print(f"Agent {agent.id} owns property: {agent.owned_properties[0]['property_id']}")
