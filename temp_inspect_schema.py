import sqlite3

def inspect_schema():
    conn = sqlite3.connect('real_estate_stage2.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='properties'")
        result = cursor.fetchone()
        if result:
            print("Current Schema for 'properties' table:")
            print(result[0])
        else:
            print("Table 'properties' not found.")
            
        cursor.execute("PRAGMA table_info(properties)")
        columns = cursor.fetchall()
        print("\nColumns:")
        for col in columns:
            print(col)
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    inspect_schema()
