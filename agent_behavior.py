"""
Core Logic for Agent Behavior (LLM Driven)
"""
import json
import random
from typing import Dict, Any, Tuple
from models import Agent, Market, AgentStory, AgentPreference
from config.settings import LIFE_EVENT_POOL, INITIAL_MARKET_CONFIG

# --- LLM Integration ---
from utils.llm_client import call_llm, safe_call_llm

# --- 1. Story Generation ---

def generate_agent_story(agent: Agent, config=None) -> AgentStory:
    """
    Generate background story and structured attributes for a new agent.
    """
    # 1. Negotiation Style (Personality) Selection
    weights = {'balanced': 0.4} # default
    if config:
        weights = config.negotiation.get('personality_weights', {
            'aggressive': 0.25, 'conservative': 0.25, 
            'balanced': 0.40, 'desperate': 0.10
        })
    
    styles = list(weights.keys())
    probs = list(weights.values())
    negotiation_style = random.choices(styles, weights=probs, k=1)[0]

    prompt = f"""
    为这个Agent生成背景故事：
    年龄：{agent.age}
    婚姻：{agent.marital_status}
    月收入：{agent.monthly_income}
    现金：{agent.cash}
    
    请包含：occupation(职业), career_outlook(职业前景), family_plan(家庭规划), education_need(教育需求), housing_need(住房需求), selling_motivation(卖房动机), background_story(3-5句故事).
    
    另外，请为该人物设定一个谈判风格 (negotiation_style)，可选值: 
    - aggressive (激进): 追求最大利益，宁可不成交
    - conservative (保守): 谨慎决策，不轻易让步
    - balanced (平衡): 理性妥协，寻求双赢
    - desperate (急迫): 急需成交，愿意大幅让步
    (建议风格: {negotiation_style})

    输出JSON格式。
    """
    
    default_story = AgentStory(
        occupation="普通职员",
        career_outlook="稳定",
        family_plan="暂无",
        education_need="无",
        housing_need="刚需",
        selling_motivation="无",
        background_story="普通工薪阶层。",
        negotiation_style="balanced"
    )
    
    result = safe_call_llm(prompt, default_story, system_prompt="你是小说家，擅长构建人物小传。")
    
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
            negotiation_style=result.get("negotiation_style", negotiation_style)
        )
    return result

