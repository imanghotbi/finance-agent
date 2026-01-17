from langgraph.graph import StateGraph, END

from src.workflow.state import AgentState, TechnicalState, FundamentalState, NewsSocialState
from src.workflow.nodes.technical import (
    trend_agent_node,
    oscillator_agent_node,
    volatility_agent_node,
    volume_agent_node,
    sr_agent_node,
    technical_consensus_node,
    smart_money_agent_node
)
from src.workflow.nodes.fundamental import (
    balance_sheet_node,
    earnings_quality_node,
    valuation_node,
    fundamental_consensus_node,
    codal_agent_node,
)
from src.workflow.nodes.social_news import (
    twitter_agent_node,
    sahamyab_agent_node,
    news_agent_node,
    social_news_consensus_node,
)
from src.workflow.nodes.reporter import reporter_node
from src.workflow.nodes.introduction import introduction_node
from src.workflow.nodes.data_preparation import run_orchestrator as data_preparation_node


# ==========================================
# 1. Technical Sub-Graph
# ==========================================
def _dispatch_technical(_):
    return ["trend_agent", "oscillator_agent", "volatility_agent", "volume_agent", "sr_agent" , "smart_money_agent"]

def build_technical_graph():
    workflow = StateGraph(TechnicalState)
    
    # Nodes
    workflow.add_node("trend_agent", trend_agent_node)
    workflow.add_node("oscillator_agent", oscillator_agent_node)
    workflow.add_node("volatility_agent", volatility_agent_node)
    workflow.add_node("volume_agent", volume_agent_node)
    workflow.add_node("sr_agent", sr_agent_node)
    workflow.add_node("smart_money_agent", smart_money_agent_node)
    workflow.add_node("technical_consensus", technical_consensus_node)

    # Dispatcher (Fan-out)
    workflow.add_node("dispatch_tech", lambda x: x)
    workflow.set_entry_point("dispatch_tech")
    
    workflow.add_conditional_edges(
        "dispatch_tech",
        _dispatch_technical,
        {
            "trend_agent": "trend_agent",
            "oscillator_agent": "oscillator_agent",
            "volatility_agent": "volatility_agent",
            "volume_agent": "volume_agent",
            "sr_agent": "sr_agent",
            "smart_money_agent" : "smart_money_agent"
        },
    )

    # Fan-in to Consensus
    workflow.add_edge("trend_agent", "technical_consensus")
    workflow.add_edge("oscillator_agent", "technical_consensus")
    workflow.add_edge("volatility_agent", "technical_consensus")
    workflow.add_edge("volume_agent", "technical_consensus")
    workflow.add_edge("sr_agent", "technical_consensus")
    workflow.add_edge("smart_money_agent", "technical_consensus")
    
    workflow.add_edge("technical_consensus", END)

    return workflow.compile()

# ==========================================
# 2. Fundamental Sub-Graph
# ==========================================
def _dispatch_fundamental(_):
    return ["balance_sheet_agent", "earnings_quality_agent", "valuation_agent", "codal_agent"]

def build_fundamental_graph():
    workflow = StateGraph(FundamentalState)
    
    # Nodes
    workflow.add_node("balance_sheet_agent", balance_sheet_node)
    workflow.add_node("earnings_quality_agent", earnings_quality_node)
    workflow.add_node("valuation_agent", valuation_node)
    workflow.add_node("codal_agent", codal_agent_node)
    workflow.add_node("fundamental_consensus", fundamental_consensus_node)

    # Dispatcher
    workflow.add_node("dispatch_fund", lambda x: x)
    workflow.set_entry_point("dispatch_fund")
    
    workflow.add_conditional_edges(
        "dispatch_fund",
        _dispatch_fundamental,
        {
            "balance_sheet_agent": "balance_sheet_agent",
            "earnings_quality_agent": "earnings_quality_agent",
            "valuation_agent": "valuation_agent",
            "codal_agent": "codal_agent",
        },
    )

    # Fan-in
    workflow.add_edge("balance_sheet_agent", "fundamental_consensus")
    workflow.add_edge("earnings_quality_agent", "fundamental_consensus")
    workflow.add_edge("valuation_agent", "fundamental_consensus")
    workflow.add_edge("codal_agent", "fundamental_consensus")
    
    workflow.add_edge("fundamental_consensus", END)

    return workflow.compile()

# ==========================================
# 3. Social & News Sub-Graph
# ==========================================
def _dispatch_social_news(_):
    return ["twitter_agent", "sahamyab_agent", "news_agent"]

def build_social_news_graph():
    workflow = StateGraph(NewsSocialState)
    
    # Nodes
    workflow.add_node("twitter_agent", twitter_agent_node)
    workflow.add_node("sahamyab_agent", sahamyab_agent_node)
    workflow.add_node("news_agent", news_agent_node)
    workflow.add_node("social_news_consensus", social_news_consensus_node)

    # Dispatcher
    workflow.add_node("dispatch_social", lambda x: x)
    workflow.set_entry_point("dispatch_social")
    
    workflow.add_conditional_edges(
        "dispatch_social",
        _dispatch_social_news,
        {
            "twitter_agent": "twitter_agent",
            "sahamyab_agent": "sahamyab_agent",
            "news_agent": "news_agent",
        },
    )

    # Fan-in
    workflow.add_edge("twitter_agent", "social_news_consensus")
    workflow.add_edge("sahamyab_agent", "social_news_consensus")
    workflow.add_edge("news_agent", "social_news_consensus")
    
    workflow.add_edge("social_news_consensus", END)

    return workflow.compile()

# ==========================================
# 4. Master Graph
# ==========================================
def _dispatch_master(_):
    return ["technical_graph", "fundamental_graph", "social_news_graph"]

def build_graph():
    # We use AgentState which has both Tech and Fund keys
    workflow = StateGraph(AgentState)
    
    # Add Nodes
    workflow.add_node("introduction_node", introduction_node)
    workflow.add_node("data_preparation", data_preparation_node)
    
    # Sub-Graphs
    workflow.add_node("technical_graph", build_technical_graph())
    workflow.add_node("fundamental_graph", build_fundamental_graph())
    workflow.add_node("social_news_graph", build_social_news_graph())
    
    # Reporter
    workflow.add_node("reporter_agent", reporter_node)

    # Entry Point
    workflow.set_entry_point("introduction_node")
    
    # Flow
    workflow.add_edge("introduction_node", "data_preparation")
    workflow.add_edge("data_preparation", "dispatch_master")
    
    # Dispatcher for Parallel Execution
    workflow.add_node("dispatch_master", lambda x: x)
    
    workflow.add_conditional_edges(
        "dispatch_master",
        _dispatch_master,
        {
            "technical_graph": "technical_graph",
            "fundamental_graph": "fundamental_graph",
            "social_news_graph": "social_news_graph",
        },
    )

    # Join at Reporter
    workflow.add_edge("technical_graph", "reporter_agent")
    workflow.add_edge("fundamental_graph", "reporter_agent")
    workflow.add_edge("social_news_graph", "reporter_agent")
    
    workflow.add_edge("reporter_agent", END)

    return workflow.compile()

app = build_graph()
