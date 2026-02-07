"""
数据库可视化查看脚本 (Database Viewer)
适合数据库小白快速查看 simulation.db 内容
"""
import sqlite3
import sys
from pathlib import Path

def view_database(db_path):
    """查看数据库所有表和关键数据"""
    
    if not Path(db_path).exists():
        print(f"❌ 数据库文件不存在: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\n" + "="*80)
    print("📊 数据库内容一览表")
    print("="*80 + "\n")
    
    # 1. 列出所有表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    
    print(f"📋 数据库包含 {len(tables)} 张表:\n")
    for i, table in enumerate(tables, 1):
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  {i}. {table:<30} ({count:>5} 条记录)")
    
    print("\n" + "-"*80 + "\n")
    
    # 2. V2 核心表数据预览
    print("🔍 V2 核心数据预览\n")
    
    # 2.1 Agents Static (人口档案)
    print("【1】 agents_static (基础人口档案) - 前5人")
    print("-" * 80)
    cursor.execute("SELECT agent_id, name, occupation, investment_style FROM agents_static LIMIT 5")
    rows = cursor.fetchall()
    if rows:
        print(f"{'ID':<5} {'姓名':<10} {'职业':<20} {'性格':<15}")
        for row in rows:
            print(f"{row[0]:<5} {row[1]:<10} {row[2]:<20} {row[3] or 'N/A':<15}")
    else:
        print("  (无数据)")
    
    print("\n")
    
    # 2.2 Agents Finance (财务状态)
    print("【2】 agents_finance (财务状态) - 前5人")
    print("-" * 80)
    cursor.execute("SELECT agent_id, monthly_income, cash, total_assets FROM agents_finance LIMIT 5")
    rows = cursor.fetchall()
    if rows:
        print(f"{'ID':<5} {'月收入':<15} {'现金':<20} {'总资产':<20}")
        for row in rows:
            print(f"{row[0]:<5} {row[1]:>15,.0f} {row[2]:>20,.0f} {row[3]:>20,.0f}")
    else:
        print("  (无数据)")
    
    print("\n")
    
    # 2.3 Active Participants (活跃参与者 - 漏斗第三层)
    print("【3】 active_participants (活跃参与者 - 漏斗第三层) ⭐")
    print("-" * 80)
    cursor.execute("SELECT agent_id, role, life_pressure, activated_month FROM active_participants")
    rows = cursor.fetchall()
    if rows:
        print(f"{'ID':<5} {'角色':<15} {'压力状态':<15} {'激活月份':<10}")
        for row in rows:
            print(f"{row[0]:<5} {row[1]:<15} {row[2]:<15} {row[3]:<10}")
        print(f"\n  💡 漏斗筛选结果: 从 20 人 → {len(rows)} 人激活")
    else:
        print("  (无激活参与者)")
    
    print("\n")
    
    # 2.4 Decision Logs (LLM 决策日志)
    print("【4】 decision_logs (LLM决策日志)")
    print("-" * 80)
    cursor.execute("SELECT agent_id, event_type, decision FROM decision_logs LIMIT 5")
    rows = cursor.fetchall()
    if rows:
        print(f"{'Agent ID':<10} {'事件类型':<20} {'决策结果':<30}")
        for row in rows:
            decision = row[2][:30] if row[2] else 'N/A'  # 截断过长内容
            print(f"{row[0]:<10} {row[1]:<20} {decision:<30}")
        cursor.execute("SELECT COUNT(*) FROM decision_logs")
        total = cursor.fetchone()[0]
        print(f"\n  💡 共记录 {total} 次 LLM 调用")
    else:
        print("  (无决策日志)")
    
    print("\n")
    
    # 2.5 Transactions (交易记录)
    print("【5】 transactions (交易记录)")
    print("-" * 80)
    cursor.execute("SELECT COUNT(*) FROM transactions")
    tx_count = cursor.fetchone()[0]
    if tx_count > 0:
        cursor.execute("SELECT month, buyer_id, seller_id, property_id, price FROM transactions LIMIT 5")
        rows = cursor.fetchall()
        print(f"{'月份':<5} {'买家ID':<10} {'卖家ID':<10} {'房产ID':<10} {'成交价':<15}")
        for row in rows:
            print(f"{row[0]:<5} {row[1]:<10} {row[2]:<10} {row[3]:<10} {row[4]:>15,.0f}")
    else:
        print("  ⚠️  无交易记录 (可能是模拟时间太短或市场冷清)")
    
    print("\n")
    
    # 2.6 Negotiations (谈判记录)
    print("【6】 negotiations (谈判记录)")
    print("-" * 80)
    cursor.execute("SELECT COUNT(*) FROM negotiations WHERE success=1")
    success = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM negotiations WHERE success=0")
    failed = cursor.fetchone()[0]
    print(f"  成功谈判: {success} 笔")
    print(f"  失败谈判: {failed} 笔")
    
    if success > 0:
        cursor.execute("SELECT buyer_id, seller_id, property_id, final_price FROM negotiations WHERE success=1 LIMIT 3")
        rows = cursor.fetchall()
        print(f"\n  最近成功谈判:")
        print(f"  {'买家ID':<10} {'卖家ID':<10} {'房产ID':<10} {'成交价':<15}")
        for row in rows:
            print(f"  {row[0]:<10} {row[1]:<10} {row[2]:<10} {row[3]:>15,.0f}")
    
    print("\n" + "="*80)
    print("✅ 数据库查看完毕！")
    print("="*80 + "\n")
    
    conn.close()

if __name__ == "__main__":
    # 默认查看最新的运行结果
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        # 自动找最新的 simulation.db
        import glob
        db_files = glob.glob("results/run_*/simulation.db")
        if db_files:
            db_path = max(db_files, key=lambda x: Path(x).stat().st_mtime)
            print(f"📂 自动选择最新数据库: {db_path}\n")
        else:
            print("❌ 未找到任何 simulation.db 文件")
            print("请指定数据库路径: python view_database.py <path/to/simulation.db>")
            sys.exit(1)
    
    view_database(db_path)
