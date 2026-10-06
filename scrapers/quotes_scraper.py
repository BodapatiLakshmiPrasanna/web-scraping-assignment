"""Quotes to Scrape: selectors for one listing page."""
from __future__ import annotations

import logging

from bs4 import BeautifulSoup

import config
from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class QuotesScraper(BaseScraper):
    source_name = config.SOURCE_QUOTES
    start_url = config.QUOTES_START_URL

    def parse_quote(self, div, page_url: str) -> dict:
        text = div.select_one("span.text")
        author = div.select_one("small.author")
        return {
            "text_raw": text.get_text() if text else None,
            "author_raw": author.get_text() if author else None,
            "tags_raw": [t.get_text() for t in div.select("div.tags a.tag")],
            "page_url": page_url,  # source_url = the page where the quote appeared
        }

    def parse_page(self, soup: BeautifulSoup, page_url: str) -> list[dict]:
        records = []
        for div in soup.select("div.quote"):
            try:
                records.append(self.parse_quote(div, page_url))
            except Exception:
                self.parse_failures += 1
                logger.exception("[%s] Skipping unparseable quote on %s", self.source_name, page_url)
        return records
