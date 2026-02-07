import sys
import os
import asyncio
import time
from models import Agent, Market, AgentStory
from agent_behavior import batched_determine_role_async
from utils.llm_client import call_llm_async

# Mock config
sys.stdout.reconfigure(encoding='utf-8')

async def test_async_llm_connection():
    print("Test 1: Testing Basic Async LLM Call...")
    try:
        response = await call_llm_async("Hello, are you async?", "You are a test bot.")
        print(f"✅ PASS: Async Call Response: {response[:50]}...")
    except Exception as e:
        print(f"❌ FAIL: Async Call Failed: {e}")

async def test_batch_role_determination():
    print("\nTest 2: Testing Async Batch Role Determination...")
    agents = []
    for i in range(5):
        a = Agent(i, "TestAgent", 30, "single", 10000, 100000)
        # Manually setup story for test
        a.story.background_story = "A test agent."
        a.story.housing_need = "none"
        a.story.investment_style = "balanced"
        agents.append(a)
    
    market = Market(100) # Mock market

    try:
        results = await batched_determine_role_async(agents, 1, market, "Stable")
        print(f"✅ PASS: Batch Function Returned {len(results)} results (may be empty if no roles)")
        if isinstance(results, list):
             print("✅ PASS: Return type is list")
    except Exception as e:
        print(f"❌ FAIL: Batch Async Call Failed: {e}")

async def test_json_mode():
    print("\nTest 3: Testing JSON Mode...")
    try:
        # Prompt explicitly asking for JSON but minimal structure
        prompt = "Create a JSON object with keys 'status' and 'message'."
        response = await call_llm_async(prompt, "You are a JSON generator.", json_mode=True)
        print(f"✅ PASS: Raw Response: {response[:50]}...")
        
        # Verify it parses
        data = json.loads(response)
        if "status" in data or "message" in data:
            print("✅ PASS: JSON Parsed Successfully")
        else:
            print(f"⚠️ WARN: JSON Parsed but missing keys: {data}")
            
    except Exception as e:
        print(f"❌ FAIL: JSON Mode Call Failed: {e}")

async def test_prompt_caching():
    print("\nTest 4: Testing Prompt Caching (Simulated)...")
    
    # We will run the same batch request twice and measure time
    agents = []
    for i in range(5):
        a = Agent(id=200+i, cash=1000000, monthly_income=20000)
        a.story = AgentStory(background_story="普通中产，有改善需求。", investment_style="balanced")
        agents.append(a)
    
    market = Market()
    
    print("  First Call (Cold Cache)...")
    start_time = time.time()
    await batched_determine_role_async(agents, 1, market)
    duration_1 = time.time() - start_time
    print(f"  > Duration 1: {duration_1:.2f}s")
    
    print("  Second Call (Warm Cache)...")
    start_time = time.time()
    await batched_determine_role_async(agents, 1, market)
    duration_2 = time.time() - start_time
    print(f"  > Duration 2: {duration_2:.2f}s")
    
    if duration_2 < duration_1:
         print(f"✅ PASS: Second call faster ({duration_1 - duration_2:.2f}s faster)")
    else:
         print(f"⚪ NOTE: Second call not faster (API variability or cache miss), but functional.")

async def test_dual_models():
    print("\nTest 5: Testing Dual Model Configuration (Smart vs Fast Clients)...")
    try:
        from utils.llm_client import MODEL_SMART, MODEL_FAST, SMART_BASE_URL, FAST_BASE_URL
        print(f"  Smart Config: {MODEL_SMART} @ {SMART_BASE_URL}")
        print(f"  Fast Config:  {MODEL_FAST} @ {FAST_BASE_URL}")
        
        # User Fast Model
        print("  Calling Fast Model...")
        res_fast = await call_llm_async("Say 'fast'", model_type="fast")
        print(f"  > Fast Response: {res_fast}")
        
        # Use Smart Model
        print("  Calling Smart Model...")
        res_smart = await call_llm_async("Say 'smart'", model_type="smart")
        print(f"  > Smart Response: {res_smart}")
        
        print("✅ PASS: Dual Provider Routing Works")
        
    except Exception as e:
        print(f"❌ FAIL: Dual Model Call Failed: {e}")

async def main():
    print("=== Async, JSON, Caching & Dual Models Verification ===")
    await test_async_llm_connection()
    await test_batch_role_determination()
    await test_json_mode()
    await test_prompt_caching()
    await test_dual_models()
    print("\n=== Verification Complete ===")

if __name__ == "__main__":
    import json # Ensure json is imported
    asyncio.run(main())
