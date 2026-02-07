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
        monthly_payment REAL,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(agent_id) REFERENCES agents_static(agent_id)
    )
    ''')
    
    # 3. active_participants
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS active_participants (
        agent_id INTEGER PRIMARY KEY,
        role TEXT, -- BUYER / SELLER / BUYER_SELLER
        target_zone TEXT,
        max_price REAL,
        selling_property_id INTEGER,
        min_price REAL,
        listed_price REAL,
        life_pressure TEXT, -- urgent/patient/opportunistic
        llm_intent_summary TEXT,
        activated_month INTEGER,
        role_duration INTEGER,
        FOREIGN KEY(agent_id) REFERENCES agents_static(agent_id)
    )
    ''')
    
    # --- Property Tables ---
    
    # 4. properties_static
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS properties_static (
        property_id INTEGER PRIMARY KEY,
        zone TEXT, -- A/B
        quality INTEGER, -- 1/2/3
        building_area REAL,
        property_type TEXT,
        is_school_district BOOLEAN,
        school_tier INTEGER,
        initial_value REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 5. properties_market
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS properties_market (
        property_id INTEGER PRIMARY KEY,
        owner_id INTEGER, -- NULL if system owned or transient
        status TEXT, -- off_market / for_sale
        current_valuation REAL,
        listed_price REAL,
        min_price REAL,
        listing_month INTEGER,
        last_transaction_month INTEGER,
        FOREIGN KEY(property_id) REFERENCES properties_static(property_id),
        FOREIGN KEY(owner_id) REFERENCES agents_static(agent_id)
    )
    ''')
    
    # --- Log Tables ---
    
    # 6. transactions
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS transactions (
        transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
        month INTEGER,
        buyer_id INTEGER,
        seller_id INTEGER,
        property_id INTEGER,
        price REAL,
        negotiation_mode TEXT, -- batch/flash/deep
        transaction_type TEXT, -- system_sale/secondary
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(buyer_id) REFERENCES agents_static(agent_id),
        FOREIGN KEY(seller_id) REFERENCES agents_static(agent_id),
        FOREIGN KEY(property_id) REFERENCES properties_static(property_id)
    )
    ''')
    
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
        log TEXT, -- JSON
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 8. decision_logs
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS decision_logs (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        agent_id INTEGER,
        month INTEGER,
        event_type TEXT,
        decision TEXT,
        reason TEXT,
        thought_process TEXT, -- JSON
        llm_called BOOLEAN,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 9. market_bulletin (市场公报表)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS market_bulletin (
        month INTEGER PRIMARY KEY,
        transaction_count INTEGER,
        avg_price REAL,
        price_change_pct REAL,
        zone_a_heat TEXT,
        zone_b_heat TEXT,
        trend_signal TEXT,
        consecutive_direction INTEGER,
        bulletin_text TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Indexes for performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_properties_market_status ON properties_market(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_active_participants_role ON active_participants(role)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_month ON transactions(month)')
    
    conn.commit()
    conn.close()
    print(f"Database initialized at {db_path} with V2 schema.")

if __name__ == "__main__":
    # Test initialization
    init_db("test_v2.db")
