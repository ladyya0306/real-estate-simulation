#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Export Results Script
Exports DB tables and Logs to a timestamped folder.
"""
import sqlite3
import shutil
import csv
import os
import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

DB_PATH = 'real_estate_stage2.db'
LOG_FILE = 'simulation_run.log'

def export_data():
    # 1. Create Result Directory
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    result_dir = os.path.join("results", f"result_{timestamp}")
    os.makedirs(result_dir, exist_ok=True)
    
    logger.info(f"📦 Exporting results to: {result_dir}")
    
    # 2. Copy Logs
    if os.path.exists(LOG_FILE):
        shutil.copy(LOG_FILE, os.path.join(result_dir, "console_log.txt"))
        
    # 3. Export Tables
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    tables = {
        'agents': 'SELECT * FROM agents',
        'trans': 'SELECT * FROM transactions', 
        'properties': 'SELECT * FROM properties',
        'thoughts': 'SELECT * FROM agent_decision_logs'
    }
    
    for filename, query in tables.items():
        try:
            cursor.execute(query)
            rows = cursor.fetchall()
            if not rows:
                continue
                
            # Get Headers
            headers = [description[0] for description in cursor.description]
            
            filepath = os.path.join(result_dir, f"{filename}.csv")
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                writer.writerows(rows)
                
            logger.info(f"  - Exported {filename}.csv ({len(rows)} rows)")
            
        except Exception as e:
            logger.error(f"  Failed to export {filename}: {e}")
            
    conn.close()
    logger.info("✅ Export Complete.")

if __name__ == "__main__":
    export_data()
