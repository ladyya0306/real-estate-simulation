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

def assign_school_district(zone: str, config=None) -> Tuple[bool, int]:
    """
    Assign school district status and tier based on zone ratio.
    Returns: (is_school_district, school_tier)
    """
    ratio = 0.0
    if config:
        ratio = config.market.get('zones', {}).get(zone, {}).get('school_district_ratio', 0.0)
    else:
        ratio = INITIAL_MARKET_CONFIG[zone]["school_district_ratio"]

    is_district = random.random() < ratio
    
    if is_district:
        # 30% Tier 1 (Key School), 70% Tier 2 (Normal School)
        tier = random.choices([1, 2], weights=[0.3, 0.7])[0]
        return True, tier
    else:
        return False, 3  # Tier 3 means no school district

def create_property(prop_id: int, zone: str, quality: int, config=None) -> Dict:
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
    base_price = 0
    if config:
        base_price = config.market.get('zones', {}).get(zone, {}).get('base_price_per_sqm', 50000)
    else:
        base_price = INITIAL_MARKET_CONFIG[zone]["base_price_per_sqm"]

    # Fluctuate based on quality factor (0.9, 1.0, 1.2)
    quality_factor = {1: 0.9, 2: 1.0, 3: 1.2}[quality]
    base_unit_price = base_price * quality_factor
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
        "base_value": base_value,
        "building_area": round(area, 2),
        "unit_price": round(unit_price, 0),
        "property_type": prop_type,
        "is_school_district": is_district,
        "school_tier": school_tier,
        "owner_id": None,  # System owned initially
        "status": "off_market",  # Fixed: was "for_sale", but unowned properties shouldn't be listed
        "listed_price": round(listed_price, 0),
        "min_price": round(base_value * 0.95, 0), # Added for V2
        "current_valuation": base_value, # Added for V2
        "listing_month": 0, # Added for V2
        "last_transaction_month": None,
        "created_at": 0 # Added for V2
    }

def convert_to_v2_tuples(prop_dict: Dict) -> Tuple[Dict, Dict]:
    """Helper to split a property dict into Static and Market dicts for V2 DB insertion"""
    static_data = {
        "property_id": prop_dict["property_id"],
        "zone": prop_dict["zone"],
        "quality": prop_dict["quality"],
        "building_area": prop_dict["building_area"],
        "property_type": prop_dict["property_type"],
        "is_school_district": prop_dict["is_school_district"],
        "school_tier": prop_dict["school_tier"],
        "initial_value": prop_dict["base_value"], # Map base_value to initial_value
        "created_at": prop_dict.get("created_at", 0)
    }
    
    market_data = {
        "property_id": prop_dict["property_id"],
        "owner_id": prop_dict.get("owner_id"),
        "status": prop_dict.get("status", "off_market"),
        "current_valuation": prop_dict.get("current_valuation", prop_dict["base_value"]),
        "listed_price": prop_dict.get("listed_price"),
        "min_price": prop_dict.get("min_price"),
        "listing_month": prop_dict.get("listing_month"),
        "last_transaction_month": prop_dict.get("last_transaction_month")
    }
    return static_data, market_data

def initialize_market_properties(target_total_count: int = None, config=None) -> List[Dict]:
    """
    Initialize market properties list
    Args:
        target_total_count: If provided, scales the default distribution to match this total
        config: SimulationConfig object
    """
    properties = []
    property_id = 1
    
    # Use config distribution or fallback
    distribution_map = {}
    if config:
        for zone, z_cfg in config.market.get('zones', {}).items():
            distribution_map[zone] = z_cfg.get('property_count', {})
    else:
        distribution_map = PROPERTY_DISTRIBUTION

    # Calculate scaling factor if target count provided
    scale_factor = 1.0
    if target_total_count:
        # Calculate current total in distribution config
        current_total = 0
        for zone_dist in distribution_map.values():
            current_total += sum(zone_dist.values())
        
        if current_total > 0:
            scale_factor = target_total_count / current_total
    
    for zone, distribution in distribution_map.items():
        for quality_level in [1, 2, 3]:
            # Scale count
            base_count = distribution.get(f"quality_{quality_level}", 0)
            count = int(base_count * scale_factor)
            
            # Ensure at least 1 if base was > 0 and scaling made it 0 (optional safeguard)
            if base_count > 0 and count == 0:
                count = 1
                
            for _ in range(count):
                prop = create_property(property_id, zone, quality_level, config)
                properties.append(prop)
                property_id += 1
                
    # If we are slightly off due to rounding, add/remove random properties to match exactly
    if target_total_count and len(properties) != target_total_count:
        diff = target_total_count - len(properties)
        if diff > 0:
            # Add more properties (clone random logic)
            for _ in range(diff):
                # Pick random zone/quality based on weights? Simplified: Random choice
                zone = random.choice(list(distribution_map.keys()))
                quality = random.choice([1, 2, 3])
                prop = create_property(property_id, zone, quality, config)
                properties.append(prop)
                property_id += 1
        elif diff < 0:
            # Trim properties (from the end or random? End is fine as order is mixed by zone loop)
            properties = properties[:target_total_count]
                
    return properties
