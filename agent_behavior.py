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

def generate_agent_story(agent: Agent) -> AgentStory:
    """
    Generate background story and structured attributes for a new agent.
    """
    prompt = f"""
    为这个Agent生成背景故事：
    年龄：{agent.age}
    婚姻：{agent.marital_status}
    月收入：{agent.monthly_income}
    现金：{agent.cash}
    
    请包含：occupation(职业), career_outlook(职业前景), family_plan(家庭规划), education_need(教育需求), housing_need(住房需求), selling_motivation(卖房动机), background_story(3-5句故事).
    
    输出JSON格式。
    """
    
    default_story = AgentStory(
        occupation="普通职员",
        career_outlook="稳定",
        family_plan="暂无",
        education_need="无",
        housing_need="刚需",
        selling_motivation="无",
        background_story="普通工薪阶层。"
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
            background_story=result.get("background_story", "平凡的一生。")
        )
    return result

def generate_buyer_preference(agent: Agent) -> AgentPreference:
    """
    Generate buyer preferences based on agent story and financial status.
    """
    prompt = f"""
    根据你的背景，设定购房偏好：
    【背景】{agent.story.background_story}
    【需求类型】{agent.story.housing_need}
    【教育需求】{agent.story.education_need}
    【现金】{agent.cash:,.0f}元
    
    输出JSON：
    {{"target_zone":"A或B", "max_price":..., "min_bedrooms":..., "need_school_district": true/false}}
    """
    
    default_pref = AgentPreference(
        target_zone="B", 
        max_price=agent.cash * 3, # Assume some leverage
        min_bedrooms=1,
        need_school_district=False
    )
    
    result = safe_call_llm(prompt, default_pref)
    
    # Map dictionary result to AgentPreference object if it's a dict
    if isinstance(result, dict):
        return AgentPreference(
            target_zone=result.get("target_zone", "B"),
            max_price=result.get("max_price", agent.cash * 3),
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
