"""
Transaction Engine: Handles Listings, Matching, Negotiation, and Execution
"""
import json
import random
from typing import List, Dict, Optional, Tuple, Any
from models import Agent, Market
from agent_behavior import safe_call_llm, safe_call_llm_async, build_macro_context, decide_negotiation_format
from mortgage_system import check_affordability, calculate_monthly_payment
from config.settings import MORTGAGE_CONFIG

# --- New Negotiation Modes (Phase 5) ---

def run_batch_bidding(seller: Agent, buyers: List[Agent], listing: Dict, market: Market, config=None) -> Dict:
    """Mode A: Batch Bidding (Blind Auction)"""
    history = []
    min_price = listing['min_price']
    
    # 1. Buyers Submit Bids
    bids = []
    for buyer in buyers:
        max_budget = buyer.preference.max_price
        prompt = f"""
        你是买家 {buyer.id}。参与房产盲拍（Batch Bidding）。
        房产: {listing['zone']}区 {listing.get('building_area')}㎡
        你的预算: {max_budget}
        当前挂牌价: {listing['listed_price']}
        
        这是盲拍，只有一次出价机会。价高者得（需高于底价）。
        
        请出价（0表示放弃）：
        输出JSON: {{"bid_price": float, "reason": "..."}}
        """
        resp = safe_call_llm(prompt, {"bid_price": 0, "reason": "Pass"})
        bid_price = float(resp.get("bid_price", 0))
        
        if bid_price > 0 and bid_price <= max_budget:
            bids.append({"buyer": buyer, "price": bid_price, "reason": resp.get("reason")})
            
    # 2. Seller Selects Winner
    if not bids:
        return {"outcome": "failed", "reason": "No valid bids"}
        
    # Sort by price desc
    bids.sort(key=lambda x: x['price'], reverse=True)
    best_bid = bids[0]
    
    if best_bid['price'] >= min_price:
        return {
            "outcome": "success", 
            "buyer_id": best_bid['buyer'].id, 
            "final_price": best_bid['price'],
            "mode": "batch_bidding",
            "history": [{"action": "WIN_BID", "price": best_bid['price'], "buyer": best_bid['buyer'].id}]
        }
    else:
        return {"outcome": "failed", "reason": "Highest bid below min_price"}

def run_flash_deal(seller: Agent, buyer: Agent, listing: Dict, market: Market) -> Dict:
    """Mode B: Flash Deal (Take it or Leave it)"""
    # 1. Seller sets Flash Price (usually discounted)
    flash_price = listing['listed_price'] * 0.95 # Auto-discount for speed
    if flash_price < listing['min_price']: 
        flash_price = listing['min_price']
        
    # 2. Buyer Decision
    prompt = f"""
    你是买家 {buyer.id}。卖家发起闪电成交（Flash Deal）。
    一口价: {flash_price:,.0f} (原价 {listing['listed_price']:,.0f})
    
    必须马上决定：接受(ACCEPT) 或 拒绝(REJECT)。
    输出JSON: {{"action": "ACCEPT"|"REJECT", "reason": "..."}}
    """
    resp = safe_call_llm(prompt, {"action": "REJECT", "reason": "Pass"})
    action = resp.get("action", "REJECT").upper()
    
    if action == "ACCEPT" and flash_price <= buyer.preference.max_price:
        return {
            "outcome": "success",
            "buyer_id": buyer.id,
            "final_price": flash_price,
            "mode": "flash_deal",
            "history": [{"action": "FLASH_ACCEPT", "price": flash_price}]
        }
    return {"outcome": "failed", "reason": "Buyer rejected flash deal"}

def run_negotiation_session(seller: Agent, buyers: List[Agent], listing: Dict, market: Market, config=None) -> Dict:
    """Main Entry Point for Negotiation Phase"""
    if not buyers:
        return {"outcome": "failed", "reason": "No valid buyers"}
        
    # 1. Seller Decides Mode
    market_hint = "买家众多" if len(buyers) > 1 else "单一买家"
    mode = decide_negotiation_format(seller, buyers, market_hint)
    
    # 2. Dispatch
    if mode == "BATCH":
        return run_batch_bidding(seller, buyers, listing, market, config)
        
    elif mode == "FLASH":
        # Pick one buyer to offer flash deal (e.g. first one)
        target_buyer = buyers[0] 
        return run_flash_deal(seller, target_buyer, listing, market)
        
    else: # CLASSIC
        # Iterate buyers until one succeeds or all fail
        for buyer in buyers:
            result = negotiate(buyer, seller, listing, market, len(buyers), config)
            if result['outcome'] == 'success':
                result['buyer_id'] = buyer.id
                result['mode'] = 'classic'
                return result
                
    return {"outcome": "failed", "reason": "All negotiations failed"}

