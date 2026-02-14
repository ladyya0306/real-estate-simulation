import asyncio
import json
import logging
import sqlite3
from typing import Dict, List

# from transaction_engine import (
#     match_property_for_buyer, run_negotiation_session_async, execute_transaction,
#     handle_failed_negotiation
# )
from agent_behavior import decide_price_adjustment
from models import Agent

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

        for (pid, _, seller_id), result_tuple in zip(tasks, results):
            # unpack result which is now (decision_dict, context_metrics)
            result = result_tuple[0]
            metrics = result_tuple[1]

            action = result.get("action", "B")
            new_price = result.get("new_price", 0)  # default?
            reason = result.get("reason", "LLM决策")

            # Defensive check
            if not new_price and action in ["B", "C"]:
                continue  # Should not happen

            if action == "A":
                # Maintain price
                logger.debug(f"Property {pid}: 维持原价 - {reason}")
            elif action in ["B", "C"]:
                # Update price (V2)
                cursor.execute("""
                    UPDATE properties_market
                    SET listed_price = ?, last_price_update_month = ?, last_price_update_reason = ?
                    WHERE property_id = ?
                """, (round(new_price, 2), month, reason, pid))
                logger.info(f"Property {pid}: 调价至 {new_price:,.0f} - {reason}")
            elif action == "D":
                # Delist (V2)
                cursor.execute("""
                    UPDATE properties_market
                    SET status='off_market', last_price_update_month = ?, last_price_update_reason = ?
                    WHERE property_id = ?
                """, (month, reason, pid))
                logger.info(f"Property {pid}: 撤牌观望 - {reason}")

            # Log decision with context_metrics
            metrics_json = json.dumps(metrics) if metrics else None

            batch_decision_logs.append((
                seller_id, month, "PRICE_ADJUSTMENT", action, reason, None,
                metrics_json, True
            ))

        if batch_decision_logs:
            cursor.executemany("""INSERT INTO decision_logs
                (agent_id, month, event_type, decision, reason, thought_process, context_metrics, llm_called)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", batch_decision_logs)
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

        # --- 1. Matching Phase (批量匹配重构) ---
        from transaction_engine import match_property_for_buyer

        # Use simpler matching for now or re-import the bulk match function if available
        # The previous version imported bulk_match_all_buyers but it wasn't in the provided transaction_engine.py content
        # I only wrote basic functions to transaction_engine.py in Step 4565.
        # So I should use the loop based matching from Step 4565 logic or implement bulk there.
        # Step 4565 transaction_engine.py has match_property_for_buyer.
        # Let's use simple loop matching since bulk_match isn't in my written file yet.
        buyer_matches = []
        for buyer in buyers:
            match = match_property_for_buyer(buyer, active_listings, props_map)
            if match:
                buyer_matches.append({'buyer': buyer, 'listing': match})

        # ✅ Phase 3.3 Fix: Log Matches to property_buyer_matches
        if buyer_matches:
            match_records = []
            for m in buyer_matches:
                b = m['buyer']
                l = m['listing']
                # Initial intent: Buyer is interested at listed price (or max budget)
                # match_property_for_buyer checks affordability, so bid is roughly listed_price
                bid = l['listed_price']
                match_records.append((
                    month, l['property_id'], b.id, l['listed_price'], bid,
                    1,  # is_valid_bid
                    1  # proceeded_to_negotiation (All matches proceed in current logic)
                ))

            try:
                cursor.executemany("""
                    INSERT INTO property_buyer_matches
                    (month, property_id, buyer_id, listing_price, buyer_bid, is_valid_bid, proceeded_to_negotiation)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, match_records)
                self.conn.commit()
            except Exception as e:
                logger.error(f"Failed to log buyer matches: {e}")

        # Build Interest Map
        interest_registry = {}
        for m in buyer_matches:
            pid = m['listing']['property_id']
            if pid not in interest_registry:
                interest_registry[pid] = []
            interest_registry[pid].append(m['buyer'])

        # --- 2. Negotiation Phase ---
        if interest_registry:
            logger.info(f"Starting {len(interest_registry)} Negotiation Sessions (Parallel)...")

            tasks = []
            session_metadata = []

            # Local imports to avoid circular dependency
            from transaction_engine import decide_negotiation_format, execute_transaction, handle_failed_negotiation, run_negotiation_session_async

            for pid, interested_buyers in interest_registry.items():
                listing = next((l for l in active_listings if l['property_id'] == pid), None)
                if not listing:
                    continue

                seller_agent = agent_map.get(listing['seller_id'])
                if not seller_agent:
                    continue

                # Determine Negotiation Mode
                market_hint = "买家众多" if len(interested_buyers) > 1 else "单一买家"

                # mode = decide_negotiation_format(seller_agent, interested_buyers, market_hint)

                # ✅ Phase 3.3: Pass db_conn to enable bid recording
                tasks.append(run_negotiation_session_async(seller_agent, interested_buyers, listing, market, month, self.config, self.conn))
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

                # Context Metrics from Negotiation?
                # The negotiation history contains reason/thought process.
                # If we want specific metrics (like bid/ask spread), we can parse history or return it.
                # Currently negotiation returns a simple dict.
                # We can enhance it later. For now, we log history.

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
                            month,
                            winner.id,
                            seller_agent.id,
                            pid,
                            tx_record['price'],
                            tx_record['down_payment'],
                            tx_record['loan_amount'],
                            len(history)
                        ))

                        batch_negotiations.append((winner.id, seller_agent.id, pid, len(history), final_price, True, "Deal Concluded", json.dumps(history)))

                        # Update Listing / Properties (V2)
                        # execute_transaction updates objects, but we need to update DB status
                        cursor.execute("UPDATE properties_market SET status='off_market', owner_id=?, last_transaction_month=?, current_valuation=? WHERE property_id=?",
                                       (winner.id, month, final_price, pid))

                        # Update Buyer Financials (Persist Mortgage & Cash)
                        # Use helper to ensure all fields (especially net_cashflow) are consistent
                        w_fin = winner.to_v2_finance_dict()
                        cursor.execute("UPDATE agents_finance SET mortgage_monthly_payment=?, cash=?, total_assets=?, total_debt=?, net_cashflow=? WHERE agent_id=?",
                                       (w_fin['mortgage_monthly_payment'], w_fin['cash'], w_fin['total_assets'], w_fin['total_debt'], w_fin['net_cashflow'], winner.id))

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
                    INSERT INTO transactions (month, buyer_id, seller_id, property_id, final_price, down_payment, loan_amount, negotiation_rounds)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, batch_transactions)

            if batch_negotiations:
                # Need to handle table columns match.
                # negotiations table might strictly be (buyer_id, seller_id, property_id, round_count, final_price, success, reason, log)
                cursor.executemany("INSERT INTO negotiations (buyer_id, seller_id, property_id, round_count, final_price, success, reason, log) VALUES (?,?,?,?,?,?,?,?)", batch_negotiations)

            self.conn.commit()

        return transactions_count, failed_negotiations
