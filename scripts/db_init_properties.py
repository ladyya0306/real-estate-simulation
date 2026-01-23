import sqlite3
import random
from typing import Dict

DB_PATH = 'real_estate_stage2.db'

# Base Value Matrix (from migration plan)
BASE_VALUE_MATRIX = {
    ("A", 1): 3500000,
    ("A", 2): 5000000,
    ("A", 3): 7000000,
    ("B", 1): 1800000,
    ("B", 2): 2500000,
    ("B", 3): 2900000,
}

# Property Distribution (from migration plan)
PROPERTY_DISTRIBUTION = {
    "A": {"quality_1": 30, "quality_2": 50, "quality_3": 20},
    "B": {"quality_1": 80, "quality_2": 100, "quality_3": 20},
}

def create_property(prop_id: int, zone: str, quality: int) -> Dict:
    """Create a single property record"""
    base_value = BASE_VALUE_MATRIX[(zone, quality)]
    
    # Listed price: Base value ±30% float (updated per user feedback)
    listed_price = base_value * random.uniform(0.70, 1.30)
    
    return {
        "property_id": prop_id,
        "zone": zone,
        "quality": quality,
        "base_value": base_value,
        "owner_id": None,  # System owned initially
        "status": "for_sale",
        "listed_price": listed_price,
        "last_transaction_month": None
    }

def initialize_properties():
    print(f"Initializing properties in {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if properties already exist
    cursor.execute("SELECT COUNT(*) FROM properties")
    count = cursor.fetchone()[0]
    if count > 0:
        print(f"Properties table already has {count} records. Skipping initialization.")
        conn.close()
        return

    properties = []
    property_id = 1
    
    for zone, distribution in PROPERTY_DISTRIBUTION.items():
        for quality_level in [1, 2, 3]:
            count = distribution[f"quality_{quality_level}"]
            for _ in range(count):
                prop = create_property(property_id, zone, quality_level)
                properties.append(prop)
                property_id += 1
                
    # Bulk insert
    print(f"Inserting {len(properties)} properties...")
    cursor.executemany("""
        INSERT INTO properties (zone, quality, base_value, owner_id, status, listed_price, last_transaction_month)
        VALUES (:zone, :quality, :base_value, :owner_id, :status, :listed_price, :last_transaction_month)
    """, properties)
    
    conn.commit()
    print("Properties initialized successfully.")
    
    # Verify counts
    cursor.execute("SELECT zone, COUNT(*) FROM properties GROUP BY zone")
    counts = cursor.fetchall()
    print("Property counts by zone:")
    for zone, count in counts:
        print(f"Zone {zone}: {count}")
        
    conn.close()

if __name__ == "__main__":
    initialize_properties()
