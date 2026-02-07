"""
Verify Tier 3 Results from latest simulation DB
"""
import sqlite3
import pandas as pd
import os
import glob

def find_latest_db():
    # Find all .db files in results directory
    search_path = os.path.join("results", "**", "*.db")
    files = glob.glob(search_path, recursive=True)
    if not files:
        # Fallback to current dir default
        if os.path.exists("simulation.db"):
            return "simulation.db"
        return None
    
    # Sort by modification time
    latest_file = max(files, key=os.path.getmtime)
    return latest_file

def verify_v1_cleanup(conn):
    print("\n【0】V1 表清理验证 (V1 Table Cleanup):")
    try:
        conn.execute("SELECT count(*) FROM property_listings")
        print("❌ 失败: property_listings 表仍然存在!")
    except sqlite3.OperationalError:
        print("✅ 成功: property_listings 表已移除 (Expected)")

def verify_results():
    print("=" * 60)
    print("Tier 3 & 4 结果验证")
    print("=" * 60)
    
    db_path = find_latest_db()
    if not db_path:
        print("❌ 未找到数据库文件")
        return
    
    print(f"Checking DB: {db_path}")
    
    conn = sqlite3.connect(db_path)
    
    verify_v1_cleanup(conn)

    
    # 1. Check Price Adjustments
    print("\n【1】超时调价决策 (LLM Autonomous Pricing):")
    try:
        df_adj = pd.read_sql_query("""
            SELECT decision, COUNT(*) as count, reason
            FROM decision_logs 
            WHERE event_type = 'PRICE_ADJUSTMENT'
            GROUP BY decision
        """, conn)
        
        if not df_adj.empty:
            print(df_adj[['decision', 'count']])
            print(f"\nSample Reason: {df_adj.iloc[0]['reason'][:50]}...")
        else:
            print("⚠️ 无超时调价记录 (可能是模拟时间太短或市场太好)")
            
    except Exception as e:
        print(f"Query Error: {e}")

    # 2. Check Pricing Coefficients
    print("\n【2】策略定价系数 (Strategy Flexibility):")
    try:
        # We need to infer coefficient from listed_price vs base_value if strictly checking DB
        # Or check decision_logs if we logged the coefficient? 
        # The code logs 'reason' which might contain info, but better to check the listings.
        
        # Note: We didn't explicitly store coefficient in a separate column in property_listings,
        # but we can infer it.
        # However, checking if listed_price is NOT exactly 1.15/1.0/0.95 * base_value is one way.
        
        df_listings = pd.read_sql_query("""
            SELECT pm.listed_price, pm.current_valuation,
                   (pm.listed_price / pm.current_valuation) as ratio
            FROM properties_market pm
            WHERE pm.status = 'for_sale'
        """, conn)
        
        if not df_listings.empty:
            print(f"挂牌样本数: {len(df_listings)}")
            print(f"定价系数范围: {df_listings['ratio'].min():.4f} ~ {df_listings['ratio'].max():.4f}")
            
            # Check for diversity (not just discrete 1.15, 1.0, 0.95)
            unique_ratios = df_listings['ratio'].round(4).nunique()
            print(f"不同系数值数量: {unique_ratios}")
            if unique_ratios > 5:
                print("✅ 验证成功: 存在多样化的定价系数")
            else:
                print("⚠️ 警告: 系数多样性不足 (可能是固定策略)")
                print(df_listings['ratio'].value_counts().head())
        else:
            print("No active listings found.")
            
    except Exception as e:
        print(f"Query Error: {e}")
        
    conn.close()

if __name__ == "__main__":
    verify_results()
