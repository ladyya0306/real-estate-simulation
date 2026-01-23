#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Oasis 房产市场仿真 - 东莞特别版 (Dongguan Real Estate Simulation)
模拟松山湖、南城、东城等地的房产博弈
"""
import asyncio
import os
import random
import sys
# 强制 stdout 使用 utf-8，防止 emoji 报错
sys.stdout.reconfigure(encoding='utf-8')

from camel.models import ModelFactory
from camel.types import ModelPlatformType
import oasis
from oasis import (ActionType, AgentGraph, LLMAction, ManualAction,
                   SocialAgent, UserInfo)

# ⚠️ 临时硬编码
DEEPSEEK_API_KEY = "sk-45765318152f49cbafae11286f222697"
os.environ["DEEPSEEK_API_KEY"] = DEEPSEEK_API_KEY

# --- 配置参数 ---
NUM_SELLERS = 5
NUM_BUYERS = 3
DB_PATH = "./real_estate_stage2.db" # 复用同一个数据库，方便 Streamlit 查看

# 东莞地区概算 (单位：万/套，假设主要为3房)
# 数据仅供仿真参考
DISTRICTS = {
    "松山湖": 600,  # 均价高，科技人才聚集
    "南城": 450,    # 市中心，配套好
    "东城": 400,    # 老城区，生活便利
    "虎门": 300,    # 滨海湾，交通枢纽
    "厚街": 250     # 工业重镇
}

def generate_seller_prompt(dist, size, price):
    return f"""
You are a property owner in Dongguan City (东莞市), Guangdong Province, China. You need to sell your property urgently.

Your property:
- Location: Dongguan {dist} (东莞{dist})
- Size: {size} sqm ({size}平方米)
- Your minimum acceptable price: {price}万元
- Your listing price: {int(price * 1.05)}万元

CRITICAL: Your property listing MUST include "东莞" (Dongguan) in the content for buyers to find it!

Action steps:
1. FIRST, use list_property to create your property listing.
   Your listing content MUST start with "东莞{dist}" and include the size "{size}平方米".
   Example: list_property({{"content": "东莞{dist}优质房产出售！{size}平方米，精装修，交通便利。售价{int(price * 1.05)}万元。"}})

2. If you receive an offer (via make_offer response):
   - If offer price >= {price}万元, use accept_offer to complete the deal.
   - If offer price < {price}万元 but within 20万 of your minimum, you may wait (do_nothing).
   - If offer is too low, ignore it.

3. After selling, you can rest (do_nothing).
    """

def generate_buyer_prompt(agent_name, target_dist, budget, persona):
    return f"""
You are a home buyer looking for property in Dongguan City (东莞市), Guangdong Province, China.
Your identity: {persona}
Your preferred district: Dongguan {target_dist} (东莞 {target_dist})
Your budget: {budget}万元 (around {budget * 10000} CNY)
You are eager to find a home.

CRITICAL: You are ONLY interested in Dongguan (东莞) properties. DO NOT search for other cities like Shanghai or Shenzhen!

Action steps:
1. Use search_property to find listings. Your query MUST include "东莞" (Dongguan).
   CORRECT example: search_property({{"query": "东莞 {target_dist} 房产"}})
   WRONG example: search_property({{"query": "Shanghai apartment"}}) <-- DO NOT DO THIS!
   
2. Review the search results carefully. Look for posts mentioning property details and prices.

3. If you find a suitable property within your budget, use make_offer to bid.
   Example: make_offer({{"property_id": <post_id from search result>, "price": {int(budget * 9000)}, "message": "我是{persona}，诚意购买"}})
   
