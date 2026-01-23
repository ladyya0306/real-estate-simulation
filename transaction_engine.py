"""
Transaction Engine: Handles Listings, Matching, Negotiation, and Execution
"""
import json
import random
from typing import List, Dict, Optional, Tuple, Any
from models import Agent, Market
from agent_behavior import safe_call_llm
from mortgage_system import check_affordability, calculate_monthly_payment
from config.settings import MORTGAGE_CONFIG

# --- 1. Seller Listing Logic ---

def generate_seller_listing(seller: Agent, property_data: Dict, market: Market) -> Dict:
    """
    LLM drives seller to set listed price and min acceptable price.
    """
    # Get Market Info
    zone = property_data['zone']
    avg_price = market.get_avg_price(zone)
    if avg_price == 0:
        avg_price = property_data['base_value']

    prompt = f"""
    你准备卖房：
    【背景】{seller.story.background_story}
    【卖房动机】{seller.story.selling_motivation}
    【房产】{zone}区，{property_data.get('building_area', 100)}㎡，{property_data.get('bedrooms', 2)}房
    【市场均价】{avg_price:,.0f}元
    【估值】{property_data['base_value']:,.0f}元

    设定挂牌价和可接受最低价：
    输出JSON：{{"listed_price":..., "min_price":..., "urgency": 0-1, "reasoning":"..."}}
    """
    
    # Default fallback
    default_listing = {
        "listed_price": property_data['base_value'] * 1.1,
        "min_price": property_data['base_value'] * 0.95,
        "urgency": 0.5,
        "reasoning": "Follow market trend"
    }

    result = safe_call_llm(prompt, default_listing)
    
    # Ensure numerical validity
    try:
        listed_price = float(result.get("listed_price", default_listing["listed_price"]))
        min_price = float(result.get("min_price", default_listing["min_price"]))
    except:
        listed_price = default_listing["listed_price"]
        min_price = default_listing["min_price"]
        
    return {
        "property_id": property_data['property_id'],
        "seller_id": seller.id,
        "listed_price": listed_price,
        "min_price": max(min_price, 1.0), # Ensure positive
        "urgency": result.get("urgency", 0.5),
        "status": "active",
        "reasoning": result.get("reasoning", "")
    }

# --- 2. Buyer Matching Logic ---

def match_property_for_buyer(buyer: Agent, listings: List[Dict], properties_map: Dict[int, Dict]) -> Optional[Dict]:
    """
    Find the best matching property for a buyer from active listings.
    listings: List of listing dicts (from property_listings table)
    properties_map: property_id -> property_data dict (full details)
    """
    pref = buyer.preference
    candidates = []
    
    for listing in listings:
        prop = properties_map.get(listing['property_id'])
        if not prop:
            print(f"Debug: Prop {listing['property_id']} not found in map")
            continue
            
        # 1. Zone Check
        if pref.target_zone and prop['zone'] != pref.target_zone:
            # print(f"Debug: Zone mismatch {prop['zone']} != {pref.target_zone}")
            continue
            
        # 2. Price Check (Listed Price <= Max Price)
        if listing['listed_price'] > pref.max_price:
            # print(f"Debug: Price mismatch {listing['listed_price']} > {pref.max_price}")
            continue
            
        # 3. Bedroom Check
        if prop.get('bedrooms', 0) < pref.min_bedrooms:
            # print(f"Debug: Bedroom mismatch {prop.get('bedrooms')} < {pref.min_bedrooms}")
            continue
            
        # 4. School District Check
        if pref.need_school_district and not prop.get('is_school_district', False):
            continue
            
        candidates.append(listing)
        
    print(f"Debug: Found {len(candidates)} candidates for Buyer {buyer.id}")
        
    if not candidates:
        return None
        
    # Sort candidates by price (cheapest first) or other criteria
    # For now, simple sort by price ascending
    candidates.sort(key=lambda x: x['listed_price'])
    
    return candidates[0]

# --- 3. Negotiation Logic (Phase 2.2) ---

