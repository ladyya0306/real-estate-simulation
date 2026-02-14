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

# 找到最新的模拟数据库
results_dir = 'd:/GitProj/oasis-main/results'
latest_run = None
latest_time = 0

for folder in os.listdir(results_dir):
    if folder.startswith('run_'):
        folder_path = os.path.join(results_dir, folder)
        if os.path.isdir(folder_path):
            db_path = os.path.join(folder_path, 'simulation.db')
            if os.path.exists(db_path):
                mtime = os.path.getmtime(db_path)
                if mtime > latest_time:
                    latest_time = mtime
                    latest_run = db_path

if not latest_run:
    print("❌ 未找到模拟数据库")
    exit(1)

print(f"📂 数据库路径: {latest_run}\n")

conn = sqlite3.connect(latest_run)
cursor = conn.cursor()

print("=" * 60)
print("数据库验证报告")
print("=" * 60)

# 1. 验证表存在
print("\n【1】表结构检查:")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [row[0] for row in cursor.fetchall()]
required_tables = [
    'agents_static', 'agents_finance', 'active_participants',
    'properties_static', 'properties_market',
    'transactions', 'negotiations', 'decision_logs', 'market_bulletin'
]

for table in required_tables:
    status = "✓" if table in tables else "✗"
    print(f"  {status} {table}")

# 2. 数据统计
print("\n【2】数据统计:")

# 智能体
cursor.execute("SELECT COUNT(*) FROM agents_static")
agent_count = cursor.fetchone()[0]
print(f"  智能体总数: {agent_count}")

# 房产
cursor.execute("SELECT COUNT(*) FROM properties_static")
property_count = cursor.fetchone()[0]
print(f"  房产总数: {property_count}")

# 交易
cursor.execute("SELECT COUNT(*) FROM transactions")
transaction_count = cursor.fetchone()[0]
print(f"  ✅ 交易记录: {transaction_count}")

# 谈判
cursor.execute("SELECT COUNT(*) FROM negotiations")
negotiation_count = cursor.fetchone()[0]
print(f"  ✅ 谈判记录: {negotiation_count}")

# 决策日志
cursor.execute("SELECT COUNT(*) FROM decision_logs")
decision_count = cursor.fetchone()[0]
print(f"  ✅ 决策日志: {decision_count}")

# 市场公报
cursor.execute("SELECT COUNT(*) FROM market_bulletin")
bulletin_count = cursor.fetchone()[0]
print(f"  ✅ 市场公报: {bulletin_count}")

# 3. 交易详情
if transaction_count > 0:
    print("\n【3】交易详情（最近3笔）:")
    cursor.execute("""
        SELECT month, property_id, buyer_id, seller_id, final_price, negotiation_rounds
        FROM transactions
        ORDER BY transaction_id DESC
        LIMIT 3
    """)
    for row in cursor.fetchall():
        month, pid, bid, sid, price, rounds = row
        print(f"  第{month}月: 房产#{pid} | 买家#{bid} → 卖家#{sid} | 成交价: ¥{price:,.0f} | 谈判轮数: {rounds}")

# 4. 谈判样本
if negotiation_count > 0:
    print("\n【4】谈判样本（最后一笔交易）:")
    cursor.execute("""
        SELECT party, action, price, reasoning
        FROM negotiations
        WHERE property_id = (SELECT property_id FROM transactions ORDER BY transaction_id DESC LIMIT 1)
        ORDER BY negotiation_id
        LIMIT 6
    """)
    for row in cursor.fetchall():
        party, action, price, reason = row
        print(f"  {party.upper()}: {action} @ ¥{price:,.0f} - {reason[:50]}...")

# 5. 决策日志样本
if decision_count > 0:
    print("\n【5】决策日志（最近3条）:")
    cursor.execute("""
        SELECT agent_id, decision_type, decision_outcome, is_llm_driven
        FROM decision_logs
        ORDER BY log_id DESC
        LIMIT 3
    """)
    for row in cursor.fetchall():
        aid, dtype, outcome, is_llm = row
        llm_tag = "🤖LLM" if is_llm else "📝规则"
        print(f"  Agent#{aid}: {dtype} → {outcome} ({llm_tag})")

print("\n" + "=" * 60)
if transaction_count > 0 and negotiation_count > 0 and decision_count > 0:
    print("✅ 所有核心功能验证通过！")
else:
    print("⚠️  部分功能可能需要检查")
print("=" * 60)

conn.close()
