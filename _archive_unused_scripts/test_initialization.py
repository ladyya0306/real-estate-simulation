
import sys
sys.stdout.reconfigure(encoding='utf-8')
import logging
import sqlite3
import os
import shutil
from services.agent_service import AgentService
from services.market_service import MarketService
from database import init_db

# Setup Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TEST_DB = "test_init_fix.db"

class MockConfig:
    def __init__(self):
        self.user_property_count = 50
        self.agent_count = 20
        self.negotiation = {'personality_weights': {'aggressive': 0.3, 'conservative': 0.3, 'balanced': 0.4}}
        self.property = {}
        self.market = {
            'zones': {
                'A': {'ratio': 0.5, 'price_range': [50000, 80000]},
                'B': {'ratio': 0.5, 'price_range': [20000, 40000]}
            }
        }
        # Agent Service expects specific tier config maybe?
        # It loads default_tier_config if user_config is None.
        self_user_config = None # It checks getattr(self.config, 'agent_tiers', None)?
        # Let's check agent_service.py usage.

def test_initialization():
    # 1. Setup
    if os.path.exists(TEST_DB):
        try:
            os.remove(TEST_DB)
        except:
            pass
    init_db(TEST_DB)
    conn = sqlite3.connect(TEST_DB)
    
    # Mock Config
    config = MockConfig()
    
    # 2. Init Services
    market_service = MarketService(config, conn)
    properties = market_service.initialize_market()
    
    agent_service = AgentService(config, conn)
    
    # 3. Run Initialization
    logger.info("Initializing Agents...")
    agent_service.initialize_agents(20, properties)
    
    # 4. Verify
    inconsistencies = 0
    checked = 0
    
    print("\n--- Verification Results ---")
    for agent in agent_service.agents:
        props = len(agent.owned_properties)
        story = agent.story.background_story
        need = agent.story.housing_need
        cash = agent.cash
        
        print(f"Agent {agent.id}: Props={props}, Cash={cash:,.0f}, Need={need}")
        print(f"Story: {story[:50]}...")
        
        if props > 0:
            checked += 1
            # Check for forbidden keywords
            if "无房" in story or "刚需" in need or "首次" in story or "租房" in story:
                print(f"  [FAIL] Inconsistent! Owns {props} properties but story says: {story}")
                inconsistencies += 1
            else:
                print("  [PASS] Consistent.")
        
    print(f"\nChecked {checked} property owners.")
    print(f"Inconsistencies found: {inconsistencies}")
    
    conn.close()
    
if __name__ == "__main__":
    test_initialization()
