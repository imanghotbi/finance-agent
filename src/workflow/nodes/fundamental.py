import json
from langchain_core.runnables import RunnableLambda
from src.utils.llm_factory import LLMFactory
from src.workflow.state import FundamentalState
from src.schema.fundamental import (
    BalanceSheetOutput,
    EarningsQualityOutput,
    ValuationOutput,
    FundamentalAnalysisOutput,
)
from src.core.prompt import (
    BALANCE_SHEET_AGENT_PROMPT,
    EARNINGS_QUALITY_AGENT_PROMPT,
    VALUATION_AGENT_PROMPT,
    FUNDAMENTAL_AGENT,
)
from src.utils.helper import create_prompt, _invoke_structured_with_recovery
from src.services.fundamental.balance_sheet import BalanceSheetAgent
from src.services.fundamental.earnings_cash import EarningsQualityAgent
from src.services.fundamental.valuation_market import ValuationAgent

llm = LLMFactory.get_model()

async def balance_sheet_node(state: FundamentalState):
    agent = BalanceSheetAgent(state["fundamental_data"])
    data = agent.process()
    
    user_content = (
    "INPUT JSON:\n{input_json}\n\n"
    "Return JSON that matches this schema:\n{schema_json}\n"
    )
    prompt = create_prompt(BALANCE_SHEET_AGENT_PROMPT, user_content)
    
    to_prompt_vars = RunnableLambda(lambda x: {
        "input_json": json.dumps(x, ensure_ascii=False, default=str),
        "schema_json": json.dumps(BalanceSheetOutput.model_json_schema(), ensure_ascii=False)
    })

    prompt_value = (to_prompt_vars | prompt).invoke(data)
    result, meta = await _invoke_structured_with_recovery(llm, prompt_value, BalanceSheetOutput)
    
    response = {"balance_sheet_report": result}
    if meta:
        response["balance_sheet_meta"] = meta
    return response

async def earnings_quality_node(state: FundamentalState):
    agent = EarningsQualityAgent(state["fundamental_data"])
    data = agent.process()
    
    user_content = (
    "INPUT JSON:\n{input_json}\n\n"
    "Return JSON that matches this schema:\n{schema_json}\n"
    )
    prompt = create_prompt(EARNINGS_QUALITY_AGENT_PROMPT, user_content)
    
    to_prompt_vars = RunnableLambda(lambda x: {
        "input_json": json.dumps(x, ensure_ascii=False, default=str),
        "schema_json": json.dumps(EarningsQualityOutput.model_json_schema(), ensure_ascii=False)
    })

    prompt_value = (to_prompt_vars | prompt).invoke(data)
    result, meta = await _invoke_structured_with_recovery(llm, prompt_value, EarningsQualityOutput)
    
    response = {"earnings_quality_report": result}
    if meta:
        response["earnings_quality_meta"] = meta
    return response

async def valuation_node(state: FundamentalState):
    agent = ValuationAgent(state["fundamental_data"])
    data = agent.process()
    
    user_content = (
    "INPUT JSON:\n{input_json}\n\n"
    "Return JSON that matches this schema:\n{schema_json}\n"
    )
    prompt = create_prompt(VALUATION_AGENT_PROMPT, user_content)
    
    to_prompt_vars = RunnableLambda(lambda x: {
        "input_json": json.dumps(x, ensure_ascii=False, default=str),
        "schema_json": json.dumps(ValuationOutput.model_json_schema(), ensure_ascii=False)
    })

    prompt_value = (to_prompt_vars | prompt).invoke(data)
    result, meta = await _invoke_structured_with_recovery(llm, prompt_value, ValuationOutput)
    
    response = {"valuation_report": result}
    if meta:
        response["valuation_meta"] = meta
    return response

async def fundamental_consensus_node(state: FundamentalState):
    # GATEKEEPER CHECK
    required_keys = ["balance_sheet_report", "earnings_quality_report", "valuation_report"]
    missing = [key for key in required_keys if not state.get(key)]
    
    if missing:
        print(f"Fundamental Consensus: Waiting for inputs: {missing}")
        return {}
        
    user_content = """
        Here is the latest fundamental telemetry:

        --- BALANCE SHEET AGENT ---
        {balance_sheet_data}

        --- EARNINGS QUALITY AGENT ---
        {earnings_data}

        --- VALUATION AGENT ---
        {valuation_data}

        Based on this, generate the Fundamental Investment Thesis.
        """
    prompt = create_prompt(FUNDAMENTAL_AGENT, user_content)
    
    to_prompt_vars = RunnableLambda(lambda x: {
        "balance_sheet_data": json.dumps(x.get("balance_sheet_report", {}), ensure_ascii=False, default=str),
        "earnings_data": json.dumps(x.get("earnings_quality_report", {}), ensure_ascii=False, default=str),
        "valuation_data": json.dumps(x.get("valuation_report", {}), ensure_ascii=False, default=str),
    })

    prompt_value = (to_prompt_vars | prompt).invoke(state)
    result, meta = await _invoke_structured_with_recovery(llm, prompt_value, FundamentalAnalysisOutput)
    
    response = {"fundamental_consensus_report": result}
    if meta:
        response["fundamental_consensus_meta"] = meta
    return response