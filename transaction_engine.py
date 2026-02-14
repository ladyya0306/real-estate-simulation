# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========

"""
Transaction Engine: Handles Listings, Matching, Negotiation, and Execution
"""
import asyncio
import json
import logging
import random
from typing import Dict, List, Optional

from agent_behavior import (decide_negotiation_format, safe_call_llm,
                            safe_call_llm_async)
from models import Agent, Market
from mortgage_system import calculate_max_affordable_price, check_affordability

logger = logging.getLogger(__name__)

# --- Helper: Build Macro Context (Moved from agent_behavior if circular dep, or reimplement) ---
def build_macro_context(month: int, config=None) -> str:
    """Builds macro-economic context string."""
    # This might need to be imported or reconstructed if agent_behavior usage causes circular import.
    # For now, let's assume it's safe to import IF agent_behavior doesn't import transaction_engine.
    # Actually transaction_engine imports agent_behavior, so it's fine.
    # But wait, I removed it from import list above to check.
    # It was: from agent_behavior import ..., build_macro_context
    # I will reimplement here to be safe and simple.

    risk_free_rate = 0.03
    ltv = 0.7
    if config:
        risk_free_rate = config.market.get('risk_free_rate', 0.03)
        ltv = config.mortgage.get('max_ltv', 0.7)

    return f"【宏观环境】无风险利率: {risk_free_rate*100:.1f}%, 首付比例: {(1-ltv)*100:.0f}%"

# --- New Negotiation Modes (Phase 5) ---

