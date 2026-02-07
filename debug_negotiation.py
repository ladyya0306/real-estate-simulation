
import asyncio
import json
import sys
from unittest.mock import MagicMock

# --- MOCK DEPENDENCIES BEFORE IMPORT ---
mock_agent_behavior = MagicMock()
mock_agent_behavior.safe_call_llm = MagicMock()
mock_agent_behavior.safe_call_llm_async = MagicMock()
mock_agent_behavior.build_macro_context = lambda *args: "Macro Context"
sys.modules['agent_behavior'] = mock_agent_behavior

mock_mortgage = MagicMock()
sys.modules['mortgage_system'] = mock_mortgage

mock_config_settings = MagicMock()
sys.modules['config.settings'] = mock_config_settings

# New: Mock models to ensure Agent class matches
class MockStory:
    def __init__(self, negotiation_style="balanced"):
        self.negotiation_style = negotiation_style
        self.background_story = "bg"
        self.selling_motivation = "motivation"

class MockPreference:
    def __init__(self, max_price=0):
        self.max_price = max_price

class MockAgent:
    def __init__(self, id, name, role):
        self.id = id
        self.name = name
        self.role = role
        self.story = MockStory()
        self.preference = MockPreference()

# We need to overwrite models import inside transaction_engine or just patch it
# Easier to import transaction_engine now that sub-modules are mocked
from transaction_engine import negotiate_async
# transaction_engine imports Agent from models. 
# Since we already imported transaction_engine, 'models' was imported too (if valid).
# But likely it failed earlier. Let's rely on sys.modules for models too if needed.
# Actually, models.py is usually simple. Let's assume models.py is importable.
# If not, we will mock it too.



async def mock_safe_call_llm_async(prompt, default, system_prompt=""):
    print(f"\n[Mock LLM Call] Prompt length: {len(prompt)}")
    print(f"[Mock LLM Call] Default: {default}")
    
    # Simulate valid LLM response
    if "决定行动" in prompt and "OFFER" in prompt: # Buyer prompt
        return {"action": "OFFER", "offer_price": 5000000, "reason": "Buyer Offer"}
    elif "决定行动" in prompt and "ACCEPT" in prompt: # Seller prompt
        return {"action": "ACCEPT", "counter_price": 0, "reason": "Seller Accept"}
        
    return default

def mock_get_market_condition(market, zone, count):
    return "stable"

async def test_negotiation():
    # Setup Agents (Using our Logic, bypassing imports if possible or using models if robust)
    # Since we mocked agent_behavior, we need to ensure transaction_engine uses our mock llm
    
    # Patch the function imported inside transaction_engine
    import transaction_engine
    transaction_engine.safe_call_llm_async = mock_safe_call_llm_async
    transaction_engine.get_market_condition = mock_get_market_condition
    
    buyer = MockAgent(id=1, name="Buyer", role="BUYER")
    buyer.story = MockStory(negotiation_style="balanced")
    buyer.preference = MockPreference(max_price=6000000)
    
    seller = MockAgent(id=2, name="Seller", role="SELLER")
    seller.story = MockStory(negotiation_style="balanced")
    
    listing = {
        "listed_price": 5500000,
        "min_price": 4500000,
        "zone": "A"
    }
    
    market = MagicMock()
    market.get_avg_price.return_value = 5000000
    
    print("Starting Negotiation Test...")
    try:
        result = await negotiate_async(buyer, seller, listing, market, 10, config=None)
        print("\nResult:", json.dumps(result, indent=2))
        if result['outcome'] == 'success':
            print("✅ SUCCEEDED")
        else:
            print("❌ FAILED")
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_negotiation())
