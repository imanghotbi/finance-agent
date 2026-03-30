import chainlit as cl
from src.workflow.graph_builder import app as graph_app
from src.utils.ui_renderer import (
    render_technical_report, 
    render_fundamental_report, 
    render_social_report, 
    render_final_report,
    build_candlestick_chart,
)
# Import Schemas to convert Dicts back to Objects
from src.schema.technical import TechnicalConsensus
from src.schema.fundamental import FundamentalAnalysisOutput
from src.schema.social_news import NewsSocialFusionOutput
from src.utils.helper import ensure_object

from langgraph.types import Command
from langchain_core.messages import AIMessage, HumanMessage
import uuid
import asyncio 

@cl.on_chat_start
async def start():
    """Initializes the session."""
    cl.user_session.set("thread_id", str(uuid.uuid4()))
    cl.user_session.set("is_interrupted", False)
    # Reset tracking
    cl.user_session.set("reports_shown", {
        "technical": False, "fundamental": False, "social": False
    })

    inputs = {"messages": [HumanMessage(content="خودت رو معرفی کن")], "symbol": ""}
    await run_graph(inputs)

@cl.on_message
async def on_message(message: cl.Message):
    """Handles user input."""
    is_interrupted = cl.user_session.get("is_interrupted")
    
    if is_interrupted:
        inputs = Command(resume=message.content)
        await run_graph(inputs)
    else:
        # User entered a new symbol
        await cl.Message(content=f"Starting analysis for: **{message.content}**...").send()
        
        # Reset Session for new analysis
        cl.user_session.set("thread_id", str(uuid.uuid4()))
        cl.user_session.set("reports_shown", {
            "technical": False, "fundamental": False, "social": False
        })
        cl.user_session.set("is_interrupted", False)
        
        inputs = {"messages": [HumanMessage(content="خودت رو معرفی کن")], "symbol": ""}
        await run_graph(inputs)

