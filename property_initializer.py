import random
from typing import List, Dict, Tuple
from config.settings import INITIAL_MARKET_CONFIG, PROPERTY_DISTRIBUTION

def classify_property_type(area: float, unit_price: float, zone: str) -> str:
    """
    Classify property type based on area and zone.
    """
    if zone == "A":
        if area < 70: return "刚需小户型"
        elif area < 120: return "普通住宅"
        elif area < 180: return "改善型大户型"
        else: return "豪宅"
    else:
        if area < 80: return "刚需小户型"
        elif area < 120: return "普通住宅"
        elif area < 180: return "改善型大户型"
        else: return "豪宅"

def assign_school_district(zone: str) -> Tuple[bool, int]:
    """
    Assign school district status and tier based on zone ratio.
    Returns: (is_school_district, school_tier)
    """
    ratio = INITIAL_MARKET_CONFIG[zone]["school_district_ratio"]
    is_district = random.random() < ratio
    
    if is_district:
        # 30% Tier 1 (Key School), 70% Tier 2 (Normal School)
        tier = random.choices([1, 2], weights=[0.3, 0.7])[0]
        return True, tier
    else:
        return False, 3  # Tier 3 means no school district

def create_property(prop_id: int, zone: str, quality: int) -> Dict:
    """Create a single property record with extended fields"""
    
    # 1. Randomize Area and Bedrooms
    if quality == 1:   # Small/Low quality
        area = random.uniform(50, 80)
        bedrooms = random.choice([1, 2])
    elif quality == 2: # Medium
        area = random.uniform(80, 130)
        bedrooms = random.choice([2, 3])
    else:              # High quality
        area = random.uniform(130, 250)
        bedrooms = random.choice([3, 4, 5])
        
    # 2. Calculate Unit Price
    config = INITIAL_MARKET_CONFIG[zone]
    # Fluctuate based on quality factor (0.9, 1.0, 1.2)
    quality_factor = {1: 0.9, 2: 1.0, 3: 1.2}[quality]
    base_unit_price = config["base_price_per_sqm"] * quality_factor
    # Add random variation (+- 10%)
    unit_price = base_unit_price * random.uniform(0.9, 1.1)
    
    # 3. Calculate Base Value
    base_value = area * unit_price
    
    # 4. Classify Type
    prop_type = classify_property_type(area, unit_price, zone)
    
    # 5. Assign School District
    is_district, school_tier = assign_school_district(zone)
    if is_district:
        # School district adds premium (15%-30%)
        premium = random.uniform(1.15, 1.30)
        unit_price *= premium
        base_value *= premium
    
    # 6. Listed Price (Base value + 10% premium initially)
    listed_price = base_value * random.uniform(1.05, 1.15)
    
    return {
        "property_id": prop_id,
        "zone": zone,
        "quality": quality,
        "base_value": base_value,
        "building_area": round(area, 2),
        "bedrooms": bedrooms,
        "unit_price": round(unit_price, 0),
        "property_type": prop_type,
        "is_school_district": is_district,
        "school_tier": school_tier,
        "owner_id": None,  # System owned initially
        "status": "for_sale",
        "listed_price": round(listed_price, 0),
        "last_transaction_month": None
    }

def initialize_market_properties() -> List[Dict]:
    """
    Initialize market properties list
    """
    properties = []
    property_id = 1
    
    for zone, distribution in PROPERTY_DISTRIBUTION.items():
        for quality_level in [1, 2, 3]:
            count = distribution[f"quality_{quality_level}"]
            for _ in range(count):
                prop = create_property(property_id, zone, quality_level)
                properties.append(prop)
                property_id += 1
                
    return properties
