import json

from langchain_core.runnables import RunnableLambda, RunnableConfig

from src.utils.llm_factory import LLMFactory
from src.workflow.state import TechnicalState
from src.schema.technical import (
    TrendAgentOutput,
    OscillatorAgentOutput,
    VolatilityAgentOutput,
    VolumeAgentOutput,
    SupportResistanceAgentOutput,
    SmartMoneyAnalysis,
    TechnicalConsensus,
)
from src.core.prompt import (
    TREND_PROMPT,
    VOLATILITY_PROMPT,
    VOLUME_PROMPT,
    SR_PROMPT,
    OSCILLATOR_PROMPT,
    SMART_MOENY_PROMPT,
    TECHNICAL_AGENT,
)
from src.utils.helper import create_prompt, _invoke_structured_with_recovery, get_session_id
from src.core.logger import logger


llm = LLMFactory.get_model(node_name="technical")


def _prompt_json(value):
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return json.dumps(value, ensure_ascii=False, default=str)

async def trend_agent_node(state: TechnicalState, config: RunnableConfig):
    logger.info("📈 Starting Trend Analysis Node...")
    data = state["technical_data"].get("trend", {})
    visual = state["technical_data"].get("visuals", {})
    
    input_data = {
        **data ,
        **visual
    }
    user_content = (
    "INPUT JSON:\n{input_json}\n\n"
    "Return JSON that matches this schema:\n{schema_json}\n"
    )
    trend_prompt = create_prompt(TREND_PROMPT , user_content)
    to_prompt_vars = RunnableLambda(lambda x: {
    "input_json": _prompt_json(x),
    "schema_json": json.dumps(TrendAgentOutput.model_json_schema(), ensure_ascii=False)
        })

    prompt_value = (to_prompt_vars | trend_prompt).invoke({"input_data": input_data})
    result, meta = await _invoke_structured_with_recovery(
        llm, prompt_value, TrendAgentOutput, node_name="trend_agent", session_id=get_session_id(config)
    )
    response = {"trend_report": result}
    if meta:
        response["trend_meta"] = meta
    
    logger.info("✅ Trend Analysis Completed.")
    return response

async def oscillator_agent_node(state: TechnicalState, config: RunnableConfig):
    logger.info("〰️ Starting Oscillator Analysis Node...")
    # Mapping 'oscillators' from input key usually found in 'technical_analysis'
    data = state["technical_data"].get("oscillators", {})
    visual = state["technical_data"].get("visuals", {})
    input_data = {
        **data ,
        **visual
    }
    user_content = (
    "INPUT JSON:\n{input_json}\n\n"
    "Return JSON that matches this schema:\n{schema_json}\n"
    )
    oscillator_prompt = create_prompt(OSCILLATOR_PROMPT , user_content)
    to_prompt_vars = RunnableLambda(lambda x: {
    "input_json": _prompt_json(x),
    "schema_json": json.dumps(OscillatorAgentOutput.model_json_schema(), ensure_ascii=False)
        })

    prompt_value = (to_prompt_vars | oscillator_prompt).invoke({"input_data": input_data})
    result, meta = await _invoke_structured_with_recovery(
        llm, prompt_value, OscillatorAgentOutput, node_name="oscillator_agent", session_id=get_session_id(config)
    )
    response = {"oscillator_report": result}
    if meta:
        response["oscillator_meta"] = meta
    
    logger.info("✅ Oscillator Analysis Completed.")
    return response

async def volatility_agent_node(state: TechnicalState, config: RunnableConfig):
    logger.info("🌩️ Starting Volatility Analysis Node...")
    data = state["technical_data"].get("volatility", {})
    visual = state["technical_data"].get("visuals", {})
    input_data = {
        **data ,
        **visual
    }

    user_content = (
    "INPUT JSON:\n{input_json}\n\n"
    "Return JSON that matches this schema:\n{schema_json}\n"
    )
    volatility_prompt = create_prompt(VOLATILITY_PROMPT , user_content)
    to_prompt_vars = RunnableLambda(lambda x: {
    "input_json": _prompt_json(x),
    "schema_json": json.dumps(VolatilityAgentOutput.model_json_schema(), ensure_ascii=False)
        })
    prompt_value = (to_prompt_vars | volatility_prompt).invoke({"input_data": input_data})
    result, meta = await _invoke_structured_with_recovery(
        llm, prompt_value, VolatilityAgentOutput, node_name="volatility_agent", session_id=get_session_id(config)
    )
    response = {"volatility_report": result}
    if meta:
        response["volatility_meta"] = meta
    
    logger.info("✅ Volatility Analysis Completed.")
    return response

