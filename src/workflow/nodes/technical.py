import json
from langchain_core.runnables import RunnableLambda

from src.utils.llm_factory import LLMFactory
from src.workflow.state import TechnicalState
from src.core.schema import TrendAgentOutput , OscillatorAgentOutput , VolatilityAgentOutput , VolumeAgentOutput , SupportResistanceAgentOutput
from src.core.prompt import TREND_PROMPT , VOLATILITY_PROMPT , VOLUME_PROMPT , SR_PROMPT , OSCILLATOR_PROMPT
from src.utils.helper import create_prompt


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

    chain = to_prompt_vars | trend_prompt | llm.with_structured_output(TrendAgentOutput)
    result = await chain.ainvoke({'input_data':input_data})
    ## check need to result dump or not
    return {"trend_report": result}

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

    chain = to_prompt_vars | oscillator_prompt | llm.with_structured_output(OscillatorAgentOutput)
    result = await chain.ainvoke({'input_data':input_data})
    
    return {"oscillator_report": result}

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
    chain = to_prompt_vars | volatility_prompt | llm.with_structured_output(VolatilityAgentOutput)
    result = await chain.ainvoke({"volatility_data": json.dumps(data), "visual_data": json.dumps(visual)})
    
    return {"volatility_report": result}

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

    chain = to_prompt_vars | volume_prompt | llm.with_structured_output(VolumeAgentOutput)
    result = await chain.ainvoke({'input_data':input_data})

    return {"volume_report": result}

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

    chain = to_prompt_vars | sr_prompt | llm.with_structured_output(SupportResistanceAgentOutput)
    result = await chain.ainvoke({'input_data':input_data})
    
    return {"sr_report": result}