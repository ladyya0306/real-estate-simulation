
"""
Buyer Decision Prompts
"""

BUYER_PREFERENCE_TEMPLATE = """
根据你的背景，设定购房偏好与决策：
【背景】{background}
【性格】{investment_style} (影响对风险和回报的权衡)
【财务】现金:{cash:,.0f}, 月入:{income:,.0f}, 购买力上限:{max_price:,.0f}
【当前环境】宏观:{macro_summary}, 趋势:{market_trend}, 无风险利率: {risk_free_rate:.1%}

{history_text}

【建议区域】{default_zone}区 (A区均价{zone_a_avg:,.0f}，B区均价{zone_b_avg:,.0f})

【财务指标分析 - 你的精明算盘】
1. 租售比 (Rental Yield): 预计年化 {rental_yield:.2%} vs 无风险利率 {risk_free_rate:.2%}
   - 如果 Yield < RiskFreeRate: 买房不如存钱，除非你确信房价大涨。
   - 如果 Yield > RiskFreeRate: 买房是好投资，即使房价不涨也划算。
2. 负担分析 (Affordability):
   - 预计月供: ¥{est_monthly_payment:,.0f}
   - 月供收入比 (DTI): {dti:.1%} (安全线 < 50%)
   - {affordability_warning}

【思考核心: 资产对比逻辑】
请对比 "房产收益" 与 "无风险收益":
决策指引:
- 激进型(Aggressive): 若市场看涨(Trend UP)且Yield尚可，倾向于追涨。
- 保守型(Conservative): 若 Yield < RiskFreeRate 且市场不明朗，坚决观望。
- 刚需: 必须买，但会在预算内选性价比最高的（即 Yield 相对较高的）。

请输出JSON：
{{
    "target_zone": "{default_zone}",
    "min_bedrooms": 1,
    "max_price": {max_price:.0f},
    "investment_motivation": "high/medium/low",
    "strategy_reason": "你的决策理由，必须引用上述财务指标（如Yield, DTI）来支持你的决定"
}}
"""

BUYER_MATCHING_TEMPLATE = """
你是买家 {name}。
【需求】{housing_need}
【预算上限】{max_price_w:.0f}万
【偏好】区域: {target_zone}, 学区: {school_need}
【投资视角】无风险利率 {risk_free_rate:.1%}

现有以下候选房源（已按价格排序）：
{props_info_json}

【精明买家分析】
请不仅仅看价格，还要看回报率 (Yield) 和 性价比。
- 如果所有房源的 Yield 都远低于无风险利率，且你不是极度刚需，可以放弃 (Selected: null)。
- 这是一个投资决策，不是简单的购物。

请选择一套最符合你需求且财务合理的房产。
输出JSON: {{"selected_property_id": int|null, "reason": "..."}}
"""
