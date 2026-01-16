import asyncio
from datetime import datetime
from typing import Optional

from src.core.mongo_manger import MongoManager
from src.workflow.state import AgentState
from src.services.prepare_data import StockAnalysisPipeline
from src.core.logger import logger
from src.workflow.nodes.mock_data import mock_data

async def should_run_pipeline(symbol: str) -> bool:
    """
    Checks the database to determine if the pipeline needs to run.
    Returns True if:
      1. The symbol does not exist in the DB.
      2. The symbol exists but 'analysis_datetime' is not from today.
    """
    mongo = MongoManager()
    
    try:
        query = {"symbol": symbol}
        document = await mongo.read_data(query, limit=1)

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
        return False
    finally:
        # strict resource cleanup
        mongo.close()

async def run_orchestrator(state: AgentState):
    """
    Orchestrates the check and execution flow.
    """
    symbol = state["symbol"]
    logger.info(f"--- 🏁 Starting Mock Orchestrator for {symbol} ---")
    
    # 1. Check Condition
    # run_required = await should_run_pipeline(symbol) ##TODO uncomment this after mongo is okay
    run_required = False
    # 2. Execute if needed
    if run_required:
        try:
            logger.info(f"🚀 Initializing Pipeline for: {symbol}")
            pipeline = StockAnalysisPipeline(symbol)
            await pipeline.execute() ##TODO store and return data
            logger.info(f"✨ Pipeline execution finished for: {symbol}")
        except Exception as e:
            logger.critical(f"🔥 Pipeline execution failed: {e}", exc_info=True)
    else:
        ##TODO read data from mongo if run_required equals false
        # logger.info(f"zzz No action needed for {symbol}.") ##TODO this is temperory
        symbol_data = await mock_data()

    logger.info("--- 🏁 Orchestrator Finished ---")
    return {
        "technical_data" : symbol_data['technical_analysis'],
        "fundamental_data" : {
            "symbol_name": symbol_data["symbol"],
            "name" : symbol_data["short_name"],
            "market_data" : symbol_data["market_data"],
            "fundamental_analysis" : symbol_data["fundamental_analysis"]
        },
        "news_social_data": {
            "symbol": symbol_data.get("symbol"),
            "short_name": symbol_data.get("short_name"),
            "analysis_date": datetime.now().strftime('%Y-%m-%dT%H:%M:%s'),
            "rapid_tweet": symbol_data.get("social_post", {}).get("rapid_tweets", []),
            "latest_sahamyab_tweet": symbol_data.get("social_post", {}).get("latest_sahamyab_tweet", []),
            "news": symbol_data.get("news_announcements", {}).get("news", []),
            "search_tavily_answer": symbol_data.get("search", {}).get("tavily", {}).get("answer", "")
        }
    }




if __name__ == "__main__":
    # You can change this target symbol or load it from args
    TARGET_SYMBOL = "فملی"
    
    try:
        asyncio.run(run_orchestrator(TARGET_SYMBOL))
    except KeyboardInterrupt:
        logger.info("🛑 Execution stopped by user.")
    except Exception as e:
        logger.critical(f"❌ Unhandled top-level error: {e}")