def negotiate(buyer: Agent, seller: Agent, listing: Dict, market: Market) -> Dict:
    """
    LLM-driven 3-5 round negotiation.
    Returns: {"outcome": "success"|"failed", "final_price": float, "history": List}
    """
    history = []
    rounds = random.randint(3, 5) # 3-5 rounds
    current_price = listing['listed_price']
    min_price = listing['min_price']
    
    buyer_offer_price = current_price * 0.9 # Start lower
    
    negotiation_log = []
    
    for r in range(1, rounds + 1):
        # --- Buyer Turn ---
        buyer_prompt = f"""
        你是买方Agent {buyer.id}，第{r}/{rounds}轮谈判。
        【你的背景】{buyer.story.background_story}
        【你的预算】{buyer.preference.max_price:,.0f}
        【当前卖方报价】{current_price:,.0f}
        【你的上一轮出价】{buyer_offer_price:,.0f}
        【谈判历史】{json.dumps(negotiation_log, ensure_ascii=False)}
        
        决定行动：
        - OFFER: 出价 (必须低于当前报价，但要合理)
        - ACCEPT: 接受当前报价
        - WITHDRAW: 觉得太贵放弃
        
        输出JSON: {{"action": "OFFER"|"ACCEPT"|"WITHDRAW", "offer_price": 0, "reason": "..."}}
        """
        buyer_resp = safe_call_llm(buyer_prompt, {"action": "WITHDRAW", "offer_price": 0, "reason": "LLM Error"}, system_prompt="你是精明的购房者。")
        buyer_action = buyer_resp.get("action", "WITHDRAW")
        
        # Validate logic
        if buyer_action == "OFFER":
            buyer_offer_price = float(buyer_resp.get("offer_price", buyer_offer_price))
            # Enforce constraints
            if buyer_offer_price >= current_price: 
                buyer_action = "ACCEPT"
                buyer_offer_price = current_price
            if buyer_offer_price > buyer.preference.max_price:
                 buyer_action = "WITHDRAW"

        negotiation_log.append({
            "round": r, 
            "party": "buyer", 
            "action": buyer_action, 
            "price": buyer_offer_price, 
            "content": buyer_resp.get("reason", "")
        })
        
        if buyer_action == "WITHDRAW":
            return {"outcome": "failed", "reason": "Buyer withdrew", "history": negotiation_log, "final_price": 0}
        if buyer_action == "ACCEPT":
             return {"outcome": "success", "final_price": current_price, "history": negotiation_log}
             
        # --- Seller Turn ---
        seller_prompt = f"""
        你是卖方Agent {seller.id}，第{r}/{rounds}轮谈判。
        【你的底价】{min_price:,.0f}
        【买方最新出价】{buyer_offer_price:,.0f}
        【当前你的报价】{current_price:,.0f}
        【谈判历史】{json.dumps(negotiation_log, ensure_ascii=False)}
        
        决定行动：
        - ACCEPT: 接受买方出价
        - COUNTER: 还价 (必须高于买方出价，低于当前报价)
        - REJECT: 价格太低拒绝
        
        输出JSON: {{"action": "ACCEPT"|"COUNTER"|"REJECT", "counter_price": 0, "reason": "..."}}
        """
        seller_resp = safe_call_llm(seller_prompt, {"action": "REJECT", "counter_price": 0, "reason": "LLM Error"}, system_prompt="你是理性的房产卖家。")
        seller_action = seller_resp.get("action", "REJECT")
        
        if seller_action == "COUNTER":
             current_price = float(seller_resp.get("counter_price", current_price))
             # Validation
             if current_price <= buyer_offer_price:
                 seller_action = "ACCEPT"
                 current_price = buyer_offer_price
        
        negotiation_log.append({
            "round": r, 
            "party": "seller", 
            "action": seller_action, 
            "price": current_price,
            "content": seller_resp.get("reason", "")
        })
        
        if seller_action == "ACCEPT":
             return {"outcome": "success", "final_price": buyer_offer_price, "history": negotiation_log}
        if seller_action == "REJECT":
             return {"outcome": "failed", "reason": "Seller rejected", "history": negotiation_log, "final_price": 0}

    return {"outcome": "failed", "reason": "Max rounds reached", "history": negotiation_log, "final_price": 0}

# --- 4. Transaction Execution (Phase 2.3 & 3) ---

def execute_transaction(buyer: Agent, seller: Optional[Agent], property_data: Dict, price: float, market: Market) -> Optional[Dict]:
    """
    Execute transaction: Transfer funds, update ownership, apply mortgage, update market.
    Returns transaction record or None if failed.
    """
    # 1. Final Affordability Check (incorporating Mortgage logic)
    is_affordable, down_payment, loan_amount = check_affordability(buyer, price)
    
    if not is_affordable:
        print(f"Transaction failed: Buyer {buyer.id} cannot afford {price}")
        return None
        
    # 2. Financial Transfer
    # Buyer pays down payment
    buyer.cash -= down_payment
    
    # Mortgage Application (Update buyer's monthly commitment)
    if loan_amount > 0:
        monthly_payment = calculate_monthly_payment(
            loan_amount,
            MORTGAGE_CONFIG["annual_interest_rate"],
            MORTGAGE_CONFIG["loan_term_years"]
        )
        buyer.monthly_payment += monthly_payment
        # In a full system, we would log the loan in a loans table suitable for amortization
        
    # Seller receives full price
    if seller:
        seller.cash += price
        # Remove property from seller's list
        seller.owned_properties = [p for p in seller.owned_properties if p['property_id'] != property_data['property_id']]
        
    # 3. Ownership Update
    start_owner_id = property_data.get('owner_id')
    
    # Update Property Data (In-Memory modification of the dict passed)
    property_data['owner_id'] = buyer.id
    property_data['status'] = 'off_market'
    property_data.pop('listed_price', None) # Clear listing
    
    # Phase 3.2: Dynamic Pricing (Update base_value to reflect market reality)
    property_data['base_value'] = price
    
    # Add to buyer's list
    # Important: append the SAME dictionary object so updates track? 
    # Or copy? Better to append the dict reference if we want consistent updates.
    buyer.owned_properties.append(property_data)
    
    # 4. Return Transaction Record
    return {
        "property_id": property_data['property_id'],
        "buyer_id": buyer.id,
        "seller_id": seller.id if seller else start_owner_id, # If system sale, seller might be None
        "price": price,
        "down_payment": down_payment,
        "loan_amount": loan_amount,
        "type": "secondary" if seller else "new_sale"
    }
