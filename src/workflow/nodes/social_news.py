import json
from datetime import datetime, timedelta, timezone
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
from src.utils.helper import create_prompt, _invoke_structured_with_recovery , parse_iso_date

llm = LLMFactory.get_model()

async def twitter_agent_node(state: NewsSocialState):
    data = state["news_social_data"].get("rapid_tweet", [])
    symbol = state["news_social_data"].get("symbol", "")
    short_name = state["news_social_data"].get("short_name", "")
    current_date = state["news_social_data"].get("analysis_date", str(datetime.now()))
    
    sorted_tweets = sorted(data, key=lambda x: int(x.get("likes", 0)), reverse=True)
    top_tweets = sorted_tweets[:10]
    
    cleaned_tweets = []
    for t in top_tweets:
        cleaned_tweets.append({
            "text": t.get("text"),
            "likes": t.get("likes"),
            "retweets": t.get("retweets"),
            "views": t.get("views"),
            "created_at": t.get("created_at")
        })

    input_data = {
        "symbol": symbol,
        "short_name": short_name,
        "current_date": current_date,
        "tweets": cleaned_tweets
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
    current_date = state["news_social_data"].get("analysis_date", str(datetime.now()))
    
    # Sort by sendTime descending
    sorted_data = sorted(
        data, 
        key=lambda x: parse_iso_date(x.get("sendTime")) or datetime(1970, 1, 1, tzinfo=timezone.utc), 
        reverse=True
    )
    top_comments = sorted_data[:10]
    
    cleaned_comments = []
    for c in top_comments:
        cleaned_comments.append({
            "content": c.get("content"),
            "date": c.get("sendTime"),
            "likeCount": c.get("likeCount"),
            "retwitCount": c.get("retwitCount")
        })
    
    input_data = {
        "symbol": symbol,
        "short_name": short_name,
        "current_date": current_date,
        "comments": cleaned_comments
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
    analysis_date_str = state["news_social_data"].get("analysis_date")
    
    filtered_news = []
    
    if analysis_date_str:
        try:
            current_date_dt = parse_iso_date(analysis_date_str)
            if current_date_dt:
                threshold_date = current_date_dt - timedelta(days=30)
                
                # Filter last 30 days
                valid_news = []
                for n in data:
                    news_date_str = n.get("date")
                    news_dt = parse_iso_date(news_date_str)
                    
                    if news_dt and news_dt >= threshold_date:
                        valid_news.append(n)
                
                # Sort by date descending
                # (Assuming news_dt comparison works with offset-aware datetimes)
                valid_news.sort(key=lambda x: parse_iso_date(x.get("date")), reverse=True)
                
                # Take top 10
                filtered_news = valid_news[:10]
            else:
                # Fallback if parsing fails
                filtered_news = data[:10]
        except Exception as e:
            print(f"Error filtering news dates: {e}")
            filtered_news = data[:10]
    else:
        filtered_news = data[:10]

    # Map fields
    cleaned_news = []
    for n in filtered_news:
        cleaned_news.append({
            "date": n.get("date"),
            "body": n.get("body"),
            "type": n.get("type")
        })

    input_data = {
        "symbol": symbol,
        "short_name": short_name,
        "current_date": analysis_date_str,
        "news_articles": cleaned_news
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
    current_date = state["news_social_data"].get("analysis_date", "")

    input_data = {
        "symbol": symbol,
        "short_name": short_name,
        "current_date": current_date,
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
