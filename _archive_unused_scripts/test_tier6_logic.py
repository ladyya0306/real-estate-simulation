
import asyncio
import logging
import sys

# Configure unbuffered utf-8 stdout
sys.stdout.reconfigure(encoding='utf-8')

from agent_behavior import (determine_listing_strategy,
                            determine_psychological_price,
                            generate_buyer_preference)
from models import Agent, AgentStory
from mortgage_system import calculate_max_affordable

# Mock Logger
logging.basicConfig(level=logging.INFO)

class MockMarket:
    def get_avg_price(self, zone):
        if zone == "A": return 5000000
        if zone == "B": return 3000000
        return 0

def test_tier6_logic():
    print("\n--- Testing Tier 6 Logic ---")

    # 1. Test Psychological Price
    print("\n[1] Psychological Price Test")
    agent = Agent(id=1, name="TestAgent", cash=1000000, monthly_income=50000)
    agent.story = AgentStory(investment_style="conservative")

    market_avg = 3000000

    trends = ["UP", "DOWN", "PANIC", "STABLE"]
    for t in trends:
        price = determine_psychological_price(agent, market_avg, t)
        print(f"  Style: Conservative, Trend: {t}, Avg: {market_avg:,.0f} -> Psych: {price:,.0f} (Ratio: {price/market_avg:.2f})")

    # 2. Test Listing Strategy
    print("\n[2] Listing Strategy Test")
    agent.owned_properties = [{"property_id": 101, "zone": "A", "base_value": 5000000}]
    market_price_map = {"A": 5000000, "B": 3000000}

    # Case: Deep Bear Market (Panic) -> Expect Option C or D
    market_bulletin = "市场极度恐慌，成交量腰斩。"
    strategy = determine_listing_strategy(agent, market_price_map, market_bulletin, market_trend="PANIC")
    print(f"  Panic Market Strategy: {strategy.get('strategy')} - Coeff: {strategy.get('pricing_coefficient')}")
    print(f"  Reason: {strategy.get('reasoning')}")

    # Case: Bull Market -> Expect Option A
    strategy_bull = determine_listing_strategy(agent, market_price_map, "牛市来了，量价齐升", market_trend="UP")
    print(f"  Bull Market Strategy: {strategy_bull.get('strategy')} - Coeff: {strategy_bull.get('pricing_coefficient')}")

    # 3. Test Buyer Preference (Affordability vs Psych)
    print("\n[3] Buyer Preference Test")
    agent.cash = 2000000 # 200w
    agent.monthly_income = 30000 # 30k
    # Max Affordable approx: Cash + Loan.
    # Loan for 30k income -> Payment ~15k.
    # 30 years, 5% interest. 15k payment supports ~280w loan.
    # Total ~480w? Let's see.
    real_max = calculate_max_affordable(agent.cash, agent.monthly_income)
    print(f"  Real Max Affordable: {real_max:,.0f}")

    # Psych limit in Panic market for Conservative agent (0.6 * 300w = 180w)
    pref_panic = generate_buyer_preference(agent, MockMarket(), market_trend="PANIC")
    print(f"  Panic Pref Max Price: {pref_panic.max_price:,.0f}")
    print(f"  Psych Price: {pref_panic.psychological_price:,.0f}")

    if pref_panic.max_price <= pref_panic.psychological_price + 1000: # tolerance
        print("  [PASS] Max Price constrained by Psych Price in Panic")
    else:
        print("  [FAIL] Max Price NOT constrained properly")

    # 4. Test Price Adjustment (Async)
    print("\n[4] Price Adjustment Logic")
    # We need to run async
    async def test_adj():
        res = await decide_price_adjustment(
            agent_id=1, agent_name="TestAgent", investment_style="aggressive",
            property_id=101, current_price=5500000, listing_duration=6,
            market_trend="DOWN", db_conn=None # Mocking DB access inside might fail?
            # Wait, decide_price_adjustment uses db_conn to fetch background story.
            # I need to mock db_conn or patch the function.
            # Since I can't easily mock sqlite conn here without a real DB, I'll skip execution
            # or rely on the fact that I reviewed the code.
            # Actually, I can create a memory DB.
        )
        return res

    # Setup Memory DB for test 4
    import sqlite3
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE agents_static (agent_id INT, background_story TEXT)")
    cursor.execute("INSERT INTO agents_static VALUES (1, 'Testing Agent')")
    conn.commit()

    # Monkey patch decide_price_adjustment db usage if needed, but passing conn should work.
    # Re-import to be safe

    try:
        adj_res = asyncio.run(decide_price_adjustment(
            agent_id=1, agent_name="TestAgent", investment_style="aggressive",
            property_id=101, current_price=5500000, listing_duration=6,
            market_trend="DOWN", db_conn=conn
        ))
        print(f"  Adjustment Decision: {adj_res['action']} - Coeff: {adj_res['coefficient']}")
        print(f"  Reason: {adj_res['reason']}")
    except Exception as e:
        print(f"  [FAIL] Adjustment Test Attempt: {e}")

    conn.close()

if __name__ == "__main__":
    test_tier6_logic()
