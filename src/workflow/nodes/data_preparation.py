import asyncio
from datetime import datetime

from src.core.mongo_manger import MongoManager
from src.workflow.state import AgentState
from src.services.prepare_data import StockAnalysisPipeline
from src.core.logger import logger


async def get_latest_symbol_data(symbol: str) -> dict | None:
    """Fetch the latest stored analysis document for a symbol."""
    mongo = MongoManager()

    try:
        return await mongo.read_data(
            {"symbol": symbol},
            limit=1,
            sort=[("analysis_datetime", -1)],
        )
    finally:
        mongo.close()

async def should_run_pipeline(symbol: str) -> bool:
    """
    Checks the database to determine if the pipeline needs to run.
    Returns True if:
      1. The symbol does not exist in the DB.
      2. The symbol exists but 'analysis_datetime' is not from today.
    """
    try:
        document = await get_latest_symbol_data(symbol)

        if not document:
            logger.info(f"🔎 Symbol '{symbol}' not found in DB. Scheduling analysis.")
            return True

        # Check timestamp
        last_analysis_ts = document.get('analysis_datetime')
        
        if not last_analysis_ts:
            logger.warning(f"⚠️ Symbol '{symbol}' exists but has no timestamp. Scheduling analysis.")
            return True

        # Ensure last_analysis_ts is a datetime object (Motor returns datetime objects)
        if isinstance(last_analysis_ts, str):
            try:
                last_analysis_ts = datetime.fromisoformat(last_analysis_ts)
            except ValueError:
                logger.error(f"❌ Invalid date format for '{symbol}'. Scheduling analysis.")
                return True

        # Compare dates
        today = datetime.now().date()
        analysis_date = last_analysis_ts.date()

        if analysis_date < today:
            logger.info(f"📉 Data for '{symbol}' is outdated ({analysis_date}). Scheduling update for {today}.")
            return True
        elif analysis_date == today:
            logger.info(f"✅ Data for '{symbol}' is already up-to-date ({today}). Skipping.")
            return False
        else:
            # Edge case: Future date?
            logger.warning(f"⚠️ Future date detected for '{symbol}'. Skipping to be safe.")
            return False

    except Exception as e:
        logger.error(f"❌ Error checking DB status for '{symbol}': {e}", exc_info=True)
        logger.warning(f"⚠️ Falling back to pipeline execution for '{symbol}' because cache validation failed.")
        return True

async def run_orchestrator(state: AgentState):
    """
    Orchestrates the check and execution flow.
    """
    symbol = state["symbol"]
    logger.info(f"--- 🏁 Starting Data Orchestrator for {symbol} ---")
    
    # 1. Check Condition
    run_required = await should_run_pipeline(symbol)

    # 2. Execute if needed
    if run_required:
        try:
            logger.info(f"🚀 Initializing Pipeline for: {symbol}")
            pipeline = StockAnalysisPipeline(symbol)
            await pipeline.execute()
            logger.info(f"✨ Pipeline execution finished for: {symbol}")
        except Exception as e:
            logger.critical(f"🔥 Pipeline execution failed: {e}", exc_info=True)

    # 3. Load the latest stored data regardless of whether we reused cache or refreshed it.
    symbol_data = await get_latest_symbol_data(symbol)
    if not symbol_data:
        raise RuntimeError(f"No stored analysis data found for symbol '{symbol}' after preparation.")

    logger.info("--- 🏁 Orchestrator Finished ---")
    return {
        "symbol": symbol_data["symbol"],
        "short_name": symbol_data.get("short_name", ""),
        "price_history": symbol_data.get("price_history", []),
        "technical_data" : symbol_data['technical_analysis'],
        "fundamental_data" : {
            "symbol_name": symbol_data["symbol"],
            "name" : symbol_data["short_name"],
            "market_data" : symbol_data["market_data"],
            "fundamental_analysis" : symbol_data["fundamental_analysis"],
            "codal": symbol_data.get("news_announcements", {}).get("codal", [])
        },
        "news_social_data": {
            "symbol": symbol_data.get("symbol"),
            "short_name": symbol_data.get("short_name"),
            "analysis_date": datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
            "rapid_tweet": symbol_data.get("social_post", {}).get("rapid_tweets", []),
            "latest_sahamyab_tweet": symbol_data.get("social_post", {}).get("latest_sahamyab_tweet", []),
            "news": symbol_data.get("news_announcements", {}).get("news", [])
        }
    }




if __name__ == "__main__":
    # You can change this target symbol or load it from args
    TARGET_SYMBOL = "فملی"
    
    try:
        data = asyncio.run(run_orchestrator({"symbol": TARGET_SYMBOL}))
    except KeyboardInterrupt:
        logger.info("🛑 Execution stopped by user.")
    except Exception as e:
        logger.critical(f"❌ Unhandled top-level error: {e}")
