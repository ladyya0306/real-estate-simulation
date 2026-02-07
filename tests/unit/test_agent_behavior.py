import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from agent_behavior import should_agent_exit_market, determine_role, AgentRole
from models import Agent, Market, AgentStory

class TestAgentBehavior(unittest.TestCase):

    def setUp(self):
        # Setup common objects
        self.agent = Agent(id=1, name="TestAgent", age=30, monthly_income=10000, cash=500000)
        self.agent.story = AgentStory(
            occupation="Tester", 
            background_story="Testing background",
            investment_style="balanced"
        )
        self.agent.role_duration = 3
        self.agent.life_pressure = "patient"
        self.agent.role = "BUYER"  # Fix: Attribute required by should_agent_exit_market
        
        self.market = MagicMock(spec=Market)
        # Mock market.properties to avoid AttributeError in some functions if accessed
        self.market.properties = [] 

    @patch('agent_behavior.safe_call_llm')
    def test_should_agent_exit_market_stay(self, mock_llm):
        # Scenario: Agent wants to STAY
        mock_llm.return_value = {"decision": "STAY", "reason": "Market is improving"}
        
        should_exit, reason = should_agent_exit_market(self.agent, self.market, 3)
        
        self.assertFalse(should_exit)
        self.assertEqual(reason, "Market is improving")
        
    @patch('agent_behavior.safe_call_llm')
    def test_should_agent_exit_market_exit(self, mock_llm):
        # Scenario: Agent wants to EXIT
        mock_llm.return_value = {"decision": "EXIT", "reason": "Too much pressure"}
        
        should_exit, reason = should_agent_exit_market(self.agent, self.market, 5)
        
        self.assertTrue(should_exit)
        self.assertEqual(reason, "Too much pressure")

    @patch('agent_behavior.safe_call_llm')
    def test_should_agent_exit_market_fallback(self, mock_llm):
        # Scenario: LLM fails (returns None or non-dict)
        mock_llm.return_value = None
        
        # Urgent agent waiting > 2 months -> Should EXIT in fallback
        self.agent.life_pressure = "urgent"
        self.agent.role_duration = 3
        
        
        should_exit, reason = should_agent_exit_market(self.agent, self.market, 3)
        
        self.assertTrue(should_exit)
        # Verify fallback reason (Chinese string in implementation)
        self.assertTrue("压力" in reason or "退出" in reason or "Fallback" in reason, f"Reason '{reason}' should indicate fallback logic")

    @patch('agent_behavior.safe_call_llm')
    def test_determine_role_no_property_seller_constraint(self, mock_llm):
        # Scenario: Agent has NO property, but LLM says SELLER
        # Constraint should force it to OBSERVER
        self.agent.owned_properties = []
        mock_llm.return_value = {"role": "SELLER", "reasoning": "I want money"}
        
        # We expect determine_role to override LLM's SELLER decision to OBSERVER
        role, reason = determine_role(self.agent, 1, self.market)
        
        self.assertEqual(role, AgentRole.OBSERVER, "Should override to OBSERVER if no properties owned")
        self.assertIn("no property", str(reason).lower(), "Reason should mention property constraint")

if __name__ == '__main__':
    unittest.main()
