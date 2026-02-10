"""
Core Logic for Agent Behavior (LLM Driven)
"""
import json
import random
from typing import Dict, Any, Tuple, List
from models import Agent, Market, AgentStory, AgentPreference
from config.settings import INITIAL_MARKET_CONFIG

# --- LLM Integration ---
# --- LLM Integration ---
from utils.llm_client import call_llm, safe_call_llm, safe_call_llm_async

# --- 1. Story Generation ---

def generate_agent_story(agent: Agent, config=None, occupation_hint: str = None) -> AgentStory:
    """
    Generate background story and structured attributes for a new agent.
    """
    # 1. Investment Style (Personality) Selection
    weights = {'balanced': 0.4} # default
    if config:
        weights = config.negotiation.get('personality_weights', {
            'aggressive': 0.30, 'conservative': 0.30, 
            'balanced': 0.40
        })
    
    styles = list(weights.keys())
    probs = list(weights.values())
    investment_style = random.choices(styles, weights=probs, k=1)[0]

    # Logic Consistency Fix (Tier 6)
    prop_count = len(agent.owned_properties)
    has_properties = prop_count > 0
    total_asset_est = agent.cash + sum(p['current_valuation'] for p in agent.owned_properties) if has_properties else agent.cash
    
    occ_str = f"建议职业: {occupation_hint}" if occupation_hint else ""

    prompt = f"""
    为这个Agent生成背景故事：
    【基础信息】
    年龄：{agent.age}
    婚姻：{agent.marital_status}
    月收入：{agent.monthly_income:,.0f}
    现金：{agent.cash:,.0f}
    {occ_str}
    【关键资产】
    持有房产数量：{prop_count} 套
    总资产预估：{total_asset_est:,.0f}
    
    【强制约束】
    1. 若持有房产({prop_count} > 0)，严禁在 story/housing_need 中描述为“无房刚需”、“首次置业”或“租房居住”。必须描述为“改善型需求”或“投资客”。
    2. 若现金充裕(>100w)且有房，严禁描述为“积蓄不多”。
    3. 住房需求(housing_need)的可选值：刚需(仅限无房), 改善(有房但小), 投资(有钱有房), 学区(有娃).
    
    请包含：occupation(职业), career_outlook(职业前景), family_plan(家庭规划), education_need(教育需求), housing_need(住房需求), selling_motivation(卖房动机), background_story(3-5句故事).
    
    另外，请为该人物设定一个投资风格 (investment_style)，可选值: 
    - aggressive (激进): 愿意承担风险，追求高回报
    - conservative (保守): 厌恶风险，追求本金安全
    - balanced (平衡): 权衡风险与收益
    (建议风格: {investment_style})
 
    输出JSON格式。
    """
    
    default_story = AgentStory(
        occupation=occupation_hint if occupation_hint else "普通职员",
        career_outlook="稳定",
        family_plan="暂无",
        education_need="无",
        housing_need="刚需",
        selling_motivation="无",
        background_story="普通工薪阶层。",
        investment_style="balanced"
    )
    
    result = safe_call_llm(prompt, default_story, system_prompt="你是小说家，擅长构建人物小传。", model_type="fast")
    
    # If result is dict (success), map to AgentStory
    if isinstance(result, dict):
        return AgentStory(
            occupation=result.get("occupation", "自由职业"),
            career_outlook=result.get("career_outlook", "未知"),
            family_plan=result.get("family_plan", "未知"),
            education_need=result.get("education_need", "无"),
            housing_need=result.get("housing_need", "刚需"),
            selling_motivation=result.get("selling_motivation", "无"),
            background_story=result.get("background_story", "平凡的一生。"),
            investment_style=result.get("investment_style", investment_style)
        )
    return result

def determine_psychological_price(agent: Agent, market_avg_price: float, market_trend: str) -> float:
    """
    Calculate psychological price based on agent personality and market trend.
    Returns the price/sqm or total price depending on input market_avg_price.
    Assumes market_avg_price is TOTAL price for a typical unit in target zone.
    """
    style = agent.story.investment_style
    
    # Coefficients
    #          Bear    Bull    Stable
    # Aggr     0.80    1.10    1.02
    # Cons     0.70    1.05    0.98
    # Bal      0.90    1.02    1.00
    
    coeffs = {
        "aggressive":   {"UP": 1.10, "DOWN": 0.80, "PANIC": 0.70, "STABLE": 1.02},
        "conservative": {"UP": 1.05, "DOWN": 0.70, "PANIC": 0.60, "STABLE": 0.95},
        "balanced":     {"UP": 1.02, "DOWN": 0.90, "PANIC": 0.80, "STABLE": 1.00}
    }
    
    # Map trend string if needed (assuming "UP", "DOWN", "STABLE", "PANIC")
    # market_trend usually comes from MarketBulletin or MarketService
    trend = market_trend.upper()
    if trend not in coeffs["balanced"]:
        trend = "STABLE"
        
    coeff = coeffs.get(style, coeffs["balanced"]).get(trend, 1.0)
    
    return market_avg_price * coeff

