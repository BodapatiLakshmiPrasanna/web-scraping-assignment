"""Single entry point:  python main.py   (run `python main.py --help` for options)."""
import argparse
import logging
import sys
from pathlib import Path

import config
from pipeline import run_pipeline
from scrapers.base_scraper import create_session
from scrapers.books_scraper import BooksScraper
from scrapers.quotes_scraper import QuotesScraper


def setup_logging(log_file: str) -> None:
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")
    handlers = [logging.StreamHandler(sys.stdout), logging.FileHandler(log_file, mode="w", encoding="utf-8")]
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for h in handlers:
        h.setFormatter(fmt)
        root.addHandler(h)


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Multi-source scraping + consolidation pipeline")
    p.add_argument("--output-dir", default=config.DEFAULT_OUTPUT_DIR)
    p.add_argument("--log-file", default=config.DEFAULT_LOG_FILE)
    p.add_argument("--delay", type=float, default=config.REQUEST_DELAY, help="seconds between requests")
    p.add_argument("--max-pages", type=int, default=None, help="limit listing pages per source (testing)")
    p.add_argument("--no-details", action="store_true",
                   help="skip book detail pages (fast; category/description stay empty)")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    setup_logging(args.log_file)
    session = create_session()
    scrapers = [
        BooksScraper(session, delay=args.delay, max_pages=args.max_pages, fetch_details=not args.no_details),
        QuotesScraper(session, delay=args.delay, max_pages=args.max_pages),
    ]
    summary = run_pipeline(scrapers, args.output_dir)
    return 1 if summary["failed_sources"] else 0


if __name__ == "__main__":
    sys.exit(main())
