import asyncio
import json
from datetime import date, datetime
from typing import Dict, List, Optional, Union, Any
import aiohttp
from aiohttp import ClientSession, ClientTimeout, TCPConnector
import logging

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
    import logging
    logger = logging.getLogger("Finance Agent System")
    logging.basicConfig(level=logging.INFO)
from config import settings


# Custom Exception
class TwitterAPIError(Exception):
    """Custom exception for Twitter RapidAPI related errors."""
    pass

class TwitterRapidClient:
    """
    Async client for fetching Twitter data via RapidAPI.
    """
    def __init__(
        self, 
        base_url: str,
        api_key: str = settings.rapid_api_key.get_secret_value(), 
        api_host: str = settings.rapid_api_host,
        proxy_url: Optional[str] = settings.proxy_url,
        timeout: int = 30
    ):
        self.headers = {
            "x-rapidapi-key": api_key,
            "x-rapidapi-host": api_host
        }
        self.proxy_url = proxy_url
        self.timeout = ClientTimeout(total=timeout)
        self.session: Optional[ClientSession] = None
        self.base_url = base_url

    async def __aenter__(self):
        # Configure connector appropriately
        connector = TCPConnector(limit=100)
        self.session = ClientSession(
            headers=self.headers,
            base_url= self.base_url,
            timeout=self.timeout,
            connector=connector
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def _format_date(self, date_obj: Union[str, date, datetime]) -> str:
        """Helper to ensure dates are in YYYY-MM-DD string format."""
        if isinstance(date_obj, (date, datetime)):
            return date_obj.strftime("%Y-%m-%d")
        return date_obj

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError, TwitterAPIError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )
    async def _request(self, endpoint:str ,params: Dict[str, Any]) -> Dict:
        """
        Internal method to handle HTTP GET requests with retry logic.
        """
        if self.session is None:
            # Fallback if context manager isn't used
            self.session = ClientSession(headers=self.headers, base_url= self.base_url ,timeout=self.timeout)

        logger.debug(f"Requesting Twitter API with params: {params}")

        try:
            # aiohttp handles proxies via the 'proxy' parameter on individual requests
            async with self.session.get(url=endpoint ,params=params, proxy=self.proxy_url) as response:
                if response.status != 200:
                    error_msg = f"API Error {response.status}: {response.reason}"
                    # RapidAPI often sends detailed error messages in the body
                    try:
                        error_body = await response.text()
                        logger.error(f"{error_msg} | Body: {error_body}")
                    except:
                        pass
                    raise TwitterAPIError(error_msg)

                try:
                    data = await response.json()
                    return data
                except json.JSONDecodeError:
                    text = await response.text()
                    raise TwitterAPIError(f"Invalid JSON received: {text[:100]}...")
                    
        except aiohttp.ClientConnectorError as e:
             # Specific handling for proxy connection issues
            logger.error(f"Connection failed (check proxy settings at {self.proxy_url}): {e}")
            raise

    async def search_tweets(
        self, 
        query: str, 
        start_date: Union[str, date], 
        end_date: Union[str, date], 
        limit: int = 20,
        min_retweets: int = 1,
        min_likes: int = 1,
        section: str = "top"
    ) -> List[Dict]:
        """
        Search for tweets using specific filters.
        """
        formatted_start = self._format_date(start_date)
        formatted_end = self._format_date(end_date)
        
        params = {
            "query": query,
            "section": section,
            "min_retweets": str(min_retweets),
            "min_likes": str(min_likes),
            "limit": str(limit),
            "start_date": formatted_start,
            "end_date": formatted_end
        }

        logger.info(f"Searching tweets for '{query}' from {formatted_start} to {formatted_end}")

        try:
            data = await self._request('search',params)
            
            raw_results = data.get('results', [])
            
            # Map to clean dictionary structure
            cleaned_tweets = []
            for tweet in raw_results:
                if tweet.get('language') == 'fa':
                    tweet_info = {
                        'text': tweet.get('text'),
                        'likes': tweet.get('favorite_count'),
                        'retweets': tweet.get('retweet_count'),
                        'views': tweet.get('views'),
                        'replies': tweet.get('reply_count'),
                        'created_at': tweet.get('creation_date'), 
                        'user': tweet.get('user', {}).get('username') 
                }
                    cleaned_tweets.append(tweet_info)
            
            logger.info(f"Successfully retrieved {len(cleaned_tweets)} tweets.")
            return cleaned_tweets

        except Exception as e:
            logger.error(f"Failed to fetch tweets for query '{query}': {e}")
            return []