from models import Agent, Market
import random

def run_llm_decision_pipeline(agent: Agent, market: Market, month: int) -> dict:
    """
    Stub for LLM decision pipeline.
    In real implementation, this would call the LLM to Observe -> Think -> Dice Roll -> Action.
    """
    # print(f"  >>> calling LLM for Agent {agent.id} (Stub)")
    
    # Mock LLM decision
    # 50% chance to buy if no property, 50% chance to wait
    action = "WAIT"
    
    # Simple logic for stub
    if not agent.owned_properties:
        if random.random() < 0.5:
            action = "BUY"
            
    return {
        "action": action,
        "thought_process": "Mock thought process...",
        "dice_roll": 0.8,
        "pipeline_step": "complete"
    }