def generate_buyer_preference(agent: Agent) -> AgentPreference:
    """
    Generate buyer preferences based on agent story and financial status.
    修复：使用真实购买力计算（考虑按揭贷款）
    """
    from mortgage_system import calculate_max_affordable
    
    # 计算真实购买力
    existing_payment = getattr(agent, 'monthly_payment', 0)
    real_max_price = calculate_max_affordable(agent.cash, agent.monthly_income, existing_payment)
    
    prompt = f"""
    根据你的背景，设定购房偏好：
    【背景】{agent.story.background_story}
    【需求类型】{agent.story.housing_need}
    【教育需求】{agent.story.education_need}
    【现金】{agent.cash:,.0f}元
    【真实购买力(含贷款)】{real_max_price:,.0f}元
    
    输出JSON：
    {{"target_zone":"A或B", "max_price":...(不超过购买力), "min_bedrooms":..., "need_school_district": true/false}}
    """
    
    default_pref = AgentPreference(
        target_zone="B", 
        max_price=real_max_price,
        min_bedrooms=1,
        need_school_district=False
    )
    
    result = safe_call_llm(prompt, default_pref)
    
    # Map dictionary result to AgentPreference object if it's a dict
    if isinstance(result, dict):
        llm_max = result.get("max_price", real_max_price)
        # 确保不超过真实购买力
        final_max = min(float(llm_max), real_max_price) if llm_max else real_max_price
        
        return AgentPreference(
            target_zone=result.get("target_zone", "B"),
            max_price=final_max,
            min_bedrooms=result.get("min_bedrooms", 1),
            need_school_district=result.get("need_school_district", False)
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

def select_monthly_event(agent: Agent, month: int) -> dict:
    """
    Select a life event for the agent for this month.
    """
    prompt = f"""
    Agent {agent.id} 背景：{agent.story.background_story}
    可能发生的事件：{[e["event"] for e in LIFE_EVENT_POOL]}
    
    第{month}月最可能发生什么？（无事件返回null）
    输出JSON：{{"event": "..." 或 null, "reasoning": "..."}}
    """
    return safe_call_llm(prompt, {"event": None, "reasoning": "No event"})

def apply_event_effects(agent: Agent, event_data: dict):
    """
    Apply the financial effects of an event.
    """
    event_name = event_data.get("event")
    if not event_name:
        return
        
    event_config = next((e for e in LIFE_EVENT_POOL if e["event"] == event_name), None)
    if event_config:
        cash_change_pct = event_config["cash_change"]
        agent.cash *= (1 + cash_change_pct)
        agent.set_life_event(0, event_name) # Using 0 as current month placeholder or pass actual month
        print(f"Agent {agent.id} experienced {event_name}, cash changed by {cash_change_pct*100}%")

# --- 3. Role Determination ---

from enum import Enum
class AgentRole(Enum):
    BUYER = "buyer"
    SELLER = "seller"
    OBSERVER = "observer"

def determine_role(agent: Agent, month: int, market: Market) -> Tuple[AgentRole, str]:
    """
    Determine the agent's role (Buyer/Seller/Observer) for the month.
    """
    # 1. Hard Constraints
    if agent.cash < agent.monthly_income * 2 and agent.owned_properties:
        return AgentRole.SELLER, "Cash tight, forced to sell"
        
    if agent.cash > agent.monthly_income * 60 and not agent.owned_properties:
        return AgentRole.BUYER, "Sufficient savings, looking to buy"
        
    # 2. LLM Decision
    prompt = f"""
    你是Agent {agent.id}。
    【背景】{agent.story.background_story}
    【本月事件】{agent.monthly_event}
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
    
    return role_map.get(role_str, AgentRole.OBSERVER), result.get("reasoning", "")

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

def batched_determine_role(agents: list[Agent], month: int, market: Market, macro_summary: str = "平稳") -> list[dict]:
    """
    Batch process agents to determine roles using a single LLM call per batch.
    Returns a list of dicts: [{"id": 1, "role": "BUYER", "reason": "...", "price_expectation": 1.1}, ...]
    """
    if not agents:
        return []

    # Construct Batch Prompt
    agent_summaries = []
    for a in agents:
        summary = {
            "id": a.id,
            "age": a.age,
            "income": a.monthly_income,
            "cash": a.cash,
            "props": len(a.owned_properties),
            "has_property": len(a.owned_properties) > 0,  # 是否持有房产
            "background": a.story.background_story[:50] + "...",
            "need": a.story.housing_need
        }
        agent_summaries.append(summary)

    prompt = f"""
    【宏观环境】{macro_summary}
    【任务】判断以下Agent本月是否产生买卖房产需求。
    【规则】
    1. 默认角色为 OBSERVER (无操作)
    2. 触发条件：有刚需(结婚/学区)或投资机会且资金充足 -> BUYER；资金紧张或止盈变现 -> SELLER
    3. **重要**：has_property=false 的Agent **不能** 成为SELLER，因为他们没有房产可卖！
    4. 输出JSON列表，包含所有产生变化的Agent。未列出的默认为OBSERVER。
    5. 每个条目包含：id, role (BUYER/SELLER), trigger (触发原因), urgency (0-1), price_expectation (1.0-1.2, 买家愿溢价/卖家愿折价程度)
    
    Agent列表 ({len(agents)}人):
    {json.dumps(agent_summaries, ensure_ascii=False)}
    
    输出示例：
    [
        {{"id": 101, "role": "BUYER", "trigger": "孩子上学", "urgency": 0.9, "price_expectation": 1.15}},
        {{"id": 102, "role": "SELLER", "trigger": "资金周转", "urgency": 0.8, "price_expectation": 0.95}}
    ]
    """
    
    # Determine default "all observer" response structure for safe fallback
    default_response = []
    
    response = safe_call_llm(prompt, default_response, system_prompt="你是房地产市场模拟引擎。")
    
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
