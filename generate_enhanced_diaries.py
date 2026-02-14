import sqlite3
import pandas as pd
import json
import os
import argparse
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.WARNING, format='%(message)s') # Default silent
logger = logging.getLogger(__name__)

class ForensicAnalyzer:
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.bulletins = self.get_market_bulletin()

    def get_market_bulletin(self):
        """Fetch all market bulletins."""
        try:
            df = pd.read_sql_query("SELECT * FROM market_bulletin", self.conn)
            return df.set_index('month').to_dict('index')
        except:
            return {}

    def get_agent_basic_info(self, agent_id):
        """Fetch static info."""
        try:
            row = self.cursor.execute("SELECT * FROM agents_static WHERE agent_id=?", (agent_id,)).fetchone()
            if not row: return None
            # Get columns
            cols = [description[0] for description in self.cursor.description]
            return dict(zip(cols, row))
        except Exception as e:
            logger.error(f"Error fetching agent info: {e}")
            return None
            
    def analyze_logic_flaws(self, agent_id):
        """
        Deep scan for logic flaws.
        Returns: errors keys list
        """
        errors = []
        
        # Fetch relevant data
        logs = pd.read_sql_query("SELECT * FROM decision_logs WHERE agent_id=? ORDER BY month", self.conn, params=(agent_id,))
        txs = pd.read_sql_query("SELECT * FROM transactions WHERE buyer_id=? OR seller_id=? ORDER BY month", self.conn, params=(agent_id, agent_id))
        
        # Map Role Per Month
        role_map = {}
        for _, l in logs.iterrows():
            if l['event_type'] == 'ROLE_DECISION':
                role_map[l['month']] = l['decision'] # Effect is immediate in month M
                
        months = sorted(list(set(logs['month'].tolist() + txs['month'].tolist())))
        
        for m in months:
            role = role_map.get(m, "UNKNOWN")
            
            # GHOST SELLER CHECK
            # If active role is BUYER, should not sell (unless Dual Role)
            if role == "BUYER":
                sales = txs[(txs['month'] == m) & (txs['seller_id'] == agent_id)]
                if not sales.empty:
                    errors.append(f"Month {m}: Ghost Seller (Role BUYER but Sold)")
                    
            # PRICE LOGIC using Bids (if available)
            try:
                bids = pd.read_sql_query("SELECT * FROM property_buyer_matches WHERE buyer_id=? AND month=?", self.conn, params=(agent_id, m))
                for _, b in bids.iterrows():
                    if b['listing_price'] and b['buyer_bid'] > b['listing_price'] * 1.5:
                        errors.append(f"Month {m}: Irrational Bid (Bid {b['buyer_bid']} > 1.5x Listing {b['listing_price']})")
            except: pass
            
        return errors

    def render_single_report(self, agent_id):
        """Generate detailed timeline report."""
        info = self.get_agent_basic_info(agent_id)
        if not info:
            print(f"❌ Agent {agent_id} not found.")
            return

        print("\n" + "="*70)
        print(f"🕵️  法医体检报告 (FORENSIC REPORT): Agent {agent_id}  [{info['name']}]")
        print("="*70)
        
        # 1. Dossier
        print(f"📋 基础档案 (Dossier)")
        print(f"   - 职业: {info['occupation']} | 年岭: {info['age']} | 婚姻: {info['marital_status']}")
        print(f"   - 风格: {info.get('investment_style', 'N/A')}")
        print(f"   - 故事: {info['background_story']}")
        
        # 2. Timeline Reconstruction
        logs = pd.read_sql_query("SELECT * FROM decision_logs WHERE agent_id=? ORDER BY month", self.conn, params=(agent_id,))
        txs = pd.read_sql_query(
            "SELECT * FROM transactions WHERE buyer_id=? OR seller_id=? ORDER BY month", 
            self.conn, params=(agent_id, agent_id)
        )
        
        # Merge events
        events = []
        for _, l in logs.iterrows():
            events.append({
                "month": l['month'], "type": "DECISION", 
                "desc": f"[{l['event_type']}] {l['decision']} ({l['reason'][:30]}...)",
                "json": l['thought_process']
            })
            
        for _, t in txs.iterrows():
            action = "BUY" if t['buyer_id'] == agent_id else "SELL"
            events.append({
                "month": t['month'], "type": "TX", 
                "desc": f"💰 成交! {action} Property {t['property_id']} @ ¥{t['price']:,.0f}",
                "json": "{}"
            })
            
        events.sort(key=lambda x: (x['month'], 0 if x['type']=='DECISION' else 1))
        
        print(f"\n⏳ 全生命周期时序复盘 (Lifecycle Timeline)")
        
        months = sorted(list(set([e['month'] for e in events])))
        if not months: print("   (No Activity Recorded)")
        
        for m in months:
            # Context
            bulletin = self.bulletins.get(m, {})
            b_text = f"📢 市场: {bulletin.get('trend_signal','N/A')} (均价: {bulletin.get('avg_price',0)/10000:.1f}万)"
            print(f"\n[Month {m}] {b_text}")
            
            m_events = [e for e in events if e['month'] == m]
            for e in m_events:
                prefix = "   ⚡" if e['type'] == 'DECISION' else "   🏆"
                print(f"{prefix} {e['desc']}")
                
                # Try parsing JSON thought
                try:
                    tp = json.loads(e['json'])
                    if 'life_pressure' in tp:
                        print(f"      🧠 心态: {tp.get('life_pressure')} | 触发: {tp.get('trigger', 'N/A')}")
                    if 'pricing_mode' in tp: # Seller strategy logic check
                        print(f"      📉 策略: {(tp.get('pricing_mode') or '')} (系数: {tp.get('pricing_coefficient', 1.0)})")
                except: pass

        # 3. Validation Summary
        print(f"\n🏥 逻辑体检结果 (Logic Health Check)")
        errors = self.analyze_logic_flaws(agent_id)
        if not errors:
             print("   ✅ 完美 (Perfect) - 行为逻辑自洽")
        else:
             for err in errors:
                 print(f"   🛑 {err}")

        print("\n" + "="*70 + "\n")

    def run_batch_scan(self):
        """Scan all agents."""
        print("🔍 正在运行批量全量扫描 (Batch Scanning)...")
        # Get all agents with logs
        aids = pd.read_sql_query("SELECT DISTINCT agent_id FROM decision_logs", self.conn)['agent_id'].tolist()
        
        flaws = {}
        for aid in aids:
            errs = self.analyze_logic_flaws(aid)
            if errs:
                flaws[aid] = errs
                
        print(f"✅ 扫描完成: {len(aids)} Agents.")
        
        if not flaws:
            print("🎉 结果: 完美! 未发现硬伤逻辑 (0 Logic Flaws).")
        else:
            print(f"⚠️ 发现 {len(flaws)} 个异常 Agent:")
            for aid, errs in flaws.items():
                print(f"   - Agent {aid}: {errs[0]} (+{len(errs)-1} more)")
            print("\n建议使用 'B. Single Profile' 模式深度查看上述 Agent.")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", help="Path to DB")
    parser.add_argument("--agent_id", type=int, help="Target Agent ID")
    parser.add_argument("--mode", choices=['batch', 'single'], default='batch')
    args = parser.parse_args()
    
    # Auto-detect DB if not provided
    db_path = args.db
    if not db_path:
        import glob
        try:
            list_of_files = glob.glob('results/*/simulation.db') 
            if list_of_files:
                db_path = max(list_of_files, key=os.path.getctime)
                print(f"📂 Auto-detected DB: {db_path}")
            else:
                db_path = "simulation.db"
        except: pass
        
    if not db_path or not os.path.exists(db_path):
        print("❌ Database not found. Please run a simulation first.")
        return

    analyzer = ForensicAnalyzer(db_path)
    
    if args.mode == 'single':
        if not args.agent_id:
            val = input("请输入 Agent ID: ").strip()
            if val.isdigit(): args.agent_id = int(val)
            else: 
                print("❌ Invalid ID"); return
        analyzer.render_single_report(args.agent_id)
    else:
        analyzer.run_batch_scan()

if __name__ == "__main__":
    main()
