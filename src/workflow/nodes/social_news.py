import json
from langchain_core.runnables import RunnableLambda
from src.utils.llm_factory import LLMFactory
from src.workflow.state import NewsSocialState
from src.schema.social_news import (
    SocialSentimentOutput,
    RetailPulseAnalysis,
    FundamentalNewsAnalysis,
    NewsSocialFusionOutput
)
from src.core.prompt import (
    TWEET_AGENT_PROMPT,
    SAHAMYAB_TWEET_PROMPT,
    NEWS_PROMPT,
    SOCIAL_NEWS_AGENT_PROMPT,
)
from src.utils.helper import create_prompt, _invoke_structured_with_recovery

llm = LLMFactory.get_model()

async def twitter_agent_node(state: NewsSocialState):
    data = state["news_social_data"].get("rapid_tweet", [])
    symbol = state["news_social_data"].get("symbol", "")
    short_name = state["news_social_data"].get("short_name", "")
    
    input_data = {
        "symbol": symbol,
        "short_name": short_name,
        "tweets": data
    }
    
    user_content = (
    "INPUT JSON:\n{input_json}\n\n"
    "Return JSON that matches this schema:\n{schema_json}\n"
    )
    prompt = create_prompt(TWEET_AGENT_PROMPT, user_content)
    
    to_prompt_vars = RunnableLambda(lambda x: {
        "input_json": json.dumps(x, ensure_ascii=False, default=str),
        "schema_json": json.dumps(SocialSentimentOutput.model_json_schema(), ensure_ascii=False)
    })

    prompt_value = (to_prompt_vars | prompt).invoke(input_data)
    result, meta = await _invoke_structured_with_recovery(llm, prompt_value, SocialSentimentOutput)
    
    return {"twitter_report": result}

async def sahamyab_agent_node(state: NewsSocialState):
    data = state["news_social_data"].get("latest_sahamyab_tweet", [])
    symbol = state["news_social_data"].get("symbol", "")
    short_name = state["news_social_data"].get("short_name", "")
    
    input_data = {
        "symbol": symbol,
        "short_name": short_name,
        "comments": data
    }
    
    user_content = (
    "INPUT JSON:\n{input_json}\n\n"
    "Return JSON that matches this schema:\n{schema_json}\n"
    )
    prompt = create_prompt(SAHAMYAB_TWEET_PROMPT, user_content)
    
    to_prompt_vars = RunnableLambda(lambda x: {
        "input_json": json.dumps(x, ensure_ascii=False, default=str),
        "schema_json": json.dumps(RetailPulseAnalysis.model_json_schema(), ensure_ascii=False)
    })

    prompt_value = (to_prompt_vars | prompt).invoke(input_data)
    result, meta = await _invoke_structured_with_recovery(llm, prompt_value, RetailPulseAnalysis)
    
    return {"sahamyab_report": result}

async def news_agent_node(state: NewsSocialState):
    data = state["news_social_data"].get("news", [])
    symbol = state["news_social_data"].get("symbol", "")
    short_name = state["news_social_data"].get("short_name", "")
    
    input_data = {
        "symbol": symbol,
        "short_name": short_name,
        "news_articles": data
    }
    
    user_content = (
    "INPUT JSON:\n{input_json}\n\n"
    "Return JSON that matches this schema:\n{schema_json}\n"
    )
    prompt = create_prompt(NEWS_PROMPT, user_content)
    
    to_prompt_vars = RunnableLambda(lambda x: {
        "input_json": json.dumps(x, ensure_ascii=False, default=str),
        "schema_json": json.dumps(FundamentalNewsAnalysis.model_json_schema(), ensure_ascii=False)
    })

    prompt_value = (to_prompt_vars | prompt).invoke(input_data)
    result, meta = await _invoke_structured_with_recovery(llm, prompt_value, FundamentalNewsAnalysis)
    
    return {"news_report": result}

async def social_news_consensus_node(state: NewsSocialState):
    # Gatekeeper Check
    required_keys = ["twitter_report", "sahamyab_report", "news_report"]
    missing = [key for key in required_keys if not state.get(key)]
    
    if missing:
        print(f"Social News Consensus: Waiting for inputs: {missing}")
        return {}
        
    tavily_answer = state["news_social_data"].get("search_tavily_answer", "")
    symbol = state["news_social_data"].get("symbol", "")
    short_name = state["news_social_data"].get("short_name", "")

    input_data = {
        "symbol": symbol,
        "short_name": short_name,
        "twitter_report": state.get("twitter_report"),
        "sahamyab_report": state.get("sahamyab_report"),
        "news_report": state.get("news_report"),
        "tavily_search_narrative": tavily_answer
    }

    user_content = (
        "INPUT DATA:\n{input_json}\n\n"
        "Return JSON that matches this schema:\n{schema_json}\n"
    )
    prompt = create_prompt(SOCIAL_NEWS_AGENT_PROMPT, user_content)
    
    to_prompt_vars = RunnableLambda(lambda x: {
        "input_json": json.dumps(x, ensure_ascii=False, default=str),
        "schema_json": json.dumps(NewsSocialFusionOutput.model_json_schema(), ensure_ascii=False)
    })

    prompt_value = (to_prompt_vars | prompt).invoke(input_data)
    result, meta = await _invoke_structured_with_recovery(llm, prompt_value, NewsSocialFusionOutput)
    
    return {"social_news_consensus_report": result}
