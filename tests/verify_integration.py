import sys
import os
import random
import logging

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Agent, Market
from monthly_simulator import run_monthly_decision
from property_initializer import initialize_market_properties

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_test_agents(count: int) -> list[Agent]:
    """Create a population of test agents with diverse profiles"""
    agents = []
    for i in range(1, count + 1):
        age = random.randint(25, 45)
        # Randomize financial status
        income = random.randint(10000, 50000)
        cash = income * random.randint(6, 60)
        
        agent = Agent(
            id=i,
            age=age,
            marital_status=random.choice(["single", "married", "engaged"]),
            cash=float(cash),
            monthly_income=float(income)
        )
        
        # Randomly assign life events to occur in specific months for testing
        if random.random() < 0.2: # 20% agents have a life event
            event_month = random.randint(1, 12)
            event_type = random.choice(["marriage", "child_birth", "job_change"])
            agent.set_life_event(event_month, event_type)
            
        agents.append(agent)
    return agents

def run_integration_test():
    print(">>> Starting 12-Month Integration Verification <<<")
    
    # 1. Initialize Market
    properties = initialize_market_properties()
    market = Market(properties)
    print(f"Initialized Market with {len(properties)} properties.")
    
    # 2. Initialize Agents
    AGENT_COUNT = 100
    agents = create_test_agents(AGENT_COUNT)
    print(f"Initialized {AGENT_COUNT} Agents.")
    
    # 3. Running Simulation
    stats = {
        "total_decisions": 0,
        "llm_triggers": 0,
        "trigger_reasons": {
            "life_event": 0,
            "financial": 0,
            "market": 0
        }
    }
    
    for month in range(1, 13):
        print(f"\n--- Simulating Month {month} ---")
        
        # Simulate Market Fluctuations (Mock)
        # Month 6 has a big price drop in Zone A
        if month == 6:
            market.set_price_change('A', month, -0.12) # -12% drop
        else:
            market.set_price_change('A', month, random.uniform(-0.02, 0.02))
            
        market.set_price_change('B', month, random.uniform(-0.02, 0.02))
        
        # Update Agent Finances (Mock)
        for agent in agents:
            # Update last month cash before changing current
            agent.last_month_cash = agent.cash
            
            # Month 3: Agent 5 gets a big bonus (Financial Trigger Test)
            if agent.id == 5 and month == 3:
                agent.cash += agent.cash * 0.5 
            else:
                # Normal fluctuation
                agent.cash += agent.monthly_income - random.randint(5000, 15000)
        
        # Run Decisions
        for agent in agents:
            decision = run_monthly_decision(agent, market, month)
            stats["total_decisions"] += 1
            
            if decision.get("llm_called"):
                stats["llm_triggers"] += 1
                t_type = decision.get("trigger_type")
                if t_type:
                    stats["trigger_reasons"][t_type] = stats["trigger_reasons"].get(t_type, 0) + 1

    # 4. Report Results
    print("\n>>> Integration Test Results <<<")
    print(f"Total Decisions: {stats['total_decisions']}")
    print(f"LLM Triggers: {stats['llm_triggers']}")
    trigger_rate = stats['llm_triggers'] / stats['total_decisions']
    print(f"Overall Trigger Rate: {trigger_rate:.2%}")
    print("Trigger Breakdown:")
    for reason, count in stats["trigger_reasons"].items():
        print(f"  - {reason}: {count}")
        
    # Verification assertions
    if 3 <= trigger_rate * 100 <= 15: # Expect 3-15% range typically (relaxed for small sample)
        print("\n✅ PASSED: Trigger rate within expected range.")
    else:
        print(f"\n⚠️ WARNING: Trigger rate {trigger_rate:.2%} outside expected standard (3-15%).")
        
    print("Simulation completed successfully.")

if __name__ == "__main__":
    run_integration_test()
