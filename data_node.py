import asyncio
from datetime import datetime
from typing import Optional

from mongo_manger import MongoManager
from prepare_data import StockAnalysisPipeline
from logger import logger

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

async def run_orchestrator(symbol: str):
    """
    Orchestrates the check and execution flow.
    """
    logger.info("--- 🏁 Starting Orchestrator ---")
    
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
    else:
        logger.info(f"zzz No action needed for {symbol}.")

    logger.info("--- 🏁 Orchestrator Finished ---")

if __name__ == "__main__":
    # You can change this target symbol or load it from args
    TARGET_SYMBOL = "فملی"
    
    try:
        asyncio.run(run_orchestrator(TARGET_SYMBOL))
    except KeyboardInterrupt:
        logger.info("🛑 Execution stopped by user.")
    except Exception as e:
        logger.critical(f"❌ Unhandled top-level error: {e}")