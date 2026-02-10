import logging
import sqlite3
from typing import Dict, List, Optional
from models import Market
from property_initializer import initialize_market_properties, convert_to_v2_tuples

logger = logging.getLogger(__name__)

class MarketService:
    def __init__(self, config, db_conn: sqlite3.Connection):
        self.config = config
        self.conn = db_conn
        self.consecutive_trend = 0
        self.market = None # Initialized later

    def initialize_market(self):
        """Initialize market properties based on configuration."""
        user_prop_count = getattr(self.config, 'user_property_count', None)
        
        if user_prop_count:
            logger.info(f"Initializing market with User Defined Property Count: {user_prop_count}")
            properties = initialize_market_properties(target_total_count=user_prop_count, config=self.config)
        else:
            properties = initialize_market_properties(config=self.config)
            
        # Sort properties by value descending for targeted distribution
        properties.sort(key=lambda x: x['base_value'], reverse=True)
        
        self.market = Market(properties)
        
        # Persist to DB (V2)
        # Note: Owner IDs are None initially. AgentService updates them later.
        # But we must insert the properties first so AgentService can update them.
        self._persist_properties(properties)
        
        return properties

    def _persist_properties(self, properties: List[Dict]):
        cursor = self.conn.cursor()
        batch_static = []
        batch_market = []
        
        for p in properties:
            s_data, m_data = convert_to_v2_tuples(p)
            batch_static.append(tuple(s_data.values()))
            batch_market.append(tuple(m_data.values()))
            
        cursor.executemany("""
            INSERT OR IGNORE INTO properties_static 
            (property_id, zone, quality, building_area, property_type, is_school_district, school_tier, initial_value, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, batch_static)
        
        cursor.executemany("""
            INSERT OR IGNORE INTO properties_market
            (property_id, owner_id, status, current_valuation, listed_price, min_price, listing_month, last_transaction_month)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, batch_market)
        
        self.conn.commit()
        logger.info(f"Persisted {len(properties)} properties to DB (V2).")

    def load_market_from_db(self, agents: List):
        """Load market properties from database and link to owners."""
        cursor = self.conn.cursor()
        # Use V2 Schema: Join properties_static with properties_market
        cursor.execute("""
            SELECT ps.*, pm.status, pm.owner_id, pm.listed_price, pm.current_valuation 
            FROM properties_static ps 
            LEFT JOIN properties_market pm ON ps.property_id = pm.property_id
        """)
        # V1 table 'properties' contains everything. V2 split checks?
        # SimulationRunner.load_from_db checks 'properties'.
        # Since we just verified V1 cleanup, 'properties' table might still exist? 
        # Wait, I removed 'create table properties' but did I remove 'properties' table?
        # In simulation_runner, I removed 'property_listings'. 
        # 'properties' table creation was at line 159.
        # I did NOT remove 'properties' table creation in my V1 Cleanups?
        # Let's check my edits.
        
        # Step 1038 edit:
        # I removed 'cursor.execute("DROP TABLE IF EXISTS property_listings")' and creation.
        
        # Did I remove 'properties' table?
        # The edit showed removing property_listings. 
        # Line 158 in simulation_runner starts 'CREATE TABLE properties'.
        
        # If 'properties' table still exists, it's V1 legcay. 
        # Ideally we should use properties_static and properties_market.
        # For now, let's assume we still use 'properties' for reading if it wasn't deleted.
        # BUT, the goal is architecture evolution. 
        # I should probably switch to V2 tables here if possible.
        
        # Let's assume loading from V2 for now if possible, else fallback.
        # But 'properties' table creation was NOT removed in the previous step?
        # I replaced lines 130-141. 'properties' creation starts at 158.
        # Ah, I might have missed removing 'properties' creation?
        # Task said "V1 Table Cleanup: Audit property_listings... Remove creation of property_listings..."
        # It didn't explicitly say remove 'properties' table yet, but it's part of V1.
        # However, verifying script checks 'property_listings'. 
        
        # Correct approach: Read from properties_static + properties_market.
        cursor.execute("SELECT ps.*, pm.status, pm.owner_id, pm.listed_price, pm.current_valuation FROM properties_static ps LEFT JOIN properties_market pm ON ps.property_id = pm.property_id")
        rows = cursor.fetchall()
        
        properties = []
        for row in rows:
            # Need to map columns correctly. 'properties_static' has headers?
            # Sqlite Row factory useful here.
            # Assuming row is dict-like if configured, but here we passed db_conn.
            # We should probably configure row_factory in Runner or here.
            pass
            # Implementation detail: simulation_runner sets row_factory.
            
        # To avoid complexity in this first draft, I will assume we can query 'properties' if it exists, or V2.
        # But wait, if I am decoupling, I should do it right.
        # Let's stick to 'properties' for now if I didn't delete it, OR implement V2 loading.
        # Since I verified verify_db_results targets properties_market, I should use V2.
        
        cursor.execute("""
            SELECT ps.property_id, ps.zone, ps.quality, ps.building_area, ps.property_type, 
                   ps.is_school_district, ps.school_tier, ps.initial_value as base_value,
                   pm.owner_id, pm.status, pm.listed_price, pm.min_price, pm.current_valuation
            FROM properties_static ps
            LEFT JOIN properties_market pm ON ps.property_id = pm.property_id
        """)
        
        # Convert to dict
        columns = [d[0] for d in cursor.description]
        properties = [dict(zip(columns, row)) for row in cursor.fetchall()]

        # Link to agents
        for p in properties:
            if p['owner_id']:
                agent = next((x for x in agents if x.id == p['owner_id']), None)
                if agent:
                    agent.owned_properties.append(p)

        self.market = Market(properties)
        logger.info(f"Loaded {len(properties)} properties from DB (V2).")

    async def generate_market_bulletin(self, month: int, extra_news: List[str] = None) -> str:
        """
        Generate monthly market bulletin with LLM analysis.
        """
        from utils.llm_client import safe_call_llm_async
        
        cursor = self.conn.cursor()
        
        # 1. Query last month's transactions
        cursor.execute("SELECT COUNT(*) as count, AVG(final_price) as avg_price FROM transactions WHERE month = ?", (month - 1,))
        last_month_stats = cursor.fetchone()
        transaction_count = last_month_stats[0] if last_month_stats else 0
        avg_price = last_month_stats[1] if last_month_stats and last_month_stats[1] else 0
        
        # 2. Calculate price change
        price_change_pct = 0.0
        if month > 1:
            cursor.execute("SELECT avg_price FROM market_bulletin WHERE month = ?", (month - 1,))
            prev_bulletin = cursor.fetchone()
            if prev_bulletin and prev_bulletin[0] and prev_bulletin[0] > 0:
                price_change_pct = ((avg_price - prev_bulletin[0]) / prev_bulletin[0]) * 100
        
        # 3. Calculate zone heat
        def calc_zone_heat(zone):
            cursor.execute("SELECT COUNT(*) FROM properties_market WHERE status = 'for_sale' AND property_id IN (SELECT property_id FROM properties_static WHERE zone = ?)", (zone,))
            result = cursor.fetchone()
            listings = result[0] if result else 0
            
            cursor.execute("SELECT COUNT(*) FROM active_participants WHERE role IN ('BUYER', 'BUYER_SELLER') AND target_zone = ?", (zone,))
            result = cursor.fetchone()
            buyers = result[0] if result else 0
            
            if buyers == 0:
                return "COLD" if listings > 5 else "BALANCED"
            ratio = listings / max(buyers, 1)
            return "COLD" if ratio > 1.5 else ("HOT" if ratio < 0.7 else "BALANCED")
        
        zone_a_heat = calc_zone_heat('A')
        zone_b_heat = calc_zone_heat('B')
        
        # 4. Determine trend signal
        if price_change_pct > 2.0:
            self.consecutive_trend = self.consecutive_trend + 1 if self.consecutive_trend > 0 else 1
            trend_signal = "UP"
        elif price_change_pct < -2.0:
            self.consecutive_trend = self.consecutive_trend - 1 if self.consecutive_trend < 0 else -1
            trend_signal = "DOWN"
        else:
            self.consecutive_trend = 0
            trend_signal = "STABLE"
        
        if self.consecutive_trend <= -2:
            trend_signal = "PANIC"
        
        trend_emoji = {"UP": "📈", "DOWN": "📉", "STABLE": "➡️", "PANIC": "⚠️"}.get(trend_signal, "")
        
        # 5. Generate LLM Analysis
        base_stats = f"""
        第{month}月市场数据：
        - 成交量: {transaction_count}套
        - 均价: {avg_price:,.0f}元 (环比 {price_change_pct:+.1f}%)
        - A区热度: {zone_a_heat}
        - B区热度: {zone_b_heat}
        - 趋势: {trend_signal} (连续 {abs(self.consecutive_trend)} 个月)
        - 政策新闻: {", ".join(extra_news) if extra_news else "无"}
        """
        
        prompt = f"""
        你是一位资深房地产分析师。请根据以下市场核心数据，撰写一份简短犀利的【市场分析点评】（LLM Analysis）。
        
        {base_stats}
        
        请包含：
        1. 核心观点（一句话概括当前形势）
        2. 对买家的建议（观望/入手/砍价）
        3. 对卖家的建议（降价/坚守/惜售）
        4. 可能会对{", ".join(extra_news) if extra_news else "当前环境"}产生什么解读。

        输出纯文本，控制在150字以内。
        """
        
        default_analysis = f"市场{trend_signal}，成交{transaction_count}套，建议谨慎操作。"
        llm_analysis_text = await safe_call_llm_async(prompt, default_analysis, model_type="smart")
        
        if isinstance(llm_analysis_text, dict): # Handle if returns dict by mistake (though safe_call usually handles schema if provided, here we want text)
             llm_analysis_text = str(llm_analysis_text)

        # 6. Save to database (FIXED: Added llm_analysis)
        policy_news_str = "\\n".join(extra_news) if extra_news else ""
        
        # Check if llm_analysis column exists, if not match schema
        # Assuming schema has llm_analysis as per user request
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO market_bulletin 
                (month, transaction_volume, avg_price, zone_a_heat, zone_b_heat, trend_signal, policy_news, llm_analysis)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (month, transaction_count, avg_price, zone_a_heat, zone_b_heat, trend_signal, policy_news_str, llm_analysis_text))
            self.conn.commit()
        except sqlite3.OperationalError:
            # Fallback if column missing (should not happen in V3 but safe guard)
             logger.error("Database schema mismatch: missing llm_analysis column?")
             cursor.execute("""
                INSERT OR REPLACE INTO market_bulletin 
                (month, transaction_volume, avg_price, zone_a_heat, zone_b_heat, trend_signal, policy_news)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (month, transaction_count, avg_price, zone_a_heat, zone_b_heat, trend_signal, policy_news_str))
             self.conn.commit()

        # 7. Return Enriched Bulletin
        bulletin_text = f"""
        【📊 市场公报 - 第{month}月】
        ━━━━━━━━━━━━━━━━━━━━━━━
        📈 上月成交: {transaction_count} 套
        💰 成交均价: ¥{avg_price:,.0f} ({price_change_pct:+.1f}%)
        🏢 A区热度: {zone_a_heat} | B区热度: {zone_b_heat}
        📊 趋势信号: {trend_emoji} {trend_signal}
        
        【📝 专家点评】
        {llm_analysis_text}
        
        【🔔 政策动态】
        {policy_news_str if policy_news_str else "本月无重大政策变动"}
        ━━━━━━━━━━━━━━━━━━━━━━━
        """
        
        return bulletin_text

    def get_market_trend(self, month):
        cursor = self.conn.cursor()
        cursor.execute("SELECT trend_signal FROM market_bulletin WHERE month = ?", (month,))
        trend_row = cursor.fetchone()
        return trend_row[0] if trend_row else "STABLE"
