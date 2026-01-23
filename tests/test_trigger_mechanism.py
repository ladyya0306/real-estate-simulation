import pytest
import sys
import os

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decision_engine import should_call_llm
from models import Agent, Market

class TestTriggerMechanism:
    
    def test_life_event_trigger(self):
        """测试生命事件触发"""
        agent = Agent(id=1, age=28, marital_status="engaged")
        agent.set_life_event(1, "即将结婚")
        market = Market()
        
        result = should_call_llm(agent, market, month=1)
        
        assert result.should_trigger is True
        assert result.trigger_type == 'life_event'
    
    def test_financial_change_trigger(self):
        """测试财务剧变触发"""
        agent = Agent(id=2, cash=2000000)
        agent.last_month_cash = 1000000 # 100% change
        market = Market()
        
        result = should_call_llm(agent, market, month=5)
        
        assert result.should_trigger is True
        assert result.trigger_type == 'financial'
    
    def test_market_volatility_trigger(self):
        """测试市场波动触发"""
        agent = Agent(id=3)
        market = Market()
        # Mock price history
        market.price_history['B'] = {9: 2000000, 10: 2310000} # >15% change
        
        # Ensure agent targets zone B (default)
        result = should_call_llm(agent, market, month=10)
        
        assert result.should_trigger is True
        assert result.trigger_type == 'market'
    
    def test_no_trigger(self):
        """测试无触发条件"""
        agent = Agent(id=4, cash=1000000)
        agent.last_month_cash = 1020000 # 2% change
        market = Market()
        market.price_history['B'] = {14: 2000000, 15: 2040000} # 2% change
        
        result = should_call_llm(agent, market, month=15)
        
        assert result.should_trigger is False

if __name__ == "__main__":
    # verification script
    try:
        t = TestTriggerMechanism()
        t.test_life_event_trigger()
        t.test_financial_change_trigger()
        t.test_market_volatility_trigger()
        t.test_no_trigger()
        print("All trigger mechanism tests passed!")
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
