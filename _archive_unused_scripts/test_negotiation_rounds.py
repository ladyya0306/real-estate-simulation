
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Add project root to path
sys.path.append('d:\\GitProj\\oasis-main')

from models import Agent, AgentPreference, AgentStory


# Mock config
class MockConfig:
    negotiation = {'rounds_range': [3, 3], 'market_conditions': {}}
    macro_environment = {}

# Import system under test
import transaction_engine


class TestNegotiationRounds(unittest.IsolatedAsyncioTestCase):
    async def test_final_round_injection(self):
        print("\n--- Testing Final Round Prompt Injection ---")

        # Setup Agents
        buyer = Agent(id=1, name="Buyer", cash=5000000, monthly_income=50000)
        buyer.preference = AgentPreference(target_zone="A", max_price=6000000)
        buyer.story = AgentStory()
        buyer.story.negotiation_style = "balanced"

        seller = Agent(id=2, name="Seller")
        seller.story = AgentStory()
        seller.story.negotiation_style = "balanced"

        listing = {
            "listed_price": 5000000,
            "min_price": 4800000,
            "zone": "A"
        }

        market = MagicMock()

        # Mock LLM
        # We want to capture the prompts sent to LLM
        with patch('transaction_engine.safe_call_llm_async', new_callable=AsyncMock) as mock_llm:
            # Setup returns to keep negotiation going until end
            # Round 1: Buyer Offer, Seller Counter
            # Round 2: Buyer Offer, Seller Counter
            # Round 3: Buyer Offer, Seller Reject (or whatever)

            mock_llm.side_effect = [
                # R1 Buyer
                {"action": "OFFER", "offer_price": 4000000, "reason": "Lowball"},
                # R1 Seller
                {"action": "COUNTER", "counter_price": 4900000, "reason": "Too low"},

                # R2 Buyer
                {"action": "OFFER", "offer_price": 4200000, "reason": "Higher"},
                # R2 Seller
                {"action": "COUNTER", "counter_price": 4850000, "reason": "Still low"},

                # R3 Buyer (Final)
                {"action": "OFFER", "offer_price": 4800000, "reason": "Final"},
                # R3 Seller (Final)
                {"action": "ACCEPT", "reason": "Deal"}
            ]

            result = await transaction_engine.negotiate_async(
                buyer, seller, listing, market, config=MockConfig()
            )

            print(f"Negotiation Result: {result['outcome']}")

            # Checks
            calls = mock_llm.call_args_list
            print(f"Total LLM Calls: {len(calls)}")

            # Check Round 3 Buyer Prompt (Index 4)
            r3_buyer_prompt = calls[4][0][0]
            if "最后通牒" in r3_buyer_prompt:
                print("[PASS] Buyer Final Round Hint found.")
            else:
                print("[FAIL] Buyer Final Round Hint MISSING!")
                print("Prompt tail:", r3_buyer_prompt[-200:])

            # Check Round 3 Seller Prompt (Index 5)
            r3_seller_prompt = calls[5][0][0]
            if "最后通牒" in r3_seller_prompt:
                 print("[PASS] Seller Final Round Hint found.")
            else:
                 print("[FAIL] Seller Final Round Hint MISSING!")
                 print("Prompt tail:", r3_seller_prompt[-200:])

if __name__ == "__main__":
    unittest.main()
