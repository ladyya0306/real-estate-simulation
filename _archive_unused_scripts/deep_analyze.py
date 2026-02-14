# -*- coding: utf-8 -*-
"""深度分析新数据库 - 追踪为什么还是只有1笔成交"""
import sqlite3
import sys

# Force UTF-8
sys.stdout.reconfigure(encoding='utf-8')

db_path = 'results/run_20260208_221507/simulation.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 80)
print("分析新数据库: run_20260208_221507")
print("=" * 80)

# 1. 基础统计
print("\n[1] 基础统计:")
cursor.execute("SELECT COUNT(*) FROM agents_static")
print(f"  总agents: {cursor.fetchone()[0]}")

cursor.execute("SELECT role, COUNT(*) FROM active_participants GROUP BY role")
print(f"  角色分布: {dict(cursor.fetchall())}")

cursor.execute("SELECT status, COUNT(*) FROM properties_market GROUP BY status")
print(f"  房产状态: {dict(cursor.fetchall())}")

cursor.execute("SELECT COUNT(*) FROM transactions")
print(f"  交易数: {cursor.fetchone()[0]}")

cursor.execute("SELECT success, COUNT(*) FROM negotiations GROUP BY success")
print(f"  谈判分布: {dict(cursor.fetchall())}")

# 2. Preference数据检查
print("\n[2] Buyer Preference数据:")
cursor.execute("""
    SELECT agent_id, target_zone, max_price
    FROM active_participants
    WHERE role IN ('BUYER', 'BUYER_SELLER')
    LIMIT 15
""")
rows = cursor.fetchall()
print("  样本数据 (前15个):")
for r in rows:
    zone = r[1] if r[1] else "NULL"
    price = f"{r[2]:,.0f}" if r[2] else "NULL"
    print(f"    Agent #{r[0]}: zone={zone}, max_price={price}")

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
print(f"\n  统计: 总buyers={total}, 有zone={with_zone}, 有price={with_price}")

# 3. 房产价格 vs Buyer预算
print("\n[3] 房产价格 vs Buyer预算:")

# 获取for_sale房产价格范围
cursor.execute("""
    SELECT ps.zone, MIN(pm.listed_price), MAX(pm.listed_price), AVG(pm.listed_price)
    FROM properties_market pm
    JOIN properties_static ps ON pm.property_id = ps.property_id
    WHERE pm.status = 'for_sale'
    GROUP BY ps.zone
""")
zone_prices = cursor.fetchall()
for z in zone_prices:
    zone, min_p, max_p, avg_p = z
    print(f"  Zone {zone}: 价格 {min_p:,.0f} ~ {max_p:,.0f} (avg: {avg_p:,.0f})")

# 获取Buyer max_price分布
cursor.execute("""
    SELECT target_zone, MIN(max_price), MAX(max_price), AVG(max_price)
    FROM active_participants
    WHERE role IN ('BUYER', 'BUYER_SELLER') AND max_price > 0
    GROUP BY target_zone
""")
buyer_prices = cursor.fetchall()
print("\n  Buyer max_price分布:")
for bp in buyer_prices:
    zone, min_p, max_p, avg_p = bp
    zone = zone if zone else "NULL"
    print(f"  Zone {zone}: 预算 {min_p:,.0f} ~ {max_p:,.0f} (avg: {avg_p:,.0f})")

# 4. 关键诊断: 有多少buyer的预算能买得起最便宜的房子
print("\n[4] 关键诊断: 买家预算是否足够?")

for zone_data in zone_prices:
    zone = zone_data[0]
    min_listing_price = zone_data[1]

    cursor.execute("""
        SELECT COUNT(*) FROM active_participants
        WHERE role IN ('BUYER', 'BUYER_SELLER')
        AND target_zone = ?
        AND max_price >= ?
    """, (zone, min_listing_price))
    can_afford = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM active_participants
        WHERE role IN ('BUYER', 'BUYER_SELLER')
        AND target_zone = ?
    """, (zone,))
    total_zone = cursor.fetchone()[0]

    print(f"  Zone {zone}: {can_afford}/{total_zone} buyers能买得起最便宜房 ({min_listing_price:,.0f})")

    # 显示买不起的
    cursor.execute("""
        SELECT agent_id, max_price FROM active_participants
        WHERE role IN ('BUYER', 'BUYER_SELLER')
        AND target_zone = ?
        AND max_price < ?
        LIMIT 5
    """, (zone, min_listing_price))
    cant = cursor.fetchall()
    if cant:
        print("    买不起的buyers:")
        for c in cant:
            print(f"      Agent #{c[0]}: max_price={c[1]:,.0f} < {min_listing_price:,.0f}")

# 5. 检查match_property_for_buyer的输入
print("\n[5] 诊断: listings_by_zone结构")

cursor.execute("""
    SELECT ps.zone, pm.property_id, pm.listed_price, pm.owner_id
    FROM properties_market pm
    JOIN properties_static ps ON pm.property_id = ps.property_id
    WHERE pm.status = 'for_sale'
""")
listings = cursor.fetchall()
listings_by_zone = {}
for l in listings:
    zone = l[0]
    if zone not in listings_by_zone:
        listings_by_zone[zone] = []
    listings_by_zone[zone].append({'property_id': l[1], 'listed_price': l[2], 'owner_id': l[3]})

for zone, lst in listings_by_zone.items():
    print(f"  Zone {zone}: {len(lst)} listings")
    for i, l in enumerate(lst[:3]):
        print(f"    #{l['property_id']}: {l['listed_price']:,.0f} (owner: {l['owner_id']})")

# 6. 谈判记录详情
print("\n[6] 谈判记录详情:")
cursor.execute("SELECT * FROM negotiations")
negs = cursor.fetchall()
print(f"  总谈判记录: {len(negs)}")
if negs:
    for n in negs:
        print(f"  {n}")

# 7. Decision logs
print("\n[7] Decision Logs:")
cursor.execute("""
    SELECT event_type, decision, COUNT(*)
    FROM decision_logs
    GROUP BY event_type, decision
    ORDER BY event_type
""")
logs = cursor.fetchall()
for l in logs:
    print(f"  {l[0]} -> {l[1]}: {l[2]}")

conn.close()
print("\n" + "=" * 80)
