from langgraph.graph import StateGraph, END

from src.workflow.state import AgentState, TechnicalState, FundamentalState
from src.workflow.nodes.technical import (
    trend_agent_node,
    oscillator_agent_node,
    volatility_agent_node,
    volume_agent_node,
    sr_agent_node,
    technical_consensus_node,
)
from src.workflow.nodes.fundamental import (
    balance_sheet_node,
    earnings_quality_node,
    valuation_node,
    fundamental_consensus_node,
)
from src.workflow.nodes.reporter import reporter_node


# ==========================================
# 1. Technical Sub-Graph
# ==========================================
def _dispatch_technical(_):
    return ["trend_agent", "oscillator_agent", "volatility_agent", "volume_agent", "sr_agent"]

def build_technical_graph():
    workflow = StateGraph(TechnicalState)
    
    # Nodes
    workflow.add_node("trend_agent", trend_agent_node)
    workflow.add_node("oscillator_agent", oscillator_agent_node)
    workflow.add_node("volatility_agent", volatility_agent_node)
    workflow.add_node("volume_agent", volume_agent_node)
    workflow.add_node("sr_agent", sr_agent_node)
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
        },
    )

    # Fan-in to Consensus
    # Note: In LangGraph, if multiple nodes point to one, it triggers on each.
    # Ideally, we want to wait. But for now, we assume the consensus node
    # can handle partial updates or we rely on the final state.
    # However, to be robust, we'll let them write to state, and we can force synchronization
    # if we used a specific 'join' pattern, but simple edges work if state is additive.
    # Realistically, for true barrier synchronization in LangGraph without sub-supersteps,
    # we usually just point them to the next node.
    workflow.add_edge("trend_agent", "technical_consensus")
    workflow.add_edge("oscillator_agent", "technical_consensus")
    workflow.add_edge("volatility_agent", "technical_consensus")
    workflow.add_edge("volume_agent", "technical_consensus")
    workflow.add_edge("sr_agent", "technical_consensus")
    
    workflow.add_edge("technical_consensus", END)

    return workflow.compile()

# ==========================================
# 2. Fundamental Sub-Graph
# ==========================================
def _dispatch_fundamental(_):
    return ["balance_sheet_agent", "earnings_quality_agent", "valuation_agent"]

def build_fundamental_graph():
    workflow = StateGraph(FundamentalState)
    
    # Nodes
    workflow.add_node("balance_sheet_agent", balance_sheet_node)
    workflow.add_node("earnings_quality_agent", earnings_quality_node)
    workflow.add_node("valuation_agent", valuation_node)
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
        },
    )

    # Fan-in
    workflow.add_edge("balance_sheet_agent", "fundamental_consensus")
    workflow.add_edge("earnings_quality_agent", "fundamental_consensus")
    workflow.add_edge("valuation_agent", "fundamental_consensus")
    
    workflow.add_edge("fundamental_consensus", END)

    return workflow.compile()

# ==========================================
# 3. Master Graph
# ==========================================
def _dispatch_master(_):
    return ["technical_graph", "fundamental_graph"]

def build_graph():
    # We use AgentState which has both Tech and Fund keys
    workflow = StateGraph(AgentState)
    
    # Add Sub-Graphs as Nodes
    # NOTE: When adding a compiled graph as a node, it receives the state and returns the state.
    workflow.add_node("technical_graph", build_technical_graph())
    workflow.add_node("fundamental_graph", build_fundamental_graph())
    
    # Reporter
    workflow.add_node("reporter_agent", reporter_node)

    # Entry: Parallel Execution of Tech and Fund
    workflow.add_node("dispatch_master", lambda x: x)
    workflow.set_entry_point("dispatch_master")
    
    workflow.add_conditional_edges(
        "dispatch_master",
        _dispatch_master,
        {
            "technical_graph": "technical_graph",
            "fundamental_graph": "fundamental_graph",
        },
    )
    workflow.add_edge("fundamental_graph", "reporter_agent")
    
    workflow.add_edge("reporter_agent", END)

    return workflow.compile()

app = build_graph()