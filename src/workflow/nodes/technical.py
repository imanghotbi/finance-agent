import json

from langchain_core.runnables import RunnableLambda

from src.utils.llm_factory import LLMFactory
from src.workflow.state import TechnicalState
from src.core.schema import (
    TrendAgentOutput,
    OscillatorAgentOutput,
    VolatilityAgentOutput,
    VolumeAgentOutput,
    SupportResistanceAgentOutput,
)
from src.core.prompt import (
    TREND_PROMPT,
    VOLATILITY_PROMPT,
    VOLUME_PROMPT,
    SR_PROMPT,
    OSCILLATOR_PROMPT,
)
from src.utils.helper import create_prompt, _invoke_structured_with_recovery


llm = LLMFactory.get_model()

async def trend_agent_node(state: TechnicalState):
    data = state["technical_data"].get("trend", {})
    visual = state.get("visual_data", {})
    ##TODO check this for input data
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
    "input_json": json.dumps(x, ensure_ascii=False, default=str),
    "schema_json": json.dumps(TrendAgentOutput.model_json_schema(), ensure_ascii=False)
        })

    prompt_value = (to_prompt_vars | trend_prompt).invoke({"input_data": input_data})
    result, meta = await _invoke_structured_with_recovery(llm, prompt_value, TrendAgentOutput)
    response = {"trend_report": result}
    if meta:
        response["trend_meta"] = meta
    return response

async def oscillator_agent_node(state: TechnicalState):
    # Mapping 'oscillators' from input key usually found in 'technical_analysis'
    data = state["technical_data"].get("oscillators", {})
    visual = state.get("visual_data", {})
    ##TODO check this for input data
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
    "input_json": json.dumps(x, ensure_ascii=False, default=str),
    "schema_json": json.dumps(OscillatorAgentOutput.model_json_schema(), ensure_ascii=False)
        })

    prompt_value = (to_prompt_vars | oscillator_prompt).invoke({"input_data": input_data})
    result, meta = await _invoke_structured_with_recovery(llm, prompt_value, OscillatorAgentOutput)
    response = {"oscillator_report": result}
    if meta:
        response["oscillator_meta"] = meta
    return response

async def volatility_agent_node(state: TechnicalState):
    data = state["technical_data"].get("volatility", {})
    visual = state.get("visual_data", {})
    ##TODO check this for input data
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
    "input_json": json.dumps(x, ensure_ascii=False, default=str),
    "schema_json": json.dumps(VolatilityAgentOutput.model_json_schema(), ensure_ascii=False)
        })
    prompt_value = (to_prompt_vars | volatility_prompt).invoke({"input_data": input_data})
    result, meta = await _invoke_structured_with_recovery(llm, prompt_value, VolatilityAgentOutput)
    response = {"volatility_report": result}
    if meta:
        response["volatility_meta"] = meta
    return response

async def volume_agent_node(state: TechnicalState):
    data = state["technical_data"].get("volume", {})
    visual = state.get("visual_data", {})
    ##TODO check this for input data
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
    "input_json": json.dumps(x, ensure_ascii=False, default=str),
    "schema_json": json.dumps(VolumeAgentOutput.model_json_schema(), ensure_ascii=False)
        })

    prompt_value = (to_prompt_vars | volume_prompt).invoke({"input_data": input_data})
    result, meta = await _invoke_structured_with_recovery(llm, prompt_value, VolumeAgentOutput)
    response = {"volume_report": result}
    if meta:
        response["volume_meta"] = meta
    return response

async def sr_agent_node(state: TechnicalState):
    data = state["technical_data"].get("support_resistance", {})
    visual = state.get("visual_data", {})
    ##TODO check this for input data
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
    "input_json": json.dumps(x, ensure_ascii=False, default=str),
    "schema_json": json.dumps(SupportResistanceAgentOutput.model_json_schema(), ensure_ascii=False)
        })

    prompt_value = (to_prompt_vars | sr_prompt).invoke({"input_data": input_data})
    result, meta = await _invoke_structured_with_recovery(llm, prompt_value, SupportResistanceAgentOutput)
    response = {"sr_report": result}
    if meta:
        response["sr_meta"] = meta
    return response
