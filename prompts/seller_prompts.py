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
Seller Decision Prompts
"""

LISTING_STRATEGY_TEMPLATE = """
你是Agent {agent_id}，卖家。
【你的背景】{background}
【你的性格】{investment_style}
【财务状况】现金: {cash:,.0f}, 月收入: {income:,.0f} (月供支出: {monthly_payment:,.0f})
【生活压力】{life_pressure}
【名下房产】
{props_info_json}

{market_bulletin}
{psych_advice}

【财务痛点分析 - 为什么要卖？】
1. 持有成本 (Holding Cost): 你每月为这些房产支付约 ¥{total_holding_cost:,.0f} (房贷+维护-潜在租金)。
2. 资金效率: 当前资金沉淀在房产中。如果卖掉变现，存入银行 ({risk_free_rate:.1%})，每年可躺赚 ¥{potential_bank_interest:,.0f}。
3. 竞品压力 (Comps): 你的邻居们同类房源最低挂牌价为 ¥{comp_min_price:,.0f}。

━━━━━━━━━━━━━━━━━━━━━━━
请基于上述财务分析和市场公报，选择你的定价策略:

A. 【激进挂高/牛市追涨】挂牌价 = 估值 × [1.05 ~ 1.30]
   - 只有当你确信你的房子比竞品好，或者不缺钱付月供时才选这个。

B. 【随行就市】挂牌价 = 市场均价 × [0.98 ~ 1.05]
   - 正常的置换策略。参考竞品价格 ¥{comp_min_price:,.0f}。

C. 【以价换量/熊市止损】挂牌价 = 估值 × [0.80 ~ 0.97]
   - 如果你的持有成本太高，或者急需现金，必须比竞品更便宜才能跑得掉。

D. 【暂不挂牌】
   - 如果你觉得租金回报还可以，或者亏损太严重不愿割肉。

━━━━━━━━━━━━━━━━━━━━━━━

输出JSON:
{{
    "strategy": "A/B/C/D",
    "pricing_coefficient": 1.0,  # 必填！
    "properties_to_sell": [property_id, ...],
    "reasoning": "你的决策理由，请提及持有成本或竞品价格"
}}
"""

PRICE_ADJUSTMENT_TEMPLATE = """
你是 {agent_name}，投资风格：{investment_style}。
背景：{background}

【当前处境】
你的房产（ID: {property_id}）已挂牌 {listing_duration} 个月未成交。
当前挂牌价：¥{current_price:,.0f}
市场趋势：{market_trend}
{psych_advice}

【残酷的现实 - 财务分析】
1. 累计亏损: 挂牌期间你已支付持有成本约 ¥{accumulated_holding_cost:,.0f}。
2. 浏览量: 只有寥寥 {daily_views} 人次浏览（模拟数据）。
3. 竞品打压: 同小区最低价已经降到了 ¥{comp_min_price:,.0f}，比你便宜 ¥{price_diff:,.0f}。

【决策选项】
A. 维持原价 (死扛，相信奇迹)
B. 小幅降价 (系数 0.95~0.98，试探市场)
C. 大幅降价/止损 (系数 0.80~0.92，承认失败，立刻套现止损)
D. 撤牌观望 (转售为租，或等待明年)

请根据你的性格和财务压力做出决策。

返回 JSON:
{{
    "action": "A",  # 选择 A/B/C/D
    "coefficient": 1.0,
    "reason": "简述原因（必须引用竞品价或持有成本）"
}}
"""
