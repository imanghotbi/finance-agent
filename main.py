import asyncio
from src.workflow.graph_builder import app
from src.core.logger import logger

async def main():
    target_symbol = "فملی"
    logger.info(f"Starting analysis for {target_symbol}")
    
    initial_state = {"symbol": target_symbol}
    
    # Run the graph
    try:
        result = await app.ainvoke(initial_state)
        
        print("\n\n==================================================")
        print("FINAL REPORT")
        print("==================================================\n")
        print(result.get("final_report", "No report generated."))
    except Exception as e:
        logger.error(f"Execution failed: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())