def generate_buyer_preference(agent: Agent, market: Market = None, market_trend: str = "STABLE") -> AgentPreference:
    """
    Generate buyer preferences based on agent story and financial status.
    Updated for Tier 6: Includes Psychological Price & Max Affordable.
    
    🔧 FIX: 
    1. Use real_max_price as operational max (not psych_price which is too conservative)
    2. Smart zone allocation based on affordability
    """
    from mortgage_system import calculate_max_affordable
    
    # 1. Financial Limit (Affordability)
    existing_payment = getattr(agent, 'monthly_payment', 0)
    real_max_price = calculate_max_affordable(agent.cash, agent.monthly_income, existing_payment)
    
    # 2. Psychological Limit (for reference, but NOT as hard constraint)
    # Get Market Context (Zone B avg as baseline for entry)
    zone_a_avg = 5000000  # Default 500w Zone A
    zone_b_avg = 2000000  # Default 200w Zone B
    
    if market:
         try:
             zone_a_avg = market.get_avg_price("A") or 5000000
             zone_b_avg = market.get_avg_price("B") or 2000000
         except:
             pass
             
    psych_price = determine_psychological_price(agent, zone_b_avg, market_trend)
    
    # 3. 🔧 FIX: Operational Max Price = real_max_price (not min with psych)
    # Psychological price is a preference indicator, not a hard financial limit
    # Buyers should use their ACTUAL affordability, not self-imposed lower limits
    final_operational_max = real_max_price  # Changed from min(real_max_price, psych_price)
    
    # 4. 🔧 FIX: Smart Zone Allocation based on affordability
    # Instead of letting LLM always choose Zone A, make a data-driven decision
    can_afford_zone_a = real_max_price >= zone_a_avg * 0.8  # Need 80% of avg to consider
    can_afford_zone_b = real_max_price >= zone_b_avg * 0.6  # More lenient for entry-level
    
    # Determine default zone based on affordability
    if can_afford_zone_a:
        default_zone = "A"  # Can afford premium zone
    elif can_afford_zone_b:
        default_zone = "B"  # Can only afford entry zone
    else:
        default_zone = "B"  # Fallback to cheaper zone
    
    # Log for debugging
    import logging
    logger = logging.getLogger(__name__)
    logger.debug(f"Agent {agent.id}: max_affordable={real_max_price:,.0f}, zone_a_threshold={zone_a_avg*0.8:,.0f}, "
                 f"zone_b_threshold={zone_b_avg*0.6:,.0f}, selected_zone={default_zone}")
    
    prompt = f"""
    根据你的背景，设定购房偏好：
    【背景】{agent.story.background_story}
    【性格】{agent.story.investment_style}
    【财务】现金:{agent.cash:,.0f}, 购买力上限:{real_max_price:,.0f}
    【市场】趋势:{market_trend}
    【建议区域】基于你的购买力，系统建议你关注{default_zone}区
       (A区均价约{zone_a_avg:,.0f}，B区均价约{zone_b_avg:,.0f})
    
    输出JSON：
    {{"target_zone":"{default_zone}", "min_bedrooms":...}}
    """
    
    default_pref = AgentPreference(
        target_zone=default_zone,  # Use calculated zone, not hardcoded "B"
        max_price=final_operational_max,
        min_bedrooms=1,
        need_school_district=False,
        max_affordable_price=real_max_price,
        psychological_price=psych_price
    )
    
    result = safe_call_llm(prompt, default_pref, model_type="fast")
    
    # Map dictionary result
    if isinstance(result, dict):
        # Sanitize Zone - BUT respect system recommendation for affordability
        raw_zone = result.get("target_zone", default_zone)
        if raw_zone not in ["A", "B"]:
            raw_zone = default_zone
        
        # 🔧 FIX: Override zone if buyer tries to select A but can't afford it
        if raw_zone == "A" and not can_afford_zone_a and can_afford_zone_b:
            logger.debug(f"Agent {agent.id}: Overriding zone A->B (can't afford A)")
            raw_zone = "B"
            
        return AgentPreference(
            target_zone=raw_zone,
            max_price=final_operational_max, # Hard constraint override
            min_bedrooms=result.get("min_bedrooms", 1),
            need_school_district=result.get("need_school_district", False),
            max_affordable_price=real_max_price,
            psychological_price=psych_price
        )
    return result

