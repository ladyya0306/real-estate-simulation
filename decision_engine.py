import logging
from typing import Optional, Dict
from dataclasses import dataclass
from models import Agent, Market

logger = logging.getLogger(__name__)

@dataclass
class TriggerResult:
    """触发判断结果"""
    should_trigger: bool
    reason: str
    trigger_type: Optional[str] = None  # 'life_event' | 'financial' | 'market'

def should_call_llm(agent: Agent, market: Market, month: int) -> TriggerResult:
    """
    判断是否需要调用LLM进行深度决策
    
    Args:
        agent: Agent对象,包含个人属性和财务状态
        market: Market对象,包含市场价格信息
        month: 当前月份 (1-60)
        
    Returns:
        TriggerResult: 触发判断结果
    """
    
    # ===== 条件1: 生命事件触发 =====
    life_event = agent.get_life_event(month)
    if life_event:
        logger.info(f"[Agent {agent.id}] 触发生命事件: {life_event}")
        return TriggerResult(
            should_trigger=True,
            reason=f"生命事件: {life_event}",
            trigger_type='life_event'
        )
    
    # ===== 条件2: 财务状况剧变 =====
    if hasattr(agent, 'last_month_cash') and agent.last_month_cash > 0:
        cash_change_rate = abs(agent.cash - agent.last_month_cash) / agent.last_month_cash
        if cash_change_rate > 0.3:  # 现金变动超过30%
            logger.info(f"[Agent {agent.id}] 财务剧变: {cash_change_rate:.1%}")
            return TriggerResult(
                should_trigger=True,
                reason=f"现金变动{cash_change_rate:.1%} (阈值30%)",
                trigger_type='financial'
            )
    
    # ===== 条件3: 市场剧烈波动 =====
    # 确定Agent关注的区域
    target_zone = determine_target_zone(agent)
    price_change_rate = market.get_price_change_rate(target_zone, month)
    
    if abs(price_change_rate) > 0.1:  # 价格变动超过±10%
        logger.info(f"[Agent {agent.id}] 市场剧变: {target_zone}区价格{price_change_rate:+.1%}")
        return TriggerResult(
            should_trigger=True,
            reason=f"{target_zone}区价格变动{price_change_rate:+.1%} (阈值10%)",
            trigger_type='market'
        )
    
    # ===== 条件4: 其他情况 - 不触发 =====
    return TriggerResult(
        should_trigger=False,
        reason="无特殊事件,保持观望"
    )

def determine_target_zone(agent: Agent) -> str:
    """
    确定Agent当前关注的区域
    
    逻辑:
    - 有学龄子女 → 关注A区(学区)
    - 未婚/新婚无房 → 关注B区(经济型)
    - 已持有B区房 → 关注A区(置换目标)
    - 其他 → 关注B区
    """
    # 检查是否有学龄子女 (5-6岁)
    if agent.has_children_near_school_age():
        return 'A'
    
    # 检查是否持有B区房产
    for prop in agent.owned_properties:
        if prop.get('zone') == 'B':
            return 'A'  # 潜在置换需求
    
    # 默认关注B区
    return 'B'
