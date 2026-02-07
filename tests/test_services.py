import unittest
import sqlite3
import os
import shutil
from services.market_service import MarketService
from services.agent_service import AgentService
from services.transaction_service import TransactionService
from database_v2 import init_db
from models import Agent

class TestServices(unittest.TestCase):
    def setUp(self):
        self.test_db = "test_services.db"
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        
        # Init DB
        init_db(self.test_db)
        self.conn = sqlite3.connect(self.test_db)
        self.conn.row_factory = sqlite3.Row
        
        # Mock Config
        class MockConfig:
            def __init__(self):
                self.life_events = True
                self.user_property_count = 10
                self.user_agent_config = None
                self.negotiation = {}
                self.market = {
                   "zones": {
                       "A": {"count": 5},
                       "B": {"count": 5}
                   }
                }
                
        self.config = MockConfig()
        
    def tearDown(self):
        self.conn.close()
        if os.path.exists(self.test_db):
            try:
                os.remove(self.test_db)
            except:
                pass

    def test_market_service_initialization(self):
        service = MarketService(self.config, self.conn)
        properties = service.initialize_market()
        
        self.assertEqual(len(properties), 10)
        self.assertIsNotNone(service.market)

    def test_agent_service_initialization(self):
        market_service = MarketService(self.config, self.conn)
        properties = market_service.initialize_market()
        
        service = AgentService(self.config, self.conn)
        service.initialize_agents(10, properties)
        
        self.assertEqual(len(service.agents), 10)
        
        # Check V2 Tables
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM agents_static")
        self.assertEqual(cursor.fetchone()[0], 10)
        
        cursor.execute("SELECT COUNT(*) FROM agents_finance")
        self.assertEqual(cursor.fetchone()[0], 10)
        
        # Check Property Allocation persistence
        cursor.execute("SELECT COUNT(*) FROM properties_market WHERE owner_id IS NOT NULL")
        alloc_count = cursor.fetchone()[0]
        self.assertTrue(alloc_count > 0)

    def test_market_bulletin(self):
        # Setup data
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO transactions (month, price) VALUES (0, 1000000)")
        cursor.execute("INSERT INTO transactions (month, price) VALUES (0, 1200000)")
        self.conn.commit()
        
        service = MarketService(self.config, self.conn)
        bulletin = service.generate_market_bulletin(1)
        
        self.assertIn("1,100,000", bulletin)
        self.assertIn("成交: 2 套", bulletin)
        
        # Check DB persistence
        cursor.execute("SELECT * FROM market_bulletin WHERE month=1")
        row = cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row['transaction_count'], 2)

    def test_transaction_match(self):
        # This requires more complex setup (active participants)
        pass

if __name__ == '__main__':
    unittest.main()