def generate_real_thought(agent: Agent, trigger: str, market: Market) -> str:
    """
    Generate a human-readable thought process.
    """
    # Ensure market prices are accessible
    try:
        zone_a_price = market.get_avg_price("A")
        zone_b_price = market.get_avg_price("B")
    except:
        zone_a_price = 0
        zone_b_price = 0

    prompt = f"""
    你是Agent {agent.id}。
    【背景】{agent.story.background_story}
    【触发】{trigger}
    【市场】A区均价{zone_a_price:,.0f}，B区均价{zone_b_price:,.0f}
    
    请思考你的决策（简短一段话）：
    """
    # For now, return a formatted string. Real LLM would yield varied text.
    return f"我是{agent.story.occupation}，看到{trigger}，考虑到当前A区均价{zone_a_price/10000:.0f}万，我决定..."

# --- 2. Event System ---

# --- 2. Event System ---

def select_monthly_event(agent: Agent, month: int, config=None) -> dict:
    """
    Select a life event for the agent for this month.
    """
    event_pool = []
    if config:
        event_pool = config.life_events.get('pool', [])
    
    if not event_pool:
        # Fallback or return None
        return {"event": None, "reasoning": "No event pool or config"}
        
    prompt = f"""
    Agent {agent.id} 背景：{agent.story.background_story}
    可能发生的事件：{[e["event"] for e in event_pool]}
    
    第{month}月最可能发生什么？（无事件返回null）
    输出JSON：{{"event": "..." 或 null, "reasoning": "..."}}
    """
    return safe_call_llm(prompt, {"event": None, "reasoning": "No event"}, model_type="fast")

def apply_event_effects(agent: Agent, event_data: dict, config=None):
    """
    Apply the financial effects of an event.
    """
    event_name = event_data.get("event")
    if not event_name:
        return
        
    event_pool = []
    if config:
        event_pool = config.life_events.get('pool', [])
    
    event_config = next((e for e in event_pool if e["event"] == event_name), None)
    if event_config:
        cash_change_pct = event_config["cash_change"]
        agent.cash *= (1 + cash_change_pct)
        agent.set_life_event(0, event_name) # Using 0 as current month placeholder or pass actual month
        # print(f"Agent {agent.id} experienced {event_name}, cash changed by {cash_change_pct*100}%")

def determine_listing_strategy(agent: Agent, market_price_map: Dict[str, float], market_bulletin: str = "", market_trend: str = "STABLE") -> dict:
    """
    For multi-property owners, decide which properties to sell and the pricing strategy.
    Uses market bulletin + strategy menu (A+C architecture).
    """
    props_info = []
    for p in agent.owned_properties:
        zone = p.get('zone', 'A')
        current_market_value = market_price_map.get(zone, p['base_value'])
        props_info.append({
            "id": p['property_id'],
            "zone": zone,
            "base_value": p['base_value'],
            "est_market_value": current_market_value
        })

    # Psychological Anchor
    psych_advice = ""
    if props_info:
        # Use first property as reference for simplicity or general sentiment
        ref_val = props_info[0]['est_market_value']
        psych_val = determine_psychological_price(agent, ref_val, market_trend)
        psych_advice = f"【参考心理价】基于你的风格({agent.story.investment_style})和市场({market_trend})，建议关注 {psych_val:,.0f} 附近的价位。"

    prompt = f"""
你是Agent {agent.id}，卖家。
【你的背景】{agent.story.background_story}
【你的性格】{agent.story.investment_style}
【财务状况】现金: {agent.cash:,.0f}, 月收入: {agent.monthly_income:,.0f}
【生活压力】{getattr(agent, 'life_pressure', 'patient')}
【名下房产】
{json.dumps(props_info, indent=2, ensure_ascii=False)}

{market_bulletin if market_bulletin else "【市场信息】暂无市场公报"}
{psych_advice}

━━━━━━━━━━━━━━━━━━━━━━━
请基于市场公报，选择你的定价策略:

A. 【激进挂高/牛市追涨】挂牌价 = 估值 × [1.05 ~ 1.30]，请自选系数
   适用于: 市场上涨、不急用钱、看好后市 (牛市可挂更高)

B. 【随行就市】挂牌价 = 市场均价 × [0.98 ~ 1.05]，请自选系数
   适用于: 市场平稳、正常置换需求

C. 【以价换量/熊市止损】挂牌价 = 估值 × [0.80 ~ 0.97]，请自选系数
   适用于: 市场下行、急需现金、恐慌避险 (熊市可大幅降价)
   (如: 0.85 表示85折甩卖)

D. 【暂不挂牌】本月观望，等待更好时机
   适用于: 市场恐慌、惜售心理、看好反弹
━━━━━━━━━━━━━━━━━━━━━━━

输出JSON:
{{
    "strategy": "A/B/C/D",
    "pricing_coefficient": 1.15,  # 必填！根据策略选择区间内的系数
    "properties_to_sell": [property_id, ...],
    "reasoning": "你的决策理由"
}}
"""
    
    # Default: Sell the cheapest one with balanced strategy
    sorted_props = sorted(props_info, key=lambda x: x['base_value'])
    default_resp = {
        "strategy": "B",
        "pricing_coefficient": 1.0,
        "properties_to_sell": [sorted_props[0]['id']] if sorted_props else [],
        "reasoning": "Default balanced strategy"
    }
    
    return safe_call_llm(prompt, default_resp)

