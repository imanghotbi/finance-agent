import asyncio
import json
from typing import Dict, Optional, Any, List
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

# Import your custom logger
try:
    from logger import logger
except ImportError:
    logger = logging.getLogger("Finance Agent System")
    logging.basicConfig(level=logging.INFO)
from config import settings

class SahamyabError(Exception):
    """Custom exception for Sahamyab API related errors."""
    pass

class SahamyabClient:
    """
    Async client for interacting with the Sahamyab API.
    """
    def __init__(self, base_url:str = settings.sahamyab_base_url ,timeout: int = 30):
        self.timeout = ClientTimeout(total=timeout)
        self.session: Optional[ClientSession] = None
        self.base_url = base_url

    async def __aenter__(self):
        connector = TCPConnector(limit=100)
        self.session = ClientSession(
            headers=settings.default_headers, 
            base_url= self.base_url,
            timeout=self.timeout,
            connector=connector
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError, SahamyabError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )
    async def _request(self, method: str, endpoint: str, params: Optional[Dict] = None, json_data: Optional[Dict] = None) -> Any:
        """
        Internal method to handle HTTP requests with Tenacity retry logic.
        """
        if self.session is None:
            self.session = ClientSession(headers=settings.default_headers, base_url=self.base_url ,timeout=self.timeout)

        logger.debug(f"Requesting: {method} {self.base_url}/{endpoint} | Params: {params}")

        async with self.session.request(method, endpoint, params=params, json=json_data) as response:
            if response.status != 200:
                error_msg = f"API Error {response.status}: {response.reason} for URL: {endpoint}"
                raise SahamyabError(error_msg)
            
            try:
                data = await response.json()
                return data
            except json.JSONDecodeError:
                text = await response.text()
                raise SahamyabError(f"Invalid JSON received: {text[:100]}...")

    async def get_trade_info(self, symbol: str) -> Optional[Dict]:
        """
        Fetches trade info (Saham Negar data).
        """
        url = 'api/proxy/symbol/getSymbolExtData'
        params = {
            'v': '0.1',
            'code': symbol,
            'stockWatch': '1'
        }
        
        try:
            data = await self._request('GET', url, params=params)
            
            if not data or 'result' not in data or not data['result']:
                logger.warning(f"No trade info found for symbol: {symbol}")
                return None

            result = data['result'][0]
            
            return {
                'index_affect': result.get('index_affect'),
                'pe': result.get('PE'),
                'group_pe': result.get('sectorPE'),
                "profit_7days": result.get("profit7Days"),
                "profit_30days": result.get("profit30Days"),
                "profit_91days": result.get("profit91Days"),
                "profit_182days": result.get("profit182Days"),
                "profit_365days": result.get("profit365Days"),
                "profit_all_days": result.get("profitAllDays"),
                "month_profit_rank": result.get("monthProfitRank"),
                "month_profit_rank_group": result.get("monthProfitRankGroup"),
                "market_value_rank": result.get("marketValueRank"),
                "market_value_rank_group": result.get("marketValueRankGroup"),
                "trade_volume_rank": result.get("tradeVolumeRank"),
                "trade_Volume_rankgroup": result.get("tradeVolumeRankGroup"),
                "liquidity_coefficient": result.get("zaribNaghdShavandegi"),
                "correlation_gold_fund": result.get("correlation_IRXYXTPI0006"),
                "correlation_main_index": result.get("correlation_main_index")
            }
        except Exception as e:
            logger.error(f"Error fetching trade info for {symbol}: {e}")
            return None

    async def get_overall_info(self, symbol: str) -> Optional[Dict]: 
        """
        Fetches general symbol info (Name, Status, IDs).
        """
        url = f'guest/twiter/symbolInfo'
        params = {'v': '0.1'}
        payload = {
            'symbol': symbol,
            'price': True,
            'bestLimits': True,
            'full': True,
        }
        
        try:
            data = await self._request('POST', url, params=params, json_data=payload)
            
            if not data:
                logger.warning(f"No overall info returned for symbol: {symbol}")
                return None

            return {
                'id': data.get('InsCode'),
                'name': data.get('name'),
                'corpName': data.get('corpName'),
                'section_name': data.get('sectionName'),
                'sub_section_name': data.get('subSectionName'),
                'queue': data.get("q_status"),
                'pe': data.get('PE'),
                'group_pe': data.get('sectorPE'),
                'estimated_eps': data.get('estimatedEPS')
            }
        except Exception as e:
            logger.error(f"Error fetching overall info for {symbol}: {e}")
            return None

    async def get_tweets(self, symbol: str, page: int = 0, last_tweet_id: Optional[str] = None) -> List[Dict]:
        """
        Fetches user comments/tweets about the symbol.
        """
        url = f'guest/twiter/list'
        params = {'v': '0.1'}
        payload = {
            'tag': symbol,
            'page': page
        }
        
        if last_tweet_id:
            payload['id'] = last_tweet_id

        try:
            data = await self._request('POST', url, params=params, json_data=payload)
            
            items = data.get('items', [])
            # Filter out items with media content (as per original logic)
            filtered_items = [
                item for item in items 
                if not item.get('mediaContentType', False)
            ]
            
            return filtered_items
        except Exception as e:
            logger.error(f"Error fetching tweets for {symbol}: {e}")
            return []

    async def get_codal_notices(self, symbol: str, cleaned: bool = True) -> List[Dict]:
        """
        Fetches Codal notices for the symbol.
        """
        url = f'api/proxy/symbol/getCodal'
        params = {
            'v': '0.1',
            'code': symbol,
            'page': '0'
        }

        try:
            data = await self._request('GET', url, params=params)
            
            raw_result = data.get('result', [])
            
            if cleaned:
                return [{
                    'id': f"codal_{idx}",
                    'publishDate': item.get('publishDate'),
                    'title': item.get('title'),
                    'url': item.get('url')
                } for idx, item in enumerate(raw_result)]
            
            return raw_result
        except Exception as e:
            logger.error(f"Error fetching Codal notices for {symbol}: {e}")
            return []