async def run_negotiation_session_async(seller: Agent, buyers: List[Agent], listing: Dict, market: Market, config=None) -> Dict:
    """Async Main Entry Point for Negotiation Phase"""
    if not buyers:
        return {"outcome": "failed", "reason": "No valid buyers"}
        
    market_hint = "买家众多" if len(buyers) > 1 else "单一买家"
    mode = decide_negotiation_format(seller, buyers, market_hint)
    
    # Simple Async Implementation: Support Classic Mode primarily for now
    # (Batch and Flash can be added later or reuse sync logic if no LLM calls inside those specific functions yet, 
    # but run_batch_bidding DOES use LLM, so they should be async too. For urgency, we map everything to classic async or implement others)
    
    
    consolidated_log = []
    
    if mode == "CLASSIC":
         for buyer in buyers:
            # Await the async negotiate
            result = await negotiate_async(buyer, seller, listing, market, len(buyers), config)
            consolidated_log.extend(result.get('history', []))
            
            if result['outcome'] == 'success':
                result['buyer_id'] = buyer.id
                result['mode'] = 'classic'
                result['history'] = consolidated_log # Preserve prior failed attempts log too
                return result
    else:
        # Fallback to sync for unimplemented modes or implement them
        # For this tier, let's just use Classic Async for all or fallback to sync wrapper
        # But to gain performance, we really want async.
        # Let's fallback to CLASSIC async for now to ensure coverage
        for buyer in buyers:
            result = await negotiate_async(buyer, seller, listing, market, len(buyers), config)
            consolidated_log.extend(result.get('history', []))
            
            if result['outcome'] == 'success':
                result['buyer_id'] = buyer.id
                result['mode'] = 'classic'
                result['history'] = consolidated_log
                return result
                
    return {"outcome": "failed", "reason": "All negotiations failed", "history": consolidated_log}

# --- 1. Seller Listing Logic ---