def decide_negotiation_format(seller: Agent, interested_buyers: List[Agent], market_info: str) -> str:
    """
    Decide the negotiation format based on seller's situation and market interest.
    Options: 'classic', 'batch_bidding', 'flash_deal'
    """
    buyer_count = len(interested_buyers)
    if buyer_count == 0:
        return "classic"
        
    prompt = f"""
    你是卖家 {seller.id}。
    【背景】{seller.story.background_story}
    【性格】{seller.story.investment_style}
    【市场环境】{market_info}
    【当前状况】有 {buyer_count} 位买家对你的房产感兴趣。
    
    请选择谈判方式：
    1. CLASSIC: 传统谈判 (一个个谈，稳妥)
    2. BATCH: 盲拍/批量竞价 (仅当买家>1时可选，适合市场火热，价高者得)
    3. FLASH: 闪电成交 (一口价甩卖，适合急需用钱或市场冷清，需降价换速度)
    
    输出JSON: {{"format": "CLASSIC"|"BATCH"|"FLASH", "reasoning": "..."}}
    """
    # Default fallback: CLASSIC
    default_resp = {"format": "CLASSIC", "reasoning": "Default safe choice"}
    
    result = safe_call_llm(prompt, default_resp)
    fmt = result.get("format", "CLASSIC").upper()
    
    # Enforce logic: Batch requires > 1 buyer
    if fmt == "BATCH" and buyer_count < 2:
        return "CLASSIC"
        
    if fmt not in ["CLASSIC", "BATCH", "FLASH"]:
        return "CLASSIC"
        
    return fmt


async def decide_price_adjustment(
    agent_id: int,
    agent_name: str,
    investment_style: str,
    property_id: int,
    current_price: float,
    listing_duration: int,
    market_trend: str,
    db_conn
) -> dict:
    """
    LLM decides whether to adjust price for a property that has been listed for too long.
    Tier 3: Part A - Replaces hardcoded 5% reduction.
    
    Args:
        agent_id: Agent ID
        agent_name: Agent name
        investment_style: aggressive/conservative/balanced
        property_id: Property ID
        current_price: Current listed price
        listing_duration: How many months it's been listed
        market_trend: UP/DOWN/STABLE/PANIC
        db_conn: Database connection
        
    Returns:
        {
            "action": "A"/"B"/"C"/"D",  # A=维持 B=小降 C=大降 D=撤牌
            "new_price": float,
            "coefficient": float,
            "reason": str
        }
    """
    
    # Fetch agent background
    cursor = db_conn.cursor()
    cursor.execute("SELECT background_story FROM agents_static WHERE agent_id = ?", (agent_id,))
    row = cursor.fetchone()
    background = row[0] if row else "普通投资者"
    
    # Calculate Psych Price
    mock_agent = Agent(id=agent_id)
    mock_agent.story = AgentStory(investment_style=investment_style)
    psych_price = determine_psychological_price(
        mock_agent, # Mock agent wrapper for function
        current_price, 
        market_trend
    )
    psych_advice = f"【参考建议】心理价位约 {psych_price:,.0f} (基于风格{investment_style})"

    prompt = f"""
你是 {agent_name}，投资风格：{investment_style}。
背景：{background}

【当前处境】
你的房产（ID: {property_id}）已挂牌 {listing_duration} 个月未成交。
当前挂牌价：¥{current_price:,.0f}
市场趋势：{market_trend}
{psych_advice}

【决策选项】
A. 维持原价 (patient, 看好后市反弹)
B. 小幅降价 (系数 0.95~0.98，适度灵活)
C. 大幅降价/止损 (系数 0.80~0.92，急于脱手)
D. 撤牌观望 (严重悲观，等待时机)

请根据你的性格和市场状况做出决策。

返回 JSON:
{{
    "action": "A",  # 选择 A/B/C/D
    "coefficient": 1.0,  # A=1.0, B=0.95~0.98, C=0.80~0.92, D=1.0
    "reason": "简述原因（一句话）"
}}
"""
    
    default_return = {
        "action": "B",
        "coefficient": 0.96,
        "reason": "默认小幅降价"
    }
    
    result = await safe_call_llm_async(
        prompt,
        default_return,
        system_prompt="你是房产投资顾问，根据性格和市场做出理性决策。",
        model_type="smart"
    )
    
    # Calculate new price
    coefficient = result.get("coefficient", 0.96)
    new_price = current_price * coefficient
    
    result["new_price"] = new_price
    
    return result

