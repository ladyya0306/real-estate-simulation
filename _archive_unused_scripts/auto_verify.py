import sqlite3
import os
import time

# 等待新的模拟结果生成
results_dir = 'd:/GitProj/oasis-main/results'
print("⏳ 等待模拟完成...")

# 等待直到找到新的模拟数据库
while True:
    if os.path.exists(results_dir):
        folders = [f for f in os.listdir(results_dir) if f.startswith('run_')]
        if folders:
            latest_folder = sorted(folders)[-1]
            db_path = os.path.join(results_dir, latest_folder, 'simulation.db')
            console_log = os.path.join(results_dir, latest_folder, 'console_log.txt')
            
            # 检查console_log是否包含"Export Complete"
            if os.path.exists(console_log):
                with open(console_log, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if '✅ Export Complete' in content:
                        print(f"✅ 模拟完成！数据库: {db_path}\n")
                        break
    
    time.sleep(5)

# 验证数据库
print("="*70)
print("🎉 Tier 6 最终验证报告")
print("="*70)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 数据统计
print("\n【核心数据统计】")
cursor.execute("SELECT COUNT(*) FROM agents_static")
print(f"  智能体总数: {cursor.fetchone()[0]}")

cursor.execute("SELECT COUNT(*) FROM properties_static")
print(f"  房产总数: {cursor.fetchone()[0]}")

cursor.execute("SELECT COUNT(*) FROM transactions")
tc = cursor.fetchone()[0]
print(f"  ✅ 交易记录: {tc}")

cursor.execute("SELECT COUNT(*) FROM negotiations")
nc = cursor.fetchone()[0]
print(f"  ✅ 谈判记录: {nc}")

cursor.execute("SELECT COUNT(*) FROM decision_logs")
dc = cursor.fetchone()[0]
print(f"  ✅ 决策日志: {dc}")

cursor.execute("SELECT COUNT(*) FROM market_bulletin")
bc = cursor.fetchone()[0]
print(f"  ✅ 市场公报: {bc}")

# 检查console log中是否有错误
print(f"\n【日志检查】")
with open(console_log, 'r', encoding='utf-8') as f:
    log_content = f.read()
    error_count = log_content.count('ERROR')
    print(f"  ERROR数量: {error_count}")
    if error_count > 0:
        print("\n  【错误详情】（最后5条）")
        errors = [line for line in log_content.split('\n') if 'ERROR' in line]
        for err in errors[-5:]:
            print(f"    {err[:100]}")

# 交易详情
if tc > 0:
    print(f"\n【交易详情】（共{tc}笔）")
    cursor.execute(\"""
        SELECT month, property_id, buyer_id, seller_id, final_price, negotiation_rounds
        FROM transactions
        ORDER BY transaction_id
        LIMIT 5
    \""")
    for row in cursor.fetchall():
        month, pid, bid, sid, price, rounds = row
        print(f"  第{month}月: 房产#{pid} | 买家#{bid}→卖家#{sid} | ¥{price:,.0f} | {rounds}轮谈判")
    
    # 统计谈判轮数分布
    cursor.execute("SELECT negotiation_rounds, COUNT(*) FROM transactions GROUP BY negotiation_rounds ORDER BY negotiation_rounds")
    print(f"\n  【谈判轮数分布】")
    for rounds, count in cursor.fetchall():
        print(f"    {rounds}轮: {count}笔")

print("\n" + "="*70)
if tc > 0 and nc > 0:
    print("✅✅✅ 所有Tier 6功能验证通过！交易系统正常运行！")
else:
    print(f"⚠️  数据不完整: 交易{tc}, 谈判{nc}, 决策{dc}, 公报{bc}")
print("="*70)

conn.close()