async def run_graph(inputs):
    """Runs the graph with granular node-by-node progress."""
    thread_id = cl.user_session.get("thread_id")
    config = {"configurable": {"thread_id": thread_id}}
    
    reports_shown = cl.user_session.get("reports_shown")
    
    # Progress Tracking
    TOTAL_STEPS = 18
    completed_steps = 0
    research_step = None 
    
    # Placeholder to store the final report data
    final_report_payload = None
    price_history_payload = None
    chart_symbol = None
    chart_short_name = None

    print(f"--- Graph Start for Thread {thread_id} ---")

    async for data in graph_app.astream(inputs, config, stream_mode="updates", subgraphs=True):
        
        # Handle tuple return (namespace, event)
        if isinstance(data, tuple):
            event = data[1] 
        else:
            event = data

        for node_name, node_output in event.items():
            if node_name == "intro_agent":
                messages = node_output.get("messages", [])
                if messages:
                    last_msg = messages[-1]
                    if isinstance(last_msg, AIMessage) and last_msg.content:
                        await cl.Message(content=last_msg.content).send()

            if node_name == "data_preparation":
                if not research_step:
                    await cl.Message(content="🔄 آغاز بررسی جامع نماد بورسی ...").send()
                    research_step = cl.Step(name="کاوش عمیق نماد بورسی (0%)", type="process" , parent_id=cl.context.current_step.id)
                    await research_step.send()
                price_history_payload = node_output.get("price_history", [])
                chart_symbol = node_output.get("symbol")
                chart_short_name = node_output.get("short_name")

            # Define worker nodes for progress calculation
            worker_nodes = [
                "data_preparation",
                "trend_agent", "oscillator_agent", "volatility_agent", 
                "volume_agent", "sr_agent", "smart_money_agent", "technical_consensus",
                "balance_sheet_agent", "earnings_quality_agent", 
                "valuation_agent", "codal_agent", "fundamental_consensus",
                "twitter_agent", "sahamyab_agent", "news_agent", "social_news_consensus"
            ]

            # --- 3. Update Progress ---
            if node_name in worker_nodes:
                completed_steps += 1
                percent = min(int((completed_steps / TOTAL_STEPS) * 100), 95)
                
                if research_step:
                    research_step.name = f"کاوش عمیق نماد بورسی ({percent}%)"
                    await research_step.update()

            # --- 4. Sub-Graph Reports ---
            
            # Technical Report
            if node_name == "technical_consensus" or (node_name == "technical_graph" and not reports_shown["technical"]):
                raw_data = node_output if node_name == "technical_consensus" else node_output.get("technical_consensus_report")
                if isinstance(raw_data, dict) and "technical_consensus_report" in raw_data:
                    raw_data = raw_data["technical_consensus_report"]

                if raw_data and not reports_shown["technical"] and research_step:
                    reports_shown["technical"] = True
                    async with cl.Step(name="تحلیل تکنیکال", type="run", parent_id=research_step.id) as step:
                        report_obj = ensure_object(raw_data, TechnicalConsensus)
                        step.output = render_technical_report(report_obj) if report_obj else "Error parsing data"

            # Fundamental Report
            if node_name == "fundamental_consensus" or (node_name == "fundamental_graph" and not reports_shown["fundamental"]):
                raw_data = node_output if node_name == "fundamental_consensus" else node_output.get("fundamental_consensus_report")
                if isinstance(raw_data, dict) and "fundamental_consensus_report" in raw_data:
                    raw_data = raw_data["fundamental_consensus_report"]

                if raw_data and not reports_shown["fundamental"] and research_step:
                    reports_shown["fundamental"] = True
                    async with cl.Step(name="تحلیل بنیادی", type="run", parent_id=research_step.id) as step:
                        report_obj = ensure_object(raw_data, FundamentalAnalysisOutput)
                        step.output = render_fundamental_report(report_obj) if report_obj else "Error parsing data"

            # Social Report
            if node_name == "social_news_consensus" or (node_name == "social_news_graph" and not reports_shown["social"]):
                raw_data = node_output if node_name == "social_news_consensus" else node_output.get("social_news_consensus_report")
                if isinstance(raw_data, dict) and "social_news_consensus_report" in raw_data:
                    raw_data = raw_data["social_news_consensus_report"]

                if raw_data and not reports_shown["social"] and research_step:
                    reports_shown["social"] = True
                    async with cl.Step(name="تحلیل اخبار و شبکه اجتماعی", type="run", parent_id=research_step.id) as step:
                        report_obj = ensure_object(raw_data, NewsSocialFusionOutput)
                        step.output = render_social_report(report_obj) if report_obj else "Error parsing data"

            # --- 5. Capture Final Report & Close Step ---
            if node_name == "reporter_agent":
                # 2. Capture the data, but DO NOT send the message yet
                final = node_output.get("final_report") 
                if final:
                    final_report_payload = final
            
            # Persist State
            cl.user_session.set("reports_shown", reports_shown)

    # --- 6. Send Final Report AFTER Loop Ends ---
    # This ensures the graph stream is closed and the previous Step is fully rendered/settled.
    final_msg = None
    if final_report_payload:
        final_msg = cl.Message(content="⏳ در حال تنظیم گزارش نهایی...")
        await final_msg.send()

    if research_step:
        research_step.name = "Market Research (100%) - Completed"
        research_step.output = "تمام مراحل با موفقیت انجام شد."
        await research_step.update()
    
    await asyncio.sleep(0.5)
    if final_report_payload:
        await cl.Message(content=render_final_report(final_report_payload) , parent_id=None).send()
        candlestick_figure = build_candlestick_chart(
            price_history_payload or [],
            chart_symbol or "",
            chart_short_name,
        )
        if candlestick_figure:
            await cl.Message(
                content=f"### 📉 Price Chart\n{chart_symbol or ''}",
                elements=[cl.Plotly(name="candlestick_chart", figure=candlestick_figure, display="inline")],
                parent_id=None,
            ).send()

    # Handle Interrupts
    snapshot = await graph_app.aget_state(config)
    if snapshot.next and snapshot.tasks and snapshot.tasks[0].interrupts:
        cl.user_session.set("is_interrupted", True)
    else:
        cl.user_session.set("is_interrupted", False)