# --- 3. Role Determination ---

from enum import Enum
class AgentRole(Enum):
    BUYER = "buyer"
    SELLER = "seller"
    BUYER_SELLER = "buyer_seller"
    OBSERVER = "observer"

def determine_role(agent: Agent, month: int, market: Market) -> Tuple[AgentRole, str]:
    """
    Determine the agent's role (Buyer/Seller/Observer) for the month.
    """
    # 1. Context Hints (No Hard Constraints)
    hints = []
    if agent.cash < agent.monthly_income * 2 and agent.owned_properties:
        hints.append("【资金预警】现金流紧张（不足2个月），请认真考虑是否需要变现资产。")
    if agent.cash > agent.monthly_income * 60 and not agent.owned_properties:
        hints.append("【存款充裕】存款超过5年收入，长期持有现金可能贬值，建议考虑置业。")
        
    hint_str = "\n".join(hints)
        
    # 2. LLM Decision
    prompt = f"""
    你是Agent {agent.id}。
    【背景】{agent.story.background_story}
    【本月事件】{agent.monthly_event}
    
    {hint_str}
    
    判断角色（BUYER/SELLER/OBSERVER）：
    输出JSON：{{"role": "...", "reasoning": "..."}}
    """
    
    result = safe_call_llm(prompt, {"role": "OBSERVER", "reasoning": "Default wait"})
    role_str = result.get("role", "OBSERVER").upper()
    role_map = {
        "BUYER": AgentRole.BUYER,
        "SELLER": AgentRole.SELLER,
        "OBSERVER": AgentRole.OBSERVER
    }
    
    role = role_map.get(role_str, AgentRole.OBSERVER)
    
    # Enforce Hard Constraint: No property = Cannot be SELLER
    if role == AgentRole.SELLER and not agent.owned_properties:
        role = AgentRole.OBSERVER
        result["reasoning"] = (result.get("reasoning", "") + " [System Corrected: No property to sell]").strip()
    
    return role, result.get("reasoning", "")

# --- 4. Batch Activation Logic (Million Agent Scale) ---

def calculate_activation_probability(agent: Agent) -> float:
    """
    Calculate the probability (0.0 - 1.0) that an agent becomes active (Buyer/Seller) this month.
    """
    base_prob = 0.003 # 0.3% base rate
    
    # Weights configuration
    weights = {
        "has_school_age_child": 0.15,
        "recently_married": 0.12,
        "high_income_growth": 0.08,
        "multi_property_holder": 0.10,
        "high_wealth_no_property": 0.20,
        "low_cash_poor": -0.5 # Penalty
    }
    
    prob_score = base_prob
    
    # 1. School Age Child
    if agent.has_children_near_school_age():
        prob_score += weights["has_school_age_child"]
        
    # 2. Marriage (Simplified: if married and young-ish)
    if agent.marital_status == "married" and 25 <= agent.age <= 35:
        prob_score += weights["recently_married"]
        
    # 3. Income/Wealth Status
    if agent.monthly_income > 50000: # High income
        prob_score += weights["high_income_growth"]
        
    if len(agent.owned_properties) > 1:
        prob_score += weights["multi_property_holder"]
        
    if agent.cash > 2000000 and not agent.owned_properties:
        prob_score += weights["high_wealth_no_property"]
        
    if agent.cash < 50000:
        prob_score += weights["low_cash_poor"]
        
    return max(0.0, min(1.0, prob_score))

