from typing import Any, Dict, Optional
from urllib.parse import urlparse

from aiohttp import TCPConnector

try:
    from aiohttp_socks import ProxyConnector
except ImportError:
    ProxyConnector = None


def normalize_proxy_url(proxy_url: Optional[str]) -> Optional[str]:
    if proxy_url is None:
        return None
    value = proxy_url.strip()
    return value or None


def is_socks_proxy(proxy_url: Optional[str]) -> bool:
    url = normalize_proxy_url(proxy_url)
    if not url:
        return False
    return urlparse(url).scheme.lower().startswith("socks")


def build_proxy_connector(proxy_url: Optional[str], limit: int = 100):
    url = normalize_proxy_url(proxy_url)
    if is_socks_proxy(url):
        if ProxyConnector is None:
            raise RuntimeError(
                "SOCKS proxy requested but aiohttp-socks is not installed."
            )
        return ProxyConnector.from_url(url, limit=limit)
    return TCPConnector(limit=limit)


def proxy_request_kwargs(proxy_url: Optional[str]) -> Dict[str, Any]:
    url = normalize_proxy_url(proxy_url)
    if not url or is_socks_proxy(url):
        return {}
    return {"proxy": url}