async def run_batch_bidding_async(seller: Agent, buyers: List[Agent], listing: Dict, market: Market, month: int, config=None, db_conn=None) -> Dict:
    """Mode A: Batch Bidding (Blind Auction) - Async"""
    history = []
    min_price = listing['min_price']

    # 1. Buyers Submit Bids (Parallel)
    async def get_buyer_bid(buyer):
        # ✅ Phase 3.1: Calculate real affordability
        max_affordable = calculate_max_affordable_price(buyer, config)

        # ✅ Phase 5.1: Fix Price Logic - Add Context
        valuation = listing.get('initial_value', listing['listed_price'])
        style = buyer.story.investment_style

        prompt = f"""
        你是买家 {buyer.id}。参与房产盲拍（Batch Bidding）。
        房产: {listing['zone']}区 {listing.get('building_area')}㎡
        当前挂牌价: {listing['listed_price']:,.0f}
        **市场估值**: ¥{valuation:,.0f} (参考基准)

        【你的画像】
        - 投资风格: {style} (决定你的溢价意愿)
        - 现金: ¥{buyer.cash:,.0f}
        - 月收入: ¥{buyer.monthly_income:,.0f}
        - **财务极限(Max Cap)**: ¥{max_affordable:,.0f}

        【决策逻辑】
        1. 不要无脑出财务极限价！这会让你成为"接盘侠"。
        2. 参考估值和挂牌价，结合你的风格出价：
           - Conservative (保守): 低于或略高于估值 (+0~5%)
           - Balanced (平衡): 适度溢价以确保拿下 (+5~10%)
           - Aggressive (激进): 为拿下心仪房源可大幅溢价 (+10~20%)，但绝不能超过财务极限。

        ⚠️ 硬性约束：出价必须 < ¥{max_affordable:,.0f}。

        请出价（0表示放弃）：
        输出JSON: {{"bid_price": float, "reason": "..."}}
        """
        resp = await safe_call_llm_async(prompt, {"bid_price": 0, "reason": "Pass"})
        bid_price = float(resp.get("bid_price", 0))

        # ✅ Phase 3.1: Validate affordability post-bid
        original_bid = bid_price
        is_valid = True
        if bid_price > 0:
            is_affordable, _, _ = check_affordability(buyer, bid_price, config)
            if not is_affordable:
                logger.warning(
                    f"🚫 买家{buyer.id}出价¥{bid_price:,.0f}超出负担能力"
                    f"（最大可负担¥{max_affordable:,.0f}），标记为无效"
                )
                bid_price = 0  # Mark as invalid bid
                is_valid = False

        return {"buyer": buyer, "price": bid_price, "original_bid": original_bid, "is_valid": is_valid, "reason": resp.get("reason")}

    tasks = [get_buyer_bid(b) for b in buyers]
    results = await asyncio.gather(*tasks)

    # ✅ Phase 3.3: Record all bids to property_buyer_matches table
    if db_conn:
        cursor = db_conn.cursor()
        for bid_result in results:
            try:
                cursor.execute("""
                    INSERT INTO property_buyer_matches
                    (month, property_id, buyer_id, listing_price, buyer_bid, is_valid_bid, proceeded_to_negotiation)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    month,
                    listing['property_id'],
                    bid_result['buyer'].id,
                    listing['listed_price'],
                    bid_result['original_bid'],
                    1 if bid_result['is_valid'] else 0,
                    1 if bid_result['price'] > 0 else 0
                ))
            except Exception as e:
                logger.error(f"Failed to record bid for buyer {bid_result['buyer'].id}: {e}")
        db_conn.commit()

    # ✅ Phase 3.1: Only filter out zero bids (affordability already checked)
    bids = [r for r in results if r['price'] > 0]

    # 2. Seller Selects Winner
    if not bids:
        return {"outcome": "failed", "reason": "No valid bids"}

    # Sort by price desc
    bids.sort(key=lambda x: x['price'], reverse=True)
    best_bid = bids[0]

    # Seller Final Decision (Auto-accept if > min_price + simple logic, or ask LLM?)
    # For speed, if highest bid > min_price, accept.
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

async def run_flash_deal_async(seller: Agent, buyer: Agent, listing: Dict, market: Market) -> Dict:
    """Mode B: Flash Deal (Take it or Leave it) - Async"""
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
    resp = await safe_call_llm_async(prompt, {"action": "REJECT", "reason": "Pass"})
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

async def run_negotiation_session_async(seller: Agent, buyers: List[Agent], listing: Dict, market: Market, month: int, config=None, db_conn=None) -> Dict:
    """Async Main Entry Point for Negotiation Phase"""
    if not buyers:
        return {"outcome": "failed", "reason": "No valid buyers"}

    market_hint = "买家众多" if len(buyers) > 1 else "单一买家"
    mode = decide_negotiation_format(seller, buyers, market_hint)

    # Simple Async Implementation: Support Classic Mode primarily for now
    # (Batch and Flash can be added later or reuse sync logic if no LLM calls inside those specific functions yet,
    # but run_batch_bidding DOES use LLM, so they should be async too. For urgency, we map everything to classic async or implement others)


    consolidated_log = []

    if mode == "BATCH":
        # ✅ Phase 3.3: Pass db_conn to record bids
        return await run_batch_bidding_async(seller, buyers, listing, market, month, config, db_conn)

    elif mode == "FLASH":
        # Pick one buyer to offer flash deal (e.g. first one or random)
        target_buyer = buyers[0]
        return await run_flash_deal_async(seller, target_buyer, listing, market)

    elif mode == "CLASSIC":
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
    Generate seller listing.
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

def match_property_for_buyer(buyer: Agent, listings: List[Dict], properties_map: Dict[int, Dict], ignore_zone: bool = False) -> Optional[Dict]:
    """
    Find the best matching property for a buyer from active listings.
    listings: List of listing dicts (from property_listings table)
    properties_map: property_id -> property_data dict (full details)
    ignore_zone: If True, skip zone matching (for desperation fallback)
    """
    pref = buyer.preference
    candidates = []

    # print(f"\n=== DEBUG Buyer {buyer.id} Matching ===")
    # print(f"Buyer Zone: {pref.target_zone}, Max Price: {pref.max_price:,.0f} (IgnoreZone={ignore_zone})")
    # print(f"Received {len(listings)} listings for matching")

    for listing in listings:
        prop = properties_map.get(listing['property_id'])
        if not prop:
            continue

        # 1. Zone Check
        if not ignore_zone and pref.target_zone and prop['zone'] != pref.target_zone:
            continue

        # 2. Price Check (Listed Price <= Max Price * Buffer)
        # Allow 20% buffer for negotiation (e.g. asking 120, max 100 -> might negotiate down)
        if listing['listed_price'] > pref.max_price * 1.2:
            continue

        # 3. Bedroom Check (Defensive: missing column in active_participants)
        min_beds = getattr(pref, 'min_bedrooms', 1)
        if prop.get('bedrooms', 999) < min_beds:  # Default 999 = assume compatible if missing
            continue

        # 4. School District Check
        needs_school = getattr(pref, 'need_school_district', False)
        if needs_school and not prop.get('is_school_district', False):
            continue

        candidates.append(listing)

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
        is_final_round = (r == rounds)
        final_round_hint = "\n        ⚡️【最后通牒】这是最后这一轮谈判。如果达不成一致，交易将失败。请慎重决策！" if is_final_round else ""

        # --- Buyer Turn ---
        buyer_prompt = f"""
        {macro_context}
        你是买方Agent {buyer.id}，第{r}/{rounds}轮谈判。
        【你的风格】{buyer_style} - {style_prompts.get(buyer_style, "")}

        【交易背景】
        - 你的预算上限: {buyer.preference.max_price:,.0f}
        - 卖方当前报价: {current_price:,.0f}
        - 你的上轮出价: {buyer_offer_price:,.0f}

        【市场提示】{market_hint}{final_round_hint}

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
        seller_final_hint = "\n        ⚡️【最后通牒】这是买家的最终出价。必须决定：接受(ACCEPT) 或 拒绝(REJECT 导致交易失败)。不建议再还价。" if is_final_round else ""

        seller_prompt = f"""
        {macro_context}
        你是卖方Agent {seller.id}，第{r}/{rounds}轮谈判。
        【你的风格】{seller_style} - {style_prompts.get(seller_style, "")}

        【交易背景】
        - 你的心理底价: {min_price:,.0f}
        - 买方最新出价: {buyer_offer_price:,.0f}
        - 当前你的报价: {current_price:,.0f}

        【市场提示】{market_hint}{seller_final_hint}
        {'【趋势建议】市场上涨中，可以坚守价格或适当提价。' if market_condition == 'undersupply' else ''}
        {'【趋势建议】市场低迷，建议适度灵活，避免流拍。' if market_condition == 'oversupply' else ''}

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

# --- 4. Transaction Execution Logic ---

def execute_transaction(buyer: Agent, seller: Agent, property_data: Dict, final_price: float, market: Market = None, config=None) -> Optional[Dict]:
    """
    Execute transaction: Transfer ownership, handle money (Cash + Mortgage).
    Returns transaction record dict or None if failed.
    """
    # 1. Financial Check (Double check)
    # Calculate Down Payment
    # Default 30% down payment
    down_payment_ratio = 0.3
    if config and hasattr(config, "mortgage_down_payment_ratio"):
        down_payment_ratio = config.mortgage_down_payment_ratio

    down_payment = final_price * down_payment_ratio
    loan_amount = final_price - down_payment

    if buyer.cash < down_payment:
        logger.error(f"Transaction Failed: Buyer {buyer.id} insufficient cash for down payment. Need {down_payment:,.0f}, Have {buyer.cash:,.0f}")
        return None

    # 2. Transfer Money
    # Buyer pays down payment
    buyer.cash -= down_payment

    # Seller receives full price (Bank pays the rest)
    seller.cash += final_price

    # 3. Handle Mortgage
    # Simple mortgage: Add to total_debt, calculate monthly payment
    buyer.total_debt += loan_amount

    # Calculate monthly payment
    # Assume 30 years, interest rate from macro or config
    interest_rate = 0.045 # Default 4.5%
    if market and hasattr(market, "average_mortgage_rate"):
        interest_rate = market.average_mortgage_rate

    years = 30
    monthly_rate = interest_rate / 12
    num_payments = years * 12

    if monthly_rate > 0:
        monthly_payment = loan_amount * (monthly_rate * (1 + monthly_rate)**num_payments) / ((1 + monthly_rate)**num_payments - 1)
    else:
        monthly_payment = loan_amount / num_payments

    buyer.mortgage_monthly_payment += monthly_payment

    # 4. Transfer Ownership
    # Remove from Seller
    # Find property in seller's list
    # Use ID to match
    pid = property_data['property_id']
    seller.owned_properties = [p for p in seller.owned_properties if p['property_id'] != pid]

    # Add to Buyer
    # Update property data
    new_prop_data = property_data.copy()
    new_prop_data['owner_id'] = buyer.id
    new_prop_data['status'] = 'off_market'
    new_prop_data['last_transaction_price'] = final_price
    # Inherit or reset other fields? base_value might update to transaction price?
    # Usually base_value tracks market value, transaction price is history.
    # Let's update base_value to reflect market recognition?
    # Or keep it separate. Let's keep base_value as is (market dictates it next month).

    buyer.owned_properties.append(new_prop_data)

    # Update Market Object (Global State) if needed
    # market.properties is the source of truth for some lookups
    # props_map or market.properties should be updated.
    # We update the dict object in place if possible, assuming property_data is a reference to the one in market.properties
    property_data['owner_id'] = buyer.id
    property_data['status'] = 'off_market'
    property_data['last_transaction_price'] = final_price

    logger.info(f"Transaction Executed: Unit {pid} sold from {seller.name}({seller.id}) to {buyer.name}({buyer.id}) @ {final_price:,.0f}")

    return {
        "price": final_price,
        "down_payment": down_payment,
        "loan_amount": loan_amount,
        "buyer_id": buyer.id,
        "seller_id": seller.id,
        "property_id": pid
    }

def handle_failed_negotiation(seller: Agent, listing: Dict, market: Market, potential_buyers_count: int = 0) -> bool:
    """
    Handle failed negotiation.
    Seller might lower price if desperate or market is cold.
    Returns True if listing was modified (e.g. price cut).
    """
    # Simple Logic:
    # If no buyers, cut price.
    # If buyers but failed, maybe cut price a little?

    # Check patience/desperation
    # We can check how long it's been listed? listing['listing_month']

    is_desperate = False
    if hasattr(seller, 'life_pressure') and seller.life_pressure == "urgent":
        is_desperate = True

    price_cut = 0.0

    if potential_buyers_count == 0:
        # No interest: Cut price
        price_cut = 0.05 # 5% cut
        if is_desperate: price_cut = 0.10

    else:
        # Had interest but failed
        # Maybe price too high?
        # Cut smaller
        price_cut = 0.02
        if is_desperate: price_cut = 0.05

    if price_cut > 0:
        old_price = listing['listed_price']
        new_price = old_price * (1 - price_cut)
        listing['listed_price'] = new_price

        # Also adjust min_price?
        listing['min_price'] = listing['min_price'] * (1 - price_cut)

        logger.info(f"Seller {seller.id} lowered price of {listing['property_id']} by {price_cut:.0%} to {new_price:,.0f} after failed negotiation.")
        return True

    return False

def decide_negotiation_format(seller: Agent, buyers: List[Agent], market_hint: str) -> str:
    """
    Decide negotiation format: 'batch' (Blind Auction) or 'flash' (1-on-1).
    """
    # Simple logic:
    # If multiple buyers -> Batch
    # If single buyer -> Flash? Or just Negotiation?
    # Logic from Phase 3:
    if len(buyers) > 1:
        return "batch"
    else:
        return "flexible" # standard negotiation
