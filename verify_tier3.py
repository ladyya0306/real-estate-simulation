"""
Tier 3 Verification Test: LLM Autonomous Pricing & Strategy Flexibility
"""
import sqlite3
import pandas as pd
from simulation_runner import SimulationRunner
from config.config_loader import SimulationConfig
import os

def verify_tier3():
    print("=" * 60)
    print("Tier 3 验证测试：LLM 自主调价 + 策略参数自由度")
    print("=" * 60)
    
    # Test Configuration
    test_config = {
        "agent_count": 50,
        "months": 3,
        "seed": 42
    }
    
    print(f"\n测试配置：{test_config['agent_count']} agents, {test_config['months']} months")
    
    # Run Simulation
    print("\n启动模拟...")
    config = SimulationConfig()
    runner = SimulationRunner(
        agent_count=test_config['agent_count'],
        months=test_config['months'],
        seed=test_config['seed'],
        config=config
    )
    
    try:
        runner.run()
        db_path = runner.db_path
        print(f"\n✅ 模拟完成！数据库: {db_path}")
    except Exception as e:
        print(f"\n❌ 模拟失败: {e}")
        return
    
    # Analyze Results
    print("\n" + "=" * 60)
    print("数据分析")
    print("=" * 60)
    
    conn = sqlite3.connect(db_path)
    
    # 1. Price Adjustment Decisions
    print("\n【1】超时调价决策分布:")
    df_price_adj = pd.read_sql_query("""
        SELECT decision, COUNT(*) as count, 
               AVG(CAST(substr(reason, 1, 10) AS REAL)) as avg_reason_len
        FROM decision_logs
        WHERE event_type = 'PRICE_ADJUSTMENT'
        GROUP BY decision
    """, conn)
    
    if len(df_price_adj) > 0:
        print(df_price_adj.to_string(index=False))
        print(f"\n总计超时调价决策: {df_price_adj['count'].sum()} 次")
    else:
        print("  无超时调价记录（可能房产未超时）")
    
    # 2. Pricing Coefficient Distribution
    print("\n【2】策略定价系数统计:")
    
    # Get listing strategies
    df_listings = pd.read_sql_query("""
        SELECT pl.listed_price, pm.base_value, 
               (pl.listed_price * 1.0 / pm.base_value) as coefficient
        FROM property_listings pl
        JOIN properties_market pm ON pl.property_id = pm.property_id
        WHERE pl.status = 'active'
    """, conn)
    
    if len(df_listings) > 0:
        print(f"  样本数: {len(df_listings)}")
        print(f"  系数范围: {df_listings['coefficient'].min():.2f} ~ {df_listings['coefficient'].max():.2f}")
        print(f"  平均系数: {df_listings['coefficient'].mean():.2f}")
        print(f"  中位数: {df_listings['coefficient'].median():.2f}")
        
        # Distribution by range
        print("\n  系数分布:")
        ranges = [
            ("策略 C 区间 (0.90~0.97)", 0.90, 0.97),
            ("策略 B 区间 (0.98~1.05)", 0.98, 1.05),
            ("策略 A 区间 (1.10~1.20)", 1.10, 1.20),
            ("其他", 0, 10)
        ]
        
        for label, min_val, max_val in ranges:
            if label == "其他":
                count = len(df_listings[(df_listings['coefficient'] < 0.90) | 
                                        (df_listings['coefficient'] > 1.20)])
            else:
                count = len(df_listings[(df_listings['coefficient'] >= min_val) & 
                                        (df_listings['coefficient'] <= max_val)])
            pct = count / len(df_listings) * 100
            print(f"  {label}: {count} ({pct:.1f}%)")
    else:
        print("  无挂牌记录")
    
    # 3. LLM Call Statistics
    print("\n【3】LLM 调用统计:")
    df_llm = pd.read_sql_query("""
        SELECT event_type, COUNT(*) as count
        FROM decision_logs
        WHERE llm_called = 1
        GROUP BY event_type
    """, conn)
    
    if len(df_llm) > 0:
        print(df_llm.to_string(index=False))
        print(f"\n总计 LLM 调用: {df_llm['count'].sum()} 次")
    else:
        print("  无 LLM 调用记录")
    
    # 4. Transaction Success Rate
    print("\n【4】交易成功率:")
    df_trans = pd.read_sql_query("""
        SELECT COUNT(*) as total_transactions
        FROM transactions
    """, conn)
    
    df_listings_total = pd.read_sql_query("""
        SELECT COUNT(*) as total_listings
        FROM property_listings
    """, conn)
    
    total_trans = df_trans.iloc[0]['total_transactions']
    total_listings = df_listings_total.iloc[0]['total_listings']
    
    if total_listings > 0:
        success_rate = total_trans / total_listings * 100
        print(f"  总挂牌: {total_listings}")
        print(f"  总成交: {total_trans}")
        print(f"  成功率: {success_rate:.1f}%")
    else:
        print("  无挂牌记录")
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("✅ 验证测试完成")
    print("=" * 60)

if __name__ == "__main__":
    verify_tier3()