4. If no results, try searching other Dongguan districts like "东莞 东城" or "东莞 虎门".
    """

async def main():
    print(f"🏘️ 启动东莞房产市场仿真: {NUM_SELLERS} 卖家 vs {NUM_BUYERS} 买家")
    print("=" * 50)

    # 1. 模型
    deepseek_model = ModelFactory.create(
        model_platform=ModelPlatformType.DEEPSEEK,
        model_type="deepseek-chat",
        url="https://api.deepseek.com/v1",
    )

    # 2. 动作空间
    seller_actions = [ActionType.LIST_PROPERTY, ActionType.ACCEPT_OFFER, ActionType.DO_NOTHING, ActionType.REFRESH]
    buyer_actions = [ActionType.SEARCH_PROPERTY, ActionType.MAKE_OFFER, ActionType.DO_NOTHING, ActionType.REFRESH]

    agent_graph = AgentGraph()
    agents = []

    # 3. 生成卖家
    print("👷 生成东莞业主...")
    for i in range(NUM_SELLERS):
        dist = random.choice(list(DISTRICTS.keys()))
        avg_price = DISTRICTS[dist]
        size = random.randint(80, 140)
        # 价格波动
        base_price = int(avg_price * (size/100) * random.uniform(0.9, 1.1))
        
        prompt = generate_seller_prompt(dist, size, base_price)
        user_info = UserInfo(
            user_name=f"seller_{i}",
            name=f"业主_{dist}_{i}号",
            description=prompt,
            profile=None,
            recsys_type="reddit"
        )
        
        agent = SocialAgent(
            agent_id=i,
            user_info=user_info,
            agent_graph=agent_graph,
            model=deepseek_model,
            available_actions=seller_actions
        )
        agent_graph.add_agent(agent)
        agents.append(agent)
        print(f"  - 业主{i}: {dist}, {size}平, 底价{base_price}w")

    # 4. 生成买家
    print("👷 生成购房者...")
    personas = [
        ("华为员工", "松山湖", 1.5), # 预算系数高
        ("本地改善", "南城", 1.1),
        ("刚需上车", "虎门", 0.9)
    ]
    
    for i in range(NUM_SELLERS, NUM_SELLERS + NUM_BUYERS):
        persona_name, pref_dist, budget_factor = personas[i - NUM_SELLERS] 
        base_budget = DISTRICTS[pref_dist]
        budget = int(base_budget * budget_factor)
        
        prompt = generate_buyer_prompt(f"buyer_{i}", pref_dist, budget, persona_name)
        user_info = UserInfo(
            user_name=f"buyer_{i}",
            name=f"{persona_name}_{i}",
            description=prompt,
            profile=None,
            recsys_type="reddit"
        )
        
        agent = SocialAgent(
            agent_id=i,
            user_info=user_info,
            agent_graph=agent_graph,
            model=deepseek_model,
            available_actions=buyer_actions
        )
        agent_graph.add_agent(agent)
        agents.append(agent)
        print(f"  - 买家{i}: {persona_name}, 意向{pref_dist}, 预算{budget}w")

    # 5. 启动
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        
    env = oasis.make(
        agent_graph=agent_graph,
        platform=oasis.DefaultPlatformType.REDDIT,
        database_path=DB_PATH,
    )
    await env.reset()

    # --- 辅助函数：修复 Agent Memory (User 创意方案) ---
    from camel.messages import BaseMessage
    from camel.types import RoleType

    def repair_agent_memory(agent):
        """
        检查并修复 Agent 的记忆。
        如果是 DeepSeek/Qwen，如果历史记录中有 Tool Call 但没有对应的 Tool Result，
        会导致 400 错误。
        此函数会检测这种情况并注入一个伪造的“成功”消息，欺骗 API 认为调用已完成。
        """
        try:
            if not hasattr(agent, 'memory'): return
            
            # --- 寻找消息列表 ---
            # 路径: agent.memory -> _chat_history_block -> storage -> memory_list
            messages = None
            storage = None
            
            try:
                # 尝试标准 CAMEL 结构 (v0.2.x)
                if hasattr(agent.memory, 'chat_history') and hasattr(agent.memory.chat_history, 'messages'):
                     messages = agent.memory.chat_history.messages
                     storage = agent.memory.chat_history # 引用持有者以便回写
                # 尝试深入内部结构 (经探测发现有效)
                elif hasattr(agent.memory, '_chat_history_block'):
                    block = agent.memory._chat_history_block
                    if hasattr(block, 'storage') and hasattr(block.storage, 'memory_list'):
                        messages = block.storage.memory_list
                        storage = block.storage
            except:
                pass

            if messages is None:
                # 最后的尝试: 看看是否有 get_context
                # print(f"  ⚠️ 无法找到消息列表: {dir(agent.memory)}")
                return

            # --- 重建和修复 ---
            new_messages = []
            modified = False
            i = 0
            while i < len(messages):
                msg = messages[i]
                new_messages.append(msg)
                i += 1
                
                # 检查是否有 tool_calls
                tool_calls = msg.meta_dict.get('tool_calls') if msg.meta_dict else None
                if tool_calls and isinstance(tool_calls, list):
                    for tc in tool_calls:
                        tc_id = tc.get('id')
                        if not tc_id: continue
                        
                        # 尝试在后续消息中寻找匹配的 Tool Response
                        matched = False
                        # 我们只看下一个是否匹配（假设顺序一致）
                        if i < len(messages):
                            cand = messages[i]
                            # 检查是否是 Tool 类型且 ID 匹配
                            cand_id = cand.meta_dict.get('tool_call_id') if cand.meta_dict else None
                            if cand.role_type == RoleType.TOOL and cand_id == tc_id:
                                new_messages.append(cand)
                                i += 1 # 消耗掉这个消息
                                matched = True
                        
                        if not matched:
                            # 没找到！注入伪造的 Tool Result
                            print(f"  🔧 [Auto-Fix] 为 {agent.agent_id} 补全缺失的 Tool Result ({tc_id})")
                            repair_msg = BaseMessage(
                                role_name="Tool",
                                role_type=RoleType.TOOL,
                                meta_dict={"tool_call_id": tc_id},
                                content='{"success": true, "message": "Action executed successfully (Auto-filled by System to fix 400 Error)"}'
                            )
                            new_messages.append(repair_msg)
                            modified = True
            
            # --- 更新回 Memory ---
            if modified:
                if hasattr(storage, 'messages'):
                    storage.messages = new_messages
                elif hasattr(storage, 'memory_list'):
                    storage.memory_list = new_messages
                # print("  ✅ Memory repaired.")

        except Exception as e:
            print(f"  ⚠️ Repair process failed: {e}")

    # --- 市场运行循环 ---
    ROUNDS = 2  # 跑2轮以验证逻辑
    print(f"\n🚀 市场开启，运行 {ROUNDS} 轮...")

    # --- 预注入房产列表（绕过 LLM 不遵循指令问题）---
    print("  🏠 预注入：为卖家创建包含'东莞'关键词的房源...")
    seller_info = {}  # Store seller info for later use
    for agent in agents:
        if "seller" in agent.user_info.user_name:
            # Extract district and price from prompt  
            prompt = agent.user_info.description
            try:
                dist = prompt.split("Dongguan ")[1].split(" (东莞")[0] if "Dongguan " in prompt else "南城"
                size = prompt.split("Size: ")[1].split(" sqm")[0] if "Size: " in prompt else "100"
                price = prompt.split("listing price: ")[1].split("万元")[0] if "listing price: " in prompt else "500"
            except:
                dist = "南城"
                size = "100"
                price = "500"
            
            content = f"东莞{dist}优质房产出售！{size}平方米，精装修，交通便利，靠近地铁口。售价{price}万元。诚意出售，价格可议。"
            list_action = ManualAction(ActionType.LIST_PROPERTY, {"content": content})
            await env.step({agent: list_action})
            seller_info[agent.agent_id] = {"dist": dist, "size": size, "price": price}
            print(f"    ✅ {agent.user_info.user_name} 已挂牌 '东莞{dist} {size}平方米 {price}万'")

    for round_id in range(1, ROUNDS + 1):
        print(f"\n🔔 [Round {round_id}] 全员行动")
        
        # 刷新消息
        refresh_actions = {agent: ManualAction(ActionType.REFRESH, {}) for agent in agents}
        await env.step(refresh_actions)
        
        # --- 为买家预执行搜索（绕过 LLM 指令理解问题）---
        if round_id == 1:
            print("  🔍 预执行：为买家搜索东莞房源...")
            for agent in agents:
                if "buyer" in agent.user_info.user_name:
                    pref_dist = agent.user_info.description.split("Dongguan ")[1].split(" (东莞")[0] if "Dongguan " in agent.user_info.description else "南城"
                    search_action = ManualAction(ActionType.SEARCH_PROPERTY, {"query": f"东莞 {pref_dist} 房产"})
                    await env.step({agent: search_action})
                    print(f"    ✅ {agent.user_info.user_name} 已搜索 '东莞 {pref_dist} 房产'")
        
        # 自主决策
        llm_actions = {agent: LLMAction() for agent in agents}
        try:
            print("  🤔 思考中...")
            await env.step(llm_actions)
        except Exception as e:
            print(f"  ⚠️ 本轮产生错误 (可能忽略): {e}")
        
        # ⚠️ 关键修复：每轮结束后，智能修复 Memory
        # 这比清空更好，因为它保留了上下文
        print("  🧠 检查并修复 Agent 记忆...")
        for agent in agents:
            repair_agent_memory(agent)

    print("\n" + "="*50)
    print("🎉 市场仿真结束！请查看 Streamlit 看板。")
    await env.close()

if __name__ == "__main__":
    asyncio.run(main())
