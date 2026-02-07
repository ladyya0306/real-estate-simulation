import logging
import random
import sqlite3
import json
import time
from typing import List, Dict, Optional

from models import Agent
from utils.name_generator import ChineseNameGenerator
from config.agent_tiers import AGENT_TIER_CONFIG
from config.agent_templates import get_template_for_tier
from agent_behavior import (
    select_monthly_event, apply_event_effects, 
    batched_determine_role_async, should_agent_exit_market,
    determine_listing_strategy, generate_buyer_preference
)
from transaction_engine import generate_seller_listing
import asyncio

logger = logging.getLogger(__name__)

class AgentService:
    def __init__(self, config, db_conn: sqlite3.Connection):
        self.config = config
        self.conn = db_conn
        self.agents: List[Agent] = []
        self.agent_map: Dict[int, Agent] = {}
        self.is_v2 = True # Default for new runs

    def initialize_agents(self, agent_count: int, market_properties: List[Dict]):
        """批量生成 Agent (V2 Schema)"""
        logger.info("Starting Batch Agent Generation (V2 Schema)...")
        self.agents = []
        cursor = self.conn.cursor()
        
        name_gen = ChineseNameGenerator(seed=random.randint(0, 10000))
        
        # 默认配置
        default_tier_config = AGENT_TIER_CONFIG
        default_prop_ownership = default_tier_config["init_params"]
        ordered_tiers = ["ultra_high", "high", "middle", "lower_middle", "low"]
        
        # 检查是否有用户自定义配置
        user_config = getattr(self.config, 'user_agent_config', None)
        # Also check _config dict in case it was saved deeply
        if not user_config and hasattr(self.config, '_config'):
            user_config = self.config._config.get('user_agent_config')
        
        if user_config:
            logger.info("Using User Custom Agent Configuration")
            tier_counts = {}
            tier_income_ranges = {}
            tier_prop_ranges = {}
            key_mapping = {'low_mid': 'lower_middle'}
            for u_key, u_data in user_config.items():
                internal_key = key_mapping.get(u_key, u_key)
                tier_counts[internal_key] = u_data['count']
                tier_income_ranges[internal_key] = u_data['income_range']
                tier_prop_ranges[internal_key] = u_data['property_count']
        else:
            logger.info("Using Default Agent Configuration")
            tier_dist = default_tier_config["tier_distribution"]
            total_dist = sum(tier_dist.values())
            tier_counts = {k: int((v / total_dist) * agent_count) for k, v in tier_dist.items()}
            current_sum = sum(tier_counts.values())
            diff = agent_count - current_sum
            if diff > 0: tier_counts["middle"] += diff
            tier_income_ranges = {}
            tier_prop_ranges = {}
         
        # Prepare Personality Weights (Investment Style)
        neg_cfg = getattr(self.config, 'negotiation', {})
        p_weights = neg_cfg.get('personality_weights', {
            'aggressive': 0.30, 'conservative': 0.30, 
            'balanced': 0.40
        })
        p_styles = list(p_weights.keys())
        p_probs = list(p_weights.values())
            
        current_id = 1
        
        # V2 Batches
        batch_static = []
        batch_finance = []
        BATCH_SIZE = 5000
        prop_idx = 0
        
        property_updates = []
        
        for tier in ordered_tiers:
            count = tier_counts.get(tier, 0)
            if count == 0: continue
            logger.info(f"Generating {count} agents for tier: {tier}")
            
            for _ in range(count):
                # Basic attrs
                age = random.randint(25, 60)
                
                # Income Logic
                if user_config:
                    inc_min, inc_max = tier_income_ranges[tier]
                    income = random.randint(inc_min, inc_max)
                else:
                    bounds = default_tier_config["tier_boundaries"]
                    lower_bound = bounds[tier]
                    if tier == "ultra_high":
                        income = random.randint(lower_bound, lower_bound * 5) // 12
                    else:
                        idx = ordered_tiers.index(tier)
                        if idx > 0: upper = bounds[ordered_tiers[idx-1]]
                        else: upper = lower_bound * 2
                        income = random.randint(lower_bound, upper) // 12
                
                # Cash Logic
                cash_ratio_range = default_prop_ownership[tier]["cash_ratio"]
                cash_ratio = random.uniform(*cash_ratio_range)
                cash = income * 12 * cash_ratio
                
                status = random.choice(["single", "married"])
                template = get_template_for_tier(tier, random)
                name = name_gen.generate()
                
                agent = Agent(
                    id=current_id, name=name, age=age, marital_status=status,
                    cash=float(cash), monthly_income=float(income)
                )
                agent.story.occupation = template["occupation"]
                agent.story.background_story = template["background"]
                # Investment Style
                agent.story.investment_style = random.choices(p_styles, weights=p_probs, k=1)[0]
                
                # Property Allocation
                if user_config:
                    p_min, p_max = tier_prop_ranges[tier]
                    target_props = random.randint(p_min, p_max)
                else:
                    prop_count_range = default_prop_ownership[tier]["property_count"]
                    target_props = random.randint(*prop_count_range)
                
                for _ in range(target_props):
                    if prop_idx < len(market_properties):
                        prop = market_properties[prop_idx]
                        prop['owner_id'] = agent.id
                        prop['status'] = 'off_market'
                        agent.owned_properties.append(prop)
                        property_updates.append((agent.id, 'off_market', prop['property_id']))
                        prop_idx += 1
                
                self.agents.append(agent)
                self.agent_map[agent.id] = agent
                
                # V2 Data Pipelining
                s_dict = agent.to_v2_static_dict()
                f_dict = agent.to_v2_finance_dict()
                
                batch_static.append((
                    s_dict['agent_id'], s_dict['name'], s_dict['birth_year'], s_dict['marital_status'], 
                    s_dict['children_ages'], s_dict['occupation'], s_dict['background_story'], 
                    s_dict['investment_style']
                ))
                
                batch_finance.append((
                    f_dict['agent_id'], f_dict['monthly_income'], f_dict['cash'], 
                    f_dict['total_assets'], f_dict['total_debt'], f_dict['monthly_payment']
                ))
                
                current_id += 1
                
                if len(batch_static) >= BATCH_SIZE:
                    self._flush_agents(cursor, batch_static, batch_finance)
                    batch_static = []
                    batch_finance = []
                    
        # Flush remaining
        if batch_static:
            self._flush_agents(cursor, batch_static, batch_finance)
            
        # Flush property updates
        if property_updates:
            logger.info(f"Assigning {len(property_updates)} properties to agents...")
            # Ideally this belongs in MarketService, but AgentService orchestrated allocation.
            # We'll update both tables to be safe for now, or just V2.
            # SimulationRunner update loop did both.
            # Let's stick to V2 (properties_market) and properties (legacy if exists).
            try:
                # Update properties (V1 legacy - optional if we fully removed it)
                # Ensure we only update if table exists? Or just try/except.
                cursor.executemany("UPDATE properties SET owner_id = ?, status = ? WHERE property_id = ?", property_updates)
            except:
                pass 
                
            cursor.executemany("UPDATE properties_market SET owner_id = ?, status = ? WHERE property_id = ?", property_updates)
            self.conn.commit()
            
        logger.info(f"Initialization Complete (V2). Generated {len(self.agents)} Agents.")
        
        # Initial Listings Logic could be here or returned to caller.
        # Let's handle it here to keep initialization self-contained.
        self._create_initial_listings(cursor)

    def _flush_agents(self, cursor, batch_static, batch_finance):
        for _retry in range(5):
            try:
                cursor.executemany("""
                    INSERT INTO agents_static (agent_id, name, birth_year, marital_status, children_ages, occupation, background_story, investment_style)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, batch_static)
                cursor.executemany("""
                    INSERT INTO agents_finance (agent_id, monthly_income, cash, total_assets, total_debt, monthly_payment)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, batch_finance)
                self.conn.commit()
                break
            except sqlite3.OperationalError as e:
                if "locked" in str(e): time.sleep(0.1 * (_retry + 1))
                else: raise

    def _create_initial_listings(self, cursor):
        """Create initial listings for multi-property owners."""
        try:
             initial_listings = []
             multi_owners = [a for a in self.agents if len(a.owned_properties) > 1]
             for agent in multi_owners[:max(3, len(multi_owners) // 5)]:
                 props = sorted(agent.owned_properties, key=lambda x: x.get('base_value', 0))
                 prop = props[0]
                 listed_price = prop['base_value'] * random.uniform(1.05, 1.15)
                 min_price = prop['base_value'] * 0.95
                 prop['status'] = 'for_sale'
                 prop['listed_price'] = listed_price
                 # Tuple for UPDATE properties_market: listed_price, min_price, property_id
                 initial_listings.append((listed_price, min_price, prop['property_id']))
                 
             if initial_listings:
                 cursor.executemany("""
                     UPDATE properties_market 
                     SET status = 'for_sale', listed_price = ?, min_price = ?, listing_month = 0
                     WHERE property_id = ? AND owner_id IS NOT NULL
                 """, initial_listings)
                 self.conn.commit()
                 logger.info(f"Created {len(initial_listings)} initial listings (V2 properties_market).")
        except Exception as e:
             logger.warning(f"Could not create initial listings: {e}")

    def load_agents_from_db(self):
        """Load agents from DB for resuming."""
        logger.info(f"Loading agents from DB...")
        conn = self.conn
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check V2
        try:
            cursor.execute("SELECT * FROM agents_static LIMIT 1")
            self.is_v2 = True
        except:
            self.is_v2 = False
            
        if self.is_v2:
            logger.info("Loading from V2 Agents tables...")
            cursor.execute("""
                SELECT s.*, f.* 
                FROM agents_static s 
                JOIN agents_finance f ON s.agent_id = f.agent_id
            """)
        else:
            logger.info("Loading from V1 Agents table...")
            cursor.execute("SELECT * FROM agents")
            
        rows = cursor.fetchall()
        self.agents = []
        for row in rows:
            row = dict(row)
            age = row.get('age')
            if age is None and row.get('birth_year'):
                age = 2024 - row['birth_year']
            
            a = Agent(
                id=row['agent_id'], 
                name=row['name'],
                age=age if age else 30,
                marital_status=row['marital_status'],
                cash=float(row['cash']), 
                monthly_income=float(row['monthly_income'])
            )
            a.story.occupation = row['occupation']
            a.story.background_story = row['background_story']
            
            if self.is_v2:
               a.story.investment_style = row.get('investment_style', 'balanced')
            else:
               a.story.housing_need = row.get('housing_need', '')
               
            self.agents.append(a)
            self.agent_map[a.id] = a
            
        # Load active participants info
        self._load_active_participants(cursor)
        
        logger.info(f"Loaded {len(self.agents)} agents from DB.")

    def _load_active_participants(self, cursor):
        if self.is_v2: 
            try:
                cursor.execute("SELECT * FROM active_participants")
                active_rows = cursor.fetchall()
                active_map = {r['agent_id']: dict(r) for r in active_rows}
                for a in self.agents:
                    if a.id in active_map:
                        a_data = active_map[a.id]
                        # Agent object doesn't have 'role' attr by default until runtime
                        # We can attach runtime attrs
                        a.role = a_data.get('role', 'OBSERVER')
                        a.monthly_event = a_data.get('llm_intent_summary')
            except Exception as e:
                logger.warning(f"Failed to load active participants: {e}")

    def update_financials(self):
        """Monthly financial updates (Income - Expenses)."""
        # Could be optimized to batch update DB?
        # For now, memory update + DB update eventually.
        # But simulation runner did this in loop.
        for agent in self.agents:
             agent.cash += agent.monthly_income * 0.4
             agent.cash -= agent.monthly_payment
             # We should probably sync to DB if crashing? 
             # SimulationRunner didn't explicitly sync every agent every month, 
             # only when transaction happened or life event. 
             # But it's good practice.

    def process_life_events(self, month: int, batch_decision_logs: List):
        """Handle stochastic life events."""
        cursor = self.conn.cursor()
        if self.config.life_events:
            life_event_sample_size = int(len(self.agents) * 0.05)
            life_event_candidates = random.sample(self.agents, min(life_event_sample_size, len(self.agents)))
            
            for agent in life_event_candidates:
                event_result = select_monthly_event(agent, month, self.config)
                if event_result and event_result.get("event"):
                    apply_event_effects(agent, event_result, self.config)
                    
                    batch_decision_logs.append((
                        agent.id, month, "LIFE_EVENT", event_result["event"], 
                        "Stochastic Life Event", json.dumps(event_result), False
                    ))
                    
                    # Update DB
                    if self.is_v2:
                        cursor.execute("UPDATE agents_finance SET cash = ? WHERE agent_id = ?", (agent.cash, agent.id))
                    else:
                        cursor.execute("UPDATE agents SET cash = ? WHERE agent_id = ?", (agent.cash, agent.id))

    def update_active_participants(self, month: int, market, batch_decision_logs: List):
        """Manage existing active participants (Timeouts, Exits)."""
        cursor = self.conn.cursor()
        batch_active_delete = []
        buyers = []
        sellers = [] # Although sellers are persistent until sold usually
        
        if self.is_v2:
            cursor.execute("SELECT * FROM active_participants")
            active_rows = cursor.fetchall()
            
            for row in active_rows:
                aid = row['agent_id']
                agent = self.agent_map.get(aid)
                if not agent: continue
                
                # Sync role info
                agent.role = row['role']
                agent.life_pressure = row['life_pressure']
                
                if agent.role in ["BUYER", "BUYER_SELLER"]:
                    # Buyer Timeout Logic
                    if not hasattr(agent, 'role_duration'): agent.role_duration = row['role_duration']
                    agent.role_duration += 1
                    
                    cursor.execute("UPDATE active_participants SET role_duration = ? WHERE agent_id = ?", (agent.role_duration, aid))
                    
                    if agent.role_duration > 2:
                        should_exit, exit_reason = should_agent_exit_market(agent, market, agent.role_duration)
                        
                        if should_exit:
                            agent.role = "OBSERVER"
                            batch_decision_logs.append((aid, month, "EXIT_DECISION", "OBSERVER", exit_reason, None, True))
                            batch_active_delete.append((aid,))
                        else:
                            buyers.append(agent)
                    else:
                        buyers.append(agent)
                
                elif agent.role == "SELLER":
                     # Sellers handled by listing status mostly, but they are active agents
                     pass
                     
        if batch_active_delete:
            cursor.executemany("DELETE FROM active_participants WHERE agent_id = ?", batch_active_delete)
            self.conn.commit()
            
        return buyers

    async def activate_new_agents(self, month: int, market, macro_desc: str, batch_decision_logs: List):
        """Select candidates and run LLM activation."""
        cursor = self.conn.cursor()
        candidates = []
        
        # SQL Filter: High Potential Agents
        if self.is_v2:
            cursor.execute("""
                SELECT f.agent_id 
                FROM agents_finance f
                LEFT JOIN active_participants ap ON f.agent_id = ap.agent_id
                WHERE ap.agent_id IS NULL 
                AND (f.cash > 300000 OR f.monthly_income > 20000)
                LIMIT 2000 
            """)
            rich_ids = [r[0] for r in cursor.fetchall()]
            
            cursor.execute("""
                SELECT pm.owner_id 
                FROM properties_market pm
                LEFT JOIN active_participants ap ON pm.owner_id = ap.agent_id
                WHERE ap.agent_id IS NULL AND pm.owner_id IS NOT NULL
                LIMIT 1000
            """)
            owner_ids = [r[0] for r in cursor.fetchall()]
            
            potential_ids = list(set(rich_ids + owner_ids))
            sample_size = min(len(potential_ids), 100) 
            selected_ids = random.sample(potential_ids, sample_size)
            
            for aid in selected_ids:
                agent = self.agent_map.get(aid)
                if agent: candidates.append(agent)
                
        logger.info(f"Activation Candidates: {len(candidates)}")
        
        if not candidates: return [], []
        
        # Async Batch Processing
        BATCH_SIZE = 50
        batches = [candidates[i:i + BATCH_SIZE] for i in range(0, len(candidates), BATCH_SIZE)]
        
        async def process_activation_batches():
            tasks = []
            for batch in batches:
                tasks.append(batched_determine_role_async(batch, month, market, macro_summary=macro_desc))
            results = await asyncio.gather(*tasks)
            return [item for sublist in results for item in sublist]

        logger.info("Running parallel LLM activation...")
        decisions_flat = await process_activation_batches()
        
        new_buyers = []
        new_sellers = [] # Just for Reference, listings are created in DB
        batch_active_insert = []
        
        for d in decisions_flat:
            a_id = d.get("id")
            role_str = d.get("role", "OBSERVER").upper()
            
            if role_str == "OBSERVER":
                if self.is_v2:
                    batch_decision_logs.append((a_id, month, "ROLE_DECISION", "OBSERVER", d.get('reason', 'No immediate need'), json.dumps(d), True))
                continue
                
            agent = self.agent_map.get(a_id)
            if not agent: continue
            
            agent.role = role_str
            agent.role_duration = 1
            agent.life_pressure = d.get("life_pressure", "patient")
            
            trigger = d.get("trigger", "Unknown")
            # 修复: 统一 event_type 为 ROLE_DECISION, 将 trigger 放入 reason 或保留在 json 中
            # event_type, decision, reason, thought_process, llm_called
            batch_decision_logs.append((
                agent.id, month, "ROLE_DECISION", role_str, 
                f"{trigger}: {d.get('reason', '')}", json.dumps(d), True
            ))
            
            is_seller = role_str in ["SELLER", "BUYER_SELLER"]
            is_buyer = role_str in ["BUYER", "BUYER_SELLER"]
            
            # Seller Logic
            if is_seller:
                if not agent.owned_properties:
                    if is_buyer:
                        agent.role = "BUYER"
                        role_str = "BUYER"
                        is_seller = False
                    else:
                        agent.role = "OBSERVER"
                        continue
                else:
                    # Generate Listing
                    self._create_seller_listing(agent, market, month)
            
            # Buyer Logic
            if is_buyer:
                agent.preference = generate_buyer_preference(agent)
                price_factor = d.get("price_expectation", 1.0)
                agent.preference.max_price *= price_factor
                new_buyers.append(agent)
                
            # Persistence Buffer
            if self.is_v2:
                selling_pid = agent.owned_properties[0]['property_id'] if is_seller and agent.owned_properties else None
                target_zone = agent.preference.target_zone if is_buyer and agent.preference else None
                max_price = agent.preference.max_price if is_buyer and agent.preference else None
                
                batch_active_insert.append((
                   agent.id, role_str, target_zone, max_price, selling_pid,
                   agent.listing.get('min_price') if hasattr(agent, 'listing') and agent.listing else None,
                   agent.listing.get('listed_price') if hasattr(agent, 'listing') and agent.listing else None,
                   agent.life_pressure, 
                   d.get('reason', ''),
                   month, 1
                ))
        
        if batch_active_insert:
             cursor.executemany("""
                INSERT OR REPLACE INTO active_participants 
                (agent_id, role, target_zone, max_price, selling_property_id, 
                 min_price, listed_price, life_pressure, llm_intent_summary, activated_month, role_duration)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
             """, batch_active_insert)
             self.conn.commit()
             
        return new_buyers, decisions_flat

    def _create_seller_listing(self, agent, market, month):
        cursor = self.conn.cursor()
        properties_to_list = []
        strategy_hint = "balanced"
        
        if len(agent.owned_properties) > 1:
            # Multi-property logic
            zone_prices = {z: market.get_avg_price(z) for z in ["A", "B"]}
            strategy_dec = determine_listing_strategy(agent, zone_prices)
            target_ids = strategy_dec.get("properties_to_sell", [])
            pricing_coefficient = strategy_dec.get("pricing_coefficient", 1.0)
            strategy_code = strategy_dec.get("strategy", "B")
            strategy_map = {"A": "aggressive", "B": "balanced", "C": "urgent", "D": "hold"}
            strategy_hint = strategy_map.get(strategy_code, "balanced")
            
            if not target_ids: target_ids = [agent.owned_properties[0]['property_id']]
            for pid in target_ids:
                p_data = next((p for p in agent.owned_properties if p['property_id'] == pid), None)
                if p_data: properties_to_list.append((p_data, pricing_coefficient))
        else:
             properties_to_list.append((agent.owned_properties[0], 1.0))
             
        for p_data, coeff in properties_to_list:
            listing = generate_seller_listing(agent, p_data, market, strategy_hint, pricing_coefficient=coeff)
            if not hasattr(agent, 'listing'): agent.listing = listing # Store first for active_participants
            
            # V2 Update
            cursor.execute("UPDATE properties_market SET status='for_sale', listed_price=?, min_price=?, listing_month=? WHERE property_id=?", 
                          (listing['listed_price'], listing['min_price'], month, listing['property_id']))

