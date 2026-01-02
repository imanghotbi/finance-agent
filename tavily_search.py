import asyncio
import json
from datetime import date, datetime
from typing import Dict, List, Optional, Union, Any
import logging
import aiohttp
from aiohttp import ClientSession, ClientTimeout, TCPConnector


from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

try:
    from logger import logger
except ImportError:
    logger = logging.getLogger("Finance Agent System")
    logging.basicConfig(level=logging.INFO)

from config import settings


class TavilyError(Exception):
    """Custom exception for Tavily API related errors."""
    pass

class TavilyClient:
    """
    Async client for the Tavily Search API (AI Search).
    """
    def __init__(self, api_key: str, base_url:str ,proxy_url:str = None ,timeout: int = 60):
        self.api_key = api_key
        self.timeout = ClientTimeout(total=timeout)
        self.session: Optional[ClientSession] = None
        self.proxy_url = proxy_url
        self.base_url = base_url

    async def __aenter__(self):
        connector = TCPConnector(limit=100)
        self.session = ClientSession(
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }, 
            timeout=self.timeout,
            connector=connector,
            base_url=self.base_url 
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def _format_date(self, date_obj: Union[str, date, datetime, None]) -> Optional[str]:
        """Helper to ensure dates are in YYYY-MM-DD string format."""
        if date_obj is None:
            return None
        if isinstance(date_obj, (date, datetime)):
            return date_obj.strftime("%Y-%m-%d")
        return date_obj

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError, TavilyError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )
    async def _request(self, endpoint ,payload: Dict[str, Any]) -> Dict:
        """
        Internal method to handle POST requests with retry logic.
        """
        if self.session is None:
            self.session = ClientSession(
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                timeout=self.timeout,
                base_url=self.base_url 
            )

        # Log payload (truncate query for cleanliness)
        debug_payload = payload.copy()
        if 'query' in debug_payload:
            debug_payload['query'] = debug_payload['query'][:50] + "..."
        logger.debug(f"Sending Tavily Request: {debug_payload}")
        try:
            async with self.session.post(endpoint, json=payload,proxy=self.proxy_url) as response:
                if response.status != 200:
                    error_msg = f"Tavily API Error {response.status}: {response.reason}"
                    try:
                        err_body = await response.text()
                        logger.error(f"{error_msg} | Body: {err_body}")
                    except:
                        pass
                    raise TavilyError(error_msg)
                
                try:
                    data = await response.json()
                    return data
                except json.JSONDecodeError:
                    text = await response.text()
                    raise TavilyError(f"Invalid JSON received from Tavily: {text[:100]}...")
                
        except aiohttp.ClientConnectorError as e:
             # Specific handling for proxy connection issues
            logger.error(f"Connection failed (check proxy settings at {self.proxy_url}): {e}")
            raise

    async def search(
        self, 
        query: str,
        search_depth: str = "advanced",
        include_answer: str = "advanced",
        start_date: Optional[Union[str, date]] = None,
        end_date: Optional[Union[str, date]] = None,
        include_usage: bool = True,
        include_raw_content: str = "text",
        country: Optional[str] = "iran",
        max_results: int = 5
    ) -> Dict:
        """
        Perform an AI search using Tavily.
        
        Args:
            query: The search question.
            search_depth: "basic" or "advanced".
            include_answer: "basic", "advanced", or None.
            start_date: Filter results after this date.
            end_date: Filter results before this date.
            country: 2-letter country code (or full name if API supports it, e.g. "ir").
        """
        
        # Format dates
        f_start = self._format_date(start_date)
        f_end = self._format_date(end_date)

        payload = {
            "query": query,
            "search_depth": search_depth,
            "include_answer": include_answer,
            "include_usage": include_usage,
            "max_results": max_results
        }

        # Add optional parameters only if they exist (cleaner payload)
        if f_start:
            payload["start_date"] = f_start
        if f_end:
            payload["end_date"] = f_end
        if include_raw_content:
            payload["include_raw_content"] = include_raw_content
        if country:
            payload["country"] = country

        logger.info(f"Searching Tavily: '{query}' (Depth: {search_depth})")

        try:
            data = await self._request('search' , payload)
            
            # You might want to process the answer or results here
            answer = data.get("answer", "No answer generated.")
            results_count = len(data.get("results", []))
            
            logger.info(f"Tavily Search Complete. Found {results_count} sources.")
            return data

        except Exception as e:
            logger.error(f"Tavily search failed for query '{query}': {e}")
            return {}