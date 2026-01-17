import asyncio
from langgraph.types import Command
from src.workflow.graph_builder import app
from src.core.logger import logger

async def main():
    logger.info("Starting interactive session...")
    
    # Unique thread ID for this session
    config = {"configurable": {"thread_id": "session_1"}}
    
    # Initial state
    initial_input = {"messages": [], "symbol": ""}
    
    # 1. Start the graph
    # It will run until it hits the interrupt() in input_node
    
    logger.info("Initializing Agent...")
    try:
        # We start with initial input. 
        # If it stops at interrupt, it raises GraphInterrupt (in sync) or returns partial state (async)?
        # For async, it usually just returns.
        await app.ainvoke(initial_input, config=config)
    except Exception:
        # It's expected to stop, but let's just proceed to the loop
        pass
    
    while True:
        # Check current status
        snapshot = await app.aget_state(config)
        
        # If no next steps and no interrupts, we are done
        if not snapshot.next and not (snapshot.tasks and snapshot.tasks[0].interrupts):
            print("\n\n==================================================")
            print("FINAL REPORT")
            print("==================================================\n")
            result = snapshot.values
            print(result.get("final_report", "No report generated."))
            break
            
        # Check if we are paused at an interrupt
        if snapshot.tasks and snapshot.tasks[0].interrupts:
            # We are waiting for input
            try:
                # The agent has likely printed its message (via logger or inside agent_node).
                # But since agent_node returns a message, we might want to print the last AI message
                # if we are in a CLI.
                messages = snapshot.values.get("messages", [])
                if messages:
                    last_msg = messages[-1]
                    if hasattr(last_msg, 'content') and last_msg.content:
                        print(f"\n🤖 Agent: {last_msg.content}")

                user_text = input("\n[You] > ")
            except (EOFError, KeyboardInterrupt):
                print("Exiting...")
                break
            
            if not user_text.strip():
                print("Please enter text.")
                continue
            
            # Resume execution by providing the value for the interrupt
            await app.ainvoke(Command(resume=user_text), config=config)
        else:
            # Should not happen if logic is correct, but safe fallback
            # e.g. if it paused for some other reason
            logger.info("Graph paused but no interrupt found. Resuming...")
            await app.ainvoke(None, config=config)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Execution stopped by user.")
    except Exception as e:
        logger.error(f"Execution failed: {e}", exc_info=True)
