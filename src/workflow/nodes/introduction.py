from typing import Literal
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import tool
from langgraph.types import interrupt, Command
from langgraph.graph import END

from src.workflow.state import AgentState
from src.utils.llm_factory import LLMFactory
from src.core.logger import logger
from src.core.prompt import INTRODUCTION_PROMPT
##TODO add this
from langchain_core.output_parsers import StrOutputParser


# 1. Define the Tool
@tool
def set_symbol(symbol: str):
    """Call this tool when the user provides a valid Iranian stock symbol (e.g., 'فملی', 'فولاد')."""
    return symbol


async def intro_agent_node(state: AgentState):
    """
    The main agent node. It generates a response or calls a tool.
    """
    messages = state.get("messages", [])
    
    # Ensure system prompt is first
    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=INTRODUCTION_PROMPT)] + messages
    ##TODO check each llm need reason or not
    llm = LLMFactory.get_model(temperature=0.5, tools=[set_symbol])
    
    logger.info("🤖 Agent thinking...")
    response = await llm.ainvoke(messages)
    
    return {"messages": [response]}

def input_node(state: AgentState):
    """
    Node to wait for user input using interrupt.
    """
    logger.info("⏳ Waiting for user input...")
    user_input = interrupt(value="user_input")
    
    if not user_input or str(user_input).lower() in ["exit", "quit"]:
        return Command(goto=END)
    
    if not user_input:
        # Should not happen if main.py handles it, but safety check
        return None
        
    logger.info(f"👤 User Input: {user_input}")
    return {"messages": [HumanMessage(content=user_input)]}

def tool_node(state: AgentState):
    """
    Executes the tool call to update the symbol in the state.
    """
    messages = state.get("messages", [])
    last_msg = messages[-1]
    
    if not isinstance(last_msg, AIMessage) or not last_msg.tool_calls:
        logger.error("Tool node called but no tool calls found.")
        return {}
        
    tool_call = last_msg.tool_calls[0]
    symbol = tool_call["args"].get("symbol")
    
    logger.info(f"🛠️ Tool executed. Symbol set to: {symbol}")

    return {"symbol": symbol}

# 4. Conditional Logic
def should_continue(state: AgentState) -> Literal["tool_node", "input_node"]:
    """
    Decides whether to go to the tool execution (next stage) or wait for input.
    """
    messages = state.get("messages", [])
    last_msg = messages[-1]
    
    if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
        return "tool_node"
    return "input_node"