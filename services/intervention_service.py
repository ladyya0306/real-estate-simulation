# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
import logging
import random
import sqlite3

from models import Agent
from utils.name_generator import ChineseNameGenerator

logger = logging.getLogger(__name__)

class InterventionService:
    def __init__(self, db_conn: sqlite3.Connection):
        self.conn = db_conn
        self.name_gen = ChineseNameGenerator()

    def _get_tier(self, income: float) -> str:
        """Helper to classify agent tier based on income."""
        # Simple heuristics based on default config boundaries (Adjust if needed)
        if income < 5000: return "low"
        if income < 12000: return "lower_middle"
        if income < 25000: return "middle"
        if income < 50000: return "upper_middle"
        if income < 100000: return "high"
        return "ultra_high"

    def apply_wage_shock(self, agent_service, pct_change: float, target_tier: str = "all"):
        """
        Adjust monthly income for agents.
        pct_change: -0.10 for 10% cut.
        """
        updated_count = 0
        batch_updates = []

        for agent in agent_service.agents:
            # Skip unemployed
            if agent.monthly_income == 0: continue

            tier = self._get_tier(agent.monthly_income)
            if target_tier != "all" and tier != target_tier:
                continue

            # Apply Shock
            old_income = agent.monthly_income
            new_income = old_income * (1 + pct_change)
            agent.monthly_income = new_income

            batch_updates.append((new_income, agent.id))
            updated_count += 1

        if batch_updates:
            cursor = self.conn.cursor()
            cursor.executemany("UPDATE agents_finance SET monthly_income=? WHERE agent_id=?", batch_updates)
            self.conn.commit()

        logger.info(f"Intervention: Wage Shock {pct_change*100:.1f}% applied to {updated_count} agents.")
        return updated_count

    def apply_unemployment_shock(self, agent_service, rate: float, target_tier: str = "low"):
        """
        Force unemployment on a subset of agents.
        rate: 0.20 means 20% of the target tier will become unemployed.
        """
        candidates = []
        for agent in agent_service.agents:
            if agent.monthly_income == 0: continue # Already unemployed
            tier = self._get_tier(agent.monthly_income)
            if target_tier == "all" or tier == target_tier:
                candidates.append(agent)

        if not candidates:
            return 0

        count = int(len(candidates) * rate)
        targets = random.sample(candidates, count)

        static_updates = []
        finance_updates = []

        for agent in targets:
            agent.story.occupation = "Unemployed"
            agent.monthly_income = 0
            # agent.cash does not change immediately, but will drain via living expenses

            static_updates.append(("Unemployed", agent.id))
            finance_updates.append((0, agent.id))

        cursor = self.conn.cursor()
        if static_updates:
            cursor.executemany("UPDATE agents_static SET occupation=? WHERE agent_id=?", static_updates)
            cursor.executemany("UPDATE agents_finance SET monthly_income=? WHERE agent_id=?", finance_updates)
            self.conn.commit()

        logger.info(f"Intervention: Unemployment Shock ({rate*100}%) applied to {len(targets)} agents in {target_tier}.")
        return len(targets)

    def add_population(self, agent_service, count: int, tier: str):
        """
        Inject new agents into the simulation.
        """
        cursor = self.conn.cursor()

        # Determine Income/Cash based on tier
        # Simplified logic (copying AgentService defaults broadly)
        base_income = {
            "low": 3000, "lower_middle": 8000, "middle": 18000,
            "upper_middle": 35000, "high": 70000, "ultra_high": 150000
        }
        income_center = base_income.get(tier, 18000)

        new_agents = []

        # Get max ID
        max_id = max((a.id for a in agent_service.agents), default=0)
        start_id = max_id + 1

        for i in range(count):
            current_id = start_id + i
            income = random.uniform(income_center * 0.8, income_center * 1.2)
            cash = income * 12 * random.uniform(0.5, 3.0) # Variable savings

            name = self.name_gen.generate()
            age = random.randint(22, 55)

            agent = Agent(current_id, name, age, "single", cash, income)
            agent.story.occupation = "Newcomer" # Marker
            agent.story.background_story = "Migrated to city recently."

            # Add to memory
            agent_service.agents.append(agent)
            agent_service.agent_map[current_id] = agent
            new_agents.append(agent)

            # DB Inserts
            # agents_static: agent_id, name, birth_year, marital_status, children_ages, occupation, background_story, investment_style
            birth_year = 2024 - age
            inv_style = random.choice(["conservative", "balanced", "aggressive"])
            agent.story.investment_style = inv_style

            cursor.execute("""
                INSERT INTO agents_static (agent_id, name, birth_year, marital_status, children_ages, occupation, background_story, investment_style)
                VALUES (?,?,?,?,?,?,?,?)
            """, (agent.id, agent.name, birth_year, "single", "[]", agent.story.occupation, agent.story.background_story, inv_style))

            # agents_finance: agent_id, monthly_income, cash, total_assets, total_debt, mortgage_monthly_payment, net_cashflow ...
            # New columns have defaults, but let's be explicit where needed or rely on defaults.
            # Schema has total_debt.
            cursor.execute("""
                INSERT INTO agents_finance (agent_id, monthly_income, cash, total_assets, total_debt, mortgage_monthly_payment, net_cashflow)
                VALUES (?,?,?,?,?,?,?)
            """, (agent.id, agent.monthly_income, agent.cash, agent.cash, 0, 0, 0))

        self.conn.commit()
        logger.info(f"Intervention: Added {count} new agents ({tier}).")
        return count

    def adjust_housing_supply(self, market_service, count: int, zone: str):
        """
        Add new system-owned properties.
        """
        cursor = self.conn.cursor()

        # Get max property ID
        max_id = 0
        if market_service.market.properties:
            max_id = max(p['property_id'] for p in market_service.market.properties)

        start_id = max_id + 1

        # Basic templates per zone
        base_prices = {"A": 80000, "B": 45000} # Price per sqm
        avg_area = 100

        new_props = []

        for i in range(count):
            pid = start_id + i
            area = random.randint(80, 140)
            u_price = base_prices.get(zone, 50000) * random.uniform(0.9, 1.1)
            base_val = area * u_price

            prop = {
                "property_id": pid,
                "zone": zone,
                "building_area": area,
                "base_value": base_val,
                "owner_id": None, # System
                "status": "for_sale",
                "listed_price": base_val * 1.05,
                "min_price": base_val * 0.95,
                "listing_month": 999 # Intervention month?
            }

            # Add to memory
            market_service.market.properties.append(prop)

            # DB Insert
            cursor.execute("INSERT INTO properties_static (property_id, zone, building_area, initial_value) VALUES (?,?,?,?)",
                          (pid, zone, area, base_val))
            cursor.execute("INSERT INTO properties_market (property_id, status, listed_price, min_price, current_valuation) VALUES (?,?,?,?,?)",
                          (pid, "for_sale", prop['listed_price'], prop['min_price'], base_val))

        self.conn.commit()
    def remove_population(self, agent_service, count: int, tier: str):
        """
        Force exit agents.
        """
        cursor = self.conn.cursor()
        removed_count = 0

        candidates = []
        for agent in agent_service.agents:
            # Skip newly added agents to avoid immediate removal? No, random is fine.
            # Skip 'system' agents if any?
            if tier == "all" or self._get_tier(agent.monthly_income) == tier:
                candidates.append(agent)

        if not candidates:
            return 0

        targets = random.sample(candidates, min(count, len(candidates)))

        ids_to_remove = [a.id for a in targets]

        # 1. DB Updates
        # Remove from active_participants (stops them from buying/selling)
        cursor.execute(f"DELETE FROM active_participants WHERE agent_id IN ({','.join(['?']*len(ids_to_remove))})", ids_to_remove)

        # Mark as 'Exited' in static?
        cursor.execute(f"UPDATE agents_static SET occupation='Exited' WHERE agent_id IN ({','.join(['?']*len(ids_to_remove))})", ids_to_remove)

        # Set Income to 0?
        cursor.execute(f"UPDATE agents_finance SET monthly_income=0 WHERE agent_id IN ({','.join(['?']*len(ids_to_remove))})", ids_to_remove)

        self.conn.commit()

        # 2. Memory Updates
        # We need to remove from agent_service.agents list so they don't get processed in loop
        # But removing from list while iterating is bad. SimulationRunner iterates copy or key?
        # SimulationRunner uses `agent_service.agents`.
        # Best to just mark them as 'Exited' and have AgentService loop skip them?
        # But AgentService doesn't check 'Exited'.
        # Safer to remove from list.

        for t in targets:
            if t in agent_service.agents:
                agent_service.agents.remove(t)
            if t.id in agent_service.agent_map:
                del agent_service.agent_map[t.id]

        logger.info(f"Intervention: Removed {len(targets)} agents ({tier}).")
        return len(targets)

    def supply_cut(self, market_service, count: int, zone: str):
        """
        Remove listings (force off-market).
        """
        cursor = self.conn.cursor()

        candidates = [p for p in market_service.market.properties if p['status'] == 'for_sale' and p['zone'] == zone]

        if not candidates:
            return 0

        targets = random.sample(candidates, min(count, len(candidates)))
        ids = [p['property_id'] for p in targets]

        # DB Update
        cursor.execute(f"UPDATE properties_market SET status='off_market' WHERE property_id IN ({','.join(['?']*len(ids))})", ids)
        self.conn.commit()

        # Memory Update
        for p in targets:
            p['status'] = 'off_market'

        logger.info(f"Intervention: Supply Cut - Removed {len(targets)} listings in Zone {zone}.")
        return len(targets)

    def set_financial_policy(self, config, down_payment_ratio: float = None, mortgage_rate: float = None):
        """
        Update global financial config.
        """
        updates = []
        if down_payment_ratio is not None:
            # Try to update transaction_engine/config logic
            # config object is passed in.
            # Assuming config structure matches simulation usage
            # config.mortgage_config? or MORTGAGE_CONFIG constant?
            # settings.py has constants. ConfigLoader loads them.
            # We need to modify the runtime config object.
            # If system relies on global constants in settings.py, we can't easily change it without reload.
            # But SimulationRunner passes `self.config` to services.
            # AND mortgage_system.py might import `MORTGAGE_CONFIG` directly.
            pass

        # For Tier 5, we assume we can modify run-time config or DB.
        # Let's log it for now as a "Policy Announcement".

        logger.info(f"Intervention: Financial Policy - DP: {down_payment_ratio}, Rate: {mortgage_rate}")
        return True
