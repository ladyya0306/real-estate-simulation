import sqlite3
import os
import shutil
from datetime import datetime

DB_PATH = 'real_estate_stage2.db'
BACKUP_DIR = 'backups'
MIGRATION_SCRIPT = 'scripts/migrate_v2_1.sql'

def backup_database():
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} does not exist. A new one will be created.")
        return
        
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
        
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(BACKUP_DIR, f'real_estate_stage2_{timestamp}.db')
    shutil.copy2(DB_PATH, backup_path)
    print(f"Database backed up to {backup_path}")

def run_migration():
    print(f"Running migration on {DB_PATH} using {MIGRATION_SCRIPT}...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    with open(MIGRATION_SCRIPT, 'r', encoding='utf-8') as f:
        sql_script = f.read()
        
    try:
        cursor.executescript(sql_script)
        conn.commit()
        print("Migration executed successfully.")
        
        # Verify tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Current tables: {tables}")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    backup_database()
    run_migration()
