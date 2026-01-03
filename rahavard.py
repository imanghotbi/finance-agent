import asyncio
import json
from datetime import datetime, timezone, date
from typing import Dict, Optional, Any, List, Union
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

class RahavardError(Exception):
    """Custom exception for Rahavard API related errors."""
    pass

class RahavardClient:
    """
    Async client for interacting with the Rahavard365 API.
    """
    def __init__(self, base_url:str=settings.rahavard_base_url ,timeout: int = 30):
        self.timeout = ClientTimeout(total=timeout)
        self.session: Optional[ClientSession] = None
        self.base_url = base_url

    async def __aenter__(self):
        connector = TCPConnector(limit=100)
        self.session = ClientSession(
            headers=settings.default_headers, 
            base_url=self.base_url,
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
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError, RahavardError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )
    async def _request(self, method: str, endpoint: str, params: Optional[Dict] = None) -> Any:
        """
        Internal method to handle HTTP requests with Tenacity retry logic.
        """
        if self.session is None:
            self.session = ClientSession(headers=settings.default_headers, base_url=self.base_url, timeout=self.timeout)

        url = endpoint
        
        logger.debug(f"Requesting: {method} {self.base_url}/{endpoint} | Params: {params}")

        async with self.session.request(method, url, params=params) as response:
            if response.status != 200:
                error_msg = f"API Error {response.status}: {response.reason} for URL: {url}"
                raise RahavardError(error_msg)
            
            try:
                data = await response.json()
                return data
            except json.JSONDecodeError:
                text = await response.text()
                raise RahavardError(f"Invalid JSON received: {text[:100]}...")

    async def get_symbol_id(self, symbol: str) -> Optional[Dict[str, str]]:
        logger.info(f"Searching for symbol: {symbol}")
        
        try:
            data = await self._request("GET", "search", params={"keyword": symbol})
            stock_list = [item for item in data.get("data", []) if item.get("type") == "سهام"]
            
            if len(stock_list) >= 1:
                info = stock_list[0]
                return {
                    "id": info["entity_id"],
                    "trade_symbol": info["trade_symbol"],
                    "name": info["name"],
                    "short_name": info["short_name"],
                }
            return None

        except Exception as e:
            logger.error(f"Failed to find symbol ID for {symbol} after retries: {e}")
            return None

    async def get_asset_details(self, asset_id: str) -> Optional[Dict]:
        """
        Fetch general asset details, EPS, DPS, P/E, etc.
        """
        logger.info(f"Fetching asset details for ID: {asset_id}")
        try:
            resp = await self._request("GET", f"asset/{asset_id}")
            data = resp.get('data', {})
            
            # Safely access nested keys
            asset_info = data.get('asset', {})
            barometer = data.get('barometer', {})

            sizes = {0: 'small', 1: 'medium', 2: 'large'}
            types = {2: 'value', 1: 'balanced', 0: 'Growth'}

            result = {
                'sub_category': asset_info.get('category', {}).get('short_name'),
                'name': asset_info.get('short_name'),
                'last_trade_summary': data.get('header_last_trade'),
                'last_trade_same_cat': data.get('same_category'),
                'eps': data.get('eps'),
                'dps': data.get('dps'),
                'returns': data.get('returns'),
                'liquidities': data.get('liquidities'),
                'last_free_float': data.get('last_free_float'),
                'last_pb': data.get('last_pb'),
                'last_value': data.get('last_value'),
                'size_type_mat': {
                    'type': types.get(barometer.get('x'), 'Unknown'),
                    'size': sizes.get(barometer.get('y'), 'Unknown')
                }
            }
            return result
        except Exception as e:
            logger.error(f"Error fetching asset details for {asset_id}: {e}")
            return None

    async def get_pivot_indicators(self, asset_id: str) -> Optional[Dict]:
        """
        Fetch pivot indicators.
        """
        try:
            resp = await self._request("GET", f"asset/{asset_id}/indicators")
            data = resp.get('data', {})
            
            target_pivots = {'PivotPointFibonacci(30)', 'PivotPointClassic(30)'}
            pivots = [
                x for x in data.get('pivots', []) 
                if x.get('short_name_en') in target_pivots
            ]
            
            return {i['short_name_en']: i['value'] for i in pivots}
        except Exception as e:
            logger.error(f"Error fetching pivot indicators for {asset_id}: {e}")
            return None

    async def get_trade_history(self, asset_id: str, skip: int = 0, count: Optional[int] = None) -> List[Dict]:
        """
        Fetch historical trade data (daily bars).
        """
        params = {'_skip': skip}
        if count is not None:
            params['_count'] = count
            
        try:
            resp = await self._request("GET", f"asset/{asset_id}/trades", params=params)
            return resp.get('data', [])
        except Exception as e:
            logger.error(f"Error fetching trade history for {asset_id}: {e}")
            return []

    async def get_trade_details(self, asset_id: str, skip: int = 0, count: Optional[int] = None) -> List[Dict]:
        """
        Fetch detailed trade history.
        """
        params = {'_skip': skip}
        if count is not None:
            params['_count'] = count

        try:
            resp = await self._request("GET", f"asset/{asset_id}/tradedetails", params=params)
            return resp
        except Exception as e:
            logger.error(f"Error fetching trade details for {asset_id}: {e}")
            return []

    async def _fetch_fundamental_report(self, asset_id: str, endpoint: str) -> Optional[Dict]:
        """
        Refactored fundamental fetcher (kept here for completeness of context)
        """
        end_date = datetime.now(timezone.utc)
        start_date = end_date.replace(year=end_date.year - 5)
        start_str = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_str = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        params = {
            "asset_id": asset_id,
            "report_type_id": 1, 
            "view_currency_id": 1,
            "view_type_id": 1,
            "combination_state_id": 2,
            "audit_state_id": 2,
            "representation_state_id": 2,
            "start_date": start_str,
            "end_date": end_str,
            "fiscal_year_order": "ASC",
            "font_type": "FA",
            "detail_state": "summary",
            "ratio_category_ids": "1,2,3,4",
            "sale_type_ids": "4",
            "detail_type_id": "1",
            "no_change_in_view_type": "true"
        }

        try:
            resp = await self._request("GET", f"fundamental/{endpoint}", params=params)
            data = resp.get('data', {})
            
            if not data:
                logger.warning(f"No data returned for {endpoint} - Asset: {asset_id}")
                return None
            
            column_defs = data.get('column_definitions', [])
            if len(column_defs) < 2:
                logger.warning("Insufficient column definitions found.")
                return None
                
            years = [col['header_name'] for col in column_defs[1:]]
            
            parsed_rows = {}
            for row in data.get('row_data', []):
                title = row.get('row_title', {}).get('title')
                ticks = row.get('row_properties', {}).get('light_chart_ticks')
                if title and ticks:
                    parsed_rows[title] = ticks

            # 3. Map values to years
            result = {}
            for key, values in parsed_rows.items():
                mapped_values = {}
                for i in range(len(values)):
                    if i < len(years):
                        mapped_values[years[i]] = values[i]
                result[key] = mapped_values

            logger.info(f"Successfully fetched {endpoint} data.")
            return result

        except Exception as e:
            logger.error(f"Error fetching fundamental data ({endpoint}) for {asset_id}: {e}")
            return None

    async def get_balance_sheet(self, asset_id: str) -> Optional[Dict]:
        return await self._fetch_fundamental_report(asset_id, "company-balance-sheets")

    async def get_profit_loss(self, asset_id: str) -> Optional[Dict]:
        return await self._fetch_fundamental_report(asset_id, "company-profit-losses")

    async def get_cash_flow(self, asset_id: str) -> Optional[Dict]:
        return await self._fetch_fundamental_report(asset_id, "company-cash-flows")

    async def get_financial_ratios(self, asset_id: str) -> Optional[Dict]:
        return await self._fetch_fundamental_report(asset_id, "company-financial-ratios")

    async def get_news(self, asset_id: str, count: int = 200, after_date: Optional[date] = None) -> List[Dict]:
        """
        Fetch news for a specific asset.
        """
        try:
            resp = await self._request("GET", f"asset/{asset_id}/feeds", params={'_count': count})
            raw_news = resp.get('data', [])

            if after_date:
                raw_news = [
                    item for item in raw_news 
                    if datetime.fromisoformat(item['date']).date() > after_date
                ]

            cleaned_news = [
                {k: item.get(k) for k in ['date', 'type', 'title', 'body']}
                for item in raw_news
            ]
            return cleaned_news
            
        except Exception as e:
            logger.error(f"Error fetching news for {asset_id}: {e}")
            return []
