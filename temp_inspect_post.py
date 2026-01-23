import sqlite3

def inspect_post_schema():
    conn = sqlite3.connect('real_estate_stage2.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='post'")
        result = cursor.fetchone()
        if result:
            print("Current Schema for 'post' table:")
            print(result[0])
            
        cursor.execute("PRAGMA table_info(post)")
        columns = cursor.fetchall()
        print("\nColumns in 'post':")
        for col in columns:
            print(col)
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    inspect_post_schema()
