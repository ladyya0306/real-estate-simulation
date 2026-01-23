from decision_engine import should_call_llm, TriggerResult
from llm_pipeline import run_llm_decision_pipeline
from models import Agent, Market
import logging
import sqlite3
import json
from datetime import datetime

logger = logging.getLogger(__name__)

DB_PATH = 'real_estate_stage2.db'

def save_step_log(agent_id: int, month: int, step_type: str, content: str, metadata: dict = None):
    """
    Save a single step log to database
    step_type: 'observation' | 'thought' | 'dice_roll' | 'action'
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO agent_decision_logs (agent_id, month, step_type, content, metadata)
            VALUES (?, ?, ?, ?, ?)
        """, (
            agent_id, 
            month, 
            step_type, 
            content, 
            json.dumps(metadata or {}, ensure_ascii=False)
        ))
        
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to save {step_type} log: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def run_monthly_decision(agent: Agent, market: Market, month: int) -> dict:
    """
    执行单个Agent的月度决策 (4-Step Log Version)
    """
    # 1. 判断触发
    trigger_result: TriggerResult = should_call_llm(agent, market, month)
    
    decision = {}
    
    if trigger_result.should_trigger:
        # === LLM Path (4 Steps) ===
        logger.info(f"[Agent {agent.id}] 触发LLM: {trigger_result.reason}")
        
        # Step 1: Observation
        obs_content = f"Trigger: {trigger_result.reason}. Market Status: Zone A Price={market.get_avg_price('A', month):.0f}..."
        save_step_log(agent.id, month, "observation", obs_content, {"trigger": trigger_result.trigger_type})
        
        # Step 2: Thought (Simulated)
        pipeline_result = run_llm_decision_pipeline(agent, market, month)
        thought_content = pipeline_result.get("thought_process", "Thinking...")
        
        # LOGGING: Show Thought Process in Console
        logger.info(f"💭 [Agent {agent.id}] Thought: {thought_content}")
        
        save_step_log(agent.id, month, "thought", thought_content)
        
        # Step 3: Dice Roll
        roll_val = pipeline_result.get("dice_roll", 0.5)
        dice_content = f"Dice Roll: {roll_val:.2f} (Threshold: 0.7)"
        save_step_log(agent.id, month, "dice_roll", dice_content, {"value": roll_val})
        
        # Step 4: Action
        action = pipeline_result.get("action", "WAIT")
        action_content = f"Final Action: {action}"
        save_step_log(agent.id, month, "action", action_content, {"action": action, "llm_called": True})
        
        decision = pipeline_result
        decision['trigger_reason'] = trigger_result.reason
        decision['llm_called'] = True
        
    else:
        # === Fast Path (1 Step) ===
        # Only log 'action' = WAIT in fast path to save space, or log nothing if undesired.
        # Requirement implies we log decision. 
        # But user requirement specifically asked "Triggered Agent has 4 logs".
        
        decision = {
            "action": "WAIT",
            "trigger_reason": trigger_result.reason,
            "llm_called": False
        }
        
        # Optional: Save simple log for non-triggered (commented out to reduce noise, or keep simple)
        # save_step_log(agent.id, month, "action", "WAIT (Rule)", {"llm_called": False})
    
    return decision
