
"""
Core Logic for Agent Behavior (LLM Driven)
"""
import json
import random
from typing import Dict, Any, Tuple, List
from models import Agent, Market, AgentStory, AgentPreference
from config.settings import INITIAL_MARKET_CONFIG, MORTGAGE_CONFIG

# --- LLM Integration ---
from utils.llm_client import call_llm, safe_call_llm, safe_call_llm_async

# --- Phase 8: Financial Calculator & New Prompts ---
from services.financial_calculator import FinancialCalculator
from prompts.buyer_prompts import BUYER_PREFERENCE_TEMPLATE
from prompts.seller_prompts import LISTING_STRATEGY_TEMPLATE, PRICE_ADJUSTMENT_TEMPLATE

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

def calculate_financial_limits(agent, market=None, market_trend="STABLE"):
    """
    Sync helper to calculate max_affordable_price and psychological_price.
    Used for rehydration without LLM.
    Returns (real_max_price, psych_price, final_operational_max)
    """
    from mortgage_system import calculate_max_affordable
    
    # Zone Averages
    zone_b_avg = market.get_avg_price("B") if market else 2000000
    
    # Affordability
    existing_payment = getattr(agent, 'monthly_payment', 0)
    real_max_price = calculate_max_affordable(agent.cash, agent.monthly_income, existing_payment)
    
    psych_price = determine_psychological_price(agent, zone_b_avg, market_trend)
    final_operational_max = real_max_price 
    
    return real_max_price, psych_price, final_operational_max


async def generate_buyer_preference(agent, market, current_month, macro_summary, market_trend, db_conn=None, recent_bulletins=None):
    """
    Tier 7.2: Generate buyer preference with Comparative Logic & Market Memory.
    Returns: (BuyerPreference, thought_process_str, context_metrics)
    """
    from services.market_service import MarketService # Avoid circular import if possible, or usually passed in
    from models import BuyerPreference
    from mortgage_system import calculate_max_affordable, calculate_monthly_payment
    
    # 1. Config & Attributes
    risk_free_rate = 0.03 # Default
    if hasattr(market, 'config') and market.config:
         risk_free_rate = market.config.market.get('risk_free_rate', 0.03)

    # Zone Averages
    zone_a_avg = market.get_avg_price("A") if market else 100000
    zone_b_avg = market.get_avg_price("B") if market else 50000
    
    # Affordability
    existing_payment = getattr(agent, 'monthly_payment', 0)
    real_max_price = calculate_max_affordable(agent.cash, agent.monthly_income, existing_payment)
    
    psych_price = determine_psychological_price(agent, zone_b_avg, market_trend)
    final_operational_max = real_max_price 

    # Zone Logic (Simple heuristic for default zone)
    can_afford_zone_a = real_max_price >= zone_a_avg * 0.8  
    can_afford_zone_b = real_max_price >= zone_b_avg * 0.6  
    
    if can_afford_zone_a:
        default_zone = "A" 
    elif can_afford_zone_b:
        default_zone = "B" 
    else:
        default_zone = "B" 
    
    # 2. Market Memory / History Construction
    history_text = "【近期市场走势】\n(暂无历史数据)"
    if recent_bulletins:
        history_lines = []
        for b in recent_bulletins:
            # Format: Month X: Price Y, Vol Z, Trend T
            history_lines.append(f"- 月份{b['month']}: 均价{b['avg_price']:,.0f}, 成交{b['volume']}, 趋势{b['trend']}")
        history_text = "【近期市场走势】\n" + "\n".join(history_lines)
    
    # 3. Financial Calculations (Phase 8)
    # Estimate rental yield for the target zone (Avg Rent / Avg Price)
    # This assumes we have average rent data or can estimate it
    # For now, let's look up a typical rental yield from market props if possible, or mock it
    # We can fetch avg unit price and avg rental price from properties_market if DB passed?
    # Simpler: use properties in market object
    
    target_zone_props = [p for p in market.properties if p['zone'] == default_zone]
    avg_price = zone_a_avg if default_zone == 'A' else zone_b_avg
    avg_rent = 0
    if target_zone_props:
        # Simple avg of rental_price if exists, else estimate
        # Assuming rental_price is populated Phase 7
        total_rent = sum(p.get('rental_price', p['base_value'] * 0.0015) for p in target_zone_props) # Fallback 1.5% yield monthly? No 1.5/12%
        avg_rent = total_rent / len(target_zone_props)
    
    # If no data, use rough 2% annual yield estimate
    if avg_rent == 0:
        avg_rent = avg_price * 0.02 / 12
        
    rental_yield = FinancialCalculator.calculate_rental_yield(avg_price, avg_rent)
    
    # Calculate estimated monthly payment for a max price purchase
    est_loan = real_max_price * 0.7 # Assuming 30% down
    annual_rate = MORTGAGE_CONFIG.get('annual_interest_rate', 0.05)
    est_monthly_payment = calculate_monthly_payment(est_loan, annual_rate, 30) # 30 years
    
    dti = 0
    if agent.monthly_income > 0:
        dti = est_monthly_payment / agent.monthly_income
        
    affordability_warning = ""
    if dti > 0.5:
        affordability_warning = f"警告: 预计月供占收入 {dti:.1%}，压力巨大！"
    
    # 4. Construct Prompt using Template
    prompt = BUYER_PREFERENCE_TEMPLATE.format(
        background=agent.story.background_story,
        investment_style=agent.story.investment_style,
        cash=agent.cash,
        income=agent.monthly_income,
        max_price=real_max_price,
        macro_summary=macro_summary,
        market_trend=market_trend,
        risk_free_rate=risk_free_rate,
        history_text=history_text,
        default_zone=default_zone,
        zone_a_avg=zone_a_avg,
        zone_b_avg=zone_b_avg,
        rental_yield=rental_yield,
        est_monthly_payment=est_monthly_payment,
        dti=dti,
        affordability_warning=affordability_warning
    )
    
    # Prepare Context Metrics for Logging
    context_metrics = {
        "risk_free_rate": risk_free_rate,
        "est_rental_yield": rental_yield,
        "yield_gap": rental_yield - risk_free_rate,
        "est_monthly_payment": est_monthly_payment,
        "dti_ratio": dti,
        "real_max_price": real_max_price
    }
    
    # Call LLM
    from utils.llm_client import safe_call_llm_async
    
    default_data = {
        "target_zone": default_zone,
        "max_price": final_operational_max,
        "min_bedrooms": 1,
        "investment_motivation": "medium",
        "strategy_reason": "Default logic due to error"
    }
    
    data = await safe_call_llm_async(prompt, default_return=default_data, model_type="smart")
    
    # Parse Result
    try:
        # Determine school need from agent story/family
        need_school = agent.story.education_need != "无" or agent.has_children_near_school_age()
        
        # Phase 7.2 Enhancement: Return explicit structure
        pref = BuyerPreference(
            target_zone=data.get("target_zone", default_zone),
            target_price_range=(0, data.get("max_price", final_operational_max)),
            min_bedrooms=data.get("min_bedrooms", 1),
            need_school_district=need_school,
            max_affordable_price=real_max_price,
            psychological_price=psych_price
        )
        pref.max_price = data.get("max_price", final_operational_max)
        
        reason = data.get("strategy_reason", "LLM Decision")
        
        # Return Tuple 3: Pref, Reason, ContextMetrics
        return pref, reason, context_metrics
        
    except Exception as e:
        # logging import might be needed if not in scope
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to parse LLM buyer preference: {e}")
        # Fallback
        # Determine school need from agent story/family (Safe check)
        try:
             need_school = agent.story.education_need != "无" or agent.has_children_near_school_age()
        except:
             need_school = False

        pref = BuyerPreference(
            target_zone=default_zone, 
            target_price_range=(0, final_operational_max), 
            min_bedrooms=1,
            need_school_district=need_school,
            max_affordable_price=real_max_price,
            psychological_price=psych_price
        )
        pref.max_price = final_operational_max
        return pref, "Fallback decision", context_metrics

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

