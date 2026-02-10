import sqlite3

conn = sqlite3.connect('test_v2.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]

print("数据库中的表:")
for table in sorted(tables):
    print(f"  ✓ {table}")
    
print(f"\n总计: {len(tables)} 个表")

# 验证所有必需的表都存在
required_tables = [
    'agents_static', 'agents_finance', 'active_participants',
    'properties_static', 'properties_market',
    'transactions', 'negotiations', 'decision_logs', 'market_bulletin'
]

missing = [t for t in required_tables if t not in tables]
if missing:
    print(f"\n❌ 缺失的表: {', '.join(missing)}")
else:
    print("\n✅ 所有必需的表都已创建！")

conn.close()
