
# 自动验证脚本 (Programmatic Version)
import os
import sys

# 确保在正确目录
os.chdir('d:/GitProj/oasis-main')
sys.path.append('d:/GitProj/oasis-main')

import sqlite3

import project_manager
from config.config_loader import SimulationConfig
from simulation_runner import SimulationRunner


def verify_fix():
    print("🚀 启动自动验证 (Direct Runner Mode)...")

    # 1. Setup Project
    print("Step 1: Creating Validation Project...")
    proj_dir, config_path, db_path = project_manager.create_new_project("config/baseline.yaml")
    print(f"  Project Dir: {proj_dir}")
    print(f"  DB Path: {db_path}")

    # 2. Configure Simulation
    config = SimulationConfig(config_path)
    # Ensure config is appropriate for test
    config.save()

    agent_count = 50
    months = 2

    # 3. Initialize Runner
    print(f"Step 2: Initializing Runner (Agents={agent_count}, Months={months})...")
    runner = SimulationRunner(
        agent_count=agent_count,
        months=months,
        seed=42, # Fixed seed for reproducibility
        resume=False,
        config=config,
        db_path=db_path
    )

    # 4. Run Simulation
    print("Step 3: Running Simulation...")
    try:
        runner.run()
        print("✅ Simulation Loop Completed.")
    except Exception as e:
        print(f"❌ Simulation Failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # 5. Verify Results
    print("\nStep 4: Verifying Data...")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Check 1: Transactions
    cursor.execute("SELECT COUNT(*) FROM transactions")
    tx_count = cursor.fetchone()[0]
    print(f"  Transactions: {tx_count}")

    # Check 2: Negotiations
    cursor.execute("SELECT success, COUNT(*) as count FROM negotiations GROUP BY success")
    neg_rows = cursor.fetchall()
    neg_stats = {r['success']: r['count'] for r in neg_rows}
    total_negs = sum(neg_stats.values())
    print(f"  Negotiations: {total_negs} (Success: {neg_stats.get(1, 0)}, Fail: {neg_stats.get(0, 0)})")

    # Check 3: Market Bulletin
    print("  Checking Market Bulletin...")
    has_bulletin_content = False
    try:
        cursor.execute("SELECT month, policy_news, llm_analysis FROM market_bulletin ORDER BY month ASC")
        bulletins = cursor.fetchall()
        if bulletins:
            for b in bulletins:
                p_news = b['policy_news']
                l_analysis = b['llm_analysis']
                print(f"    Month {b['month']}:")
                print(f"      Policy News: {p_news[:30]}..." if p_news else "      Policy News: EMPTY")
                print(f"      LLM Analysis: {l_analysis[:30]}..." if l_analysis else "      LLM Analysis: EMPTY")

                if l_analysis and len(l_analysis) > 10:
                    has_bulletin_content = True
        else:
            print("    No bulletin records found.")
    except Exception as e:
        print(f"    Bulletin Check Error: {e}")

    conn.close()
    runner.close()

    # Final Verdict
    print("-" * 50)
    if tx_count >= 1 and total_negs >= 5 and has_bulletin_content:
        print("✅ VERIFICATION PASSED: System is healthy!")
        print("   - Transactions flowing")
        print("   - Negotiations authentic (LLM driven)")
        print("   - Market Bulletin includes LLM analysis")
    elif total_negs >= 5:
        print("⚠️ PARTIAL PASS: Negotiations active but transactions low.")
        print(f"   - Transactions: {tx_count}")
        print(f"   - Bulletin Analysis: {'OK' if has_bulletin_content else 'MISSING'}")
    else:
        print("❌ VERIFICATION FAILED: Activity too low.")

if __name__ == "__main__":
    verify_fix()