def determine_listing_strategy(agent: Agent, market_price_map: Dict[str, float], market_bulletin: str = "", market_trend: str = "STABLE", config=None) -> tuple[dict, dict]:
    """
    For multi-property owners, decide which properties to sell and the pricing strategy.
    Returns: (DecisionDict, ContextMetrics)
    """
    props_info = []
    total_holding_cost = 0
    
    for p in agent.owned_properties:
        zone = p.get('zone', 'A')
        current_market_value = market_price_map.get(zone, p['base_value'])
        
        # Calculate holding cost
        # Assuming existing mortgage info is stored or estimated
        # Simplified: estimate mortgage based on loan amount? 
        # For now, let's use a standard estimate from FinancialCalculator
        holding_cost = FinancialCalculator.calculate_holding_cost(agent, p, mortgage_payment=0) # Need real mortgage data validation in later phase
        # Actually agent.mortgage_monthly_payment is total. We can amortize? 
        # Let's simple check if property is rented.
        
        total_holding_cost += holding_cost
        
        props_info.append({
            "id": p['property_id'],
            "zone": zone,
            "base_value": p['base_value'],
            "est_market_value": current_market_value,
            "holding_cost": holding_cost
        })

    # Psychological Anchor
    psych_advice = ""
    comp_min_price = 0
    if props_info:
        # Use first property as reference 
        ref_val = props_info[0]['est_market_value']
        psych_val = determine_psychological_price(agent, ref_val, market_trend)
        psych_advice = f"【参考心理价】基于你的风格({agent.story.investment_style})和市场({market_trend})，建议关注 {psych_val:,.0f} 附近的价位。"
        comp_min_price = ref_val * 0.95 # Mock competitor price 5% lower
    
    # Financial Context
    risk_free_rate = 0.03
    if config:
        risk_free_rate = config.market.get('risk_free_rate', 0.03)
        
    total_property_value = sum(p['est_market_value'] for p in props_info)
    potential_bank_interest = total_property_value * risk_free_rate

    # Construct Prompt
    prompt = LISTING_STRATEGY_TEMPLATE.format(
        agent_id=agent.id,
        background=agent.story.background_story,
        investment_style=agent.story.investment_style,
        cash=agent.cash,
        income=agent.monthly_income,
        monthly_payment=getattr(agent, 'mortgage_monthly_payment', 0),
        life_pressure=getattr(agent, 'life_pressure', 'patient'),
        props_info_json=json.dumps(props_info, indent=2, ensure_ascii=False),
        market_bulletin=market_bulletin if market_bulletin else "【市场信息】暂无市场公报",
        psych_advice=psych_advice,
        total_holding_cost=total_holding_cost,
        risk_free_rate=risk_free_rate,
        potential_bank_interest=potential_bank_interest,
        comp_min_price=comp_min_price
    )
    
    # Prepare metrics for logging
    context_metrics = {
        "total_holding_cost": total_holding_cost,
        "potential_bank_interest": potential_bank_interest,
        "comp_min_price": comp_min_price,
        "risk_free_rate": risk_free_rate
    }
    
    # Default: Sell the cheapest one with balanced strategy
    sorted_props = sorted(props_info, key=lambda x: x['base_value'])
    default_resp = {
        "strategy": "B",
        "pricing_coefficient": 1.0,
        "properties_to_sell": [sorted_props[0]['id']] if sorted_props else [],
        "reasoning": "Default balanced strategy"
    }
    
    decision = safe_call_llm(prompt, default_resp)
    return decision, context_metrics

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
) -> tuple[dict, dict]:
    """
    LLM decides whether to adjust price for a property that has been listed for too long.
    Returns: (DecisionDict, ContextMetrics)
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

    # Mock Data for Comp & Holding Cost (Phase 8: To be real DB query)
    # For now, simulate:
    accumulated_holding_cost = current_price * 0.005 * listing_duration # 0.5% per month holding cost
    daily_views = max(0, int(30 - listing_duration * 2)) # Decay views
    comp_min_price = current_price * 0.95 # Competitor is 5% cheaper
    price_diff = current_price - comp_min_price

    prompt = PRICE_ADJUSTMENT_TEMPLATE.format(
        agent_name=agent_name,
        investment_style=investment_style,
        background=background,
        property_id=property_id,
        listing_duration=listing_duration,
        current_price=current_price,
        market_trend=market_trend,
        psych_advice=psych_advice,
        accumulated_holding_cost=accumulated_holding_cost,
        daily_views=daily_views,
        comp_min_price=comp_min_price,
        price_diff=price_diff
    )
    
    context_metrics = {
        "accumulated_holding_cost": accumulated_holding_cost,
        "daily_views": daily_views,
        "comp_min_price": comp_min_price,
        "price_gap": price_diff
    }
    
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
    
    return result, context_metrics

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

async def batched_determine_role_async(
    agents: list[Agent], 
    month: int, 
    market: Market, 
    macro_summary: str = "平稳",
    market_trend: str = "STABLE",
    recent_bulletins: list[str] = None
) -> list[dict]:
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
    
    bulletin_text = "暂无历史数据"
    if recent_bulletins:
        bulletin_text = "\n".join([f"- {b}" for b in recent_bulletins])

    prompt = f"""
    【当前宏观环境】{macro_summary} (市场趋势: {market_trend})
    
    【近期市场动态 (Market Memory)】
    {bulletin_text}
    
    【任务】
    请分析以下Agent列表，根据他们的财务状况、需求、宏观环境和近期市场动态，决定每个人本月的角色 (BUYER, SELLER, OBSERVER)。
    - BUYER: 有购房意愿且有能力。若市场过热(Panic Up)且Agent保守，应谨慎；若Agent激进，可能追涨。
    - SELLER: 有卖房意愿且持有房产。若市场下跌，可能恐慌抛售；若上涨，可能止盈。
    - OBSERVER: 暂时观望。

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
        market: Agent对象
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

    return {"role": "OBSERVER", "reasoning": "Placeholder"}

def should_agent_exit_market(agent: Agent, market: Market, duration_months: int) -> Tuple[bool, str]:
    """
    Determine if an active agent (Buyer/Seller) should exit due to fatigue or market conditions.
    Returns: (should_exit, reason)
    """
    # Base probability increases with duration
    base_exit_prob = min(0.1 * duration_months, 0.8)
    
    # Check patience based on "life pressure"
    pressure = getattr(agent, 'life_pressure', 'patient')
    if pressure == 'urgent' and duration_months > 2:
        return True, "Urgent need unmet, giving up"
    if pressure == 'anxious' and duration_months > 4:
        return True, "Anxiety overwhelmed patience"
        
    # Random roll
    if random.random() < base_exit_prob:
        return True, f"Market fatigue after {duration_months} months"
        
    return False, ""
