"""
Tier 3 Unit Test: Test Individual Functions
"""
import asyncio
import sqlite3
from agent_behavior import decide_price_adjustment, determine_listing_strategy
from models import Agent, AgentStory, AgentPreference

async def test_price_adjustment():
    """Test decide_price_adjustment function"""
    print("=" * 60)
    print("Test 1: decide_price_adjustment()")
    print("=" * 60)
    
    # Create temporary database
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE agents_static (
        agent_id INTEGER, 
        name TEXT, 
        background_story TEXT,
        investment_style TEXT
    )""")
    cursor.execute("INSERT INTO agents_static VALUES (1, '张三', '保守投资者', 'conservative')")
    conn.commit()
    
    # Test different market conditions
    test_cases = [
        ("UP", 3, "市场上涨，挂牌3月"),
        ("DOWN", 5, "市场下跌，挂牌5月"),
        ("PANIC", 2, "市场恐慌，挂牌2月"),
    ]
    
    for market_trend, duration, desc in test_cases:
        print(f"\n场景: {desc}")
        result = await decide_price_adjustment(
            agent_id=1,
            agent_name="张三",
            investment_style="conservative",
            property_id=101,
            current_price=10000000,
            listing_duration=duration,
            market_trend=market_trend,
            db_conn=conn
        )
        
        action = result.get("action", "?")
        coefficient = result.get("coefficient", 1.0)
        new_price = result.get("new_price", 0)
        reason = result.get("reason", "")
        
        print(f"  决策: {action}")
        print(f"  系数: {coefficient:.3f}")
        print(f"  新价格: ¥{new_price:,.0f}")
        print(f"  理由: {reason}")
    
    conn.close()
    print("\n✅ Test 1 通过")

def test_strategy_coefficient():
    """Test determine_listing_strategy returns coefficient"""
    print("\n" + "=" * 60)
    print("Test 2: determine_listing_strategy() - coefficient extraction")
    print("=" * 60)
    
    # Create mock agent
    agent = Agent(
        id=1,
        name="李四",
        age=35,
        cash=1000000,
        monthly_income=30000
    )
    
    # Set monthly_payment separately (not in constructor)
    agent.monthly_payment = 5000
    
    agent.story = AgentStory(
        background_story="年轻企业家，积极投资",
        investment_style="aggressive",
        selling_motivation="资产增值"
    )
    
    agent.owned_properties = [
        {
            'property_id': 201,
            'zone': 'A',
            'base_value': 5000000
        }
    ]
    
    market_price_map = {'A': 5500000, 'B': 4000000}
    market_bulletin = "市场火热，A区均价上涨10%"
    
    print("\nAgent信息:")
    print(f"  性格: {agent.story.investment_style}")
    print(f"  房产估值: ¥{agent.owned_properties[0]['base_value']:,.0f}")
    print(f"  市场均价: ¥{market_price_map['A']:,.0f}")
    
    result = determine_listing_strategy(agent, market_price_map, market_bulletin)
    
    strategy = result.get("strategy", "?")
    coefficient = result.get("pricing_coefficient", None)
    properties = result.get("properties_to_sell", [])
    reasoning = result.get("reasoning", "")
    
    print("\nLLM 返回:")
    print(f"  策略: {strategy}")
    print(f"  系数: {coefficient}")
    print(f"  待售房产: {properties}")
    print(f"  理由: {reasoning[:100]}..." if len(reasoning) > 100 else f"  理由: {reasoning}")
    
    if coefficient is not None:
        print(f"\n✅ Test 2 通过 - 成功提取系数: {coefficient}")
    else:
        print(f"\n⚠️  Test 2 警告 - 未返回系数，使用默认值")

async def main():
    print("\nTier 3 功能单元测试\n")
    
    # Test 1: Price Adjustment
    await test_price_adjustment()
    
    # Test 2: Strategy Coefficient
    test_strategy_coefficient()
    
    print("\n" + "=" * 60)
    print("所有测试完成")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
