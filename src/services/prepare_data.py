import asyncio
import pandas as pd
from datetime import datetime, timedelta

# Import custom modules
from src.core.config import settings
from src.core.logger import logger
from src.core.mongo_manger import MongoManager

# Clients
from src.services.providers.rahavard import RahavardClient
from src.services.providers.sahamyab import SahamyabClient
from src.services.providers.twitter_rapid import TwitterRapidClient
from src.services.providers.tavily_search import TavilyClient

# Analyzers
from src.services.technical.trend import TrendAnalyzer
from src.services.technical.oscillator import OscillatorAnalyzer
from src.services.technical.volume import VolumeAnalyzer
from src.services.technical.volatility import VolatilityAnalyzer
from src.services.technical.sr import SupportResistanceAnalyzer
from src.services.technical.spark_trend import SparklineReporter
from src.services.technical.smart_money import SmartMoneyAnalyzer

class StockAnalysisPipeline:
    def __init__(self, symbol_name: str):
        self.symbol_name = symbol_name
        self.mongo_manager = MongoManager()
        self.rahavard_data = {}
        self.sahamyab_data = {}
        self.external_data = {}
        self.df = pd.DataFrame()

    def _transform_rahavard_to_df(self, trade_history: list) -> pd.DataFrame:
        """Internal helper to convert raw history to DataFrame."""
        try:
            if not trade_history:
                return pd.DataFrame()

            df = pd.DataFrame(trade_history)
            column_map = {
                'date_time': 'date',
                'real_close_price': 'close',
                'open_price': 'open',
                'high_price': 'high',
                'low_price': 'low',
                'volume': 'volume'
            }
            df.rename(columns=column_map, inplace=True)
            
            # Data cleaning
            if 'date' in df.columns:
                df['date'] = df.date.str.replace('da', '-')
                df['date'] = pd.to_datetime(df['date']).dt.date

            # Ensure numeric types
            cols = ['open', 'high', 'low', 'close', 'volume']
            for c in cols:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors='coerce') # coerce makes invalid parsing NaN
            
            # Drop rows with NaN in critical columns
            df.dropna(subset=['close'], inplace=True)
            return df
        except Exception as e:
            logger.error(f"⚠️ Error transforming dataframe: {e}", exc_info=True)
            return pd.DataFrame()

    def _calculate_return(self, df_raw, days_ago: int):
        """Helper to calculate past returns."""
        try:
            # Assuming df_raw is the raw list, not the pandas DF, based on original code logic
            # If df_raw is list of dicts:
            if len(df_raw) <= days_ago:
                return None
            
            current = df_raw[0]
            past = df_raw[days_ago]
            
            current_price = current.get('real_close_price', 0)
            past_price = past.get('real_close_price', 1) # avoid div by zero
            
            if past_price == 0: return 0

            return {
                'return': (current_price - past_price) / past_price,
                'start_date_time': past.get('date_time'),
                'end_date_time': current.get('date_time')
            }
        except Exception as e:
            logger.warning(f"Could not calculate return for {days_ago} days ago: {e}")
            return None

    async def fetch_rahavard_data(self):
        """Fetches critical market data. Returns False if critical failure."""
        logger.info("1️⃣ Fetching Rahavard Data...")
        try:
            async with RahavardClient() as r_client:
                symbol_info = await r_client.get_symbol_id(self.symbol_name)
                
                if not symbol_info:
                    logger.error(f"❌ Symbol {self.symbol_name} not found in Rahavard.")
                    return False

                asset_id = symbol_info['id']
                logger.debug(f"Asset ID: {asset_id}")

                # Gather all data points
                results = await asyncio.gather(
                    r_client.get_trade_history(asset_id, count=365),
                    r_client.get_asset_details(asset_id),
                    r_client.get_pivot_indicators(asset_id),
                    r_client.get_balance_sheet(asset_id),
                    r_client.get_profit_loss(asset_id),
                    r_client.get_cash_flow(asset_id),
                    r_client.get_financial_ratios(asset_id),
                    r_client.get_news(asset_id),
                    r_client.get_symbol_trade_detail_history(asset_id , count=7),
                    return_exceptions=True # Prevent one failure from crashing all
                )

                # Unpack and check for exceptions in results
                keys = ['history', 'details', 'pivots', 'balance', 'profit_loss', 'cash_flow', 'ratios', 'news' , 'real_legal_trade']
                self.rahavard_data = {'info': symbol_info}
                
                for key, result in zip(keys, results):
                    if isinstance(result, Exception):
                        logger.error(f"⚠️ Error fetching {key}: {result}")
                        self.rahavard_data[key] = None
                    else:
                        self.rahavard_data[key] = result

                # Post-processing returns
                if self.rahavard_data.get('history'):
                    self.rahavard_data['details']['returns'] = {}
                    periods = {'return_7_d': 6, 'return_1_m': 30, 'return_3_m': 90}
                    for name, days in periods.items():
                        res = self._calculate_return(self.rahavard_data['history'], days)
                        if res:
                            self.rahavard_data['details']['returns'][name] = res

                return True

        except Exception as e:
            logger.critical(f"🔥 Critical error in Rahavard Fetch: {e}", exc_info=True)
            return False

    async def fetch_sahamyab_data(self):
        """Fetches social/sentiment data."""
        logger.info("2️⃣ Fetching Sahamyab Data...")
        try:
            async with SahamyabClient() as s_client:
                results = await asyncio.gather(
                    s_client.get_trade_info(self.symbol_name),
                    s_client.get_overall_info(self.symbol_name),
                    s_client.get_tweets(self.symbol_name),
                    s_client.get_codal_notices(self.symbol_name),
                    return_exceptions=True
                )
                
                # Check for exceptions
                cleaned_results = []
                for res in results:
                    if isinstance(res, Exception):
                        logger.warning(f"⚠️ Sahamyab sub-task failed: {res}")
                        cleaned_results.append({}) # Default empty dict
                    else:
                        cleaned_results.append(res)

                self.sahamyab_data = {
                    "trade_info": cleaned_results[0],
                    "symbol_info": cleaned_results[1],
                    "tweets": cleaned_results[2],
                    "codal": cleaned_results[3]
                }
        except Exception as e:
            logger.error(f"❌ Error in Sahamyab Fetch: {e}", exc_info=True)

    async def fetch_external_search(self):
        """Fetches Twitter RapidAPI and Tavily. Non-critical."""
        logger.info("3️⃣ Fetching External Search Data (Twitter/Tavily)...")
        
        # Twitter Rapid API
        try:
            async with TwitterRapidClient(base_url=settings.rapid_base_url) as rapid_twitter:
                end_date = datetime.now().date()
                start_date = end_date - timedelta(days=90)
                self.external_data['rapid_tweets'] = await rapid_twitter.search_tweets(
                    query=self.symbol_name, start_date=start_date, end_date=end_date
                )
        except Exception as e:
            logger.warning(f"⚠️ Twitter RapidAPI failed: {e}")
            self.external_data['rapid_tweets'] = []

        # Tavily Search
        try:
            async with TavilyClient(api_key=settings.tavily_api_key.get_secret_value(), base_url=settings.tavily_base_url, proxy_url=settings.proxy_url) as tavily:
                asset_name = self.rahavard_data.get('details', {}).get('name', '')
                query = f"تحلیل بنیادی و تکنیکال و بررسی نماد {self.symbol_name} یا {asset_name}"
                end_date = datetime.now().date()
                start_date = end_date - timedelta(days=30)
                self.external_data['tavily'] = await tavily.search(query=query, start_date=start_date, end_date=end_date)
        except Exception as e:
            logger.warning(f"⚠️ Tavily Search failed: {e}")
            self.external_data['tavily'] = None

    def run_technical_analysis(self):
        """Runs the technical analysis logic."""
        logger.info("⚙️ Running Technical Analysis ...")
        try:
            self.df = self._transform_rahavard_to_df(self.rahavard_data.get('history'))
            
            if self.df.empty or len(self.df) < 50:
                logger.error("❌ Insufficient historical data for technical analysis.")
                return None

            current_price = int(self.df['close'].iloc[0])
            
            # Initialize Agents
            trend_agent = TrendAnalyzer(self.df, symbol=self.symbol_name)
            osc_agent = OscillatorAnalyzer(self.df, symbol=self.symbol_name)
            vol_agent = VolumeAnalyzer(self.df, symbol=self.symbol_name)
            volatility_agent = VolatilityAnalyzer(self.df, symbol=self.symbol_name)
            sr_agent = SupportResistanceAnalyzer(
                self.df, 
                symbol=self.symbol_name, 
                raw_pivots_data=self.rahavard_data.get('pivots')
            )
            spark_agent = SparklineReporter()
            smart_money = SmartMoneyAnalyzer(self.rahavard_data.get('real_legal_trade') , window_size=7)

            # Generate Reports
            technicals = {
                "trend": trend_agent.analyze(current_price),
                "oscillators": osc_agent.analyze(current_price),
                "volume": vol_agent.analyze(current_price),
                "volatility": volatility_agent.analyze(current_price),
                "support_resistance": sr_agent.analyze(current_price),
                "visuals": spark_agent.create_report(
                    self.df[['open', 'close', 'volume']].to_dict('records'), 
                    period=14
                ),
                "smart_money": smart_money.analyze()
            }
            return technicals, current_price
        except Exception as e:
            logger.error(f"❌ Error during technical analysis execution: {e}", exc_info=True)
            return None, None

    def _merge_sahamyab_extra_data(self):
        """Merges extra sahamyab fields into rahavard details structure."""
        try:
            details = self.rahavard_data.get('details', {})
            trade_info = self.sahamyab_data.get('trade_info', {})
            symbol_info = self.sahamyab_data.get('symbol_info', {})

            if details and trade_info:
                details['eps'] = details.get('eps', {})
                details['eps']['group_pe'] = trade_info.get('group_pe')
                details['index_affect'] = trade_info.get('index_affect')
                details['liquidity_coefficient'] = trade_info.get('liquidity_coefficient')
                details['correlation_gold_fund'] = trade_info.get('correlation_gold_fund')
                details['correlation_main_index'] = trade_info.get('correlation_main_index')
                
            if details and symbol_info:
                details['category_name'] = symbol_info.get('section_name')
                details['last_trade_summary'] = details.get('last_trade_summary', {})
                details['last_trade_summary']['queue'] = symbol_info.get('queue')
                details['eps']['estimated_eps'] = symbol_info.get('estimated_eps')
                
        except Exception as e:
            logger.warning(f"⚠️ Error merging extra data: {e}")

    async def execute(self):
        """Main execution method."""
        logger.info(f"🚀 Starting Pipeline for Symbol: {self.symbol_name}")
        
        # 1. Critical Data
        success = await self.fetch_rahavard_data()
        if not success:
            logger.error("🛑 Stopping pipeline due to missing Rahavard data.")
            return

        # 2. Secondary Data (Parallel)
        await asyncio.gather(
            self.fetch_sahamyab_data(),
            self.fetch_external_search()
        )

        # 3. Technical Analysis
        technicals, current_price = self.run_technical_analysis()
        if not technicals:
            logger.error("🛑 Stopping pipeline due to Technical Analysis failure.")
            return

        # 4. Merge Data
        self._merge_sahamyab_extra_data()

        # 5. Construct Final Document
        try:
            final_document = {
                '_id': f'{self.rahavard_data["info"]["trade_symbol"]}_{self.rahavard_data["info"]["id"]}',
                "rahavard_asset_id": self.rahavard_data["info"]['id'],
                "symbol": self.rahavard_data["info"]['trade_symbol'],
                "short_name": self.rahavard_data["info"]['short_name'],
                "analysis_datetime": datetime.now(),
                "data_points_analyzed": len(self.df),
                "market_data": {
                    "current_price": current_price,
                    "general_snapshot": self.rahavard_data.get('details')
                },
                "technical_analysis": technicals,
                "fundamental_analysis": {
                    "balance_sheet": self.rahavard_data.get("balance"),
                    "profit_loss": self.rahavard_data.get("profit_loss"),
                    "cash_flow": self.rahavard_data.get("cash_flow"),
                    "financial_ratios": self.rahavard_data.get("ratios")
                },
                "social_post": {
                    "latest_sahamyab_tweet": self.sahamyab_data.get('tweets'),
                    "rapid_tweets": self.external_data.get('rapid_tweets')
                },
                "news_announcements": {
                    "news": self.rahavard_data.get('news'),
                    "codal": self.sahamyab_data.get("codal")
                },
                "search": {
                    "tavily": self.external_data.get('tavily')
                }
            }

            # 6. Save to DB
            await self.mongo_manager.upsert_data(final_document)

        except Exception as e:
            logger.critical(f"❌ Error constructing or saving final document: {e}", exc_info=True)


if __name__ == "__main__":
    target_symbol = "فملی"
    
    pipeline = StockAnalysisPipeline(target_symbol)
    
    try:
        asyncio.run(pipeline.execute())
    except KeyboardInterrupt:
        logger.info("Pipeline stopped by user.")
    except Exception as e:
        logger.critical(f"Unhandled pipeline exception: {e}", exc_info=True)