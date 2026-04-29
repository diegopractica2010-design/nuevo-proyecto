from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Mapping

import requests


logger = logging.getLogger(__name__)


class ScraperRequestError(RuntimeError):
    pass


@dataclass
class BaseScraper:
    timeout: float = 15.0
    delay_seconds: float = 0.5
    max_retries: int = 3
    backoff_seconds: float = 0.5
    headers: Mapping[str, str] = field(
        default_factory=lambda: {
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
        }
    )

    def __post_init__(self) -> None:
        self.session = requests.Session()

    def get(self, url: str, *, params: dict | None = None) -> str:
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            if self.delay_seconds > 0:
                time.sleep(self.delay_seconds)

            try:
                response = self.session.get(
                    url,
                    params=params,
                    headers=dict(self.headers),
                    timeout=self.timeout,
                )
                response.raise_for_status()
                return response.text
            except requests.RequestException as exc:
                last_error = exc
                logger.warning("Scraper request failed on attempt %s/%s: %s", attempt, self.max_retries, exc)
                if attempt < self.max_retries:
                    time.sleep(self.backoff_seconds * (2 ** (attempt - 1)))

        raise ScraperRequestError(f"Failed to fetch {url}") from last_error

