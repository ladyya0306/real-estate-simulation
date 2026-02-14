"""
简化版本的测试脚本
"""
import sqlite3

db_path = 'results/run_20260208_201643/simulation.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 60)
print("检查active_participants表中的buyer数据")
print("=" * 60)

cursor.execute("""
    SELECT agent_id, role, target_zone, max_price
    FROM active_participants
    WHERE role IN ('BUYER', 'BUYER_SELLER')
    LIMIT 10
""")

rows = cursor.fetchall()
print(f"\n找到 {len(rows)} 个buyers (显示前10个):\n")
for row in rows:
    aid, role, zone, price = row
    print(f"  Agent #{aid}: role={role}, zone={zone or 'NULL'}, max_price={price or 'NULL'}")

# 统计
cursor.execute("""
    SELECT
        COUNT(*) as total,
        SUM(CASE WHEN target_zone IS NOT NULL THEN 1 ELSE 0 END) as with_zone,
        SUM(CASE WHEN max_price IS NOT NULL AND max_price > 0 THEN 1 ELSE 0 END) as with_price
    FROM active_participants
    WHERE role IN ('BUYER', 'BUYER_SELLER')
""")

total, with_zone, with_price = cursor.fetchone()
print("\n统计:")
print(f"  总buyers: {total}")
print(f"  有target_zone: {with_zone} ({with_zone/total*100:.1f}%)")
print(f"  有max_price: {with_price} ({with_price/total*100:.1f}%)")

if with_zone == total and with_price == total:
    print("\n✅ 数据库中的preference数据完整！")
else:
    print(f"\n⚠️ 数据库中有 {total-with_zone} 个buyers缺少zone, {total-with_price} 个buyers缺少price")

conn.close()
print("=" * 60)
