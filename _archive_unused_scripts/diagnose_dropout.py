#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
诊断脚本：分析为什么 Agent 在 Month 1 激活后大量退出市场
"""
import sqlite3
import json

db_path = r'd:\GitProj\oasis-main\results\run_20260209_205146\simulation.db'
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=" * 80)
print("诊断报告：Agent 激活与退出分析")
print("=" * 80)

# 1. 统计各月激活情况
print("\n【1】激活情况统计")
cursor.execute("""
    SELECT activated_month, role, COUNT(*) as count 
    FROM active_participants 
    GROUP BY activated_month, role 
    ORDER BY activated_month, role
""")
for row in cursor.fetchall():
    print(f"  Month {row['activated_month']}: {row['role']} = {row['count']} 人")

# 2. 查看 decision_logs 中的退出决策
print("\n【2】退出决策统计 (EXIT_DECISION)")
cursor.execute("""
    SELECT month, decision, reason, COUNT(*) as count 
    FROM decision_logs 
    WHERE event_type = 'EXIT_DECISION' 
    GROUP BY month, decision 
    ORDER BY month
""")
exit_rows = cursor.fetchall()
if exit_rows:
    for row in exit_rows:
        print(f"  Month {row['month']}: {row['decision']} ({row['count']} agents)")
        if row['count'] <= 5:  # 打印少数样本的理由
            cursor.execute("""
                SELECT agent_id, reason 
                FROM decision_logs 
                WHERE event_type='EXIT_DECISION' AND month=? AND decision=? 
                LIMIT 3
            """, (row['month'], row['decision']))
            samples = cursor.fetchall()
            for s in samples:
                print(f"    - Agent {s['agent_id']}: {s['reason'][:80]}")
else:
    print("  ⚠️  没有 EXIT_DECISION 记录！")

# 3. 检查 active_participants 的 role_duration
print("\n【3】Active Participants 的 role_duration 分析")
cursor.execute("""
    SELECT role, role_duration, COUNT(*) as count 
    FROM active_participants 
    GROUP BY role, role_duration 
    ORDER BY role, role_duration
""")
for row in cursor.fetchall():
    print(f"  {row['role']} (持续 {row['role_duration']} 月): {row['count']} 人")

# 4. 检查 Month 1 激活的 Agent 现在是否还在表中
print("\n【4】Month 1 激活的 Agent 留存情况")
cursor.execute("""
    SELECT COUNT(*) as total 
    FROM active_participants 
    WHERE activated_month = 1
""")
month1_remaining = cursor.fetchone()['total']
print(f"  Month 1 激活的 Agent 当前仍在 active_participants: {month1_remaining} 人")

# 推测：如果 Month 1 激活了 80 人，但现在只剩 2 人，那么 78 人去哪了？
# 可能性 1: 被成功交易后移除 (应该有 transaction 记录)
# 可能性 2: 被 EXIT_DECISION 移除
# 可能性 3: 被超时机制移除但没有日志

# 5. 检查交易记录
print("\n【5】交易记录")
cursor.execute("SELECT COUNT(*) as count FROM transactions")
tx_count = cursor.fetchone()['count']
print(f"  总交易数: {tx_count}")

if tx_count > 0:
    cursor.execute("SELECT month, buyer_id, seller_id, final_price FROM transactions")
    for row in cursor.fetchall():
        print(f"  - Month {row['month']}: Buyer {row['buyer_id']} <- Seller {row['seller_id']}, Price: {row['final_price']:,.0f}")

# 6. 谈判记录
print("\n【6】谈判记录")
cursor.execute("SELECT COUNT(*) as count FROM negotiations")
neg_count = cursor.fetchone()['count']
print(f"  总谈判数: {neg_count}")

cursor.execute("SELECT negotiation_id, buyer_id, seller_id, success, final_price, round_count FROM negotiations")
for row in cursor.fetchall():
    status = "成功" if row['success'] else "失败"
    print(f"  - Neg {row['negotiation_id']}: Buyer {row['buyer_id']} vs Seller {row['seller_id']} -> {status}, {row['round_count']} 轮, 价格: {row['final_price'] or 0:,.0f}")

# 7. 检查是否有 Buyer 被意外删除的痕迹
print("\n【7】检查 decision_logs 中所有与 BUYER 相关的事件")
cursor.execute("""
    SELECT month, event_type, COUNT(*) as count 
    FROM decision_logs 
    WHERE event_type NOT IN ('LIFE_EVENT', 'ROLE_DECISION') 
    GROUP BY month, event_type 
    ORDER BY month, event_type
""")
for row in cursor.fetchall():
    print(f"  Month {row['month']}: {row['event_type']} = {row['count']} 条")

# 8. 关键诊断：查看 Month 2 开始时有多少 active_participants
print("\n【8】推测：Month 1 结束后的 Agent 清理")
print("  如果 Month 1 激活了 80 人，但 Month 2 只剩 2 人，可能原因：")
print("  ① 代码在 Month 1->2 转换时意外清空了 active_participants")
print("  ② update_active_participants() 的退出逻辑过于激进")
print("  ③ 交易完成后的 Agent 移除逻辑有误")

# 9. 检查 Month 1 的 ROLE_ACTIVATION 日志
print("\n【9】Month 1 的 ROLE_ACTIVATION 决策")
cursor.execute("""
    SELECT decision, COUNT(*) as count 
    FROM decision_logs 
    WHERE month = 1 AND event_type = 'ROLE_ACTIVATION' 
    GROUP BY decision
""")
month1_activation = cursor.fetchall()
if month1_activation:
    for row in month1_activation:
        print(f"  {row['decision']}: {row['count']} 人")
else:
    print("  ⚠️  没有 ROLE_ACTIVATION 记录 (可能表名不对，或者改为了 ROLE_DECISION)")

# Fallback: 查看 ROLE_DECISION
cursor.execute("""
    SELECT month, decision, COUNT(*) as count 
    FROM decision_logs 
    WHERE event_type = 'ROLE_DECISION' 
    GROUP BY month, decision 
    ORDER BY month
""")
print("\n【10】ROLE_DECISION 统计")
for row in cursor.fetchall():
    print(f"  Month {row['month']}: {row['decision']} = {row['count']} 人")

conn.close()

print("\n" + "=" * 80)
print("诊断完成")
print("=" * 80)

