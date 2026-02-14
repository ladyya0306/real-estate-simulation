"""
Transaction Engine: Handles Listings, Matching, Negotiation, and Execution
"""
import json
import asyncio
import random
from typing import List, Dict, Optional, Tuple, Any
from models import Agent, Market
from agent_behavior import safe_call_llm, safe_call_llm_async, build_macro_context, decide_negotiation_format
from mortgage_system import check_affordability, calculate_monthly_payment
from config.settings import MORTGAGE_CONFIG
import logging

logger = logging.getLogger(__name__)

# === 在文件末尾添加批量匹配函数 ===

def bulk_match_all_buyers(
    buyers: List[Agent], 
    listings: List[Dict], 
    props_map: Dict[int, Dict]
) -> Dict[int, List[int]]:
    """
    批量匹配：为所有买家找到候选房源（纯规则筛选，无LLM调用）
    
    这是匹配重构的核心函数，替代了原来的串行LLM选房逻辑。
    
    Args:
        buyers: 所有激活的买家列表
        listings: 所有for_sale的房源列表
        props_map: property_id -> property详细信息的映射
    
    Returns:
        {
            buyer_id: [property_id1, property_id2, ...],  # 每个买家的候选房源ID列表
            ...
        }
    
    Example:
        Input:  buyers=[买家1, 买家2, ...], listings=[房源A, 房源B, ...]
        Output: {1: [房源A, 房源C], 2: [房源A, 房源B, 房源D], ...}
    """
    matches = {}
    
    logger.info(f"=== 批量匹配开始 ===")
    logger.info(f"买家数量: {len(buyers)}, 房源数量: {len(listings)}")
    
    for buyer in buyers:
        if not hasattr(buyer, 'preference') or not buyer.preference:
            logger.warning(f"买家 {buyer.id} 没有偏好设置，跳过")
            continue
            
        pref = buyer.preference
        candidates = []
        
        for listing in listings:
            prop = props_map.get(listing['property_id'])
            if not prop:
                continue
            
            # === 硬规则筛选（和原match_property_for_buyer的逻辑一致）===
            
            # 1. 区域匹配
            if pref.target_zone and prop.get('zone') != pref.target_zone:
                continue
            
            # 2. 价格匹配（允许20%溢价空间用于谈判）
            if listing['listed_price'] > pref.max_price * 1.2:
                continue
            
            # 3. 学区匹配（如果买家要求学区房）
            need_school = getattr(pref, 'need_school_district', False)
            if need_school and not prop.get('is_school_district', False):
                continue
            
            # 4. 卧室数匹配（防御性检查）
            min_beds = getattr(pref, 'min_bedrooms', 1)
            if prop.get('bedrooms', 999) < min_beds:
                continue
            
            # === 通过所有筛选，加入候选列表 ===
            candidates.append(listing['property_id'])
        
        # 如果这个买家有候选房源，记录下来
        if candidates:
            matches[buyer.id] = candidates
            logger.debug(f"买家 {buyer.id}: 找到 {len(candidates)} 个候选房源")
    
    logger.info(f"批量匹配完成: {len(matches)} 个买家找到候选房源")
    return matches


def build_property_to_buyers_map(
    buyer_matches: Dict[int, List[int]],
    agent_map: Dict[int, Agent]
) -> Dict[int, List[Agent]]:
    """
    反向构建映射：从"买家→房源列表"转为"房源→买家列表"
    
    这个函数实现了视角转换，让我们能看到每套房源有多少买家感兴趣，
    从而触发正确的谈判模式（多买家=竞价，单买家=1v1）。
    
    Args:
        buyer_matches: {buyer_id: [property_ids]} 买家的候选房源
        agent_map: {agent_id: Agent对象} Agent映射表
    
    Returns:
        {
            property_id: [Agent1, Agent2, ...],  # 每套房源的意向买家列表
            ...
        }
    
    Example:
        Input:  {买家1: [房源A, 房源C], 买家2: [房源A, 房源B]}
        Output: {房源A: [买家1对象, 买家2对象], 房源B: [买家2对象], 房源C: [买家1对象]}
    """
    property_to_buyers = {}
    
    # 遍历每个买家的候选列表
    for buyer_id, property_ids in buyer_matches.items():
        buyer = agent_map.get(buyer_id)
        if not buyer:
            logger.warning(f"买家 {buyer_id} 不在agent_map中，跳过")
            continue
        
        # 将这个买家添加到每个候选房源的买家列表中
        for prop_id in property_ids:
            if prop_id not in property_to_buyers:
                property_to_buyers[prop_id] = []
            
            property_to_buyers[prop_id].append(buyer)
    
    # 日志输出：显示房源的买家分布
    logger.info(f"=== 房源买家分布 ===")
    for prop_id, buyers in property_to_buyers.items():
        buyer_count = len(buyers)
        if buyer_count > 1:
            logger.info(f"房源 {prop_id}: {buyer_count} 个买家感兴趣 → 触发竞价")
        else:
            logger.info(f"房源 {prop_id}: {buyer_count} 个买家感兴趣 → 1v1谈判")
    
    return property_to_buyers

