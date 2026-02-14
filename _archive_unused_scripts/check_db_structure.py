"""检查数据库表结构"""
import sqlite3

db_path = 'results/run_20260208_201643/simulation.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 查看所有表
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("数据库中的所有表:")
for table in tables:
    print(f"  - {table[0]}")

# 查看每个表的结构
print("\n各表的字段结构:")
for table in tables:
    table_name = table[0]
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    print(f"\n{table_name}:")
    for col in columns:
        print(f"  {col[1]} ({col[2]})")

conn.close()
