import sqlite3
import os
import sys

# Add project root to path
sys.path.append(r'd:\GitProj\oasis-main')

# Mock models if needed or import
from models import Agent, AgentPreference, Market
from transaction_engine import match_property_for_buyer

db_path = r'd:\GitProj\oasis-main\results\run_20260208_171858\simulation.db'

def verify_matching():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Load Agent 27
    print("Loading Agent 27...")
    cursor.execute("SELECT * FROM active_participants WHERE agent_id = 27")
    row = cursor.fetchone()
    if not row:
        print("Agent 27 not found")
        return

    # Map row to minimal Agent object
    # active_participants columns:
    # 0: agent_id, 1: role, 2: target_zone, 3: max_price, ...
    agent_id = row[0]
    role = row[1]
    target_zone = row[2]
    max_price = row[3]
    
    print(f"Agent {agent_id} Preferences: Zone={target_zone}, MaxPrice={max_price:,.2f}")
    
    agent = Agent(id=agent_id)
    agent.role = role
    agent.preference = AgentPreference(
        target_zone=target_zone,
        max_price=max_price,
        min_bedrooms=1,
        need_school_district=False,
        max_affordable_price=max_price,
        psychological_price=max_price
    )
    
    # 2. Load Listings
    print("\nLoading Listed Properties...")
    cursor.execute("""
        SELECT pm.property_id, pm.listed_price, ps.zone 
        FROM properties_market pm
        JOIN properties_static ps ON pm.property_id = ps.property_id
        WHERE pm.status = 'for_sale'
    """)
    listings_rows = cursor.fetchall()
    
    listings = []
    props_map = {}
    
    for r in listings_rows:
        pid, price, zone = r
        # Simulate listing dict structure expected by match_property_for_buyer
        listings.append({
            'property_id': pid,
            'listed_price': price,
            'status': 'for_sale',
            'zone': zone # Used for filtering
        })
        props_map[pid] = {
            'property_id': pid,
            'zone': zone,
            'listed_price': price,
            'base_value': price, # Mock
            'building_area': 100 # Mock
        }
        print(f"  Prop {pid}: Zone={zone}, Price={price:,.2f}")

    # 3. Run Matching
    print("\nRunning matching logic (Primary Zone)...")
    matched = match_property_for_buyer(agent, listings, props_map)
    
    if matched:
        print(f"\n✅ MATCH FOUND: Property {matched['property_id']} (Price: {matched['listed_price']:,.2f})")
    else:
        print("\n❌ NO MATCH IN PRIMARY ZONE")
        print("Running fallback logic (Cross-Zone)...")
        matched = match_property_for_buyer(agent, listings, props_map, ignore_zone=True)
        
        if matched:
             print(f"\n✅ CROSS-ZONE MATCH FOUND: Property {matched['property_id']} (Price: {matched['listed_price']:,.2f})")
        else:
             print("\n❌ NO MATCH EVEN IN CROSS-ZONE")

    conn.close()

if __name__ == "__main__":
    verify_matching()