async def volume_agent_node(state: TechnicalState, config: RunnableConfig):
    logger.info("📊 Starting Volume Analysis Node...")
    data = state["technical_data"].get("volume", {})
    visual = state["technical_data"].get("visuals", {})
    input_data = {
        **data ,
        **visual
    }
    user_content = (
    "INPUT JSON:\n{input_json}\n\n"
    "Return JSON that matches this schema:\n{schema_json}\n"
    )
    volume_prompt = create_prompt(VOLUME_PROMPT , user_content)
    to_prompt_vars = RunnableLambda(lambda x: {
    "input_json": _prompt_json(x),
    "schema_json": json.dumps(VolumeAgentOutput.model_json_schema(), ensure_ascii=False)
        })

    prompt_value = (to_prompt_vars | volume_prompt).invoke({"input_data": input_data})
    result, meta = await _invoke_structured_with_recovery(
        llm, prompt_value, VolumeAgentOutput, node_name="volume_agent", session_id=get_session_id(config)
    )
    response = {"volume_report": result}
    if meta:
        response["volume_meta"] = meta
    
    logger.info("✅ Volume Analysis Completed.")
    return response

async def sr_agent_node(state: TechnicalState, config: RunnableConfig):
    logger.info("🧱 Starting S/R Analysis Node...")
    data = state["technical_data"].get("support_resistance", {})
    visual = state["technical_data"].get("visuals", {})
    input_data = {
        **data ,
        **visual
    }

    user_content = (
    "INPUT JSON:\n{input_json}\n\n"
    "Return JSON that matches this schema:\n{schema_json}\n"
    )
    sr_prompt = create_prompt(SR_PROMPT , user_content)
    to_prompt_vars = RunnableLambda(lambda x: {
    "input_json": _prompt_json(x),
    "schema_json": json.dumps(SupportResistanceAgentOutput.model_json_schema(), ensure_ascii=False)
        })

    prompt_value = (to_prompt_vars | sr_prompt).invoke({"input_data": input_data})
    result, meta = await _invoke_structured_with_recovery(
        llm, prompt_value, SupportResistanceAgentOutput, node_name="sr_agent", session_id=get_session_id(config)
    )
    response = {"sr_report": result}
    if meta:
        response["sr_meta"] = meta
    
    logger.info("✅ S/R Analysis Completed.")
    return response

async def smart_money_agent_node(state: TechnicalState, config: RunnableConfig):
    logger.info("🏦 Starting Smart Money Analysis Node...")
    input_data = state["technical_data"].get("smart_money", {})
    user_content = (
    "INPUT JSON:\n{input_json}\n\n"
    "Return JSON that matches this schema:\n{schema_json}\n"
    )

    smart_money_prompt = create_prompt(SMART_MOENY_PROMPT , user_content)
    to_prompt_vars = RunnableLambda(lambda x: {
    "input_json": _prompt_json(x),
    "schema_json": json.dumps(SmartMoneyAnalysis.model_json_schema(), ensure_ascii=False)
        })
    
    prompt_value = (to_prompt_vars | smart_money_prompt).invoke({"input_data": input_data})
    result, meta = await _invoke_structured_with_recovery(
        llm, prompt_value, SmartMoneyAnalysis, node_name="smart_money_agent", session_id=get_session_id(config)
    )
    response = {"smart_money_report": result}
    if meta:
        response["smart_money_meta"] = meta
    
    logger.info("✅ Smart Money Analysis Completed.")
    return response

async def technical_consensus_node(state: TechnicalState, config: RunnableConfig):
    logger.info("🧠 Starting Technical Consensus Node...")

    required_keys = ["trend_report", "oscillator_report", "volatility_report", "volume_report", "sr_report", "smart_money_report"]
    missing = [key for key in required_keys if not state.get(key)]
    
    if missing:
        logger.warning(f"⏳ Technical Consensus waiting for inputs: {missing}")
        return {}
        
    user_content = """
        Here is the latest technical telemetry:

        --- TREND AGENT ---
        {trend_data}

        --- OSCILLATOR AGENT ---
        {oscillator_data}

        --- VOLATILITY AGENT ---
        {volatility_data}

        --- VOLUME AGENT ---
        {volume_data}

        --- SR AGENT (Levels) ---
        {sr_data}

        --- SMART MONEY AGENT (Levels) ---
        {smart_money_data}

        Based on this, generate the Technical Consensus.
        """
    consensus_prompt = create_prompt(TECHNICAL_AGENT, user_content)
    to_prompt_vars = RunnableLambda(lambda x: {
        "trend_data": _prompt_json(x.get("trend_report", {})),
        "oscillator_data": _prompt_json(x.get("oscillator_report", {})),
        "volatility_data": _prompt_json(x.get("volatility_report", {})),
        "volume_data": _prompt_json(x.get("volume_report", {})),
        "sr_data": _prompt_json(x.get("sr_report", {})),
        "smart_money_data": _prompt_json(x.get("smart_money_report", {}))
    })

    prompt_value = (to_prompt_vars | consensus_prompt).invoke(state)
    result, meta = await _invoke_structured_with_recovery(
        llm,
        prompt_value,
        TechnicalConsensus,
        node_name="technical_consensus",
        session_id=get_session_id(config),
    )
    response = {"technical_consensus_report": result}
    if meta:
        response["technical_consensus_meta"] = meta
    
    logger.info("✅ Technical Consensus Completed.")
    return response