def generate_seller_listing(seller: Agent, property_data: Dict, market: Market, strategy_hint: str = "balanced", pricing_coefficient: float = None) -> Dict:
    """
    Generate seller listing with pricing based on LLM-driven coefficient (Tier 3).
    
    Strategy Hint: aggressive, balanced, urgent
    pricing_coefficient: If provided (from determine_listing_strategy), use directly.
                         Otherwise fall back to calling LLM.
    """
    
    # Get Market Info
    zone = property_data.get('zone', 'A') # Default to A if missing
    avg_price = market.get_avg_price(zone)
    if avg_price == 0:
        avg_price = property_data['base_value']
    
    base_val = property_data['base_value']
    
    # Tier 3: If coefficient provided, use it directly
    if pricing_coefficient is not None:
        # Apply coefficient based on strategy type
        if strategy_hint == 'aggressive':  # Strategy A: based on valuation
            listed_price = base_val * pricing_coefficient
            min_price = base_val * (pricing_coefficient - 0.05)  # 5% buffer
        elif strategy_hint == 'balanced':  # Strategy B: based on market price
            listed_price = avg_price * pricing_coefficient
            min_price = avg_price * (pricing_coefficient - 0.03)
        elif strategy_hint == 'urgent':  # Strategy C: based on valuation
            listed_price = base_val * pricing_coefficient
            min_price = base_val * (pricing_coefficient - 0.03)
        else:
            listed_price = base_val * pricing_coefficient
            min_price = base_val * 0.95
        
        return {
            "property_id": property_data['property_id'],
            "seller_id": seller.id,
            "zone": zone,
            "listed_price": listed_price,
            "min_price": max(min_price, 1.0),
            "urgency": 0.5,
            "status": "active",
            "reasoning": f"Coefficient {pricing_coefficient:.2f} from LLM strategy"
        }
    
    # Legacy path: Call LLM if no coefficient (backward compatibility)
    prompt = f"""
    你准备卖房：
    【背景】{seller.story.background_story}
    【卖房动机】{seller.story.selling_motivation}
    【房产】{zone}区，{property_data.get('building_area', 100)}㎡
    【市场均价】{avg_price:,.0f}元
    【估值】{property_data['base_value']:,.0f}元
    
    【定价策略】{strategy_hint}
    (aggressive=尝试挂高价, balanced=随行就市, urgent=急售降价)

    设定挂牌价和可接受最低价：
    输出JSON：{{"listed_price":..., "min_price":..., "urgency": 0-1, "reasoning":"..."}}
    """
    
    # Default fallback logic based on strategy
    if strategy_hint == 'aggressive':
        def_list = base_val * 1.15
        def_min = base_val * 1.05
    elif strategy_hint == 'urgent':
        def_list = base_val * 0.95
        def_min = base_val * 0.90
    else:
        def_list = base_val * 1.1
        def_min = base_val * 0.95

    default_listing = {
        "listed_price": def_list,
        "min_price": def_min,
        "urgency": 0.5,
        "reasoning": f"Follow {strategy_hint} strategy"
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
        "zone": zone,  # 添加zone字段，negotiate需要用它判断市场供需
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
    
    print(f"\n=== DEBUG Buyer {buyer.id} Matching ===")
    print(f"Buyer Zone: {pref.target_zone}, Max Price: {pref.max_price:,.0f}")
    print(f"Received {len(listings)} listings for zone {pref.target_zone}")
    
    for listing in listings:
        prop = properties_map.get(listing['property_id'])
        if not prop:
            print(f"  ✗ Prop {listing['property_id']}: NOT IN MAP")
            continue
            
        # 1. Zone Check
        if pref.target_zone and prop['zone'] != pref.target_zone:
            print(f"  ✗ Prop {listing['property_id']}: Zone mismatch ({prop['zone']} != {pref.target_zone})")
            continue
            
        # 2. Price Check (Listed Price <= Max Price)
        if listing['listed_price'] > pref.max_price:
            print(f"  ✗ Prop {listing['property_id']}: Price too high ({listing['listed_price']:,.0f} > {pref.max_price:,.0f})")
            continue
            

        # 3. Bedroom Check (Defensive: missing column in active_participants)
        min_beds = getattr(pref, 'min_bedrooms', 1)
        if prop.get('bedrooms', 999) < min_beds:  # Default 999 = assume compatible if missing
            print(f"  ✗ Prop {listing['property_id']}: Not enough bedrooms ({prop.get('bedrooms', '?')} < {min_beds})")
            continue
            
        # 4. School District Check (Defensive: missing column in active_participants)
        needs_school = getattr(pref, 'need_school_district', False)
        if needs_school and not prop.get('is_school_district', False):
            print(f"  ✗ Prop {listing['property_id']}: School district required but not available")
            continue
        
        print(f"  ✓ Prop {listing['property_id']}: MATCH! (Price: {listing['listed_price']:,.0f})")
        candidates.append(listing)
        
    print(f"Total candidates: {len(candidates)}")
        
    if not candidates:
        return None
        
    # 5. LLM Selection from Candidates
    # Heuristic: Filter to top 5 cheapest to save tokens, but let LLM decide among them.
    candidates.sort(key=lambda x: x['listed_price'])
    shortlist = candidates[:5]
    
    # helper to format prop for prompt
    def format_prop(l):
        p = properties_map.get(l['property_id'])
        return {
            "id": l['property_id'],
            "zone": p['zone'],
            "area": p['building_area'],
            "price": l['listed_price'],
            "school": "Yes" if p.get('is_school_district') else "No",
            "type": p.get('property_type', 'N/A')
        }
        
    props_info = [format_prop(c) for c in shortlist]
    
    prompt = f"""
    你是买家 {buyer.name}。
    【需求】{buyer.story.housing_need}
    【预算上限】{pref.max_price/10000:.0f}万
    【偏好】区域: {pref.target_zone}, 学区: {"需要" if pref.need_school_district else "无所谓"}
    
    现有以下候选房源（已按价格排序）：
    {json.dumps(props_info, indent=2, ensure_ascii=False)}
    
    请选择一套最符合你需求的房产。如果不满意，可以不选。
    输出JSON: {{"selected_property_id": int|null, "reason": "..."}}
    """
    
    # Default to cheapest (old logic behavior as fallback)
    default_resp = {"selected_property_id": shortlist[0]['property_id'], "reason": "Default cheapest"}
    
    result = safe_call_llm(prompt, default_resp)
    selected_id = result.get("selected_property_id")
    
    if selected_id:
        for c in shortlist:
            if c['property_id'] == selected_id:
                return c
                
    # Fallback/Logic for explicit None
    if selected_id is None:
        return None
        
    return shortlist[0]

# --- 3. Negotiation Logic (Phase 2.2) ---

# --- 3. Negotiation Logic (Phase 2.2 & P3) ---

def get_market_condition(market: Market, zone: str, potential_buyers_count: int) -> str:
    """
    Determine market condition based on Supply/Demand Ratio.
    Ratio = Active Listings / Potential Buyers
    """
    listings = [p for p in market.properties if p['status'] == 'for_sale' and p['zone'] == zone]
    listing_count = len(listings)
    
    # Avoid division by zero
    buyer_count = max(potential_buyers_count, 1)
    
    ratio = listing_count / buyer_count
    
    # Thresholds
    if ratio > 1.5:
        return "oversupply"      # 供过于求 (买方市场)
    elif ratio < 0.7:
        return "undersupply"     # 供不应求 (卖方市场)
    else:
        return "balanced"        # 供需平衡

def negotiate(buyer: Agent, seller: Agent, listing: Dict, market: Market, potential_buyers_count: int = 10, config=None) -> Dict:
    """
    LLM-driven negotiation with Market Context, Configurable Rounds, and Personality.
    """
    # 1. Configuration & Context Setup
    neg_cfg = config.negotiation if config else {}
    rounds_range = neg_cfg.get('rounds_range', [2, 3])
    gap_threshold = neg_cfg.get('heuristic_gap_threshold', 0.20)
    market_conds = neg_cfg.get('market_conditions', {})
    
    current_price = listing['listed_price']
    min_price = listing['min_price']
    
    # 2. Heuristic Pre-check (Fail early if gap is too large)
    buyer_max = buyer.preference.max_price
    # Check gap between listed price and buyer max
    # If listed_price is significantly higher than buyer_max, skip
    price_gap = (current_price - buyer_max) / current_price
    
    # Also check min_price vs buyer_max
    if min_price > buyer_max * (1 + gap_threshold):
         return {"outcome": "failed", "reason": f"Pre-check: Price gap {price_gap:.1%} too large", "history": [], "final_price": 0}

    # 3. Market Condition & Strategy
    market_condition = get_market_condition(market, listing['zone'], potential_buyers_count)
    
    cond_cfg = market_conds.get(market_condition, {})
    lowball_ratio = cond_cfg.get('buyer_lowball', 0.90)
    market_hint = cond_cfg.get('llm_hint', "【市场供需平衡】供需相当，价格理性。")
    
    # Macro Environment Context
    macro_context = build_macro_context(1, config) # Month is not passed effectively here, defaulting to 1 or need to pass in
    
    history = []
    rounds = random.randint(*rounds_range)
    
    # Starting offer based on configuration
    buyer_offer_price = current_price * lowball_ratio

    negotiation_log = []
    
    # Agent Styling
    buyer_style = getattr(buyer.story, 'negotiation_style', 'balanced')
    seller_style = getattr(seller.story, 'negotiation_style', 'balanced')
    
    style_prompts = {
        "aggressive": "你是个激进派。大幅杀价/坐地起价，一言不合就退出，绝不吃亏。",
        "conservative": "你是个保守派。谨慎出价，坚守底线，不轻易冒进。",
        "balanced": "你是个理性派。寻求双赢，愿意适度妥协以达成交易。",
        "desperate": "你是个急迫派。为了快速成交，愿意大幅让步。"
    }

    for r in range(1, rounds + 1):
        # --- Buyer Turn ---
        buyer_prompt = f"""
        {macro_context}
        你是买方Agent {buyer.id}，第{r}/{rounds}轮谈判。
        【你的风格】{buyer_style} - {style_prompts.get(buyer_style, "")}
        
        【交易背景】
        - 你的预算上限: {buyer.preference.max_price:,.0f}
        - 卖方当前报价: {current_price:,.0f}
        - 你的上轮出价: {buyer_offer_price:,.0f}
        
        【市场提示】{market_hint}
        
        【谈判历史】
        {json.dumps(negotiation_log, ensure_ascii=False)}
        
        决定行动 (请遵循你的风格):
        - OFFER: 出价 (必须低于报价，可参考建议: {current_price*lowball_ratio:,.0f} ~ {current_price:,.0f})
        - ACCEPT: 接受报价
        - WITHDRAW: 放弃 (如果价格太高或对方太顽固)
        
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
        {macro_context}
        你是卖方Agent {seller.id}，第{r}/{rounds}轮谈判。
        【你的风格】{seller_style} - {style_prompts.get(seller_style, "")}
        
        【交易背景】
        - 你的心理底价: {min_price:,.0f}
        - 买方最新出价: {buyer_offer_price:,.0f}
        - 当前你的报价: {current_price:,.0f}
        
        【市场提示】{market_hint}
        {'【趋势建议】市场上涨中，可以坚守价格或适当提价。' if market_condition == 'undersupply' else ''}
        {'【趋势建议】市场低迷，建议适度灵活，避免流拍。' if market_condition == 'oversupply' else ''}
        
        【谈判历史】
        {json.dumps(negotiation_log, ensure_ascii=False)}
        
        决定行动 (请遵循你的风格):
        - ACCEPT: 接受买方出价 (如果高于底价或你是急迫型)
        - COUNTER: 还价 (必须降低报价以示诚意，除非你是激进型)
        - REJECT: 拒绝 (价格太低且无意让步)
        
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

async def negotiate_async(buyer: Agent, seller: Agent, listing: Dict, market: Market, potential_buyers_count: int = 10, config=None) -> Dict:
    """
    Async version of negotiate.
    """
    # 1. Configuration & Context Setup
    neg_cfg = config.negotiation if config else {}
    rounds_range = neg_cfg.get('rounds_range', [2, 3])
    gap_threshold = neg_cfg.get('heuristic_gap_threshold', 0.20)
    market_conds = neg_cfg.get('market_conditions', {})
    
    current_price = listing['listed_price']
    min_price = listing['min_price']
    
    # 2. Heuristic Pre-check
    buyer_max = buyer.preference.max_price
    price_gap = (current_price - buyer_max) / current_price
    
    if min_price > buyer_max * (1 + gap_threshold):
         return {"outcome": "failed", "reason": f"Pre-check: Price gap {price_gap:.1%} too large", "history": [], "final_price": 0}

    # 3. Market Condition & Strategy
    market_condition = get_market_condition(market, listing['zone'], potential_buyers_count)
    cond_cfg = market_conds.get(market_condition, {})
    lowball_ratio = cond_cfg.get('buyer_lowball', 0.90)
    market_hint = cond_cfg.get('llm_hint', "【市场供需平衡】供需相当，价格理性。")
    
    macro_context = build_macro_context(1, config)
    
    negotiation_log = []
    rounds = random.randint(*rounds_range)
    buyer_offer_price = current_price * lowball_ratio
    
    buyer_style = getattr(buyer.story, 'negotiation_style', 'balanced')
    seller_style = getattr(seller.story, 'negotiation_style', 'balanced')
    
    style_prompts = {
        "aggressive": "你是个激进派。大幅杀价/坐地起价，一言不合就退出，绝不吃亏。",
        "conservative": "你是个保守派。谨慎出价，坚守底线，不轻易冒进。",
        "balanced": "你是个理性派。寻求双赢，愿意适度妥协以达成交易。",
        "desperate": "你是个急迫派。为了快速成交，愿意大幅让步。"
    }

    for r in range(1, rounds + 1):
        # --- Buyer Turn ---
        buyer_prompt = f"""
        {macro_context}
        你是买方Agent {buyer.id}，第{r}/{rounds}轮谈判。
        【你的风格】{buyer_style} - {style_prompts.get(buyer_style, "")}
        
        【交易背景】
        - 你的预算上限: {buyer.preference.max_price:,.0f}
        - 卖方当前报价: {current_price:,.0f}
        - 你的上轮出价: {buyer_offer_price:,.0f}
        
        【市场提示】{market_hint}
        
        【谈判历史】
        {json.dumps(negotiation_log, ensure_ascii=False)}
        
        决定行动 (请遵循你的风格):
        - OFFER: 出价 (必须低于报价，可参考建议: {current_price*lowball_ratio:,.0f} ~ {current_price:,.0f})
        - ACCEPT: 接受报价
        - WITHDRAW: 放弃 (如果价格太高或对方太顽固)
        
        输出JSON: {{"action": "OFFER"|"ACCEPT"|"WITHDRAW", "offer_price": 0, "reason": "..."}}
        """
        buyer_resp = await safe_call_llm_async(buyer_prompt, {"action": "WITHDRAW", "offer_price": 0, "reason": "LLM Error"}, system_prompt="你是精明的购房者。")
        buyer_action = buyer_resp.get("action", "WITHDRAW")
        
        if buyer_action == "OFFER":
            buyer_offer_price = float(buyer_resp.get("offer_price", buyer_offer_price))
            if buyer_offer_price >= current_price: 
                buyer_action = "ACCEPT"
                buyer_offer_price = current_price
            if buyer_offer_price > buyer.preference.max_price:
                 buyer_action = "WITHDRAW"

        negotiation_log.append({
            "round": r, "party": "buyer", "action": buyer_action, "price": buyer_offer_price, "content": buyer_resp.get("reason", "")
        })
        
        if buyer_action == "WITHDRAW":
            return {"outcome": "failed", "reason": "Buyer withdrew", "history": negotiation_log, "final_price": 0}
        if buyer_action == "ACCEPT":
             return {"outcome": "success", "final_price": current_price, "history": negotiation_log}
             
        # --- Seller Turn ---
        seller_prompt = f"""
        {macro_context}
        你是卖方Agent {seller.id}，第{r}/{rounds}轮谈判。
        【你的风格】{seller_style} - {style_prompts.get(seller_style, "")}
        
        【交易背景】
        - 你的心理底价: {min_price:,.0f}
        - 买方最新出价: {buyer_offer_price:,.0f}
        - 当前你的报价: {current_price:,.0f}
        
        【市场提示】{market_hint}
        
        【谈判历史】
        {json.dumps(negotiation_log, ensure_ascii=False)}
        
        决定行动 (请遵循你的风格):
        - ACCEPT: 接受买方出价
        - COUNTER: 还价
        - REJECT: 拒绝
        
        输出JSON: {{"action": "ACCEPT"|"COUNTER"|"REJECT", "counter_price": 0, "reason": "..."}}
        """
        seller_resp = await safe_call_llm_async(seller_prompt, {"action": "REJECT", "counter_price": 0, "reason": "LLM Error"}, system_prompt="你是理性的房产卖家。")
        seller_action = seller_resp.get("action", "REJECT")
        
        if seller_action == "COUNTER":
             current_price = float(seller_resp.get("counter_price", current_price))
             if current_price <= buyer_offer_price:
                 seller_action = "ACCEPT"
                 current_price = buyer_offer_price
        
        negotiation_log.append({
            "round": r, "party": "seller", "action": seller_action, "price": current_price, "content": seller_resp.get("reason", "")
        })
        
        if seller_action == "ACCEPT":
             return {"outcome": "success", "final_price": buyer_offer_price, "history": negotiation_log}
        if seller_action == "REJECT":
             return {"outcome": "failed", "reason": "Seller rejected", "history": negotiation_log, "final_price": 0}

    return {"outcome": "failed", "reason": "Max rounds reached", "history": negotiation_log, "final_price": 0}

def handle_failed_negotiation(seller: Agent, listing: Dict, market: Market, potential_buyers_count: int) -> bool:
    """
    Handle negotiation failure. In oversupply market, seller might drop price immediately.
    Returns: True if price adjusted, False otherwise.
    """
    market_condition = get_market_condition(market, listing.get('zone', 'A'), potential_buyers_count)
    
    
    if market_condition == "oversupply":
        # 30% chance to drop price immediately in panic market
        import random
        if random.random() < 0.3:
            price_reduction = random.uniform(0.02, 0.05) # 2-5% drop
            old_price = listing['listed_price']
            new_price = old_price * (1 - price_reduction)
            listing['listed_price'] = new_price
            listing['min_price'] = listing['min_price'] * (1 - price_reduction * 0.5)
            # print(f"📉 Market Pressure: Seller {seller.id} cuts price {old_price:,.0f} -> {new_price:,.0f}")
            return True
            
    return False

# --- 4. Transaction Execution (Phase 2.3 & 3) ---

def execute_transaction(buyer: Agent, seller: Optional[Agent], property_data: Dict, price: float, market: Market, config=None) -> Optional[Dict]:
    """
    Execute transaction: Transfer funds, update ownership, apply mortgage, update market.
    Returns transaction record or None if failed.
    """
    # 1. Final Affordability Check (incorporating Mortgage logic)
    is_affordable, down_payment, loan_amount = check_affordability(buyer, price, config)
    
    if not is_affordable:
        # print(f"Transaction failed: Buyer {buyer.id} cannot afford {price}")
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


# --- 5. Open Negotiation (LLM-Driven Free Strategy) ---

def open_negotiate(buyer: Agent, seller: Agent, listing: Dict, market: Market,
                   buyer_context: str = "", seller_context: str = "", config=None) -> Dict:
    """
    开放式谈判 - LLM自由表达策略，代码解析执行
    
    Args:
        buyer: 买家Agent
        seller: 卖家Agent
        listing: 挂牌信息
        market: 市场对象
        buyer_context: 买家历史上下文
        seller_context: 卖家历史上下文
    
    Returns:
        dict: {"outcome": "success"|"failed"|"max_rounds", "final_price": float, "history": list}
    """
    from agent_behavior import safe_call_llm
    
    history = []
    max_rounds = 5
    current_ask = listing.get('listed_price', 0)
    min_price = listing.get('min_price', current_ask * 0.9)
    
    # 获取买家预算
    buyer_max = getattr(buyer, 'preference', None)
    if buyer_max:
        buyer_max = buyer_max.max_price
    else:
        from mortgage_system import calculate_max_affordable
        buyer_max = calculate_max_affordable(buyer.cash, buyer.monthly_income, config=config)
    
    # 市场状态
    supply = len([p for p in market.properties if p.get('status') == 'for_sale'])
    zone = listing.get('zone', 'B')
    zone_supply = len([p for p in market.properties if p.get('status') == 'for_sale' and p.get('zone') == zone])
    
    if zone_supply > 15:
        market_desc = "买方市场(供过于求，房源充足)"
    elif zone_supply < 5:
        market_desc = "卖方市场(供不应求，房源紧缺)"
    else:
        market_desc = "均衡市场(供需相当)"
    
    # 宏观与性格上下文
    macro_context = build_macro_context(1, config)
    buyer_style = getattr(buyer.story, 'negotiation_style', 'balanced')
    seller_style = getattr(seller.story, 'negotiation_style', 'balanced')

    # 房产信息
    prop_info = f"{zone}区 {listing.get('building_area', 80):.0f}㎡ {listing.get('property_type', '普通住宅')}"
    
    for round_num in range(1, max_rounds + 1):
        # === 买方回合 ===
        buyer_prompt = f"""
{macro_context}
你是买家 {buyer.name}，正在第{round_num}轮谈判。
【你的性格】{buyer_style}

【你的背景】{buyer.story.background_story}
【你的预算上限】¥{buyer_max:,.0f}
【你的历史行为】
{buyer_context if buyer_context else "无历史记录"}

【目标房产】{prop_info}
【卖方当前报价】¥{current_ask:,.0f}

【市场环境】{market_desc}
【谈判历史】{json.dumps(history[-4:], ensure_ascii=False) if history else "首轮谈判"}

---
请自由思考并决定你的行动。你可以：
- 出价（给出具体金额和理由）
- 接受当前价格
- 放弃（觉得不值或超预算）
- 其他策略（如要求附加条件、表示可以再谈等）

输出JSON:
{{
  "action": "OFFER" / "ACCEPT" / "WITHDRAW" / 其他,
  "offer_price": 你的出价(数字，不出价则为null),
  "message": "你想对卖家说的话",
  "inner_thought": "你内心的真实想法（不会告诉对方）"
}}
"""
        buyer_resp = safe_call_llm(buyer_prompt, {
            "action": "WITHDRAW", 
            "offer_price": None, 
            "message": "价格超出预算", 
            "inner_thought": "默认放弃"
        }, system_prompt="你是一个精明但理性的购房者。")
        
        # 解析买方行动
        buyer_action = str(buyer_resp.get("action", "WITHDRAW")).upper()
        buyer_offer = buyer_resp.get("offer_price")
        
        # 验证出价
        if buyer_offer is not None:
            try:
                buyer_offer = float(buyer_offer)
                if buyer_offer > buyer_max:
                    buyer_action = "WITHDRAW"
                    buyer_resp["inner_thought"] = "出价超过预算上限，放弃"
            except:
                buyer_offer = None
        
        history.append({
            "round": round_num, 
            "party": "buyer", 
            "agent_id": buyer.id,
            "action": buyer_action,
            "price": buyer_offer, 
            "message": buyer_resp.get("message", ""),
            "thought": buyer_resp.get("inner_thought", "")
        })
        
        # 检查终止条件
        if buyer_action == "WITHDRAW":
            return {
                "outcome": "failed", 
                "reason": "买方放弃", 
                "history": history, 
                "final_price": 0
            }
        if buyer_action == "ACCEPT":
            return {
                "outcome": "success", 
                "final_price": current_ask, 
                "history": history
            }
        
        # 如果没有出价，设置默认出价
        if buyer_offer is None:
            buyer_offer = current_ask * 0.9
            
        # === 卖方回合 ===
        seller_prompt = f"""
你是卖家 {seller.name}，正在第{round_num}轮谈判。

【你的背景】{seller.story.background_story}
【你的历史行为】
{seller_context if seller_context else "无历史记录"}

【你的房产】{prop_info}
【你的挂牌价】¥{listing['listed_price']:,.0f}
【你的心理底价】约 ¥{min_price:,.0f}

【买方最新出价】¥{buyer_offer:,.0f}
【买方说】"{buyer_resp.get('message', '')}"

【市场环境】{market_desc}
【谈判历史】{json.dumps(history[-4:], ensure_ascii=False)}

---
请自由思考并决定你的行动。你可以：
- 接受买方出价
- 还价（给出新价格）
- 拒绝（结束谈判）
- 其他策略（如提出附加条件、表示可以再谈等）

输出JSON:
{{
  "action": "ACCEPT" / "COUNTER" / "REJECT" / 其他,
  "counter_price": 你的还价(数字，不还价则为null),
  "message": "你想对买家说的话",
  "inner_thought": "你内心的真实想法"
}}
"""
        seller_resp = safe_call_llm(seller_prompt, {
            "action": "REJECT", 
            "counter_price": None, 
            "message": "价格太低", 
            "inner_thought": "默认拒绝"
        }, system_prompt="你是一个理性的房产卖家。")
        
        seller_action = str(seller_resp.get("action", "REJECT")).upper()
        counter_price = seller_resp.get("counter_price")
        
        # 验证还价
        if counter_price is not None:
            try:
                counter_price = float(counter_price)
            except:
                counter_price = None
        
        history.append({
            "round": round_num, 
            "party": "seller", 
            "agent_id": seller.id,
            "action": seller_action,
            "price": counter_price if counter_price else current_ask,
            "message": seller_resp.get("message", ""),
            "thought": seller_resp.get("inner_thought", "")
        })
        
        # 检查终止条件
        if seller_action == "ACCEPT":
            final_price = buyer_offer if buyer_offer else current_ask
            return {
                "outcome": "success", 
                "final_price": final_price, 
                "history": history
            }
        if seller_action == "REJECT":
            return {
                "outcome": "failed", 
                "reason": "卖方拒绝", 
                "history": history, 
                "final_price": 0
            }
        if seller_action == "COUNTER" and counter_price:
            current_ask = counter_price
    
    # 达到最大轮数
    return {
        "outcome": "max_rounds", 
        "reason": "超过最大谈判轮数", 
        "history": history, 
        "final_price": 0
    }

