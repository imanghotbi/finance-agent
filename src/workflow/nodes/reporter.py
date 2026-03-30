import json
from langchain_core.runnables import RunnableLambda, RunnableConfig
from src.utils.llm_factory import LLMFactory
from src.workflow.state import AgentState
from src.core.prompt import REPORTER_AGENT
from src.utils.helper import create_prompt, get_session_id, invoke_llm_and_log, save_agent_run, build_analysis_timing
from src.core.logger import logger

llm = LLMFactory.get_model(node_name="reporter")

async def reporter_node(state: AgentState, config: RunnableConfig):
    logger.info("📝 Starting Reporter Node...")
    
    # GATEKEEPER CHECK: Ensure all three consensus reports are present.
    # This prevents running the reporter on partial data if one subgraph finishes early.
    tech_consensus = state.get("technical_consensus_report")
    fund_consensus = state.get("fundamental_consensus_report")
    social_consensus = state.get("social_news_consensus_report")

    if not tech_consensus or not fund_consensus or not social_consensus:
        missing = []
        if not tech_consensus: missing.append("Technical")
        if not fund_consensus: missing.append("Fundamental")
        if not social_consensus: missing.append("Social/News")
        logger.warning(f"⏳ Reporter Node waiting for consensus reports: {missing}")
        # Return empty update to signal no change yet
        return {}

    user_content = """
        Here are the consensus reports:

        --- TECHNICAL CONSENSUS ---
        {technical_consensus}

        --- FUNDAMENTAL CONSENSUS ---
        {fundamental_consensus}
        
        --- SOCIAL & NEWS CONSENSUS ---
        {social_news_consensus}

        Generate the final Investment Memo.
        """
    prompt = create_prompt(REPORTER_AGENT, user_content)
    
    to_prompt_vars = RunnableLambda(lambda x: {
        "technical_consensus": json.dumps(x.get("technical_consensus_report", {}), ensure_ascii=False, default=str),
        "fundamental_consensus": json.dumps(x.get("fundamental_consensus_report", {}), ensure_ascii=False, default=str),
        "social_news_consensus": json.dumps(x.get("social_news_consensus_report", {}), ensure_ascii=False, default=str),
    })

    # We expect a string (Markdown), not structured JSON
    prompt_value = (to_prompt_vars | prompt).invoke(state)
    
    # Simple invoke for text output
    session_id = get_session_id(config)
    response_msg = await invoke_llm_and_log(
        llm,
        prompt_value,
        node_name="reporter_agent",
        session_id=session_id,
    )
    
    logger.info("✅ Reporter Node Completed. Final report generated.")
    timing_data = build_analysis_timing(state)
    await save_agent_run(session_id=session_id, state=state, final_report=response_msg.content)
    return {
        "final_report": response_msg.content,
        **timing_data,
    }
