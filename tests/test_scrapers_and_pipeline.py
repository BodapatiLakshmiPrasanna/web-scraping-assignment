"""Offline tests: fake HTTP session serving HTML shaped like the two real sites."""
import csv
import json

import requests

from pipeline import run_pipeline
from scrapers.books_scraper import BooksScraper
from scrapers.quotes_scraper import QuotesScraper

BOOK_LISTING = """<html><body><ol>
<article class="product_pod"><p class="star-rating Three"></p>
<h3><a href="{href}" title="{title}">{short}...</a></h3>
<div class="product_price"><p class="price_color">\u00c2\u00a3{price}</p>
<p class="instock availability"><i></i>
   In stock
</p></div></article>
<article class="product_pod"><h3></h3></article>
</ol>{nxt}</body></html>"""
BOOK_DETAIL = """<html><ul class="breadcrumb"><li>Home</li><li>Books</li><li>Poetry</li><li>x</li></ul>
<div id="product_description"></div><p>A fine   book.</p></html>"""
QUOTES_PAGE = """<html><body>
<div class="quote"><span class="text">\u201cQ{n}\u201d</span><span>by <small class="author">Al</small></span>
<div class="tags"><a class="tag">Life</a><a class="tag">love</a></div></div>
<div class="quote"><span class="text">\u201cNo author {n}\u201d</span></div>
{nxt}</body></html>"""


class FakeResponse:
    def __init__(self, text, status=200):
        self.text, self.status_code, self.encoding = text, status, None

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}")


class FakeSession:
    def __init__(self, pages):
        self.pages, self.calls = pages, []

    def get(self, url, timeout=None):
        self.calls.append(url)
        if url not in self.pages:
            return FakeResponse("", 404)
        page = self.pages[url]
        if isinstance(page, Exception):
            raise page
        return FakeResponse(page)


def nxt(href):
    return f'<ul><li class="next"><a href="{href}">next</a></li></ul>'


def books_site():
    s = "https://books.toscrape.com/"
    return {
        s: BOOK_LISTING.format(href="catalogue/b1/index.html", title="Book One", short="Book", price="10.00", nxt=nxt("catalogue/page-2.html")),
        s + "catalogue/page-2.html": BOOK_LISTING.format(href="b2/index.html", title="Book Two", short="Book", price="20.00", nxt=""),
        s + "catalogue/b1/index.html": BOOK_DETAIL,
        s + "catalogue/b2/index.html": BOOK_DETAIL,
    }


def quotes_site():
    s = "https://quotes.toscrape.com/"
    return {s: QUOTES_PAGE.format(n=1, nxt=nxt("/page/2/")), s + "page/2/": QUOTES_PAGE.format(n=2, nxt="")}


def test_books_scraper_pagination_and_details():
    sc = BooksScraper(FakeSession(books_site()), delay=0)
    raw = sc.scrape()
    assert sc.pages_scraped == 2 and len(raw) == 4   # 2 real + 2 empty <article> per page
    first = raw[0]
    assert first["title"] == "Book One" and first["href"].endswith("catalogue/b1/index.html")
    assert first["category_raw"] == "Poetry" and "fine" in first["description_raw"]


def test_page_failure_stops_only_that_source():
    pages = books_site()
    pages["https://books.toscrape.com/catalogue/page-2.html"] = requests.ConnectionError("boom")
    sc = BooksScraper(FakeSession(pages), delay=0, fetch_details=False)
    raw = sc.scrape()
    assert sc.pages_failed == 1 and len(raw) == 2


def test_full_pipeline_files_and_reconciliation(tmp_path):
    books = BooksScraper(FakeSession(books_site()), delay=0)
    quotes = QuotesScraper(FakeSession(quotes_site()), delay=0)
    summary = run_pipeline([books, quotes], tmp_path)

    rows = list(csv.DictReader(open(tmp_path / "final_dataset.csv", encoding="utf-8")))
    saved = json.load(open(tmp_path / "summary_report.json", encoding="utf-8"))
    assert saved["totals"]["final_record_count"] == len(rows) == summary["totals"]["final_record_count"]
    assert saved["totals"]["reconciles"] is True
    sources = {r["source"] for r in rows}
    assert sources == {"Books to Scrape", "Quotes to Scrape"}
    book = next(r for r in rows if r["name_or_title"] == "Book One")
    assert book["price"] == "10.0" and book["rating"] == "3" and book["category"] == "Poetry"
    assert book["author"] == "" and book["tags"] == ""
    assert saved["per_source"]["Books to Scrape"]["rejected_by_reason"]["missing_name"] == 2
    assert saved["per_source"]["Quotes to Scrape"]["rejected_by_reason"]["missing_author"] == 2


def test_failed_source_does_not_stop_other(tmp_path):
    class Boom:
        source_name = "Books to Scrape"
        pages_scraped = pages_failed = parse_failures = 0

        def scrape(self):
            raise RuntimeError("down")

    summary = run_pipeline([Boom(), QuotesScraper(FakeSession(quotes_site()), delay=0)], tmp_path)
    assert "Books to Scrape" in summary["failed_sources"]
    assert summary["per_source"]["Quotes to Scrape"]["final"] == 2
