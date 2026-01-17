from typing import Any, Dict, Optional, Tuple, Type
from datetime import datetime , timedelta
import ssl
import aiohttp
from bs4 import BeautifulSoup
import jdatetime
from tenacity import retry, stop_after_attempt, wait_fixed
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, ValidationError

try:
    from src.core.logger import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


def create_prompt(system_prompt: str, user_message: str) -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages([("system", system_prompt), ("human", user_message)])


def _prompt_to_text(prompt_value: Any) -> str:
    if hasattr(prompt_value, "to_string"):
        return prompt_value.to_string()
    return str(prompt_value)


async def _invoke_structured_with_recovery(
    llm: Any,
    prompt_value: Any,
    schema_model: Type[BaseModel],
    fallback_prompt: Optional[str] = None,
) -> Tuple[BaseModel, Optional[Dict[str, str]]]:
    try:
        out = await llm.with_structured_output(schema_model).ainvoke(prompt_value)
        return out, None
    except Exception:
        prompt_text = _prompt_to_text(prompt_value)
        fix_prompt = f"""
        Return ONLY valid JSON matching this schema:
        {schema_model.model_json_schema()}
        No extra text. Use null when unknown.

        Original prompt:
        {prompt_text}
        """
        raw_msg = await llm.ainvoke(fix_prompt)
        raw = raw_msg.content if hasattr(raw_msg, "content") else str(raw_msg)
        try:
            out = schema_model.model_validate_json(raw)
            return out, {"recovered": "fix_prompt"}
        except ValidationError:
            if fallback_prompt is None:
                fallback_prompt = f"""
Return ONLY valid JSON matching this schema:
{schema_model.model_json_schema()}
No extra text. Use null when unknown.
"""
            raw2_msg = await llm.ainvoke(fallback_prompt + "\n\n" + prompt_text)
            raw2 = raw2_msg.content if hasattr(raw2_msg, "content") else str(raw2_msg)
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
        async with session.get(url, ssl=ssl_context, timeout=10) as response:
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