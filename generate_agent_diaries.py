import sqlite3
import json
import logging
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("DiaryGenerator")

DB_PATH = "results/run_20260211_163443/simulation.db"

class AgentDiaryGenerator:
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.flaw_count = 0
        self.diaries = []

    def get_agent_data(self, agent_id):
        # 1. Fetch Static Info (if available, else infer)
        # In V2, static info is in agents_static, but simulation DB might only have logs/transactions if not fully synced.
        # Let's try to get profile from first thought process
        self.cursor.execute("SELECT * FROM decision_logs WHERE agent_id = ? ORDER BY month ASC LIMIT 1", (agent_id,))
        first_log = self.cursor.fetchone()
        profile = {}
        if first_log:
            try:
                tp = json.loads(first_log['thought_process'])
                profile = tp # Basic profile
            except:
                pass
        return profile

    def analyze_agent(self, agent_id):
        diary_entries = []
        errors = []
        
        # Fetch all logs
        self.cursor.execute("SELECT * FROM decision_logs WHERE agent_id = ? ORDER BY month ASC", (agent_id,))
        logs = self.cursor.fetchall()
        
        # Fetch all transactions
        self.cursor.execute("SELECT * FROM transactions WHERE buyer_id = ? OR seller_id = ? ORDER BY month ASC", (agent_id, agent_id))
        txs = self.cursor.fetchall()
        
        # Fetch Bids (property_buyer_matches)
        try:
            self.cursor.execute("SELECT * FROM property_buyer_matches WHERE buyer_id = ? ORDER BY month ASC", (agent_id,))
            bids = self.cursor.fetchall()
        except:
            bids = []

        # Group by Month
        months = sorted(list(set([l['month'] for l in logs] + [t['month'] for t in txs])))
        
        # Map Role Per Month: {month: set(roles)}
        # Decision in Month M determines Role for Month M+1
        # Initial Role (Month 1) is unknown from logs, assumed correct or inferred from Init logs if avail.
        # We track role intention.
        role_map = {} # month -> role
        
        for l in logs:
            if l['event_type'] == 'ROLE_DECISION':
                # Decision in Month M effects Month M (Immediate Activation in Phase 7)
                target_month = l['month']
                role_map[target_month] = l['decision']
        
        for month in months:
            month_log = [l for l in logs if l['month'] == month]
            month_tx = [t for t in txs if t['month'] == month and (t['buyer_id'] == agent_id or t['seller_id'] == agent_id)]
            month_Bid = [b for b in bids if b['month'] == month]
            
            entry = f"### Month {month}\n"
            
            # 1. Mindset (Logs - Decision for Next Month)
            for l in month_log:
                if l['event_type'] == 'ROLE_DECISION':
                     entry += f"- **本月决策**: 下月担任 `{l['decision']}`\n"
                     try:
                        tp = json.loads(l['thought_process'])
                        entry += f"  - **心态**: {tp.get('reason', 'N/A')}\n"
                     except: pass
                elif l['event_type'] == 'LISTING_ACTION':
                     entry += f"- **挂牌操作**: {l['decision']}\n"

            # 2. Logic Checks (Role Active in This Month)
            # Check Ghost Seller: Active Role is BUYER, but Sold
            active_role = role_map.get(month, "UNKNOWN (Init)")
            if month > 1 and active_role == "BUYER":
                 # If active role is BUYER, should not sell
                 has_sell_tx = any(t['seller_id'] == agent_id for t in month_tx)
                 if has_sell_tx:
                      errors.append(f"🔴 [Hard Flaw] Month {month}: Ghost Seller! Active Role (from M{month-1}) is BUYER, but Sold.")
                      entry += "  - ⚠️ **逻辑矛盾**: 本月身份为买家，却卖房了！(Ghost Seller)\n"
            
            entry += f"- **本月身份**: `{active_role}`\n"

            # 3. Actions (Transactions)
            for t in month_tx:
                if t['buyer_id'] == agent_id:
                    entry += f"- **买入**: {t['property_id']} | ¥{t['final_price']:,.0f}\n"
                else:
                     entry += f"- **卖出**: {t['property_id']} | ¥{t['final_price']:,.0f}\n"

            # 4. Bidding Logic (Price Logic Checker)
            for b in month_Bid:
                entry += f"- **竞价记录**: 房产 {b['property_id']} | 出价 ¥{b['buyer_bid']:,.0f} | 挂牌 ¥{b['listing_price']:,.0f}\n"
                ratio = b['buyer_bid'] / b['listing_price'] if b['listing_price'] else 0
                if ratio > 1.5:
                     errors.append(f"🔴 [Hard Flaw] Month {month}: Price Logic Error! Bid ratio {ratio:.2f} > 1.5")
                     entry += f"  - ⚠️ **逻辑矛盾**: 溢价率 {ratio*100-100:.0f}% (严重超标)！\n"
                elif ratio > 1.2:
                     entry += f"  - ⚠️ **风险提示**: 溢价率 {ratio*100-100:.0f}% (较高)。\n"

            diary_entries.append(entry)

        return diary_entries, errors

    def generate_report(self):
        # Find active agents (Transactions or Bids or Role Changes)
        self.cursor.execute("SELECT DISTINCT agent_id FROM decision_logs")
        agent_ids = [r['agent_id'] for r in self.cursor.fetchall()]
        
        # Filter for interesting agents (at least one transaction or high bid)
        # Or just top 10?
        # Let's verify ALL agents who had logical flaws first
        
        report = "# 🕵️‍♂️ 全量 Agent 逻辑体检报告 (Logic Health Check)\n\n"
        report += f"检查数据库: `{DB_PATH}`\n"
        report += f"扫描 Agent 总数: {len(agent_ids)}\n\n"
        
        all_errors = []
        
        for aid in agent_ids:
            # Quick check if interesting
            # self.cursor.execute("SELECT count(*) FROM transactions WHERE buyer_id=? OR seller_id=?", (aid, aid))
            # if self.cursor.fetchone()[0] == 0: continue
            
            entries, errors = self.analyze_agent(aid)
            if errors:
                self.flaw_count += 1
                report += f"## ⚠️ Agent {aid} (发现 {len(errors)} 处硬伤)\n"
                for err in errors:
                    report += f"- {err}\n"
                report += "\n**日记摘录**:\n"
                report += "\n".join(entries)
                report += "\n---\n"
                
                all_errors.extend([(aid, e) for e in errors])

        if self.flaw_count == 0:
            report += "## ✅ 完美！未发现逻辑硬伤。\n"
            report += "所有参与者的行为均符合逻辑设定。\n"
        else:
            report += f"\n## 🛑 总结\n共发现 {self.flaw_count} 个 Agent 存在逻辑硬伤。\n"

        return report

if __name__ == "__main__":
    generator = AgentDiaryGenerator(DB_PATH)
    report = generator.generate_report()
    
    with open("agent_logic_report.md", "w", encoding='utf-8') as f:
        f.write(report)
    
    print(f"Report generated: agent_logic_report.md. Found {generator.flaw_count} flawed agents.")
    print(report[:2000]) # Print preview
