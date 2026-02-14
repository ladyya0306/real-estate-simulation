
import sqlite3
import os

def init_db(db_path):
    """
    Initialize the V2 Database with Staged Data Architecture.
    
    Tables:
    1. agents_static: Read-only biographical data
    2. agents_finance: High-frequency financial data
    3. active_participants: Dynamic table for LLM-driven agents
    4. properties_static: Read-only property attributes
    5. properties_market: Dynamic market status (listings, ownership)
    6. transactions: Historical transaction records
    7. negotiations: negotiation logs
    8. decision_logs: Agent decision history
    """
    
    # Ensure directory exists
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # --- Agent Tables ---
    
    # 1. agents_static
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS agents_static (
        agent_id INTEGER PRIMARY KEY,
        name TEXT,
        birth_year INTEGER,
        marital_status TEXT,
        children_ages TEXT, -- JSON list
        occupation TEXT,
        background_story TEXT,
        investment_style TEXT, -- aggressive/conservative/balanced
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 2. agents_finance
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS agents_finance (
        agent_id INTEGER PRIMARY KEY,
        monthly_income REAL,
        cash REAL,
        total_assets REAL,
        total_debt REAL,
        mortgage_monthly_payment REAL,  -- ✅ Phase 3.2: Renamed from monthly_payment
        net_cashflow REAL, -- New in V2.6
        max_affordable_price REAL, -- New in V2.7
        psychological_price REAL, -- New in V2.7
        last_price_update_month INTEGER, -- New in V2.7
        last_price_update_reason TEXT, -- New in V2.7
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(agent_id) REFERENCES agents_static(agent_id)
    )
    ''')
    
    # 3. active_participants
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS active_participants (
        agent_id INTEGER PRIMARY KEY,
        role TEXT, -- BUYER / SELLER / BUYER_SELLER / LANDLORD / TENANT
        rental_status TEXT, -- 🆕 'owned', 'renting_market', 'renting_shadow', 'unhoused'
        target_zone TEXT, -- A / B (for buyers)
        max_price REAL, -- buyer's max budget
        selling_property_id INTEGER, -- property being sold (for sellers)
        min_price REAL, -- seller's minimum acceptable price
        listed_price REAL, -- seller's current listing price
        life_pressure TEXT, -- patient / anxious / desperate
        llm_intent_summary TEXT,
        activated_month INTEGER, -- month when agent became active
        role_duration INTEGER DEFAULT 0,
        FOREIGN KEY(agent_id) REFERENCES agents_static(agent_id),
        FOREIGN KEY(selling_property_id) REFERENCES properties_static(property_id)
    )
    ''')

    # 4. properties_static
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS properties_static (
        property_id INTEGER PRIMARY KEY,
        zone TEXT, -- A / B
        quality TEXT, -- Low / Medium / High
        building_area REAL,
        property_type TEXT,
        is_school_district BOOLEAN,
        school_tier TEXT,
        price_per_sqm REAL NOT NULL DEFAULT 0,  -- 🆕 单价（¥/㎡）
        zone_price_tier TEXT,  -- 🆕 价格档位: 'premium', 'standard', 'budget'
        initial_value REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # 5. properties_market
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS properties_market (
        property_id INTEGER PRIMARY KEY,
        owner_id INTEGER, -- NULL if system owned or transient
        status TEXT, -- off_market / for_sale / for_rent 🆕
        current_valuation REAL,
        listed_price REAL,
        min_price REAL,
        rental_price REAL, -- 🆕 月租金
        rental_yield REAL, -- 🆕 租售比 (年租金/房价)
        listing_month INTEGER,
        last_transaction_month INTEGER,
        last_price_update_month INTEGER, -- New in V2.7
        last_price_update_reason TEXT, -- New in V2.7
        FOREIGN KEY(property_id) REFERENCES properties_static(property_id),
        FOREIGN KEY(owner_id) REFERENCES agents_static(agent_id)
    )
    ''')

    # 6. transactions
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS transactions (
        transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
        month INTEGER,
        property_id INTEGER,
        buyer_id INTEGER,
        seller_id INTEGER,
        final_price REAL,
        down_payment REAL,
        loan_amount REAL,
        negotiation_rounds INTEGER,
        buyer_strategy TEXT,
        seller_strategy TEXT,
        transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(property_id) REFERENCES properties_static(property_id),
        FOREIGN KEY(buyer_id) REFERENCES agents_static(agent_id),
        FOREIGN KEY(seller_id) REFERENCES agents_static(agent_id)
    )
    ''')
    
    # ✅ Phase 3.3: property_buyer_matches - Track all bidding activity
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS property_buyer_matches (
        match_id INTEGER PRIMARY KEY AUTOINCREMENT,
        month INTEGER NOT NULL,
        property_id INTEGER NOT NULL,
        buyer_id INTEGER NOT NULL,
        listing_price REAL NOT NULL,
        buyer_bid REAL NOT NULL,
        is_valid_bid BOOLEAN DEFAULT 1,
        proceeded_to_negotiation BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(property_id) REFERENCES properties_static(property_id),
        FOREIGN KEY(buyer_id) REFERENCES agents_static(agent_id)
    )
    ''')
    
    # Create indexes for efficient querying
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_matches_month ON property_buyer_matches(month)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_matches_property ON property_buyer_matches(property_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_matches_buyer ON property_buyer_matches(buyer_id)')
    
    # 7. negotiations
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS negotiations (
        negotiation_id INTEGER PRIMARY KEY AUTOINCREMENT,
        buyer_id INTEGER,
        seller_id INTEGER,
        property_id INTEGER,
        round_count INTEGER,
        final_price REAL,
        success BOOLEAN,
        reason TEXT,
        log TEXT, -- JSON history
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(property_id) REFERENCES properties_static(property_id),
        FOREIGN KEY(buyer_id) REFERENCES agents_static(agent_id),
        FOREIGN KEY(seller_id) REFERENCES agents_static(agent_id)
    )
    ''')
    
    # 8. decision_logs
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS decision_logs (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        agent_id INTEGER,
        month INTEGER,
        event_type TEXT, -- Was decision_type
        decision TEXT, -- Was decision_outcome
        reason TEXT, -- Was reasoning
        thought_process TEXT, -- Was llm_response
        context_metrics TEXT, -- 🆕 Phase 8: Hard financial metrics JSON
        llm_called BOOLEAN, -- Was is_llm_driven
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(agent_id) REFERENCES agents_static(agent_id)
    )
    ''')
    
    # 9. rental_transactions (Phase 7.2)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS rental_transactions (
        transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id INTEGER,
        landlord_id INTEGER,
        tenant_id INTEGER,
        monthly_rent REAL,
        start_month INTEGER,
        end_month INTEGER, -- NULL if ongoing
        contract_type TEXT, -- 'standard', 'shadow'
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(property_id) REFERENCES properties_static(property_id),
        FOREIGN KEY(landlord_id) REFERENCES agents_static(agent_id),
        FOREIGN KEY(tenant_id) REFERENCES agents_static(agent_id)
    )
    ''')
    
    # 10. market_bulletin (Tier 5)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS market_bulletin (
        month INTEGER PRIMARY KEY,
        transaction_volume INTEGER,
        avg_price REAL,
        avg_unit_price REAL, -- 🆕 Phase 5: Unit Price
        zone_a_heat TEXT,
        zone_b_heat TEXT,
        trend_signal TEXT, -- UP / DOWN / STABLE / PANIC
        policy_news TEXT, -- Researcher interventions
        llm_analysis TEXT, -- Optional LLM commentary
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # 11. agent_end_reports (Phase 10: Automated Analysis)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS agent_end_reports (
        report_id INTEGER PRIMARY KEY AUTOINCREMENT,
        agent_id INTEGER,
        simulation_run_id TEXT, -- Optional identifier for the run
        identity_summary TEXT, -- JSON
        finance_summary TEXT, -- JSON
        transaction_summary TEXT, -- JSON/Text
        imp_decision_log TEXT, -- JSON/Text (Important decisions)
        llm_portrait TEXT, -- The "Spicy" Commentary / Biography
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(agent_id) REFERENCES agents_static(agent_id)
    )
    ''')
    
    conn.commit()
    conn.close()
    
    # Auto-run migration to ensure schema is up to date
    migrate_db_v2_7(db_path)

def migrate_db_v2_7(db_path):
    """Ensure V2.7 Schema (Add detailed finance & log columns)"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        # 1. agents_finance additions
        cursor.execute("PRAGMA table_info(agents_finance)")
        columns = [info[1] for info in cursor.fetchall()]
        
        new_cols_af = {
            "net_cashflow": "REAL DEFAULT 0",
            "max_affordable_price": "REAL DEFAULT 0",
            "psychological_price": "REAL DEFAULT 0",
            "last_price_update_month": "INTEGER",
            "last_price_update_reason": "TEXT"
        }
        
        for col, type_def in new_cols_af.items():
            if col not in columns:
                print(f"Migrating agents_finance: Adding {col}...")
                cursor.execute(f"ALTER TABLE agents_finance ADD COLUMN {col} {type_def}")

        # 2. properties_market additions
        cursor.execute("PRAGMA table_info(properties_market)")
        columns_pm = [info[1] for info in cursor.fetchall()]
        
        new_cols_pm = {
            "last_price_update_month": "INTEGER",
            "last_price_update_reason": "TEXT"
        }
        
        for col, type_def in new_cols_pm.items():
            if col not in columns_pm:
                print(f"Migrating properties_market: Adding {col}...")
                cursor.execute(f"ALTER TABLE properties_market ADD COLUMN {col} {type_def}")

        # 3. active_participants additions
        cursor.execute("PRAGMA table_info(active_participants)")
        columns_ap = [info[1] for info in cursor.fetchall()]
        
        if "rental_status" not in columns_ap:
             print("Migrating active_participants: Adding rental_status...")
             cursor.execute("ALTER TABLE active_participants ADD COLUMN rental_status TEXT")
        
        # 4. market_bulletin additions (Phase 5)
        cursor.execute("PRAGMA table_info(market_bulletin)")
        columns_mb = [info[1] for info in cursor.fetchall()]
        
        if "avg_unit_price" not in columns_mb:
             print("Migrating market_bulletin: Adding avg_unit_price...")
             cursor.execute("ALTER TABLE market_bulletin ADD COLUMN avg_unit_price REAL DEFAULT 0")

        # 5. decision_logs additions (Phase 8)
        cursor.execute("PRAGMA table_info(decision_logs)")
        columns_dl = [info[1] for info in cursor.fetchall()]

        if "context_metrics" not in columns_dl:
            print("Migrating decision_logs: Adding context_metrics...")
            cursor.execute("ALTER TABLE decision_logs ADD COLUMN context_metrics TEXT")

        # 6. agent_end_reports (Phase 10)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='agent_end_reports'")
        if not cursor.fetchone():
            print("Migrating: Creating agent_end_reports table...")
            cursor.execute('''
            CREATE TABLE agent_end_reports (
                report_id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id INTEGER,
                simulation_run_id TEXT,
                identity_summary TEXT,
                finance_summary TEXT,
                transaction_summary TEXT,
                imp_decision_log TEXT,
                llm_portrait TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(agent_id) REFERENCES agents_static(agent_id)
            )
            ''')

        conn.commit()
    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    # Test initialization
    init_db("test_v2.db")
