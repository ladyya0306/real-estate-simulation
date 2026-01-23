import sqlite3
import pandas as pd
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

def find_faulty_offers():
    conn = sqlite3.connect('real_estate_stage2.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT info FROM trace WHERE action='make_offer'")
    rows = cursor.fetchall()
    
    faulty_count = 0
    total = 0
    
    print("--- Inspecting 'make_offer' Traces ---")
    for r in rows:
        total += 1
        info_str = r[0]
        try:
            # Handle Python string dicts representation if applicable, though normally it's JSON
            if info_str.startswith("{'"):
                info_str = info_str.replace("'", '"')
            
            info = json.loads(info_str)
            price = info.get('price')
            
            if price is None:
                print(f"FAILED (No Price): {info_str}")
                faulty_count += 1
            else:
                # Check if price is reasonable
                pass
                # print(f"OK: {price}")
                
        except json.JSONDecodeError:
            print(f"FAILED (JSON Error): {info_str}")
            faulty_count += 1
            
    print(f"\nTotal Offers: {total}")
    print(f"Faulty Offers: {faulty_count}")
    conn.close()

if __name__ == "__main__":
    find_faulty_offers()
