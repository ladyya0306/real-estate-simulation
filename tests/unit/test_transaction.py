import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from transaction_engine import execute_transaction
from models import Agent, Market

class TestTransactionEngine(unittest.TestCase):

    def setUp(self):
        self.buyer = Agent(id=101, name="Buyer", cash=2000000, monthly_income=50000)
        self.seller = Agent(id=202, name="Seller", cash=1000000, monthly_income=30000)
        
        self.property_data = {
            "property_id": 1,
            "owner_id": 202,
            "base_value": 3000000,
            "status": "for_sale",
            "listed_price": 3200000,
            "zone": "A"
        }
        
        # Link property to seller
        self.seller.owned_properties = [self.property_data]
        
        self.market = MagicMock(spec=Market)
        self.config = MagicMock()

    @patch('transaction_engine.check_affordability')
    @patch('transaction_engine.calculate_monthly_payment')
    def test_execute_transaction_success_full_payment(self, mock_calc_payment, mock_check_affordability):
        # Scenario: Full cash payment (no loan)
        price = 2000000
        mock_check_affordability.return_value = (True, price, 0) # affordable, down_payment=price, loan=0
        
        result = execute_transaction(self.buyer, self.seller, self.property_data, price, self.market, self.config)
        
        # Verify Transaction Record
        self.assertIsNotNone(result)
        self.assertEqual(result['buyer_id'], 101)
        self.assertEqual(result['seller_id'], 202)
        self.assertEqual(result['price'], price)
        self.assertEqual(result['loan_amount'], 0)
        
        # Verify Financials
        self.assertEqual(self.buyer.cash, 0) # 2m - 2m
        self.assertEqual(self.seller.cash, 1000000 + 2000000)
        
        # Verify Ownership
        self.assertEqual(self.property_data['owner_id'], 101)
        self.assertEqual(self.property_data['status'], 'off_market')
        self.assertEqual(self.property_data['base_value'], price)
        self.assertNotIn('listed_price', self.property_data)
        
        # Verify Lists
        self.assertEqual(len(self.seller.owned_properties), 0)
        self.assertEqual(len(self.buyer.owned_properties), 1)
        self.assertEqual(self.buyer.owned_properties[0]['property_id'], 1)

    @patch('transaction_engine.check_affordability')
    @patch('transaction_engine.calculate_monthly_payment')
    def test_execute_transaction_success_with_loan(self, mock_calc_payment, mock_check_affordability):
        # Scenario: Loan
        price = 3000000
        down_payment = 1000000
        loan = 2000000
        monthly_pay = 10000
        
        mock_check_affordability.return_value = (True, down_payment, loan)
        mock_calc_payment.return_value = monthly_pay
        
        result = execute_transaction(self.buyer, self.seller, self.property_data, price, self.market, self.config)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['loan_amount'], loan)
        
        # Verify Buyer Financials
        self.assertEqual(self.buyer.cash, 2000000 - down_payment)
        self.assertEqual(self.buyer.monthly_payment, monthly_pay)
        
        # Verify Seller Financials (Seller always gets full price, bank pays the rest)
        self.assertEqual(self.seller.cash, 1000000 + price)

    @patch('transaction_engine.check_affordability')
    def test_execute_transaction_fail_affordability(self, mock_check_affordability):
        # Scenario: Not affordable
        mock_check_affordability.return_value = (False, 0, 0)
        
        result = execute_transaction(self.buyer, self.seller, self.property_data, 5000000, self.market, self.config)
        
        self.assertIsNone(result)
        
        # Verify State Unchanged
        self.assertEqual(self.buyer.cash, 2000000)
        self.assertEqual(self.property_data['owner_id'], 202)
        
if __name__ == '__main__':
    unittest.main()
