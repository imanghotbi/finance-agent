import json
from datetime import datetime, timedelta, timezone
from langchain_core.runnables import RunnableLambda
from langchain_core.messages import HumanMessage

from src.utils.llm_factory import LLMFactory
from src.workflow.state import FundamentalState
from src.schema.fundamental import (
    BalanceSheetOutput,
    EarningsQualityOutput,
    ValuationOutput,
    FundamentalAnalysisOutput,
    CodalReportSelection,
    CodalAnalysisOutput
)
from src.core.prompt import (
    BALANCE_SHEET_AGENT_PROMPT,
    EARNINGS_QUALITY_AGENT_PROMPT,
    VALUATION_AGENT_PROMPT,
    FUNDAMENTAL_AGENT,
    CODAL_LIST_PROMPT,
    CODAL_CONTENT_PROMPT
)
from src.utils.helper import (
    create_prompt, 
    _invoke_structured_with_recovery, 
    scrape_codal_report, 
    parse_persian_date
)
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

async def codal_agent_node(state: FundamentalState):
    data = state["fundamental_data"].get("codal", [])
    symbol = state.get("symbol", "")
    

    # Get current date in Gregorian
    current_date = datetime.now()

    # Calculate date 60 days ago
    sixty_days_ago = current_date - timedelta(days=60)

    # Filter and sort the data
    filtered_data = []

    for item in data:
        try:
            # Parse the Persian publish date
            publish_date = parse_persian_date(item["publishDate"])
            
            # Check if the date is within the last 60 days
            if publish_date >= sixty_days_ago:
                filtered_data.append(item)
        except Exception as e:
            print(f"Error parsing date for item {item['id']}: {e}")

    # Sort filtered data by publishDate (newest first)
    sorted_filtered_data = sorted(
        filtered_data, 
        key=lambda x: parse_persian_date(x["publishDate"]), 
        reverse=True
    )
    
    filtered_reports = sorted_filtered_data[:20]
    clean_filtered_reports = [{'id':x['id'] , 'title':x['title']} for x in filtered_reports]

    # 2. Select Relevant Reports
    codal_list_prompt = CODAL_LIST_PROMPT.format(symbol=symbol), data=json.dumps(clean_filtered_reports, ensure_ascii=False)
    prompt_value_select = [HumanMessage(content=codal_list_prompt)]

    selection_result, _ = await _invoke_structured_with_recovery(llm, prompt_value_select, CodalReportSelection)
    
    final_codal_list = [x for x in clean_filtered_reports if x['id'] in selection_result.selected_ids]

    # 3. Scrape Content
    scraped_contents = []
    for data in final_codal_list:
        url = data['url']
        try:
            content = await scrape_codal_report(url)
            scraped_contents.append(content[:2000]) # Truncate to avoid context limit
        except Exception as e:
            print(f"Failed to scrape {url}: {e}")

    if not scraped_contents:
        return {"codal_report": CodalAnalysisOutput(key_findings=["No accessible reports found"], summary="Unable to analyze codal reports.")}

    # 4. Analyze Content
    combined_content = "\n\n---\n\n".join(scraped_contents)
    

    codal_content_prompt = CODAL_CONTENT_PROMPT.format(symbol = symbol, data=combined_content)
    prompt_analyze = [HumanMessage(content=codal_content_prompt)]

    analysis_result, meta = await _invoke_structured_with_recovery(llm, prompt_analyze, CodalAnalysisOutput)
    
    response = {"codal_report": analysis_result}
    if meta:
        response["codal_meta"] = meta
    return response

async def fundamental_consensus_node(state: FundamentalState):
    # GATEKEEPER CHECK
    required_keys = ["balance_sheet_report", "earnings_quality_report", "valuation_report","codal_report"]
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
        
        --- CODAL AGENT ---
        {codal_data}

        Based on this, generate the Fundamental Investment Thesis.
        """
    prompt = create_prompt(FUNDAMENTAL_AGENT, user_content)
    
    to_prompt_vars = RunnableLambda(lambda x: {
        "balance_sheet_data": json.dumps(x.get("balance_sheet_report", {}), ensure_ascii=False, default=str),
        "earnings_data": json.dumps(x.get("earnings_quality_report", {}), ensure_ascii=False, default=str),
        "valuation_data": json.dumps(x.get("valuation_report", {}), ensure_ascii=False, default=str),
        "codal_data": json.dumps(x.get("codal_report", {}), ensure_ascii=False, default=str),
    })

    prompt_value = (to_prompt_vars | prompt).invoke(state)
    result, meta = await _invoke_structured_with_recovery(llm, prompt_value, FundamentalAnalysisOutput)
    
    response = {"fundamental_consensus_report": result}
    if meta:
        response["fundamental_consensus_meta"] = meta
    return response