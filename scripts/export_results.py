#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Export Results Script
Exports DB tables and Logs to a timestamped folder.
Enhanced to produce "房产交易中心记录.csv" with rich details.
"""
import sqlite3
import shutil
import csv
import os
import datetime
import logging
import json
import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

DB_PATH = 'real_estate_stage2.db'
LOG_FILE = 'simulation_run.log'

def find_latest_result_dir(base_dir="results"):
    """Find the most recently created result directory"""
    if not os.path.exists(base_dir):
        return None
    
    dirs = [os.path.join(base_dir, d) for d in os.listdir(base_dir) if d.startswith("result_")]
    if not dirs:
        return None
        
    # Sort by creation time (or name which has timestamp)
    dirs.sort(key=os.path.getmtime, reverse=True)
    return dirs[0]

def export_data():
    # 1. Determine Result Directory
    # Strategy: If a result directory was created recently (e.g. < 5 mins), use it.
    # Otherwise create new.
    # Actually, BehaviorLogger always creates a dir. We should find that one.
    
    result_dir = find_latest_result_dir()
    
    # If no recent dir (e.g. within 10 mins), or doesn't exist, create one
    if not result_dir or (datetime.datetime.now().timestamp() - os.path.getmtime(result_dir)) > 600:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        result_dir = os.path.join("results", f"result_{timestamp}")
        os.makedirs(result_dir, exist_ok=True)
        logger.info(f"📦 Created new result directory: {result_dir}")
    else:
        logger.info(f"📂 Using existing result directory: {result_dir}")
    
    # 2. Copy Logs
    if os.path.exists(LOG_FILE):
        shutil.copy(LOG_FILE, os.path.join(result_dir, "console_log.txt"))

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 3. Export Standard Tables (Raw)
    standard_tables = {
        'agents': 'SELECT * FROM agents',
        'trans': 'SELECT * FROM transactions', 
        'properties': 'SELECT * FROM properties',
        'property_listings': 'SELECT * FROM property_listings'
    }
    
    agents_map = {} # Cache for processing
    
    for filename, query in standard_tables.items():
        try:
            cursor.execute(query)
            rows = cursor.fetchall()
            
            # Cache agents for later lookup
            if filename == 'agents':
                for r in rows:
                    agents_map[r['agent_id']] = dict(r)
            
            if rows:
                headers = [description[0] for description in cursor.description]
                filepath = os.path.join(result_dir, f"{filename}.csv")
                with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    writer.writerow(headers)
                    writer.writerows(rows)
                logger.info(f"  - Exported {filename}.csv ({len(rows)} rows)")
        except Exception as e:
            logger.error(f"  Failed to export {filename}: {e}")

    # 4. Generate "房产交易中心记录.csv" (Rich Chinese Report)
    try:
        # Load Negotiations for context
        neg_file = os.path.join(result_dir, "negotiations_detail.csv")
        neg_df = None
        if os.path.exists(neg_file):
            try:
                neg_df = pd.read_csv(neg_file)
            except:
                pass
        
        cursor.execute("SELECT * FROM transactions")
        transactions = cursor.fetchall()
        
        if transactions:
            filepath = os.path.join(result_dir, "房产交易中心记录.csv")
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                header = [
                    "交易编号", "交易时间", 
                    "房产ID", "区域", "房屋类型", "面积(m2)",
                    "成交价格", 
                    "买家ID", "买家姓名", "买家职业", "买家交易前现金", "买家交易后现金",
                    "卖家ID", "卖家姓名", "卖家职业", "卖家交易前现金", "卖家交易后现金",
                    "谈判对话记录 (摘要)"
                ]
                writer.writerow(header)
                
                cursor.execute("SELECT property_id, zone, property_type, building_area FROM properties")
                props = {r[0]: dict(r) for r in cursor.fetchall()}
                
                for t in transactions:
                    # Schema: id, month, buyer_id, seller_id, property_id, price, type, created_at
                    # Use dictionary access since we set row_factory=sqlite3.Row!
                    # Wait, if I iterate over result of fetchall with Row factory, t is a Row object.
                    # I can access by name. Much safer.
                    
                    tid = t['transaction_id']
                    date = t['created_at']
                    pid = t['property_id']
                    bid = t['buyer_id']
                    sid = t['seller_id']
                    price = t['price']
                    
                    prop = props.get(pid, {})
                    buyer = agents_map.get(bid, {})
                    seller = agents_map.get(sid, {})
                    
                    # Estimate Pre-Transaction Cash
                    # Buyer current cash = Pre - Price -> Pre = Current + Price
                    b_cash_post = buyer.get('cash', 0)
                    b_cash_pre = b_cash_post + price
                    
                    # Seller current cash = Pre + Price -> Pre = Current - Price
                    s_cash_post = seller.get('cash', 0)
                    s_cash_pre = s_cash_post - price
                    
                    # Find negotiation context
                    neg_context = "无记录"
                    if neg_df is not None:
                        # Try to find negotiation involving this property and buyer/seller
                        # Or match close timestamp? Matching by property_id is harder as CSV doesn't strictly link trans to neg ID
                        pass 
                        # Assuming neg_df has columns like "对外发言"
                        # We need to filter by Agent_ID and context. 
                        # Simplified: Look for rows where "内心想法" contain Property ID? No.
                        # Best effort: Look for negotiation rows right before transaction date?
                        pass
                    
                    # Better: simulation_runner knows the mapping. But here we are post-hoc.
                    # Let's try to grab from neg_df where Agent_ID matches buyer/seller and result is Success
                    if neg_df is not None:
                        # Find relevant rows
                        mask = (
                            (neg_df['Agent_ID'] == bid) | 
                            (neg_df['Agent_ID'] == sid)
                        )
                        relevant_negs = neg_df[mask]
                        # Just take the last few lines of dialogue
                        dialogues = []
                        if not relevant_negs.empty:
                            last_negs = relevant_negs.tail(10)
                            for _, r in last_negs.iterrows():
                                role = r.get('角色', '')
                                msg = r.get('对外发言', '')
                                if pd.notna(msg) and msg:
                                    dialogues.append(f"[{role}]: {msg}")
                            if dialogues:
                                neg_context = "\n".join(dialogues)

                    row = [
                        tid, date,
                        pid, prop.get('zone', ''), prop.get('property_type', ''), prop.get('building_area', ''),
                        f"¥{price:,.0f}",
                        bid, buyer.get('name', ''), buyer.get('occupation', ''), f"¥{b_cash_pre:,.0f}", f"¥{b_cash_post:,.0f}",
                        sid, seller.get('name', ''), seller.get('occupation', ''), f"¥{s_cash_pre:,.0f}", f"¥{s_cash_post:,.0f}",
                        neg_context
                    ]
                    writer.writerow(row)
            
            logger.info(f"  - Generated 房产交易中心记录.csv ({len(transactions)} deals)")
    
    except Exception as e:
        logger.error(f"  Failed to generate 房产交易中心记录.csv: {e}")
        import traceback
        traceback.print_exc()

    # 5. Export Thoughts (Enhanced)
    try:
        cursor.execute("SELECT month, agent_id, decision as role, reason as trigger, thought_process FROM decision_logs")
        rows = cursor.fetchall()
        if rows:
            fieldnames = ['月份', '代理人ID', '角色', '触发原因', '紧迫程度', '价格预期', '原始数据']
            filepath = os.path.join(result_dir, "thoughts.csv")
            with open(filepath, "w", newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for row in rows:
                    tp = {}
                    try:
                        tp = json.loads(row['thought_process'] or '{}')
                    except:
                        tp = {}
                    
                    writer.writerow({
                        '月份': row['month'],
                        '代理人ID': row['agent_id'],
                        '角色': row['role'],
                        '触发原因': row['trigger'],
                        '紧迫程度': tp.get('urgency', ''),
                        '价格预期': tp.get('price_expectation', ''),
                        '原始数据': row['thought_process']
                    })
            logger.info(f"  - Exported thoughts.csv ({len(rows)} rows)")
    except Exception as e:
        logger.error(f"  Failed to export thoughts.csv: {e}")
            
    conn.close()
    logger.info("✅ Export Complete.")

if __name__ == "__main__":
    export_data()
