import logging
import sqlite3
import json
import asyncio
from typing import List, Dict, Tuple
from datetime import datetime

from models import Agent
from transaction_engine import (
    match_property_for_buyer, run_negotiation_session_async, execute_transaction, 
    handle_failed_negotiation
)
from agent_behavior import decide_price_adjustment

logger = logging.getLogger(__name__)

class TransactionService:
    def __init__(self, config, db_conn: sqlite3.Connection):
        self.config = config
        self.conn = db_conn
        
    async def process_listing_price_adjustments(self, month: int, market_trend: str):
        """Tier 3: LLM Autonomous Price Adjustment."""
        cursor = self.conn.cursor()
        
        # Select stale listings using V2 tables
        cursor.execute("""
            SELECT pm.property_id, pm.owner_id, pm.listed_price, pm.listing_month,
                   ast.name, ast.investment_style
            FROM properties_market pm
            JOIN agents_static ast ON pm.owner_id = ast.agent_id
            WHERE pm.status='for_sale' AND pm.listing_month <= ?
        """, (month - 2,))
        
        stale_listings = cursor.fetchall()
        
        if not stale_listings:
            return

        tasks = []
        for row in stale_listings:
            pid, seller_id, current_price, created_m = row[0], row[1], row[2], row[3]
            agent_name, investment_style = row[4], row[5]
            listing_duration = month - created_m
            
            task = decide_price_adjustment(
                agent_id=seller_id,
                agent_name=agent_name,
                investment_style=investment_style,
                property_id=pid,
                current_price=current_price,
                listing_duration=listing_duration,
                market_trend=market_trend,
                db_conn=self.conn
            )
            tasks.append((pid, task, seller_id))
        
        results = await asyncio.gather(*[t[1] for t in tasks])
        
        batch_decision_logs = []
        
        for (pid, _, seller_id), result in zip(tasks, results):
            action = result.get("action", "B")
            new_price = result.get("new_price", 0) # default?
            reason = result.get("reason", "LLM决策")
            
            # Defensive check
            if not new_price and action in ["B", "C"]:
                 continue # Should not happen
            
            if action == "A":
                # Maintain price
                logger.debug(f"Property {pid}: 维持原价 - {reason}")
            elif action in ["B", "C"]:
                # Update price (V2)
                cursor.execute("UPDATE properties_market SET listed_price = ? WHERE property_id = ?", (new_price, pid))
                logger.info(f"Property {pid}: 调价至 {new_price:,.0f} - {reason}")
            elif action == "D":
                # Delist (V2)
                cursor.execute("UPDATE properties_market SET status='off_market' WHERE property_id = ?", (pid,))
                logger.info(f"Property {pid}: 撤牌观望 - {reason}")
            
            # Log decision
            batch_decision_logs.append((
                seller_id, month, "PRICE_ADJUSTMENT", action, reason, None, True
            ))
            
        if batch_decision_logs:
            cursor.executemany("""INSERT INTO decision_logs 
                (agent_id, month, event_type, decision, reason, thought_process, llm_called) 
                VALUES (?, ?, ?, ?, ?, ?, ?)""", batch_decision_logs)
            self.conn.commit()

    async def process_monthly_transactions(self, month: int, buyers: List[Agent], 
                                         listings_by_zone: Dict, active_listings: List[Dict], 
                                         props_map: Dict, agent_map: Dict, 
                                         market, wf_logger, exchange_display):
        """
        Orchestrate matching, negotiation, and execution.
        Returns: (transactions_count, failed_negotiations_count)
        """
        cursor = self.conn.cursor()
        transactions_count = 0
        failed_negotiations = 0
        
        # --- 1. Matching Phase ---
        interest_registry = {} # {property_id: [buyers]}
        
        if buyers:
            for buyer in wf_logger.get_progress_bar(buyers, desc="Buyer Matching"):
                target_zone = buyer.preference.target_zone
                relevant_listings = listings_by_zone.get(target_zone, [])
                
                if not relevant_listings:
                    continue
                
                matched_listing = match_property_for_buyer(buyer, relevant_listings, props_map)
                
                if matched_listing:
                    pid = matched_listing['property_id']
                    if pid not in interest_registry:
                        interest_registry[pid] = []
                    interest_registry[pid].append(buyer)

        # --- 2. Negotiation Phase ---
        if interest_registry:
            logger.info(f"Starting {len(interest_registry)} Negotiation Sessions (Parallel)...")
            
            tasks = []
            session_metadata = [] 
            
            for pid, interested_buyers in interest_registry.items():
                 listing = next((l for l in active_listings if l['property_id'] == pid), None)
                 if not listing: continue
                 
                 seller_agent = agent_map.get(listing['seller_id'])
                 if not seller_agent: continue
                 
                 tasks.append(run_negotiation_session_async(seller_agent, interested_buyers, listing, market, self.config))
                 session_metadata.append({
                     "pid": pid,
                     "seller": seller_agent,
                     "buyers": interested_buyers,
                     "listing": listing
                 })
                 
            if tasks:
                session_results = await asyncio.gather(*tasks)
            else:
                session_results = []
            
            # Process Results
            batch_transactions = []
            batch_negotiations = []
            
            for i, session_result in enumerate(session_results):
                meta = session_metadata[i]
                pid = meta['pid']
                seller_agent = meta['seller']
                interested_buyers = meta['buyers']
                listing = meta['listing']
                
                outcome = session_result.get('outcome', 'failed')
                history = session_result.get('history', [])
                winner_id = session_result.get('buyer_id')
                winner = agent_map.get(winner_id) if winner_id else None
                
                if outcome == 'success' and winner:
                     # Display
                     exchange_display.show_deal_result(True, winner.id, seller_agent.id, pid, session_result['final_price'])
                     
                     # Check cash (double check)
                     final_price = session_result['final_price']
                     prop_data = props_map[pid]
                     
                     tx_record = execute_transaction(winner, seller_agent, prop_data, final_price, market, config=self.config)
                     
                     if tx_record:
                         transactions_count += 1
                         batch_transactions.append((
                             month, winner.id, seller_agent.id, pid, final_price, 'market'
                         ))
                         
                         batch_negotiations.append((winner.id, seller_agent.id, pid, len(history), final_price, True, "Deal Concluded", json.dumps(history)))
                         
                         # Update Listing / Properties (V2)
                         # execute_transaction updates objects, but we need to update DB status
                         cursor.execute("UPDATE properties_market SET status='off_market', owner_id=?, last_transaction_month=?, current_valuation=? WHERE property_id=?", 
                                      (winner.id, month, final_price, pid))
                         
                         # Reset winner role
                         winner.role = "OBSERVER"
                         # Clean up active_participants
                         cursor.execute("DELETE FROM active_participants WHERE agent_id = ?", (winner.id,))
                         
                else:
                     failed_negotiations += 1
                     # Log failed
                     for buyer in interested_buyers:
                         batch_negotiations.append((
                             buyer.id, seller_agent.id, pid, len(history), 
                             0, False,
                             session_result.get('reason', 'Negotiation Failed'),
                             json.dumps(history)
                         ))
                     
                     # Handle failed (Price Cut)
                     potential_buyers_est = len(interested_buyers)
                     try:
                         adjusted = handle_failed_negotiation(seller_agent, listing, market, potential_buyers_count=potential_buyers_est)
                         if adjusted:
                             cursor.execute("UPDATE properties_market SET listed_price=?, min_price=? WHERE property_id=?", 
                                           (listing['listed_price'], listing['min_price'], pid))
                     except Exception as e:
                         logger.warning(f"Failed to adjust price after failure: {e}")

            # Batch Insert
            if batch_transactions:
                cursor.executemany("""
                    INSERT INTO transactions (month, buyer_id, seller_id, property_id, price, transaction_type)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, batch_transactions)
                
            if batch_negotiations:
                # Need to handle table columns match
                cursor.executemany("INSERT INTO negotiations (buyer_id, seller_id, property_id, round_count, final_price, success, reason, log) VALUES (?,?,?,?,?,?,?,?)", batch_negotiations)
                
            self.conn.commit()
            
        return transactions_count, failed_negotiations