# --- Constant System Prompt for Caching ---
BATCH_ROLE_SYSTEM_PROMPT = """你是一个房地产市场模拟引擎。
【任务】判断Agent本月是否产生买卖房产需求。
【规则】
1. 默认角色为 OBSERVER (无操作)
2. 角色定义:
   - BUYER: 刚需或投资买入
   - SELLER: 变现或置换卖出
   - BUYER_SELLER: 置换需求 (既买又卖)
3. **重要限制**: 
   - 只有持有房产 (props > 0) 才能成为 SELLER 或 BUYER_SELLER。
   - 现金不足 (cash < 50w) 且无房产者只能是 OBSERVER。
   - **推理约束**: 若无房产(props=0)，严禁在 reasoning 中虚构“卖掉名下房产”/“卖老破小”。资金来源必须描述为“卖掉外省老家房产”或“父母资助”。
4. 输出JSON列表，包含所有产生变化的Agent。
5. 每个条目包含：
   - id
   - role (BUYER/SELLER/BUYER_SELLER)
   - trigger (触发原因)
   - life_pressure: "urgent"(迫切), "patient"(耐心), "opportunistic"(投机)
   - price_expectation: 浮点数 (1.0-1.2)
   
输出示例：
[
    {"id": 101, "role": "BUYER", "trigger": "婚房刚需", "life_pressure": "urgent", "price_expectation": 1.1},
    {"id": 102, "role": "SELLER", "trigger": "资金周转", "life_pressure": "urgent", "price_expectation": 0.95}
]"""

def batched_determine_role(agents: list[Agent], month: int, market: Market, macro_summary: str = "平稳") -> list[dict]:
    """
    Batch process agents to determine roles using a single LLM call per batch.
    """
    if not agents:
        return []

    # Construct Batch Data
    agent_summaries = []
    for a in agents:
        summary = {
            "id": a.id,
            "age": a.age,
            "income": a.monthly_income,
            "cash": a.cash,
            "props": len(a.owned_properties),
            "background": a.story.background_story[:50] + "...",
            "need": a.story.housing_need,
            "style": a.story.investment_style
        }
        agent_summaries.append(summary)

    # Dynamic part follows static system prompt
    prompt = f"""
    【当前宏观环境】{macro_summary}
    
    【待处理Agent列表】({len(agents)}人):
    {json.dumps(agent_summaries, ensure_ascii=False)}
    """
    
    default_response = []
    
    # Use global system prompt for caching
    response = safe_call_llm(prompt, default_response, system_prompt=BATCH_ROLE_SYSTEM_PROMPT)
    
    if not isinstance(response, list):
        return []
        
    return response

async def batched_determine_role_async(agents: list[Agent], month: int, market: Market, macro_summary: str = "平稳") -> list[dict]:
    """
    Async Batch process agents to determine roles. Optimizes prompt caching.
    """
    if not agents:
        return []

    # Construct Batch Data
    agent_summaries = []
    for a in agents:
        summary = {
            "id": a.id,
            "age": a.age,
            "income": a.monthly_income,
            "cash": a.cash,
            "props": len(a.owned_properties),
            "background": a.story.background_story[:50] + "...",
            "need": a.story.housing_need,
            "style": a.story.investment_style
        }
        agent_summaries.append(summary)

    prompt = f"""
    【当前宏观环境】{macro_summary}
    
    【任务】
    请分析以下Agent列表，根据他们的财务状况、需求和宏观环境，决定每个人本月的角色 (BUYER, SELLER, OBSERVER)。
    - BUYER: 有购房意愿且有能力
    - SELLER: 有卖房意愿且持有房产
    - OBSERVER: 暂时观望

    【重要约束】
    1. 若Agent无房产(props=0)，严禁在 reasoning 中虚构“卖掉郊区房产”或“卖掉名下房产”等理由。若需描述资金来源，必须描述为“卖掉外省老家房产”或“父母资助”。
    2. 无房产者不可成为 SELLER。

    【输出要求】
    请输出严格的JSON列表格式，包含每个Agent的决策：
    [
      {{"id": 123, "role": "BUYER", "trigger": "life_event", "reason": "...", "life_pressure": "calm", "price_expectation": 1.0}}
    ]

    【待处理Agent列表】({len(agents)}人):
    {json.dumps(agent_summaries, ensure_ascii=False)}
    """
    
    default_response = []
    
    # Use global system prompt for caching
    response = await safe_call_llm_async(prompt, default_response, system_prompt=BATCH_ROLE_SYSTEM_PROMPT)
    
    if not isinstance(response, list):
        return []
        
    return response


# --- 5. Open Role Evaluation (LLM-Driven Free Strategy) ---

