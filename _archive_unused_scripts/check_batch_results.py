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

import os
import sqlite3

proj_name = "test_run_batch_match_v2"
db_path = os.path.join("results", proj_name, "simulation.db")

print(f"=== Checking Results: {proj_name} ===")

if not os.path.exists(db_path):
    print("❌ DB not found!")
    exit()

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# 1. Transactions
cursor.execute("SELECT COUNT(*) FROM transactions")
tx_count = cursor.fetchone()[0]
print(f"\n✅ Total Transactions: {tx_count}")

if tx_count > 0:
    cursor.execute("SELECT month, buyer_id, seller_id, price, negotiation_mode FROM transactions")
    for row in cursor.fetchall():
        print(f"  - Month {row['month']}: Buyer {row['buyer_id']} <- Seller {row['seller_id']} | Price: {row['price']:,.0f} | Mode: {row['negotiation_mode']}")

# 2. Negotiations
cursor.execute("SELECT COUNT(*) FROM negotiations")
neg_count = cursor.fetchone()[0]
print(f"\n✅ Total Negotiations: {neg_count}")

cursor.execute("SELECT negotiation_id, buyer_id, seller_id, success, round_count FROM negotiations")
for row in cursor.fetchall():
    status = "SUCCESS" if row['success'] else "FAIL"
    print(f"  - Neg {row['negotiation_id']}: {status} (Rounds: {row['round_count']})")

# 3. Active Buyers
cursor.execute("SELECT COUNT(*) FROM active_participants WHERE role IN ('BUYER', 'BUYER_SELLER')")
buyer_count = cursor.fetchone()[0]
print(f"\n✅ Active Buyers Remaining: {buyer_count}")

conn.close()
