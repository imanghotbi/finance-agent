from typing import Any, Dict, Optional, Tuple, Type
from datetime import datetime , timedelta
import json
import ssl
import aiohttp
from bs4 import BeautifulSoup
import jdatetime
from tenacity import retry, stop_after_attempt, wait_fixed
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, ValidationError

try:
    from src.core.logger import logger
    from src.core.config import settings
    from src.core.mongo_manger import MongoManager
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


def create_prompt(system_prompt: str, user_message: str) -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages([("system", system_prompt), ("human", user_message)])


def _prompt_to_text(prompt_value: Any) -> str:
    if hasattr(prompt_value, "to_string"):
        return prompt_value.to_string()
    return str(prompt_value)


def get_session_id(config: Optional[RunnableConfig]) -> Optional[str]:
    if not config:
        return None
    configurable = config.get("configurable", {})
    return configurable.get("session_id") or configurable.get("thread_id")


def _extract_token_usage(response: Any) -> Dict[str, Any]:
    response_metadata = getattr(response, "response_metadata", {}) or {}
    token_usage = response_metadata.get("token_usage")
    if isinstance(token_usage, dict):
        return token_usage

    usage_metadata = getattr(response, "usage_metadata", None)
    if isinstance(usage_metadata, dict):
        return usage_metadata

    return {}