def open_role_evaluation(agent: Agent, month: int, market: Market, history_context: str = "") -> Dict:
    """
    开放式角色评估 - 让LLM自由决定Agent本月策略
    
    Args:
        agent: Agent对象
        month: 当前月份
        market: 市场对象
        history_context: Agent历史行为记录（用于保持一致性）
    
    Returns:
        dict: {"role": str, "action_description": str, "target_zone": str|None, 
               "price_expectation": float|None, "urgency": float, "reasoning": str}
    """
    from mortgage_system import calculate_max_affordable
    
    # 计算真实购买力
    existing_payment = getattr(agent, 'monthly_payment', 0)
    max_affordable = calculate_max_affordable(agent.cash, agent.monthly_income, existing_payment)
    
    # 获取市场状态
    properties = getattr(market, 'properties', [])
    supply = len([p for p in properties if p.get('status') == 'for_sale'])
    total_props = len(properties)
    demand_estimate = max(1, int(total_props * 0.08))  # 假设8%人口有购房意愿
    
    if supply > demand_estimate * 1.2:
        supply_demand_desc = "供过于求（买方市场）"
    elif supply < demand_estimate * 0.8:
        supply_demand_desc = "供不应求（卖方市场）"
    else:
        supply_demand_desc = "供需平衡"
    
    # 持有房产信息
    owned_info = ""
    if agent.owned_properties:
        owned_list = []
        for p in agent.owned_properties[:3]:
            zone = p.get('zone', '?')
            ptype = p.get('property_type', '住宅')[:6]
            area = p.get('building_area', 0)
            value = p.get('base_value', 0)
            status = p.get('status', 'off_market')
            owned_list.append(f"  - {zone}区 {ptype} {area:.0f}㎡ 估值¥{value:,.0f} [{status}]")
        owned_info = "\n".join(owned_list)
        if len(agent.owned_properties) > 3:
            owned_info += f"\n  ...共{len(agent.owned_properties)}套"
    else:
        owned_info = "  无"
    
    prompt = f"""
你是 {agent.name}，{agent.age}岁，{agent.story.occupation}。
【背景故事】{agent.story.background_story}

【当前是第 {month} 月】

【你的财务状况】
- 现金: ¥{agent.cash:,.0f}
- 月收入: ¥{agent.monthly_income:,.0f}
- 购买力上限(含贷款): ¥{max_affordable:,.0f}
- 月供支出: ¥{existing_payment:,.0f}
- 持有房产:
{owned_info}

【市场环境】
- 供需状态: {supply_demand_desc} (在售{supply}套)
- 你的住房需求: {agent.story.housing_need or "无特殊需求"}

【你最近3个月的行为记录】
{history_context if history_context else "无历史记录（这是你第一次参与市场）"}

---
现在，请自由思考并决定你这个月的策略。你可以：
- 买房（如果你需要且买得起）
- 卖房（如果你持有房产且有卖房理由）
- 观望（如果时机不对或条件不满足）
- 调整策略（如降价、换目标区域等）

请输出JSON格式：
{{
  "role": "BUYER" 或 "SELLER" 或 "OBSERVER",
  "action_description": "你打算做什么（自由描述）",
  "target_zone": "A" 或 "B" 或 null,
  "price_expectation": 你愿意出/接受的价格(数字) 或 null,
  "urgency": 0.0-1.0 之间的紧迫程度,
  "reasoning": "你的完整思考过程（至少3句话）"
}}
"""
    
    default = {
        "role": "OBSERVER",
        "action_description": "继续观望",
        "target_zone": None,
        "price_expectation": None,
        "urgency": 0.3,
        "reasoning": "LLM调用失败，默认观望"
    }
    
    result = safe_call_llm(prompt, default, system_prompt="你是一个有独立思想的房产市场参与者，请根据自身情况做出理性决策。")
    
    # 确保返回的是字典
    if isinstance(result, dict):
        # 验证: 如果没有房产不能成为SELLER
        role = str(result.get('role', 'OBSERVER')).upper()
        if role == 'SELLER' and not agent.owned_properties:
            result['role'] = 'OBSERVER'
            result['action_description'] = '没有房产可卖，继续观望'
            result['reasoning'] = '虽然想卖房，但实际上没有持有任何房产。'
        return result
    
    return default

# --- 6. Helper Functions for Context Building (Phase 6) ---

def build_macro_context(month: int, config) -> str:
    """构建宏观环境上下文，注入到所有LLM Prompt"""
    if not config:
        return "【宏观环境】暂无数据"
        
    macro_cfg = config.macro_environment
    override = macro_cfg.get('override_mode')
    
    if override:
        sentiment = override
    else:
        schedule = macro_cfg.get('schedule', {})
        norm_month = (month - 1) % 12 + 1
        sentiment = schedule.get(norm_month, 'stable')
    
    params = macro_cfg.get('parameters', {}).get(sentiment, {})
    description = params.get('llm_description', params.get('description', '市场平稳'))
    price_exp = params.get('price_expectation', 0)
    
    return f"""
【当前宏观环境】{sentiment.upper()}
- 描述: {description}
- 市场预期: 预计房价{'上涨' if price_exp > 0 else '下跌' if price_exp < 0 else '波动'} {abs(price_exp)*100:.1f}%
"""

