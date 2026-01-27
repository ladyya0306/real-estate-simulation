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
    determine_role, batched_determine_role, calculate_activation_probability,
    open_role_evaluation
)
from transaction_engine import (
    generate_seller_listing, match_property_for_buyer, negotiate, execute_transaction, 
    handle_failed_negotiation, open_negotiate
)
from generate_simulation_report import generate_all_reports
from utils.name_generator import ChineseNameGenerator
from config.agent_tiers import AGENT_TIER_CONFIG
from config.agent_templates import get_template_for_tier
from config.settings import get_current_macro_sentiment, MACRO_ENVIRONMENT

# Import new modules for enhanced display and logging
from utils.behavior_logger import BehaviorLogger
from utils.exchange_display import ExchangeDisplay

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

from config.config_loader import SimulationConfig

class SimulationRunner:
    def __init__(self, agent_count=None, months=None, seed=None, resume=False, config: SimulationConfig = None):
        """
        初始化模拟运行器
        
        Args:
            config: 统一配置对象 (SimulationConfig实例)
            agent_count, months, seed: 可选覆盖参数 (优先级高于config)
        """
        # 1. 加载配置 (如果未提供，加载默认)
        if config is None:
            config = SimulationConfig("config/baseline.yaml")
        self.config = config
        
        # 2. 参数优先级处理 (Args > Config)
        self.agent_count = agent_count if agent_count is not None else self.config.simulation['agent_count']
        self.months = months if months is not None else self.config.simulation['months']
        
        # 随机种子处理
        cfg_seed = self.config.simulation.get('random_seed')
        self.seed = seed if seed is not None else cfg_seed
        
        # 3. 初始化状态
        self.market = None
        self.agents: List[Agent] = []
        self.current_month = 0
        self.resume = resume
        
        # 4. 设置随机种子
        if self.seed is not None:
            random.seed(self.seed)
            np.random.seed(self.seed)
            logger.info(f"随机种子已设置为: {self.seed}")
        else:
            logger.info("使用随机种子 (结果不可复现)")
        
    def initialize(self):
        """Initialize Market and Agents with Batch Generation Strategy (Million Agent Scale)"""
        logger.info("Initializing New Simulation (Batch Mode)...")
        
        # Ensure clean state by waiting for file releases
        import time
        time.sleep(1)
        
        # Use single connection for initialization sequence
        try:
            conn = sqlite3.connect('real_estate_stage2.db', timeout=60.0, isolation_level=None)
            # Disable WAL, use simple file locking
            conn.execute("PRAGMA journal_mode = DELETE") 
            conn.execute("PRAGMA synchronous = OFF")
            conn.execute("PRAGMA busy_timeout = 60000")
            
            cursor = conn.cursor()
            
            cursor.execute("DROP TABLE IF EXISTS agents")
            cursor.execute("DROP TABLE IF EXISTS transactions")
            cursor.execute("DROP TABLE IF EXISTS decision_logs")
            cursor.execute("DROP TABLE IF EXISTS property_listings")
            cursor.execute("DROP TABLE IF EXISTS negotiations")
            cursor.execute("DROP TABLE IF EXISTS properties")
            conn.commit()
            
            for script in [
                'scripts/create_agents_table.sql', 
                'scripts/create_transactions_table.sql', 
                'scripts/create_decision_logs_table.sql',
                'scripts/create_property_listings_table.sql',
                'scripts/create_negotiations_table.sql'
            ]:
                with open(script, 'r', encoding='utf-8') as f:
                    cursor.executescript(f.read())
            conn.commit()
            
            # 2. Market Properties
            # Check for user custom property count (from enhanced CLI)
            user_prop_count = getattr(self.config, 'user_property_count', None)
            if user_prop_count:
                logger.info(f"Initializing market with User Defined Property Count: {user_prop_count}")
                properties = initialize_market_properties(target_total_count=user_prop_count, config=self.config)
            else:
                properties = initialize_market_properties(config=self.config)
                
            # Sort properties by value descending for targeted distribution
            properties.sort(key=lambda x: x['base_value'], reverse=True)
            
            self.market = Market(properties)
            
            cursor.execute("""
                CREATE TABLE properties (
                    property_id INTEGER PRIMARY KEY,
                    zone TEXT,
                    quality INTEGER,
                    base_value REAL,
                    building_area REAL,
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
            
            # Add Indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_agents_role ON agents(role)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_agents_cash ON agents(cash)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_properties_owner ON properties(owner_id)")
            conn.commit()
            
            # Insert Properties
            cursor.executemany("INSERT INTO properties VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", [
                (p['property_id'], p['zone'], p['quality'], p['base_value'],
                 p['building_area'], p['unit_price'], p['property_type'],
                 p['is_school_district'], p['school_tier'],
                 p['owner_id'], p['status'], p['listed_price'], p['last_transaction_month'])
                for p in properties
            ])
            conn.commit()
            logger.info(f"Market initialized with {len(properties)} properties.")
            
            # Create initial property listings for properties that have owners
            # Properties without owners will be listed when agents are assigned as sellers
            for_sale_with_owner = [p for p in properties if p.get('status') == 'for_sale' and p.get('owner_id')]
            if for_sale_with_owner:
                cursor.executemany("""
                    INSERT INTO property_listings 
                    (property_id, seller_id, listed_price, min_price, status, created_month)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, [
                    (p['property_id'], 
                     p['owner_id'],
                     p['listed_price'], 
                     p['base_value'] * 0.95,  # min price is 95% of base value
                     'active', 
                     0)  # created in month 0 (initial)
                    for p in for_sale_with_owner
                ])
                conn.commit()
                logger.info(f"Created {len(for_sale_with_owner)} initial property listings.")
            
            self._batch_gen_agents(cursor, conn)
            
        except Exception as e:
            logger.error(f"Init DB Error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def _batch_gen_agents(self, cursor, conn):
        """批量生成 Agent，支持默认配置或用户自定义配置"""
        logger.info("Starting Batch Agent Generation...")
        self.agents = []
        
        name_gen = ChineseNameGenerator(seed=random.randint(0, 10000))
        
        # 默认配置
        default_tier_config = AGENT_TIER_CONFIG
        default_prop_ownership = default_tier_config["init_params"]
        ordered_tiers = ["ultra_high", "high", "middle", "lower_middle", "low"]
        
        # 检查是否有用户自定义配置
        user_config = getattr(self.config, 'user_agent_config', None)
        
        if user_config:
            logger.info("Using User Custom Agent Configuration")
            # 适配用户配置结构到生成逻辑
            # user_config structure: {tier: {'count': int, 'income_range': (min, max), 'property_count': (min, max)}}
            
            # 转换收入边界和房产分配
            tier_counts = {}
            tier_income_ranges = {}
            tier_prop_ranges = {}
            
            # Map user config keys (match what's in real_estate_demo_v2_1.py) to internal tier names
            # User config uses: ultra_high, high, middle, low_mid, low
            # Internal uses: ultra_high, high, middle, lower_middle, low
            # Need to map low_mid -> lower_middle
            key_mapping = {'low_mid': 'lower_middle'}
            
            for u_key, u_data in user_config.items():
                internal_key = key_mapping.get(u_key, u_key)
                tier_counts[internal_key] = u_data['count']
                tier_income_ranges[internal_key] = u_data['income_range']
                tier_prop_ranges[internal_key] = u_data['property_count']
                
        else:
            logger.info("Using Default Agent Configuration")
            # Calculate counts per tier based on distribution
            tier_dist = default_tier_config["tier_distribution"]
            total_dist = sum(tier_dist.values())
            tier_counts = {k: int((v / total_dist) * self.agent_count) for k, v in tier_dist.items()}
            
            # Adjust remainder to middle class
            current_sum = sum(tier_counts.values())
            diff = self.agent_count - current_sum
            if diff > 0:
                tier_counts["middle"] += diff
            
            # 使用默认配置的数据结构
            tier_income_ranges = {} # Will be handled by legacy logic if empty
            tier_prop_ranges = {}   # Will be handled by legacy logic if empty
         
        # Prepare Personality Weights
        neg_cfg = getattr(self.config, 'negotiation', {})
        p_weights = neg_cfg.get('personality_weights', {
            'aggressive': 0.25, 'conservative': 0.25, 
            'balanced': 0.40, 'desperate': 0.10
        })
        p_styles = list(p_weights.keys())
        p_probs = list(p_weights.values())
            
        current_id = 1
        db_batch = []
        BATCH_SIZE = 5000
        prop_idx = 0
        
        property_updates = []
        properties = self.market.properties
        
        for tier in ordered_tiers:
            count = tier_counts.get(tier, 0)
            if count == 0: continue
            
            logger.info(f"Generating {count} agents for tier: {tier}")
            
            for _ in range(count):
                # Basic attrs
                age = random.randint(25, 60)
                
                # Income Logic
                if user_config:
                    # 使用用户定义的具体范围
                    inc_min, inc_max = tier_income_ranges[tier]
                    # Convert to monthly income directly (user input is already monthly)
                    income = random.randint(inc_min, inc_max)
                else:
                    # 使用默认的相对边界逻辑
                    bounds = default_tier_config["tier_boundaries"]
                    lower_bound = bounds[tier]
                    if tier == "ultra_high":
                        income = random.randint(lower_bound, lower_bound * 5) // 12
                    else:
                        idx = ordered_tiers.index(tier)
                        if idx > 0:
                            upper = bounds[ordered_tiers[idx-1]]
                        else:
                            upper = lower_bound * 2
                        income = random.randint(lower_bound, upper) // 12
                
                # Cash Logic
                # Cash 依然基于收入倍数，使用默认配置中的比例
                # 未来也可以让用户配置储蓄率
                cash_ratio_range = default_prop_ownership[tier]["cash_ratio"]
                cash_ratio = random.uniform(*cash_ratio_range)
                cash = income * 12 * cash_ratio
                
                status = random.choice(["single", "married"])
                
                # Template Logic
                template = get_template_for_tier(tier, random)
                
                # Generate Name
                name = name_gen.generate()
                
                agent = Agent(
                    id=current_id, name=name, age=age, marital_status=status,
                    cash=float(cash), monthly_income=float(income)
                )
                agent.story.occupation = template["occupation"]
                agent.story.background_story = template["background"]
                # Assign Personality
                agent.story.negotiation_style = random.choices(p_styles, weights=p_probs, k=1)[0]
                
                # Property Allocation
                if user_config:
                    p_min, p_max = tier_prop_ranges[tier]
                    target_props = random.randint(p_min, p_max)
                else:
                    prop_count_range = default_prop_ownership[tier]["property_count"]
                    target_props = random.randint(*prop_count_range)
                
                for _ in range(target_props):
                    if prop_idx < len(properties):
                        prop = properties[prop_idx]
                        prop['owner_id'] = agent.id
                        prop['status'] = 'off_market'
                        agent.owned_properties.append(prop)
                        property_updates.append((agent.id, 'off_market', prop['property_id']))
                        prop_idx += 1
                
                self.agents.append(agent)
                db_batch.append((
                    current_id, agent.name, age, status, income, cash, 
                    template["occupation"], "stable", "none", "none", 
                    template.get("housing_need", "none"), "none", 
                    template["background"], "OBSERVER"
                ))
                
                current_id += 1
                
                if len(db_batch) >= BATCH_SIZE:
                    import time
                    for _retry in range(5):
                        try:
                            cursor.executemany("""
                                INSERT INTO agents (agent_id, name, age, marital_status, monthly_income, cash, 
                                                  occupation, career_outlook, family_plan, education_need, 
                                                  housing_need, selling_motivation, background_story, role)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, db_batch)
                            db_batch = []
                            conn.commit()
                            break
                        except sqlite3.OperationalError as e:
                            if "locked" in str(e):
                                time.sleep(0.1 * (_retry + 1))
                            else:
                                raise
                    
        # Flush remaining agents
        if db_batch:
            cursor.executemany("""
                INSERT INTO agents (agent_id, name, age, marital_status, monthly_income, cash, 
                                  occupation, career_outlook, family_plan, education_need, 
                                  housing_need, selling_motivation, background_story, role)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, db_batch)
            conn.commit()
            
        # Flush property updates
        if property_updates:
            logger.info(f"Assigning {len(property_updates)} properties to agents...")
            for _retry in range(5):
                try:
                    cursor.executemany("UPDATE properties SET owner_id = ?, status = ? WHERE property_id = ?", property_updates)
                    conn.commit()
                    break
                except sqlite3.OperationalError as e:
                    if "locked" in str(e):
                        time.sleep(0.1 * (_retry + 1))
                    else:
                        raise
            
        logger.info(f"Initialization Complete. Generated {self.agent_count} Agents.")
        
        # Create initial listings from agents who own properties
        # Ensure a mix of price ranges by including B zone properties
        initial_listings = []
        
        # Strategy 1: Multi-property owners list one (prefer lower value)
        multi_owners = [a for a in self.agents if len(a.owned_properties) > 1]
        for agent in multi_owners[:max(3, len(multi_owners) // 5)]:
            props = sorted(agent.owned_properties, key=lambda x: x.get('base_value', 0))
            prop = props[0]  # Lowest value
            listed_price = prop['base_value'] * random.uniform(1.05, 1.15)
            min_price = prop['base_value'] * 0.95
            prop['status'] = 'for_sale'
            prop['listed_price'] = listed_price
            initial_listings.append((
                prop['property_id'], agent.id, listed_price, min_price, 'active', 0
            ))
        
        # Strategy 2: Some single-property owners in B zone (simulating urgent sellers)
        single_owners_b = [a for a in self.agents 
                          if len(a.owned_properties) == 1 
                          and a.owned_properties[0].get('zone') == 'B']
        urgent_sellers = random.sample(single_owners_b, min(5, len(single_owners_b)))
        for agent in urgent_sellers:
            prop = agent.owned_properties[0]
            listed_price = prop['base_value'] * random.uniform(0.98, 1.08)  # More competitive pricing
            min_price = prop['base_value'] * 0.90
            prop['status'] = 'for_sale'
            prop['listed_price'] = listed_price
            initial_listings.append((
                prop['property_id'], agent.id, listed_price, min_price, 'active', 0
            ))
        
        if initial_listings:
            cursor.executemany("""
                INSERT INTO property_listings 
                (property_id, seller_id, listed_price, min_price, status, created_month)
                VALUES (?, ?, ?, ?, ?, ?)
            """, initial_listings)
            
            for listing in initial_listings:
                cursor.execute(
                    "UPDATE properties SET status='for_sale', listed_price=? WHERE property_id=?",
                    (listing[2], listing[0])
                )
            conn.commit()
            logger.info(f"Created {len(initial_listings)} initial listings (multi-owners + B zone urgent sellers).")
        
        # Show Agent Samples
        from utils.workflow_logger import WorkflowLogger
        wf_logger = WorkflowLogger(self.config)
        wf_logger.show_agent_generation_summary(self.agents, sample_size=3)

    def load_from_db(self):
        """Load agents and market state from DB for resuming."""
        logger.info("Loading state from database...")
        conn = sqlite3.connect('real_estate_stage2.db', timeout=60.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 1. Load Agents
        cursor.execute("SELECT * FROM agents")
        rows = cursor.fetchall()
        self.agents = []
        for row in rows:
            a = Agent(
                id=row['agent_id'], 
                name=row['name'],
                age=row['age'], 
                marital_status=row['marital_status'],
                cash=float(row['cash']), 
                monthly_income=float(row['monthly_income'])
            )
            # Restore story attributes
            a.story.occupation = row['occupation']
            a.story.background_story = row['background_story']
            a.story.housing_need = row['housing_need']
            # Role mapping
            if 'role' in row.keys() and row['role']:
                a.role = row['role']
                
            self.agents.append(a)
            
        logger.info(f"Loaded {len(self.agents)} agents from DB.")
        
        # 2. Load Market/Properties
        cursor.execute("SELECT * FROM properties")
        prop_rows = cursor.fetchall()
        properties = []
        for row in prop_rows:
            p = dict(row)
            properties.append(p)
            # Re-link owned properties to agents
            if p['owner_id']:
                agent = next((x for x in self.agents if x.id == p['owner_id']), None)
                if agent:
                    agent.owned_properties.append(p)
                    
        self.market = Market(properties)
        logger.info(f"Loaded {len(properties)} properties from DB.")
        conn.close()

    def run(self):
        if self.resume:
            logger.info("Resuming simulation... Skipping initialization.")
            self.load_from_db()
        else:
            self.initialize() 
            
        conn = sqlite3.connect('real_estate_stage2.db', timeout=60.0)
        conn.execute("PRAGMA busy_timeout = 30000")
        cursor = conn.cursor()
        
        # Initialize Workflow Logger
        from utils.workflow_logger import WorkflowLogger
        wf_logger = WorkflowLogger(self.config)
        
        # Initialize Behavior Logger and Exchange Display
        behavior_logger = BehaviorLogger(results_dir="results")
        exchange_display = ExchangeDisplay(use_rich=True)
        
        logger.info(f"Starting Simulation: {self.months} Months")
        logger.info(f"Results will be saved to: {behavior_logger.get_output_dir()}")
        import time
        overall_start_time = time.time()
        
        try:
            for month in range(1, self.months + 1):
                month_start_time = time.time()
                self.current_month = month
                
                # Reset workflow stats
                wf_logger.negotiation_count = 0
                
                # Get Macro Sentiment
                macro_key = get_current_macro_sentiment(month)
                macro_info = MACRO_ENVIRONMENT[macro_key]
                macro_desc = f"{macro_key.upper()}: {macro_info['description']}"
                
                logger.info(f"--- Month {month} [{macro_key.upper()}] ---")
                
                # Show Exchange Header
                exchange_display.show_exchange_header(month, macro_desc)
                
                # A. Environment Updates
                for agent in wf_logger.get_progress_bar(self.agents, desc=f"Month {month} Updates"):
                     agent.cash += agent.monthly_income * 0.4
                     agent.cash -= agent.monthly_payment
                     
                # B. Agent Decisions & Roles (Batch Mode)
                sellers = []
                buyers = []
                
                # --- 1. Lifecycle Maintenance ---
                # Buyer Timeout
                reverted_count = 0
                for agent in self.agents:
                    if hasattr(agent, 'role') and agent.role == "BUYER":
                        if not hasattr(agent, 'role_duration'): agent.role_duration = 0
                        agent.role_duration += 1
                        
                        if agent.role_duration > 3:
                            agent.role = "OBSERVER"
                            agent.role_duration = 0
                            reverted_count += 1
                            cursor.execute("INSERT INTO decision_logs (agent_id, month, decision, reason) VALUES (?, ?, ?, ?)",
                                          (agent.id, month, "OBSERVER", "Timeout: 3 months no purchase"))
                    else:
                        if not hasattr(agent, 'role_duration'): agent.role_duration = 0
                        
                # Seller Price Cuts
                cursor.execute("SELECT property_id, listed_price, created_month FROM property_listings WHERE status='active' AND created_month <= ?", (month - 2,))
                stale_listings = cursor.fetchall()
                for pid, price, created_m in stale_listings:
                    new_price = price * 0.95
                    cursor.execute("UPDATE property_listings SET listed_price = ? WHERE property_id = ?", (new_price, pid))
                    cursor.execute("UPDATE properties SET listed_price = ? WHERE property_id = ?", (new_price, pid))
                    
                # --- 2. Batch Activation ---
                candidates = []
                for agent in self.agents:
                    current_role = getattr(agent, 'role', 'OBSERVER')
                    if current_role != "OBSERVER":
                        if current_role == "BUYER": 
                            buyers.append(agent)
                        elif current_role == "SELLER":
                            pass
                        continue
                        
                    prob = calculate_activation_probability(agent)
                    if random.random() < prob:
                        candidates.append(agent)
                        
                logger.info(f"Activation Candidates: {len(candidates)}")
                
                # Batch Process Candidates
                BATCH_SIZE = 50
                from agent_behavior import AgentRole 
                
                activated_count = 0
                active_decisions_log = [] 
                
                if candidates:
                    batches = [candidates[i:i + BATCH_SIZE] for i in range(0, len(candidates), BATCH_SIZE)]
                    
                    for batch in wf_logger.get_progress_bar(batches, desc="LLM Role Activation"):
                        decisions = batched_determine_role(batch, month, self.market, macro_summary=macro_desc)
                        active_decisions_log.extend(decisions)
                        
                        for d in decisions:
                            a_id = d.get("id")
                            role_str = d.get("role", "OBSERVER").upper()
                            
                            if role_str == "OBSERVER": continue
                            
                            agent = next((a for a in batch if a.id == a_id), None)
                            if not agent: continue
                            
                            agent.role = role_str
                            agent.role_duration = 1
                            trigger = d.get("trigger", "Unknown")
                            
                            cursor.execute("""
                                INSERT INTO decision_logs (agent_id, month, event_type, decision, reason, thought_process, llm_called)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (
                                agent.id, month, trigger, role_str, 
                                d.get("trigger", ""), json.dumps(d), True
                            ))
                            
                            if role_str == "SELLER":
                                if not agent.owned_properties:
                                    agent.role = "OBSERVER"
                                    continue
                                
                                agent.owned_properties.sort(key=lambda p: p.get('base_value', 0))
                                prop = agent.owned_properties[0]
                                listing = generate_seller_listing(agent, prop, self.market)
                                sellers.append(listing)
                                cursor.execute("UPDATE properties SET status='for_sale', listed_price=? WHERE property_id=?", 
                                              (listing['listed_price'], listing['property_id']))
                                cursor.execute("INSERT INTO property_listings (property_id, seller_id, listed_price, min_price, status, created_month) VALUES (?,?,?,?,?,?)",
                                              (listing['property_id'], agent.id, listing['listed_price'], listing['min_price'], 'active', month))
                                    
                            elif role_str == "BUYER":
                                agent.preference = generate_buyer_preference(agent)
                                price_factor = d.get("price_expectation", 1.0)
                                agent.preference.max_price *= price_factor
                                buyers.append(agent)
                            
                            cursor.execute("UPDATE agents SET role = ? WHERE agent_id = ?", (role_str, agent.id))
                            activated_count += 1
                            
                        if activated_count > 5000:
                            break
                            
                conn.commit()
                
                # LOGGING
                wf_logger.show_activation_summary(active_decisions_log)
                wf_logger.show_role_lists(buyers, sellers)
                
                # Use props_map for quick lookup
                props_map = {p['property_id']: p for p in self.market.properties}
                
                # Fetch Active Listings
                cursor.execute("SELECT * FROM property_listings WHERE status='active'")
                cols = [description[0] for description in cursor.description]
                active_listings_rows = cursor.fetchall()
                active_listings = [dict(zip(cols, row)) for row in active_listings_rows]
                
                for listing in active_listings:
                    pid = listing.get('property_id')
                    if pid in props_map:
                        listing['zone'] = props_map[pid].get('zone', 'A')

                # Show listings on exchange display
                exchange_display.show_listings(active_listings, props_map)
                exchange_display.show_buyers(buyers)
                exchange_display.show_supply_demand(len(active_listings), len(buyers))
                
                transactions_count = 0
                transactions_log_data = [] 
                failed_negotiations = 0
                
                random.shuffle(buyers)
                
                # Matching & Negotiation Loop (Using Open Negotiation)
                if buyers:
                    for buyer in wf_logger.get_progress_bar(buyers, desc="Buyer Actions"):
                        matched_listing = match_property_for_buyer(buyer, active_listings, props_map)
                        
                        if matched_listing:
                            seller_agent = next((a for a in self.agents if a.id == matched_listing['seller_id']), None)
                            if not seller_agent: continue
                            
                            # Get history context for consistency
                            buyer_context = behavior_logger.get_agent_history(buyer.id, max_months=3)
                            seller_context = behavior_logger.get_agent_history(seller_agent.id, max_months=3)
                            
                            # Add property details to listing for display
                            prop_detail = props_map.get(matched_listing['property_id'], {})
                            matched_listing['building_area'] = prop_detail.get('building_area', 80)
                            matched_listing['property_type'] = prop_detail.get('property_type', '普通住宅')
                            
                            # Show negotiation start
                            exchange_display.show_negotiation_start(
                                buyer.id, seller_agent.id, 
                                matched_listing['property_id'], 
                                matched_listing['listed_price']
                            )
                            
                            neg_result = open_negotiate(
                                buyer, seller_agent, matched_listing, self.market,
                                buyer_context=buyer_context, seller_context=seller_context,
                                config=self.config
                            )
                            
                            # Display negotiation rounds
                            for entry in neg_result.get('history', []):
                                exchange_display.show_negotiation_round(
                                    entry.get('round', 0),
                                    entry.get('party', ''),
                                    entry.get('action', ''),
                                    entry.get('price'),
                                    entry.get('message', '')
                                )
                            
                            # Log negotiation to behavior logger
                            behavior_logger.log_negotiation(
                                month, buyer.id, seller_agent.id,
                                matched_listing['property_id'],
                                neg_result.get('history', []),
                                neg_result.get('outcome', 'failed'),
                                neg_result.get('final_price', 0)
                            )
                            
                            # Log to workflow logger (legacy)
                            wf_logger.log_negotiation(
                                buyer_id=buyer.id,
                                seller_id=seller_agent.id,
                                property_id=matched_listing['property_id'],
                                listed_price=matched_listing['listed_price'],
                                history=neg_result['history'],
                                success=(neg_result['outcome'] == 'success'),
                                final_price=neg_result.get('final_price', 0)
                            )
                            
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
                                transaction_record = execute_transaction(buyer, seller_agent, props_map[matched_listing['property_id']], final_price, self.market, config=self.config)
                                
                                if transaction_record:
                                    transactions_count += 1
                                    transactions_log_data.append({'price': final_price})
                                    
                                    # Show deal result
                                    exchange_display.show_deal_result(
                                        True, buyer.id, seller_agent.id,
                                        matched_listing['property_id'], final_price
                                    )
                                    
                                    cursor.execute("""
                                        INSERT INTO transactions (month, buyer_id, seller_id, property_id, price, transaction_type)
                                        VALUES (?, ?, ?, ?, ?, ?)
                                    """, (month, buyer.id, seller_agent.id, transaction_record['property_id'], final_price, 'secondary'))
                                    
                                    # Update listing status
                                    cursor.execute("UPDATE property_listings SET status='sold' WHERE property_id=?", (matched_listing['property_id'],))
                                    cursor.execute("UPDATE properties SET status='off_market', owner_id=? WHERE property_id=?", (buyer.id, matched_listing['property_id']))
                                    
                                    # Reset buyer role
                                    buyer.role = "OBSERVER"
                                    cursor.execute("UPDATE agents SET role = 'OBSERVER' WHERE agent_id = ?", (buyer.id,))
                                    
                                    active_listings.remove(matched_listing)
                            else:
                                failed_negotiations += 1
                                exchange_display.show_deal_result(
                                    False, buyer.id, seller_agent.id,
                                    matched_listing['property_id'], 0,
                                    reason=neg_result.get('reason', '谈判失败')
                                )
                                
                                # Handle failed negotiation (seller may adjust price)
                                potential_buyers_est = len(buyers)
                                adjusted = handle_failed_negotiation(seller_agent, matched_listing, self.market, potential_buyers_count=potential_buyers_est)
                                if adjusted:
                                    cursor.execute("UPDATE property_listings SET listed_price=?, min_price=? WHERE property_id=?", 
                                                  (matched_listing['listed_price'], matched_listing['min_price'], matched_listing['property_id']))
                                    cursor.execute("UPDATE properties SET listed_price=? WHERE property_id=?", 
                                                  (matched_listing['listed_price'], matched_listing['property_id']))
                                
                conn.commit()
                
                # Monthly Summary with enhanced display
                month_duration = time.time() - month_start_time
                total_volume = sum([t.get('price', 0) for t in transactions_log_data])
                exchange_display.show_monthly_summary(month, transactions_count, total_volume, failed_negotiations, month_duration)
                wf_logger.show_monthly_summary(month, transactions_log_data, month_duration)
                
        except Exception as e:
            import traceback
            logger.error(traceback.format_exc())
            raise
        finally:
            conn.close()
            handlers = logger.handlers[:]
            for handler in handlers:
                handler.close()
                logger.removeHandler(handler)
            
        total_duration = time.time() - overall_start_time
        logger.info(f"Simulation completed in {total_duration:.2f} seconds.")
                
        # Generate Reports
        logger.info("Generating final reports...")
        try:
            generate_all_reports()
            wf_logger.section_header("🎉 模拟结束，报告已生成")
        except Exception as e:
            print(f"Report generation failed: {e}")

if __name__ == "__main__":
    runner = SimulationRunner(agent_count=5, months=3)
    runner.run()
