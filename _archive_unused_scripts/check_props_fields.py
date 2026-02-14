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
"""快速检查properties_market的字段"""
import sqlite3

import pandas as pd

db_path = 'results/run_20260208_201643/simulation.db'
conn = sqlite3.connect(db_path)

# 查看properties_market的前几行
print("properties_market 表前5行:")
df = pd.read_sql_query("SELECT * FROM properties_market LIMIT 5", conn)
print(df.to_string())
print(f"\n字段名: {df.columns.tolist()}")

print("\n" + "=" * 80)

# 查看properties_static的前几行
print("properties_static 表前5行:")
df2 = pd.read_sql_query("SELECT * FROM properties_static LIMIT 5", conn)
print(df2.to_string())
print(f"\n字段名: {df2.columns.tolist()}")

conn.close()
