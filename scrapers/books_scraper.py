"""Books to Scrape: listing selectors, optional detail-page enrichment."""
from __future__ import annotations

import logging
from urllib.parse import urljoin

from bs4 import BeautifulSoup

import config
from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class BooksScraper(BaseScraper):
    source_name = config.SOURCE_BOOKS
    start_url = config.BOOKS_START_URL

    def __init__(self, *args, fetch_details: bool = True, **kwargs):
        super().__init__(*args, **kwargs)
        self.fetch_details = fetch_details
        self.detail_failures = 0

    def parse_book(self, article, page_url: str) -> dict:
        link = article.select_one("h3 > a")
        price = article.select_one("p.price_color")
        rating = article.select_one("p.star-rating")
        avail = article.select_one("p.instock.availability")
        return {
            "title": (link.get("title") or link.get_text()) if link else None,
            "href": urljoin(page_url, link["href"]) if link and link.get("href") else None,
            "price_raw": price.get_text() if price else None,
            "rating_raw": " ".join(rating.get("class", [])) if rating else None,
            "availability_raw": avail.get_text() if avail else None,
            "category_raw": None,
            "description_raw": None,
        }

    def parse_page(self, soup: BeautifulSoup, page_url: str) -> list[dict]:
        records = []
        for article in soup.select("article.product_pod"):
            try:
                records.append(self.parse_book(article, page_url))
            except Exception:
                self.parse_failures += 1
                logger.exception("[%s] Skipping unparseable book on %s", self.source_name, page_url)
        return records

    def parse_detail(self, soup: BeautifulSoup) -> dict:
        """Category = 3rd breadcrumb item (Home > Books > <Category> > Title)."""
        crumbs = soup.select("ul.breadcrumb li")
        category = crumbs[2].get_text() if len(crumbs) >= 3 else None
        desc = soup.select_one("#product_description + p")
        return {"category_raw": category, "description_raw": desc.get_text() if desc else None}

    def scrape(self) -> list[dict]:
        records = super().scrape()
        if not self.fetch_details:
            logger.info("[%s] Detail pages disabled: category/description left empty.", self.source_name)
            return records
        for i, rec in enumerate(records, 1):
            if not rec.get("href"):
                continue
            soup = self.fetch(rec["href"])
            if soup is None:
                self.detail_failures += 1  # keep the record; category/description stay empty
                continue
            try:
                rec.update(self.parse_detail(soup))
            except Exception:
                self.detail_failures += 1
                logger.exception("[%s] Could not parse detail page %s", self.source_name, rec["href"])
            if i % 100 == 0:
                logger.info("[%s] Detail pages done: %d/%d", self.source_name, i, len(records))
        return records
