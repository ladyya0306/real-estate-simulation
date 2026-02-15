import asyncio
import logging
import os
import sqlite3
import sys
from typing import List

from config.config_loader import SimulationConfig
from config.settings import MACRO_ENVIRONMENT, get_current_macro_sentiment
from database import init_db
from services.agent_service import AgentService
from services.intervention_service import InterventionService
from services.market_service import MarketService
from services.rental_service import RentalService
from services.reporting_service import ReportingService
from services.transaction_service import TransactionService

# from utils.behavior_logger import BehaviorLogger
from utils.exchange_display import ExchangeDisplay
from utils.workflow_logger import WorkflowLogger

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("simulation_run.log", encoding='utf-8', mode='w'),
        logging.StreamHandler()
    ]
)
# Force set stdout to utf-8
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

logger = logging.getLogger(__name__)


class SimulationRunner:
    def __init__(self, agent_count=50, months=12, seed=42, resume=False, config=None, db_path=None):
        self.agent_count = agent_count
        self.months = months
        self.seed = seed
        self.resume = resume
        self.config = config if config else SimulationConfig()
        self.db_path = db_path

        # Initialize Database connection
        if not self.db_path:
            # Fallback if not provided (though main script usually provides it)
            self.db_path = 'simulation.db'

        # Initialize DB Schema if needed
        if not self.resume:
            init_db(self.db_path)

        self.conn = sqlite3.connect(self.db_path, timeout=60.0)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA busy_timeout = 30000")

        # Initialize Services
        self.market_service = MarketService(self.config, self.conn)
        self.agent_service = AgentService(self.config, self.conn)
        self.transaction_service = TransactionService(self.config, self.conn)
        self.intervention_service = InterventionService(self.conn)
        self.rental_service = RentalService(self.config, self.conn)
        self.reporting_service = ReportingService(self.config, self.conn)

        # Pending Interventions (Tier 5)
        self.pending_interventions = []

    def set_interventions(self, news_items: List[str]):
        """Set interventions for the upcoming month."""
        self.pending_interventions = news_items

    def initialize(self):
        """Initialize Simulation State"""

        if self.resume:
            self.load_from_db()
            return

        logger.info(f"Initializing Simulation with Seed: {self.seed}")
        import random
        random.seed(self.seed)

        try:
            # 1. Initialize Market
            properties = self.market_service.initialize_market()

            # 2. Initialize Agents (and allocate properties)
            self.agent_service.initialize_agents(self.agent_count, properties)

            # Show Summary
            wf_logger = WorkflowLogger(self.config)
            wf_logger.show_agent_generation_summary(self.agent_service.agents, sample_size=3)

        except Exception as e:
            logger.error(f"Initialization Failed: {e}")
            raise

    def load_from_db(self):
        """Load state from DB"""
        from database import migrate_db_v2_7

        # Ensure Schema is up to date (V2.7)
        migrate_db_v2_7(self.db_path)

        self.agent_service.load_agents_from_db()
        self.market_service.load_market_from_db(self.agent_service.agents)

    def get_last_simulation_month(self) -> int:
        """Get the last simulated month from DB."""
        try:
            cursor = self.conn.cursor()
            # Check decision_logs or transactions
            cursor.execute("SELECT MAX(month) FROM decision_logs")
            result = cursor.fetchone()
            if result and result[0]:
                return int(result[0])
            return 0
        except Exception as e:
            logger.warning(f"Could not determine last month: {e}")
            return 0

    def run(self):
        """Main Simulation Loop (Coordinator)"""
        start_month = 0

        if self.resume:
            logger.info("Resuming simulation...")
            self.load_from_db()
            start_month = self.get_last_simulation_month()
            logger.info(f"Resuming from Month {start_month}")
        else:
            self.initialize()

        # Initialize Loggers
        log_dir = os.path.dirname(self.db_path)
        if not log_dir:
            log_dir = "results"
        # behavior_logger = BehaviorLogger(results_dir=log_dir)
        exchange_display = ExchangeDisplay(use_rich=True)
        wf_logger = WorkflowLogger(self.config)

        logger.info(f"Starting Simulation: {self.months} Months (From {start_month + 1} to {start_month + self.months})")

        try:
            # Shifted Loop Range
            for month in range(start_month + 1, start_month + self.months + 1):

                logger.info(f"--- Month {month} ---")

                # 1. Macro Environment
                macro_key = get_current_macro_sentiment(month)
                macro_desc = f"{macro_key.upper()}: {MACRO_ENVIRONMENT[macro_key]['description']}"
                exchange_display.show_exchange_header(month, macro_desc)

                # 2. Market Bulletin (Service)
                # Pass pending interventions
                bulletin = asyncio.run(self.market_service.generate_market_bulletin(month, self.pending_interventions))
                logger.info(bulletin)

                # Clear interventions after broadcasting (unless they are persistent? No, news is valid for one month usually)
                # If policy is persistent, the EFFECT is persistent, but the NEWS is one-off.
                self.pending_interventions = []

                market_trend = self.market_service.get_market_trend(month)

                # 3. Agent Updates (Financials)
                self.agent_service.update_financials()

                # 3.5 Rental Market (Phase 7.2)
                self.rental_service.process_rental_market(month)

                # 4. Agent Lifecycle: Manage Active Participants (Timeouts/Exits)
                batch_decision_logs = []
                active_buyers = self.agent_service.update_active_participants(month, self.market_service.market, batch_decision_logs)

                # 5. Tier 3: LLM Price Adjustments (Service)
                # Run async task
                # Note: TransactionService needs to return logs if we want to batch them here, or insert them directly.
                # Assuming it inserts directly or returns logs?
                # Let's check TransactionService.process_listing_price_adjustments
                # It likely needs to be updated to capture context_metrics too.
                # For now just run it.
                asyncio.run(self.transaction_service.process_listing_price_adjustments(month, market_trend))

                # 6. Life Events (Stochastic)
                self.agent_service.process_life_events(month, batch_decision_logs)

                # 6.5 Market Memory (Phase 7.2)
                recent_bulletins = self.market_service.get_recent_bulletins(month, n=3)

                # 7. Agent Activation (New Participants)
                new_buyers, decisions = asyncio.run(
                    self.agent_service.activate_new_agents(
                        month, self.market_service.market, macro_desc,
                        batch_decision_logs, market_trend, bulletin,
                        recent_bulletins=recent_bulletins  # 棣冨晭 Pass History
                    )
                )

                # Merge lists for display/processing
                all_buyers = active_buyers + new_buyers
                # Note: sellers are implicitly defined by 'status=for_sale' properties in DB/Market

                # Flush decision logs from activation/lifecycle
                if batch_decision_logs:
                    # Update to include context_metrics
                    self.conn.executemany("""INSERT INTO decision_logs
                            (agent_id, month, event_type, decision, reason, thought_process, context_metrics, llm_called)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", batch_decision_logs)
                    self.conn.commit()

                # Logging
                wf_logger.show_activation_summary(decisions)

                # 8. Transaction Processing (Service)
                # Prep data for matching
                # We need active listings. TransactionService can query DB or MarketService can provide.
                # Let's query DB via cursor or properties_market to get latest state (including price adjustments)
                # Or better: TransactionService handles fetching active listings internally?
                # The method signature I designed: process_monthly_transactions(locals...)
                # Let's construct arguments.

                # Fetch Active Listings (from DB to ensure latest prices)
                cursor = self.conn.cursor()
                cursor.execute("""
                    SELECT property_id, owner_id as seller_id, listed_price, min_price, status, listing_month as created_month
                    FROM properties_market
                    WHERE status='for_sale'
                """)
                cols = [description[0] for description in cursor.description]
                active_listings = [dict(zip(cols, row)) for row in cursor.fetchall()]

                # Build maps
                props_map = {p['property_id']: p for p in self.market_service.market.properties}

                # Cluster by Zone
                listings_by_zone = {}
                for listing in active_listings:
                    pid = listing.get('property_id')
                    if pid in props_map:
                        z = props_map[pid].get('zone', 'A')
                        listing['zone'] = z
                        if z not in listings_by_zone:
                            listings_by_zone[z] = []
                        listings_by_zone[z].append(listing)

                exchange_display.show_listings(active_listings, props_map)
                exchange_display.show_buyers(all_buyers)

                # Execute Transactions
                tx_count, fail_count = asyncio.run(self.transaction_service.process_monthly_transactions(
                    month, all_buyers, listings_by_zone, active_listings,
                    props_map, self.agent_service.agent_map,
                    self.market_service.market,
                    wf_logger, exchange_display
                ))

                logger.info(f"Month {month} Complete. Transactions: {tx_count}, Failed Negs: {fail_count}")

            # --- Phase 10: End-of-Run Reporting ---
            logger.info("Generating Final Agent Reports (Automated Portrait)...")
            asyncio.run(self.reporting_service.generate_all_agent_reports(self.months))

        except KeyboardInterrupt:
            logger.info("Simulation Stopped by User.")
        except Exception as e:
            logger.error(f"Simulation Error: {e}")
            import traceback
            traceback.print_exc()

    def close(self):
        if self.conn:
            self.conn.close()


if __name__ == "__main__":
    # Allow running directly for testing

    # Clean up previous DB to avoid unique constraint errors
    db_file = "simulation.db"
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
            print(f"Removed existing {db_file} for clean run.")
        except Exception as e:
            print(f"Warning: Could not remove {db_file}: {e}")

    runner = SimulationRunner(agent_count=50, months=1)
    runner.run()
    runner.close()
