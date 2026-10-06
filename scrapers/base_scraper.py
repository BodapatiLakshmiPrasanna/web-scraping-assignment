"""Shared networking + pagination logic. Source scrapers only add selectors/parsing."""
from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

import config

logger = logging.getLogger(__name__)


def create_session() -> requests.Session:
    """Session with User-Agent and automatic retries (exponential backoff) for temporary errors."""
    session = requests.Session()
    session.headers.update({"User-Agent": config.USER_AGENT})
    retries = Retry(
        total=config.RETRY_TOTAL,
        backoff_factor=config.RETRY_BACKOFF,
        status_forcelist=config.RETRY_STATUSES,
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


class BaseScraper(ABC):
    source_name: str = ""
    start_url: str = ""

    def __init__(self, session: requests.Session | None = None,
                 delay: float = config.REQUEST_DELAY,
                 timeout: float = config.REQUEST_TIMEOUT,
                 max_pages: int | None = None):
        self.session = session or create_session()
        self.delay = delay
        self.timeout = timeout
        self.max_pages = max_pages
        self.pages_scraped = 0
        self.pages_failed = 0
        self.parse_failures = 0   # records skipped because parsing raised

    # ---- networking -------------------------------------------------------
    def fetch(self, url: str) -> BeautifulSoup | None:
        """Download and parse one page. Returns None (and logs) on any request failure."""
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            response.encoding = "utf-8"  # keeps the GBP symbol correct
            return BeautifulSoup(response.text, "lxml")
        except requests.RequestException as exc:
            logger.error("[%s] Failed to fetch %s: %s", self.source_name, url, exc)
            return None
        finally:
            time.sleep(self.delay)  # be polite to the server

    # ---- pagination -------------------------------------------------------
    @abstractmethod
    def parse_page(self, soup: BeautifulSoup, page_url: str) -> list[dict]:
        """Return raw record dicts (text exactly as found) for one listing page."""

    def next_page_url(self, soup: BeautifulSoup, current_url: str) -> str | None:
        link = soup.select_one("li.next > a")
        if link and link.get("href"):
            return urljoin(current_url, link["href"])
        return None

    def scrape(self) -> list[dict]:
        """Follow the 'next' link until there is none. Never needs to know the page count."""
        url: str | None = self.start_url
        visited: set[str] = set()
        records: list[dict] = []
        page = 1
        while url and url not in visited:
            if self.max_pages and page > self.max_pages:
                logger.info("[%s] Reached max_pages=%d, stopping.", self.source_name, self.max_pages)
                break
            visited.add(url)
            logger.info("[%s] Page %d: %s", self.source_name, page, url)
            soup = self.fetch(url)
            if soup is None:
                self.pages_failed += 1
                break  # stop this source only; other sources still run
            self.pages_scraped += 1
            try:
                records.extend(self.parse_page(soup, url))
            except Exception:  # unexpected page layout: log and keep going
                logger.exception("[%s] Could not parse page %s", self.source_name, url)
            url = self.next_page_url(soup, url)
            page += 1
        logger.info("[%s] Finished: %d raw records from %d pages (%d page failures)",
                    self.source_name, len(records), self.pages_scraped, self.pages_failed)
        return records
