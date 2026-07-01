"""
Cliente HTTP con protección antibot:
- Proxy rotation
- Random User-Agents
- Random delays entre requests
- Headers que imitan navegador real
"""

import asyncio
import logging
import random
from typing import Optional

import httpx

from backend.config import get_settings
from backend.infrastructure.proxy_manager import get_proxy_manager

logger = logging.getLogger(__name__)

# User-Agents reales de navegadores
REAL_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
]

# Headers que imitan navegador real
BASE_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "es-CL,es;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Cache-Control": "max-age=0",
}


def _get_antibot_headers() -> dict[str, str]:
    """Devuelve headers con User-Agent aleatorio para evadir detección."""
    headers = BASE_HEADERS.copy()
    headers["User-Agent"] = random.choice(REAL_USER_AGENTS)
    return headers


async def _random_delay(min_seconds: float = 0.5, max_seconds: float = 3.0) -> None:
    """Delay aleatorio para evitar detección de bot."""
    delay = random.uniform(min_seconds, max_seconds)
    await asyncio.sleep(delay)


class AntiBotHTTPClient:
    """Cliente HTTP con protección antibot."""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.proxy_manager = get_proxy_manager()
        self.settings = get_settings()
    
    async def get(
        self,
        url: str,
        *,
        headers: Optional[dict[str, str]] = None,
        retry_count: int = 3,
        apply_delay: bool = True,
    ) -> Optional[httpx.Response]:
        """GET request con reintentos y protección antibot."""
        
        if apply_delay:
            await _random_delay()
        
        merged_headers = _get_antibot_headers()
        if headers:
            merged_headers.update(headers)
        
        for attempt in range(retry_count):
            try:
                proxy_dict = self.proxy_manager.get_proxies_dict()
                proxy_url = proxy_dict.get("http") if proxy_dict else None
                
                async with httpx.AsyncClient(
                    proxies=proxy_dict,
                    timeout=self.timeout,
                    follow_redirects=True,
                ) as client:
                    logger.debug(f"GET {url} (intento {attempt + 1}/{retry_count})")
                    response = await client.get(url, headers=merged_headers)
                    
                    # Reporte de éxito al proxy manager
                    if proxy_url:
                        self.proxy_manager.report_success(proxy_url)
                    
                    logger.debug(f"Respuesta: {response.status_code}")
                    return response
            
            except Exception as exc:
                logger.warning(f"GET {url} falló (intento {attempt + 1}): {exc}")
                proxy_url = self.proxy_manager.get_next_proxy()
                if proxy_url:
                    self.proxy_manager.report_failure(proxy_url)
                
                if attempt < retry_count - 1:
                    await asyncio.sleep(2 ** attempt)  # Backoff exponencial
        
        logger.error(f"GET {url} falló después de {retry_count} intentos")
        return None
    
    async def post(
        self,
        url: str,
        *,
        data: Optional[dict] = None,
        json: Optional[dict] = None,
        headers: Optional[dict[str, str]] = None,
        retry_count: int = 3,
        apply_delay: bool = True,
    ) -> Optional[httpx.Response]:
        """POST request con reintentos y protección antibot."""
        
        if apply_delay:
            await _random_delay()
        
        merged_headers = _get_antibot_headers()
        if headers:
            merged_headers.update(headers)
        
        for attempt in range(retry_count):
            try:
                proxy_dict = self.proxy_manager.get_proxies_dict()
                proxy_url = proxy_dict.get("http") if proxy_dict else None
                
                async with httpx.AsyncClient(
                    proxies=proxy_dict,
                    timeout=self.timeout,
                    follow_redirects=True,
                ) as client:
                    logger.debug(f"POST {url} (intento {attempt + 1}/{retry_count})")
                    response = await client.post(
                        url,
                        data=data,
                        json=json,
                        headers=merged_headers,
                    )
                    
                    if proxy_url:
                        self.proxy_manager.report_success(proxy_url)
                    
                    logger.debug(f"Respuesta: {response.status_code}")
                    return response
            
            except Exception as exc:
                logger.warning(f"POST {url} falló (intento {attempt + 1}): {exc}")
                proxy_url = self.proxy_manager.get_next_proxy()
                if proxy_url:
                    self.proxy_manager.report_failure(proxy_url)
                
                if attempt < retry_count - 1:
                    await asyncio.sleep(2 ** attempt)
        
        logger.error(f"POST {url} falló después de {retry_count} intentos")
        return None


# Singleton global
_http_client: Optional[AntiBotHTTPClient] = None


def get_http_client() -> AntiBotHTTPClient:
    """Devuelve el cliente HTTP singleton."""
    global _http_client
    if _http_client is None:
        _http_client = AntiBotHTTPClient()
    return _http_client
