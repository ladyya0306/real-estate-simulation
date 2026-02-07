已经设定好的重要规则：
1、D:\GitProj\oasis-main\config\baseline.yaml非常重要，是系统主配置
2、项目遵循"LLM 自由表达策略，代码只负责解析和执行" 原则。如下所述：
    类型	代码行为
    系统控制型	代码强制执行
    LLM 上下文型	注入 Prompt，LLM 自主决策
    LLM 建议型	作为"建议"，不强制
3、目前Prompt 结构示例
    【系统提示 (System Prompt)】
    {style_prompts[negotiation_style]}
    【用户提示 (User Prompt)】
    # 宏观环境 (来自 macro_environment)
    {macro_context}
    # 市场供需 (来自 market_conditions)  
    {market_hint}
    # 你的处境 (来自 decision_factors)
    {agent_context}
    # 交易信息
    【目标房产】A区 100㎡ 学区房
    【卖方挂牌价】¥5,000,000
    【你的预算上限】¥4,800,000
    ---
    请自由决策。JSON 输出: {"action": ..., "offer_price": ..., "reasoning": ...}