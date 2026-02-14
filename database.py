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
import sqlite3


def init_db(db_path):
    """Initialize the database with V3 Schema."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 1. Agents Static
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agents_static (
            agent_id INTEGER PRIMARY KEY,
            name TEXT,
            birth_year INTEGER,
            marital_status TEXT,
            children_ages TEXT,  -- JSON
            occupation TEXT,
            background_story TEXT,
            investment_style TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 2. Agents Finance
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agents_finance (
            agent_id INTEGER PRIMARY KEY,
            monthly_income REAL,
            cash REAL,
            total_assets REAL,
            total_debt REAL,
            mortgage_monthly_payment REAL,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(agent_id) REFERENCES agents_static(agent_id)
        )
    """)

    # 3. Active Participants
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS active_participants (
            agent_id INTEGER PRIMARY KEY,
            role TEXT,
            target_zone TEXT,
            max_price REAL,
            selling_property_id INTEGER,
            min_price REAL,
            listed_price REAL,
            life_pressure TEXT,
            llm_intent_summary TEXT,
            activated_month INTEGER,
            role_duration INTEGER,
            FOREIGN KEY(agent_id) REFERENCES agents_static(agent_id)
        )
    """)

    # 4. Properties Static
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS properties_static (
            property_id INTEGER PRIMARY KEY,
            zone TEXT,
            quality INTEGER,
            building_area REAL,
            property_type TEXT,
            is_school_district BOOLEAN,
            school_tier INTEGER,
            price_per_sqm REAL,
            zone_price_tier TEXT,
            initial_value REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 5. Properties Market
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS properties_market (
            property_id INTEGER PRIMARY KEY,
            owner_id INTEGER,
            status TEXT,
            current_valuation REAL,
            listed_price REAL,
            min_price REAL,
            rental_price REAL,  -- V3.2 Added
            rental_yield REAL,  -- V3.2 Added
            listing_month INTEGER,
            last_transaction_month INTEGER,
            FOREIGN KEY(property_id) REFERENCES properties_static(property_id),
            FOREIGN KEY(owner_id) REFERENCES agents_static(agent_id)
        )
    """)

    # 6. Transactions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            month INTEGER,
            buyer_id INTEGER,
            seller_id INTEGER,
            property_id INTEGER,
            final_price REAL,
            negotiation_mode TEXT,
            transaction_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(buyer_id) REFERENCES agents_static(agent_id),
            FOREIGN KEY(seller_id) REFERENCES agents_static(agent_id),
            FOREIGN KEY(property_id) REFERENCES properties_static(property_id)
        )
    """)

    # 7. Negotiations
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS negotiations (
            negotiation_id INTEGER PRIMARY KEY AUTOINCREMENT,
            buyer_id INTEGER,
            seller_id INTEGER,
            property_id INTEGER,
            round_count INTEGER,
            final_price REAL,
            success BOOLEAN,
            log TEXT, -- JSON
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 8. Decision Logs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS decision_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id INTEGER,
            month INTEGER,
            event_type TEXT,
            decision TEXT,
            reason TEXT,
            thought_process TEXT,
            context_metrics TEXT, -- JSON (New Phase 8)
            llm_called BOOLEAN,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 9. Market Bulletin
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS market_bulletin (
            month INTEGER PRIMARY KEY,
            transaction_volume INTEGER,
            avg_price REAL,
            avg_unit_price REAL,
            price_change_pct REAL,
            zone_a_heat TEXT,
            zone_b_heat TEXT,
            trend_signal TEXT,
            consecutive_direction INTEGER,
            policy_news TEXT,
            llm_analysis TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 10. Agent End Reports (Phase 10)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_end_reports (
            report_id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id INTEGER,
            simulation_run_id TEXT,
            identity_summary TEXT, -- JSON
            finance_summary TEXT, -- JSON
            transaction_summary TEXT, -- JSON
            imp_decision_log TEXT, -- JSON
            llm_portrait TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(agent_id) REFERENCES agents_static(agent_id)
        )
    """)

    # Indices
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_properties_market_status ON properties_market(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_active_participants_role ON active_participants(role)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_month ON transactions(month)")

    conn.commit()
    conn.close()
