from langchain_core.runnables import RunnableLambda
from src.workflow.state import AgentState

async def introduction_node(state: AgentState):
    # In a real CLI/Chat app, this would stream to stdout or return a message.
    # For now, we simulate the interaction.
    intro_msg = "سلام! من دستیار مالی هوشمند شما هستم. لطفاً نام نماد مورد نظر خود را وارد کنید."
    print(intro_msg)
    
    # Simulating user input for the symbol 'فملی' as per the mock data requirement
    symbol = "فملی"
    print(f"کاربر: {symbol}")
    
    return {"symbol": symbol}
