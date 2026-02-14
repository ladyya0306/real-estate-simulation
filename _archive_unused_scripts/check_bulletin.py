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
import sys

# Force UTF-8
sys.stdout.reconfigure(encoding='utf-8')

db_path = r'd:\GitProj\oasis-main\results\run_20260208_230234\simulation.db'
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print(f"Checking market_bulletin in {db_path}...")

# Check table schema
cursor.execute("PRAGMA table_info(market_bulletin)")
columns = [r[1] for r in cursor.fetchall()]
print(f"Columns: {columns}")

# Check data
try:
    cursor.execute("SELECT * FROM market_bulletin LIMIT 1")
    row = cursor.fetchone()
    if row:
        print("Sample Row:")
        for col in columns:
            print(f"  {col}: {row[col]}")
    else:
        print("Table is empty.")
except Exception as e:
    print(f"Error querying data: {e}")

conn.close()
