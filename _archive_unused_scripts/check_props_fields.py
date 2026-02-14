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
