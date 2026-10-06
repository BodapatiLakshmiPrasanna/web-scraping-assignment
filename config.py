"""Central settings. Everything tunable lives here (or is overridden via CLI flags in main.py)."""

BOOKS_START_URL = "https://books.toscrape.com/"
QUOTES_START_URL = "https://quotes.toscrape.com/"

SOURCE_BOOKS = "Books to Scrape"
SOURCE_QUOTES = "Quotes to Scrape"
VALID_SOURCES = {SOURCE_BOOKS, SOURCE_QUOTES}

USER_AGENT = "ScrapingAssignment/1.0 (learning project)"
REQUEST_TIMEOUT = 10        # seconds
REQUEST_DELAY = 0.5         # polite pause after every request, seconds
RETRY_TOTAL = 3
RETRY_BACKOFF = 1.0         # 1s, 2s, 4s ...
RETRY_STATUSES = [429, 500, 502, 503, 504]

# Fixed CSV column order (every row has every column; N/A fields are left empty).
COLUMNS = [
    "source", "source_url", "name_or_title", "category", "price", "rating",
    "author", "tags", "description", "availability", "scraped_at",
]

DEFAULT_OUTPUT_DIR = "output"
DEFAULT_LOG_FILE = "logs/scraper.log"
