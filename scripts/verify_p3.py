
import sys
import os
import sqlite3

sys.path.append(os.getcwd())

from models import Market, Agent
from transaction_engine import get_market_condition, handle_failed_negotiation

def verify_p3():
    print("Verifying P3 (Negotiation Optimization)...")
    
    # 1. Setup Mock Market
    properties = [
        {"property_id": 1, "zone": "A", "status": "for_sale", "listed_price": 5000000, "min_price": 4500000, "base_value": 4800000},
        {"property_id": 2, "zone": "A", "status": "for_sale", "listed_price": 5000000},
        {"property_id": 3, "zone": "B", "status": "for_sale", "listed_price": 2000000},
    ]
    market = Market(properties)
    
    # 2. Test Market Condition (Oversupply)
    # Zone A: 2 listings. If 1 buyer -> Ratio 2.0 (>1.5) -> Oversupply
    cond = get_market_condition(market, "A", potential_buyers_count=1)
    print(f"\nCondition (2 Listings / 1 Buyer): {cond}")
    if cond == "oversupply":
        print("✅ PASS: Oversupply detected")
    else:
        print(f"❌ FAILED: Expected oversupply, got {cond}")
        
    # 3. Test Market Condition (Undersupply)
    # Zone A: 2 listings. If 10 buyers -> Ratio 0.2 (<0.7) -> Undersupply
    cond = get_market_condition(market, "A", potential_buyers_count=10)
    print(f"Condition (2 Listings / 10 Buyers): {cond}")
    if cond == "undersupply":
        print("✅ PASS: Undersupply detected")
    else:
        print(f"❌ FAILED: Expected undersupply, got {cond}")
        
    # 4. Test Failure Handling (Price Cut)
    # Force Oversupply logic in handle_failed_negotiation
    # We need to mock get_market_condition or ensure it returns oversupply logic inside logic
    # The function calls get_market_condition internally.
    
    seller = Agent(id=99, name="Seller99")
    listing = properties[0] # Zone A (Oversupply if we pass 1 buyer)
    
    print("\nTesting Price Cut (Runs 100 times to trigger 30% chance)...")
    cut_count = 0
    for _ in range(100):
        # Reset price
        listing['listed_price'] = 5000000
        listing['min_price'] = 4500000
        
        adjusted = handle_failed_negotiation(seller, listing, market, potential_buyers_count=1)
        if adjusted:
            cut_count += 1
            if listing['listed_price'] < 5000000:
                pass # Good
            else:
                print("❌ FAILED: Price did not decrease despite True return")
                
    print(f"Price cut triggered {cut_count}/100 times")
    if 20 <= cut_count <= 40: # Expect ~30
        print("✅ PASS: Price cut probability within range")
    else:
        print(f"⚠️ WARNING: cut count {cut_count} outside expected 20-40 range (Randomness?)")

if __name__ == "__main__":
    verify_p3()
