from langgraph.graph import StateGraph, END

from src.workflow.state import TechnicalState
from src.workflow.nodes.technical import (
    trend_agent_node,
    oscillator_agent_node,
    volatility_agent_node,
    volume_agent_node,
    sr_agent_node,
    technical_consensus_node,
)


def _dispatch(_):
    return ["trend_agent", "oscillator_agent", "volatility_agent", "volume_agent", "sr_agent"]


def build_technical_graph():
    # Correct Parallel Graph Construction
    parallel_workflow = StateGraph(TechnicalState)
    parallel_workflow.add_node("trend_agent", trend_agent_node)
    parallel_workflow.add_node("oscillator_agent", oscillator_agent_node)
    parallel_workflow.add_node("volatility_agent", volatility_agent_node)
    parallel_workflow.add_node("volume_agent", volume_agent_node)
    parallel_workflow.add_node("sr_agent", sr_agent_node)
    parallel_workflow.add_node("technical_consensus", technical_consensus_node)

    # We need a dummy start node to dispatch
    parallel_workflow.add_node("dispatch", lambda x: x)
    parallel_workflow.set_entry_point("dispatch")

    parallel_workflow.add_conditional_edges(
        "dispatch",
        _dispatch,
        {
            "trend_agent": "trend_agent",
            "oscillator_agent": "oscillator_agent",
            "volatility_agent": "volatility_agent",
            "volume_agent": "volume_agent",
            "sr_agent": "sr_agent",
        },
    )

    parallel_workflow.add_edge("trend_agent", "technical_consensus")
    parallel_workflow.add_edge("oscillator_agent", "technical_consensus")
    parallel_workflow.add_edge("volatility_agent", "technical_consensus")
    parallel_workflow.add_edge("volume_agent", "technical_consensus")
    parallel_workflow.add_edge("sr_agent", "technical_consensus")
    parallel_workflow.add_edge("technical_consensus", END)

    return parallel_workflow.compile()


technical_graph = build_technical_graph()
