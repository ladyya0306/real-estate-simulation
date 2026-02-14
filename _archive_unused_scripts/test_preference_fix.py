"""
快速测试脚本：验证preference加载修复
"""
import sqlite3
import sys

sys.path.insert(0, 'd:/GitProj/oasis-main')

from config.config_loader import SimulationConfig
from services.agent_service import AgentService

db_path = 'results/run_20260208_201643/simulation.db'
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

config = SimulationConfig()
agent_service = AgentService(config, conn)

print("=" * 80)
print("测试：从数据库加载agents并验证preference")
print("=" * 80)

# 加载agents
agent_service.load_agents_from_db()

print(f"\n总共加载了 {len(agent_service.agents)} 个agents")

# 检查有多少buyers
buyers = [a for a in agent_service.agents if hasattr(a, 'role') and a.role in ['BUYER', 'BUYER_SELLER']]
print(f"其中 {len(buyers)} 个是BUYER或BUYER_SELLER")

# 检查preference
print("\n检查前10个buyer的preference:")
print("-" * 80)
for i, buyer in enumerate(buyers[:10]):
    has_pref = hasattr(buyer, 'preference') and buyer.preference is not None
    if has_pref:
        zone = buyer.preference.target_zone or "None"
        max_price = buyer.preference.max_price
        print(f"  Buyer #{buyer.id}: ✓ preference存在 | zone={zone} | max_price={max_price:,.0f}")
    else:
        print(f"  Buyer #{buyer.id}: ✗ preference缺失!")

# 统计
buyers_with_pref = [b for b in buyers if hasattr(b, 'preference') and b.preference and b.preference.target_zone]
buyers_without_pref = [b for b in buyers if not (hasattr(b, 'preference') and b.preference and b.preference.target_zone)]

print("\n" + "=" * 80)
print("统计结果:")
print(f"  有完整preference的buyers: {len(buyers_with_pref)} ({len(buyers_with_pref)/len(buyers)*100:.1f}%)")
print(f"  缺少preference的buyers: {len(buyers_without_pref)} ({len(buyers_without_pref)/len(buyers)*100:.1f}%)")
print("=" * 80)

if len(buyers_with_pref) == len(buyers):
    print("\n✅ 修复成功！所有buyers都有完整的preference数据")
else:
    print(f"\n❌ 修复未完全生效，还有 {len(buyers_without_pref)} 个buyers缺少preference")

conn.close()
