import sys
import os
import random
import logging
import numpy as np

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Agent, Market
from monthly_simulator import run_monthly_decision
from property_initializer import initialize_market_properties

# Configure logging
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_test_agents(count: int) -> list[Agent]:
    """Create a population of test agents"""
    agents = []
    for i in range(1, count + 1):
        age = random.randint(25, 45)
        income = random.randint(10000, 50000)
        cash = income * random.randint(6, 60)
        
        agent = Agent(
            id=i,
            age=age,
            marital_status=random.choice(["single", "married", "engaged"]),
            cash=float(cash),
            monthly_income=float(income)
        )
        
        # Life events (approx 2% per month)
        for m in range(1, 13):
            if random.random() < 0.02: 
                event_type = random.choice(["marriage", "child_birth", "job_change"])
                agent.set_life_event(m, event_type)
            
        agents.append(agent)
    return agents

def run_integration_test_tuned():
    print(">>> Starting Tuned 12-Month Integration Verification <<<")
    
    # 1. Initialize
    properties = initialize_market_properties()
    market = Market(properties)
    agents = create_test_agents(100) # 100 Agents
    
    stats = {
        "total_decisions": 0,
        "llm_triggers": 0,
        "trigger_reasons": {
            "life_event": 0,
            "financial": 0,
            "market": 0
        }
    }
    
    # Volatility Parameters
    MARKET_VOLATILITY = 0.05  # Standard deviation for monthly price change
    INCOME_VOLATILITY = 0.40  # Probability of significant income shock
    
    for month in range(1, 13):
        print(f"--- Month {month} ---")
        
        # 1. Market Simulation (Biased Random Walk)
        # We want occasional shocks > 10%
        for zone in ['A', 'B']:
            # Normal fluctuation
            change = np.random.normal(0, 0.03) 
            
            # Occasional Shock (10% chance)
            if random.random() < 0.10:
                change += np.random.choice([-0.12, 0.12]) 
                
            market.set_price_change(zone, month, change)
            print(f"  Zone {zone} Price Change: {change:.2%}")
        
        # 2. Agent Finance Simulation
        for agent in agents:
            agent.last_month_cash = agent.cash
            
            # Income Flow
            income_this_month = agent.monthly_income
            
            # Financial Shock (Bonus or Loss) - 2% chance of huge change
            if random.random() < 0.02:
                # 30-50% change (Bonus or Emergency Spend)
                bonus = agent.cash * random.uniform(0.35, 0.50) * random.choice([1, -1])
                agent.cash += bonus
            
            # Regular savings
            savings = income_this_month * 0.4 
            agent.cash += savings
        
        # 3. Decision Loop
        for agent in agents:
            decision = run_monthly_decision(agent, market, month)
            stats["total_decisions"] += 1
            
            if decision.get("llm_called"):
                stats["llm_triggers"] += 1
                t_type = decision.get("trigger_type")
                if t_type:
                    stats["trigger_reasons"][t_type] = stats["trigger_reasons"].get(t_type, 0) + 1

    # Report
    print("\n>>> Tuned Results <<<")
    total = stats['total_decisions']
    triggers = stats['llm_triggers']
    rate = triggers / total
    
    print(f"Total Decisions: {total}")
    print(f"LLM Triggers: {triggers}")
    print(f"Trigger Rate: {rate:.2%}")
    print("Breakdown:")
    for reason, count in stats["trigger_reasons"].items():
        print(f"  - {reason}: {count} ({count/total:.2%})")
        
    if 0.03 <= rate <= 0.08:
        print("\n✅ SUCCESS: Trigger rate in target range (3-8%)")
    else:
        print(f"\n⚠️ NOTE: Trigger rate {rate:.2%} (Target: ~5%)")

if __name__ == "__main__":
    run_integration_test_tuned()