def _make_mongo_safe(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {key: _make_mongo_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_make_mongo_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_make_mongo_safe(item) for item in value]
    try:
        json.dumps(value)
        return value
    except TypeError:
        return str(value)


async def save_llm_usage(node_name: str, session_id: Optional[str], response: Any) -> None:
    response_metadata = getattr(response, "response_metadata", {}) or {}
    document = {
        "node_name": node_name,
        "session_id": session_id,
        "model_name": response_metadata.get("model_name"),
        **_extract_token_usage(response),
        "created_at": datetime.utcnow(),
    }
    mongo = MongoManager(settings.mongo_llm_usage_collection_name)
    try:
        await mongo.write_data(_make_mongo_safe(document))
    except Exception as exc:
        logger.warning("Failed to persist LLM usage for node %s.", node_name, exc_info=exc)
    finally:
        mongo.close()


def build_analysis_timing(state: Dict[str, Any]) -> Dict[str, Any]:
    completed_at = datetime.utcnow()
    started_at_raw = state.get("analysis_started_at")
    started_at = None
    if started_at_raw:
        try:
            started_at = datetime.fromisoformat(started_at_raw)
        except ValueError:
            started_at = None

    elapsed_seconds = round((completed_at - started_at).total_seconds(), 2) if started_at else None
    if elapsed_seconds is None:
        elapsed_display = None
    elif elapsed_seconds < 60:
        elapsed_display = f"{elapsed_seconds:.2f} ثانیه"
    else:
        minutes = int(elapsed_seconds // 60)
        seconds = elapsed_seconds % 60
        elapsed_display = f"{minutes} دقیقه و {seconds:.2f} ثانیه"

    return {
        "analysis_completed_at": completed_at.isoformat(),
        "time_consumption_seconds": elapsed_seconds,
        "time_consumption_display": elapsed_display,
    }


async def save_agent_run(session_id: Optional[str], state: Dict[str, Any], final_report: str) -> None:
    if not session_id:
        logger.warning("Skipping final agent state persistence because session_id is missing.")
        return

    timing_data = build_analysis_timing(state)

    final_state = {
        **state,
        "final_report": final_report,
        **timing_data,
    }

    document = {
        "_id": session_id,
        "session_id": session_id,
        "symbol": state.get("symbol"),
        "final_report": final_report,
        "final_state": _make_mongo_safe(final_state),
        "updated_at": datetime.fromisoformat(timing_data["analysis_completed_at"]),
    }
    mongo = MongoManager(settings.mongo_agent_run_collection_name)
    try:
        await mongo.upsert_data(document)
    except Exception as exc:
        logger.warning("Failed to persist final agent run for session %s.", session_id, exc_info=exc)
    finally:
        mongo.close()


async def invoke_llm_and_log(llm: Any, prompt_value: Any, node_name: str, session_id: Optional[str]):
    response = await llm.ainvoke(prompt_value)
    await save_llm_usage(node_name=node_name, session_id=session_id, response=response)
    return response

async def _invoke_structured_with_recovery(
    llm: Any,
    prompt_value: Any,
    schema_model: Type[BaseModel],
    fallback_prompt: Optional[str] = None,
    node_name: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Tuple[BaseModel, Optional[Dict[str, str]]]:
    try:
        parsed_output = await llm.with_structured_output(schema_model).ainvoke(prompt_value)
        if not parsed_output:
            raise
        return parsed_output, None
    except Exception as exc:
        logger.warning(
            "Structured output invocation failed for schema %s; attempting recovery.",
            schema_model.__name__,
            exc_info=exc,
        )
        prompt_text = _prompt_to_text(prompt_value)
        fix_prompt = f"""
        Return ONLY valid JSON matching this schema:
        {schema_model.model_json_schema()}
        No extra text. Use null when unknown.

        Original prompt:
        {prompt_text}
        """
        raw_msg = await invoke_llm_and_log(
            llm,
            fix_prompt,
            node_name or schema_model.__name__,
            session_id,
        )
        raw = raw_msg.content if hasattr(raw_msg, "content") else str(raw_msg)
        try:
            raw = raw.replace('```','').replace('json','')
            out = schema_model.model_validate_json(raw)
            return out, {"recovered": "fix_prompt"}
        except ValidationError as validation_exc:
            logger.warning(
                "Recovery validation failed for schema %s; attempting JSON-only fallback.",
                schema_model.__name__,
                exc_info=validation_exc,
            )
            if fallback_prompt is None:
                fallback_prompt = f"""
Return ONLY valid JSON matching this schema:
{schema_model.model_json_schema()}
No extra text. Use null when unknown.
"""
            raw2_msg = await invoke_llm_and_log(
                llm,
                fallback_prompt + "\n\n" + prompt_text,
                node_name or schema_model.__name__,
                session_id,
            )
            raw2 = raw2_msg.content if hasattr(raw2_msg, "content") else str(raw2_msg)
            raw2 = raw2.replace('```','').replace('json','')
            out = schema_model.model_validate_json(raw2)
            return out, {"recovered": "json_only_fallback"}


def parse_iso_date(date_str):
    try:
        if not date_str:
            return None
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except ValueError:
        return None


@retry(stop=stop_after_attempt(5), wait=wait_fixed(2))
async def scrape_codal_report(url: str) -> str:
    """
    Asynchronously scrapes text content from a Codal report URL.
    Extracts text from all <p> tags.
    """
    logger.info(f"Scraping Codal report: {url}")
    
    # Create a custom SSL context that does not verify certificates
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    async with aiohttp.ClientSession() as session:
        async with session.get(url, ssl=ssl_context, timeout=30) as response:
            response.raise_for_status()
            content = await response.read()
            
            soup = BeautifulSoup(content, 'html.parser')
            p_tags = soup.find_all('p')
            
            logger.debug(f"Found {len(p_tags)} paragraphs in report.")
            
            final_text = []
            for p in p_tags:
                text = p.get_text(separator="\n", strip=True)
                if text:
                    final_text.append(text)
            
            return "\n".join(final_text)
        

def parse_persian_date(date_str):
    """Parse Persian date string to Gregorian datetime"""
    # Split date and time
    date_part, time_part = date_str.split(' ')
    
    # Parse Persian date
    year, month, day = map(int, date_part.split('/'))
    
    # Create jdatetime object
    persian_date = jdatetime.datetime(year, month, day)
    
    # Convert to Gregorian datetime
    gregorian_date = persian_date.togregorian()
    
    # Add time if needed (for more precise filtering)
    if time_part:
        hour, minute = map(int, time_part.split(':'))
        gregorian_date = gregorian_date.replace(hour=hour, minute=minute)
    
    return gregorian_date


def ensure_object(data, schema_class):
    """Converts a dict to a Pydantic object if necessary."""
    if isinstance(data, dict):
        try:
            return schema_class(**data)
        except Exception as e:
            print(f"Error converting to {schema_class.__name__}: {e}")
            return None
    return data
