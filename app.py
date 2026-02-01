import chainlit as cl
from src.workflow.graph_builder import app as graph_app
from src.utils.ui_renderer import render_technical_report, render_fundamental_report, render_social_report, render_final_report
from langgraph.types import Command
from langchain_core.messages import AIMessage
import uuid

@cl.on_chat_start
async def start():
    """Initializes the session and starts the graph to get the welcome message."""
    cl.user_session.set("thread_id", str(uuid.uuid4()))
    cl.user_session.set("is_interrupted", False)
    
    # Tracking for intermediate reports to avoid re-rendering
    cl.user_session.set("reports_shown", {
        "technical": False,
        "fundamental": False,
        "social": False
    })

    # Start the graph with empty input to trigger intro_agent
    inputs = {"messages": [], "symbol": ""}
    
    # We use a dedicated function to handle graph execution to avoid code duplication
    await run_graph(inputs)

@cl.on_message
async def on_message(message: cl.Message):
    """Handles user input, resuming the graph if interrupted."""
    is_interrupted = cl.user_session.get("is_interrupted")
    
    if is_interrupted:
        # Resume the graph with user input
        inputs = Command(resume=message.content)
        await run_graph(inputs)
    else:
        await cl.Message(content="Starting new analysis...").send()
        
        # Reset tracking
        cl.user_session.set("thread_id", str(uuid.uuid4()))
        cl.user_session.set("reports_shown", {
            "technical": False,
            "fundamental": False,
            "social": False
        })
        cl.user_session.set("is_interrupted", False)
        
        inputs = {"messages": [], "symbol": ""}
        await run_graph(inputs)

async def run_graph(inputs):
    """Runs the graph and streams updates to the UI."""
    thread_id = cl.user_session.get("thread_id")
    config = {"configurable": {"thread_id": thread_id}}
    
    reports_shown = cl.user_session.get("reports_shown")
    
    research_step = None

    
    async for event in graph_app.astream(inputs, config, stream_mode="updates"):
        for node_name, node_output in event.items():
            
            # 1. Handle Intro Agent Messages (Chat)
            if node_name == "intro_agent":
                messages = node_output.get("messages", [])
                if messages:
                    last_msg = messages[-1]
                    if isinstance(last_msg, AIMessage) and last_msg.content:
                        await cl.Message(content=last_msg.content).send()

            if node_name == "data_preparation":
                if not research_step:
                    research_step = cl.Step(name="Market Research", type="process")
                    await research_step.send()
                    await cl.Message(content="🔄 تحلیل جامع نماد آغاز شد").send()

            if (node_name in ["technical_consensus", "fundamental_consensus", "social_news_consensus"]) and not research_step:
                 research_step = cl.Step(name="Market Research", type="process")
                 await research_step.send()

            if node_name == "technical_consensus" and not reports_shown["technical"]:
                report = node_output.get("technical_consensus_report")
                if report:
                    reports_shown["technical"] = True
                    async with cl.Step(name="Technical Analysis", type="run", parent_id=research_step.id if research_step else None) as step:
                        step.output = render_technical_report(report)
            
            if node_name == "fundamental_consensus" and not reports_shown["fundamental"]:
                report = node_output.get("fundamental_consensus_report")
                if report:
                    reports_shown["fundamental"] = True
                    async with cl.Step(name="Fundamental Analysis", type="run", parent_id=research_step.id if research_step else None) as step:
                        step.output = render_fundamental_report(report)

            if node_name == "social_news_consensus" and not reports_shown["social"]:
                report = node_output.get("social_news_consensus_report")
                if report:
                    reports_shown["social"] = True
                    async with cl.Step(name="Social & News Analysis", type="run", parent_id=research_step.id if research_step else None) as step:
                        step.output = render_social_report(report)

            # 4. Handle Final Report
            if node_name == "reporter_agent":
                if research_step:
                    research_step.output = "Analysis Complete."
                    await research_step.update()
                
                final = node_output.get("final_report") 
                if final:
                    await cl.Message(content=render_final_report(final)).send()
            
    # Update session state for reports
    cl.user_session.set("reports_shown", reports_shown)

    # Check for Interrupts
    snapshot = await graph_app.aget_state(config)
    if snapshot.next and snapshot.tasks and snapshot.tasks[0].interrupts:
        cl.user_session.set("is_interrupted", True)
    else:
        cl.user_session.set("is_interrupted", False)
