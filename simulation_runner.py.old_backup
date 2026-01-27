import logging
import random
import numpy as np
import sqlite3
import sys
import json
from typing import List, Dict
from models import Agent, Market
from property_initializer import initialize_market_properties
from agent_behavior import (
    generate_agent_story, generate_buyer_preference, select_monthly_event, 
    determine_role
)
from transaction_engine import (
    generate_seller_listing, match_property_for_buyer, negotiate, execute_transaction
)
from generate_simulation_report import generate_all_reports

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("simulation_run.log", encoding='utf-8', mode='w'),
        logging.StreamHandler()
    ]
)
# Force set stdout to utf-8
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass
logger = logging.getLogger(__name__)

class SimulationRunner:
    def __init__(self, agent_count=100, months=12):
        self.agent_count = agent_count
        self.months = months
        self.market = None
        self.agents: List[Agent] = []
        self.current_month = 0
        
    def initialize(self):
        """Initialize Market and Agents with advanced Stories"""
        logger.info("Initializing New Simulation...")
        conn = sqlite3.connect('real_estate_stage2.db')
        cursor = conn.cursor()
        
        # 1. Init Tables
        cursor.execute("DROP TABLE IF EXISTS agents")
        cursor.execute("DROP TABLE IF EXISTS transactions") # Cleanup others too
        cursor.execute("DROP TABLE IF EXISTS decision_logs")
        cursor.execute("DROP TABLE IF EXISTS property_listings")
        cursor.execute("DROP TABLE IF EXISTS negotiations")
        
        for script in [
            'scripts/create_agents_table.sql', 
            'scripts/create_transactions_table.sql', 
            'scripts/create_decision_logs_table.sql',
            'scripts/create_property_listings_table.sql',
            'scripts/create_negotiations_table.sql'
        ]:
            with open(script, 'r', encoding='utf-8') as f:
                cursor.executescript(f.read())
        
        # 2. Market Properties
        properties = initialize_market_properties()
        self.market = Market(properties) # Market object holds live property state
        
        cursor.execute("DROP TABLE IF EXISTS properties")
        cursor.execute("""
            CREATE TABLE properties (
                property_id INTEGER PRIMARY KEY,
                zone TEXT,
                quality INTEGER,
                base_value REAL,
                building_area REAL,
                bedrooms INTEGER,
                unit_price REAL,
                property_type TEXT,
                is_school_district BOOLEAN,
                school_tier INTEGER,
                owner_id INTEGER,
                status TEXT,
                listed_price REAL,
                last_transaction_month INTEGER
            )
        """)
        
        prop_data = []
        for p in properties:
            prop_data.append((
                p['property_id'], p['zone'], p['quality'], p['base_value'],
                p['building_area'], p['bedrooms'], p['unit_price'], p['property_type'],
                p['is_school_district'], p['school_tier'],
                p['owner_id'], p['status'], p['listed_price'], p['last_transaction_month']
            ))
        cursor.executemany("INSERT INTO properties VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", prop_data)
        conn.commit()
        
        logger.info(f"Market initialized with {len(properties)} properties.")
        
        # 3. Agents with Stories
        self.agents = []
        db_agent_rows = []
        
        for i in range(1, self.agent_count + 1):
            age = random.randint(25, 45)
            income = random.randint(10000, 50000)
            # Create Rich (Buyers) and Poor (Sellers)
            if random.random() < 0.5:
                cash = income * random.randint(0, 5) # Poor
            else:
                cash = income * random.randint(70, 120) # Rich
            
            status = random.choice(["single", "married"])
            
            agent = Agent(
                id=i, age=age, marital_status=status,
                cash=float(cash), monthly_income=float(income)
            )
            
            # Generate Background Story (LLM-driven)
            # Optimization: Generate story locally or batch to save time?
            # For this run, we call generate_agent_story individually.
            # It mock calls LLM unless real API is hooked up, so fast.
            agent.story = generate_agent_story(agent)
            
            self.agents.append(agent)
            db_agent_rows.append((
                i, age, status, income, cash, 
                agent.story.background_story, agent.story.occupation
            ))
            
        cursor.executemany("""
            INSERT INTO agents (agent_id, age, marital_status, monthly_income, cash, background_story, occupation)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, db_agent_rows)
        
        # 4. Assign Initial Ownership
        logger.info("Assigning initial ownership...")
        random.shuffle(properties)
        assignments = []
        
        # 50% ownership rate
        for i, prop in enumerate(properties[: self.agent_count // 2]):
            owner = self.agents[i]
            prop['owner_id'] = owner.id
            prop['status'] = 'off_market'
            owner.owned_properties.append(prop)
            assignments.append((owner.id, 'off_market', prop['property_id']))
            
        cursor.executemany("UPDATE properties SET owner_id = ?, status = ? WHERE property_id = ?", assignments)
        conn.commit()
        conn.close()
        logger.info(f"Agents initialized: {self.agent_count}")

    def run(self):
        self.initialize() 
        conn = sqlite3.connect('real_estate_stage2.db')
        cursor = conn.cursor()
        
        logger.info(f"Starting Simulation: {self.months} Months")
        
        try:
            for month in range(1, self.months + 1):
                self.current_month = month
                logger.info(f"--- Month {month} ---")
                
                # A. Environment Updates
                # Simple income accumulation
                for agent in self.agents:
                     agent.cash += agent.monthly_income * 0.4 # Saving rate
                     agent.cash -= agent.monthly_payment # Mortgage payment
                     
                # B. Agent Decisions & Roles
                sellers = []
                buyers = []
                
                # 1. Clear old listings in DB for this month (Simplified: Listings expire monthly)
                # In complex sim, listings stay. Here we refresh.
                cursor.execute("DELETE FROM property_listings")
                
                from agent_behavior import AgentRole
                
                for agent in self.agents:
                    # 1. Event
                    event_result = select_monthly_event(agent, month)
                    event = event_result.get("event")
                    
                    # 2. Role
                    # Signature: determine_role(agent, month, market)
                    role_enum, reason = determine_role(agent, month, self.market)
                    
                    # Log Decision
                    # role_enum is AgentRole.BUYER/SELLER/OBSERVER
                    role_str = role_enum.name # "BUYER", "SELLER"
                    
                    cursor.execute("""
                        INSERT INTO decision_logs (agent_id, month, event_type, decision, reason, thought_process, llm_called)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        agent.id, month, event or "None", role_str, 
                        reason, reason, True # Using reason as thought_process for now
                    ))
                    
                    if role_enum == AgentRole.SELLER:
                        if agent.owned_properties:
                            prop = agent.owned_properties[0] # Sell first property
                            listing = generate_seller_listing(agent, prop, self.market)
                            sellers.append(listing)
                            
                            # Add to DB
                            cursor.execute("""
                                INSERT INTO property_listings (property_id, seller_id, listed_price, min_price, status, created_month)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (listing['property_id'], agent.id, listing['listed_price'], listing['min_price'], 'active', month))
                            
                    elif role_enum == AgentRole.BUYER:
                         # Generate Preference
                         agent.preference = generate_buyer_preference(agent)
                         buyers.append(agent)
                
                conn.commit()
                logger.info(f"Roles: Sellers={len(sellers)}, Buyers={len(buyers)}")
                
                # C. Transaction Matching
                active_listings = sellers # List of dicts
                
                # Map for quick lookup
                props_map = {p['property_id']: p for p in self.market.properties}
                
                # Debug: Show what we have
                print(f"\nDebug: Active listings: {len(active_listings)}")
                if active_listings:
                    first_listing = active_listings[0]
                    print(f"Debug: First listing: {first_listing}")
                    print(f"Debug: First listing property_id type: {type(first_listing.get('property_id'))}")
                print(f"Debug: Props_map has {len(props_map)} entries")
                if props_map:
                    sample_keys = list(props_map.keys())[:5]
                    print(f"Debug: First few props_map keys: {sample_keys}")
                    print(f"Debug: Props_map key type: {type(sample_keys[0]) if sample_keys else 'N/A'}")
                    
                    # Check if first listing ID is in map
                    if active_listings:
                        test_id = active_listings[0].get('property_id')
                        print(f"Debug: Is listing[0] property_id {test_id} in props_map? {test_id in props_map}")
                
                transactions_count = 0
                
                for buyer in buyers:
                    # 1. Match
                    matched_listing = match_property_for_buyer(buyer, active_listings, props_map)
                    
                    if matched_listing:
                        logger.info(f"match found: Buyer {buyer.id} -> Prop {matched_listing['property_id']} (Listed: {matched_listing['listed_price']})")
                        seller_agent = next((a for a in self.agents if a.id == matched_listing['seller_id']), None)
                        if not seller_agent: continue
                        
                        # 2. Negotiate
                        neg_result = negotiate(buyer, seller_agent, matched_listing, self.market)
                        
                        # Log Negotiation
                        cursor.execute("""
                            INSERT INTO negotiations (buyer_id, seller_id, property_id, round_count, final_price, success, log)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (
                            buyer.id, seller_agent.id, matched_listing['property_id'], 
                            len(neg_result['history']), neg_result.get('final_price', 0),
                            neg_result['outcome'] == 'success', json.dumps(neg_result['history'])
                        ))
                        
                        if neg_result['outcome'] == 'success':
                            final_price = neg_result['final_price']
                            
                            # 3. Execute
                            tx_record = execute_transaction(buyer, seller_agent, props_map[matched_listing['property_id']], final_price, self.market)
                            
                            if tx_record:
                                transactions_count += 1
                                logger.info(f"✅ Transaction: Agent {buyer.id} bought Prop {tx_record['property_id']} for {final_price:,.0f}")
                                
                                # Log Transaction
                                cursor.execute("""
                                    INSERT INTO transactions (month, buyer_id, seller_id, property_id, price, transaction_type)
                                    VALUES (?, ?, ?, ?, ?, ?)
                                """, (month, buyer.id, seller_agent.id, tx_record['property_id'], final_price, 'secondary'))
                                
                                # Remove listing from active
                                active_listings.remove(matched_listing)
                                
                conn.commit()
                logger.info(f"Month {month} Complete. Transactions: {transactions_count}")
        except Exception as e:
            import traceback
            logger.error(traceback.format_exc())
            raise
        finally:
            conn.close()
            # Force close logging to ensure all logs are written before copying
            handlers = logger.handlers[:]
            for handler in handlers:
                handler.close()
                logger.removeHandler(handler)
            
            logger.info("Generating Reports...")
            try:
                generate_all_reports()
            except Exception as e:
                print(f"Report generation failed: {e}")
                
        logger.info("Simulation Finished.")

if __name__ == "__main__":
    runner = SimulationRunner(agent_count=5, months=3) # Small run for testing
    runner.run()