def build_agent_context(agent: Agent, config) -> str:
    """构建 Agent 个人处境上下文"""
    if not config:
        return ""
        
    hints = config.decision_factors.get('activation', {}).get('context_hints', {})
    context_lines = []
    
    if agent.has_children_near_school_age():
        context_lines.append(f"- {hints.get('has_school_age_child', '有学龄儿童')}")
    if agent.marital_status == 'married' and 25 <= agent.age <= 35:
        context_lines.append(f"- {hints.get('recently_married', '新婚家庭')}")
    if len(agent.owned_properties) > 1:
        context_lines.append(f"- {hints.get('multi_property_holder', '多套房持有者')}")
    if agent.cash > 2000000 and not agent.owned_properties:
        context_lines.append(f"- {hints.get('high_wealth_no_property', '高净值刚需')}")
        
    return "【你的特殊处境】\n" + "\n".join(context_lines) if context_lines else ""


# --- P1: LLM-Driven Exit Decision ---

def should_agent_exit_market(agent, market, months_waiting: int) -> Tuple[bool, str]:
    """
    Ask LLM if an agent should exit the market after waiting for months_waiting.
    Replaces hardcoded 3-month timeout with intelligent decision-making.
    
    Args:
        agent: Agent object with background_story, life_pressure, role
        market: Market object for getting market condition hints
        months_waiting: How many months the agent has been waiting
    
    Returns:
        (should_exit: bool, reason: str)
    """
    # Get market condition hint
    market_hint = "市场平稳"
    try:
        if hasattr(market, 'get_market_condition'):
            condition = market.get_market_condition()
            market_hint = {
                'hot': '卖方市场，一房难求',
                'balanced': '市场平稳',
                'cold': '买方市场，供过于求'
            }.get(condition, '市场平稳')
    except:
        pass
    
    role_desc = {
        'BUYER': '买家',
        'SELLER': '卖家',
        'BUYER_SELLER': '换房者（既是买家也是卖家）'
    }.get(agent.role, '参与者')
    
    prompt = f"""
你是 {agent.name}，{role_desc}。

【背景信息】
- 你的故事: {agent.background_story if hasattr(agent, 'background_story') else '普通购房者'}
- 当前压力状态: {agent.life_pressure if hasattr(agent, 'life_pressure') else 'patient'}
- 市场状况: {market_hint}
- 你已在市场等待了 {months_waiting} 个月

【决策任务】
请根据你的性格、处境和市场情况，决定是否继续在市场等待，还是暂时退出观望。

输出 JSON 格式:
{{
    "decision": "STAY" 或 "EXIT",
    "reason": "决策理由（1-2句话）"
}}

**提示**:
- 如果你很急迫（urgent），可能在2-3月后就退出
- 如果你很有耐心（patient），可能愿意等待6个月甚至更久
- 如果市场对你不利（买方市场但你是卖家），可能更快退出
- 如果你的背景故事表明有明确时间压力（如孩子要上学），要考虑时间成本
"""
    
    try:
        response = safe_call_llm(prompt, default_return={"decision": "STAY", "reason": "LLM Error"})
        
        # Parse response
        if isinstance(response, dict):
            decision = response.get('decision', 'STAY').upper()
            reason = response.get('reason', 'LLM决策')
        else:
            # Try to parse JSON from string
            try:
                data = json.loads(response)
                decision = data.get('decision', 'STAY').upper()
                reason = data.get('reason', 'LLM决策')
            except:
                # Fallback: simple text parsing
                if 'EXIT' in response or '退出' in response:
                    decision = 'EXIT'
                    reason = '等待时间过长，暂时退出观望'
                else:
                    decision = 'STAY'
                    reason = '继续等待合适机会'
        
        should_exit = (decision == 'EXIT')
        return should_exit, reason
        
    except Exception as e:
        # Fallback to heuristic if LLM fails
        print(f"⚠️ LLM exit decision failed for agent {agent.id}: {e}")
        
        # Simple heuristic: very urgent agents exit after 2 months, patient after 6
        if agent.life_pressure == 'urgent' and months_waiting > 2:
            return True, "生活压力大，暂时退出观望"
        elif agent.life_pressure == 'patient' and months_waiting > 6:
            return True, "等待时间过长，暂时退出观望"
        elif months_waiting > 4:
            return True, "等待超过4个月，暂时退出观望"
        else:
            return False, "继续等待"
