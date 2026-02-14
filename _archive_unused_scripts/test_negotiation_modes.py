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
import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from transaction_engine import run_batch_bidding_async, run_flash_deal_async


# Mock Classes
class MockAgent:
    def __init__(self, id, max_price):
        self.id = id
        self.preference = MagicMock()
        self.preference.max_price = max_price

class MockMarket:
    pass

class TestNegotiationModes(unittest.TestCase):
    def setUp(self):
        self.seller = MockAgent(999, 0)
        self.buyers = [MockAgent(101, 5000000), MockAgent(102, 4500000)]
        self.listing = {
            'property_id': 1,
            'owner_id': 999,
            'zone': 'A',
            'listing_month': 1,
            'listed_price': 4000000,
            'min_price': 3800000,
            'status': 'for_sale'
        }
        self.market = MockMarket()

    @patch('transaction_engine.safe_call_llm_async', new_callable=AsyncMock)
    def test_batch_bidding_success(self, mock_llm):
        # Setup mock responses for 2 buyers
        # Buyer 1 bids 4.2M (Winner)
        # Buyer 2 bids 3.9M
        mock_llm.side_effect = [
            {"bid_price": 4200000, "reason": "I want it"},
            {"bid_price": 3900000, "reason": "Lowball"}
        ]

        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(
            run_batch_bidding_async(self.seller, self.buyers, self.listing, self.market)
        )

        self.assertEqual(result['outcome'], 'success')
        self.assertEqual(result['buyer_id'], 101)
        self.assertEqual(result['final_price'], 4200000)
        self.assertEqual(result['mode'], 'batch_bidding')

    @patch('transaction_engine.safe_call_llm_async', new_callable=AsyncMock)
    def test_flash_deal_accept(self, mock_llm):
        buyer = self.buyers[0]
        # Flash price will be 4.0M * 0.95 = 3.8M

        mock_llm.return_value = {"action": "ACCEPT", "reason": "Good deal"}

        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(
            run_flash_deal_async(self.seller, buyer, self.listing, self.market)
        )

        self.assertEqual(result['outcome'], 'success')
        self.assertEqual(result['mode'], 'flash_deal')
        self.assertEqual(result['final_price'], 3800000.0) # 4M * 0.95

    @patch('transaction_engine.safe_call_llm_async', new_callable=AsyncMock)
    def test_flash_deal_reject(self, mock_llm):
        buyer = self.buyers[0]

        mock_llm.return_value = {"action": "REJECT", "reason": "Still too expensive"}

        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(
            run_flash_deal_async(self.seller, buyer, self.listing, self.market)
        )

        self.assertEqual(result['outcome'], 'failed')

if __name__ == '__main__':
    unittest.main()
