import asyncio
from langgraph.types import Command
from src.workflow.graph_builder import app
from src.core.logger import logger

async def main():
    logger.info("Starting Finance Agent System...")
    config = {"configurable": {"thread_id": "session_1"}}
    initial_input = {"messages": [], "symbol": ""}

    # Use a flag to handle the first run vs resumes
    inputs = initial_input 

    while True:
        async for event in app.astream(inputs, config, stream_mode="values"):
            # Update local tracking if needed
            snapshot = await app.aget_state(config)
            
        # Check for interrupts after the stream finishes/pauses
        snapshot = await app.aget_state(config)
        
        if snapshot.next and snapshot.tasks and snapshot.tasks[0].interrupts:
            # Print the last message from AI
            messages = snapshot.values.get("messages", [])
            if messages:
                print(f"\n🤖 Agent: {messages[-1].content}")

            user_text = input("\n[You] > ")
            logger.info(f"User interaction: {user_text}")
            
            # CRITICAL: For the next iteration, send the Command as the input
            inputs = Command(resume=user_text)
        else:
            # Graph finished naturally
            logger.info("Workflow completed naturally.")
            print("\nDone!")
            break

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Execution stopped by user.")
    except Exception as e:
        logger.error(f"Execution failed: {e}", exc_info=True)
