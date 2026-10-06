# Multi-Source Web Scraping & Data Consolidation

## 1. Overview
A small ETL pipeline: **Scrape -> Clean -> Validate -> Deduplicate -> Consolidate -> Save**.
It collects data from [Books to Scrape](https://books.toscrape.com/) (~1,000 books, 50 pages) and
[Quotes to Scrape](https://quotes.toscrape.com/) (100 quotes, 10 pages), maps both into one schema and writes
`output/final_dataset.csv`, `output/summary_report.json` and `logs/scraper.log`.

> **Run time:** The full run takes about 15 minutes because it visits every book's detail page. For a quick check, use `--no-details` or `--max-pages 2`.

## 2. Python version
Python 3.10 - 3.12 (developed on 3.12).

## 3. Setup
```
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```
Dependencies: `requests`, `beautifulsoup4`, `lxml`, `pytest` (tests only). Before submitting, run
`pip freeze > requirements.txt` if you want exact pins.

## 4. How to run
```
python main.py                    # full run (book detail pages included, ~10 min at 0.5 s/request)
python main.py --no-details       # fast run (~1 min): book category/description stay empty
python main.py --max-pages 2      # quick smoke test
python main.py --delay 1.0 --output-dir out --log-file logs/run.log
python -m pytest -q               # offline unit tests (no internet needed)
```

## 5. Source observations (Step 1)
| Item | Books to Scrape | Quotes to Scrape |
|---|---|---|
| Record | `article.product_pod` | `div.quote` |
| Main text | `h3 > a` - full title in the `title` attribute (visible text is truncated with `...`) | `span.text` (wrapped in curly quotes) |
| Price | `p.price_color` (`£51.77`) | - |
| Rating | class on `p.star-rating` (`Three`) | - |
| Availability | `p.instock.availability` | - |
| Author / tags | - | `small.author` / `div.tags a.tag` (0..n) |
| Category, description | Only on the detail page: 3rd breadcrumb item, `#product_description + p` | - |
| Next page | `li.next > a` (relative href) | `li.next > a` (relative href) |

Both sites are server-rendered HTML, so Requests + BeautifulSoup (lxml parser) is sufficient; Selenium/Playwright would only add overhead.

## 6. Pagination
`BaseScraper.scrape()` starts at the home page, parses it, looks for `li.next > a`, converts the relative link with
`urljoin` and repeats until there is no next link. Page numbers are never hard-coded, so it keeps working if the site grows or shrinks.
A `visited` set prevents loops; `--max-pages` limits pages for testing.

## 7. Data model
| Column | Books | Quotes |
|---|---|---|
| source | Books to Scrape | Quotes to Scrape |
| source_url | Book detail page URL | **Page URL where the quote appeared** (chosen; the author page would repeat for many quotes) |
| name_or_title | Title | Quote text (curly quotes removed) |
| category | Detail-page breadcrumb (empty if detail pages skipped/failed) | empty |
| price | float (GBP, e.g. 51.77) | empty |
| rating | int 1-5 | empty |
| author | empty | Author name |
| tags | empty | `tag1;tag2` (lowercase, sorted, unique) |
| description | Detail-page description (may be empty) | empty |
| availability | e.g. `In stock` | empty |
| scraped_at | UTC ISO timestamp | UTC ISO timestamp |

`availability` is an extra column beyond the suggested schema because the assignment lists it as a Books field.
Non-applicable fields are left **empty** (never faked, e.g. quotes do not get a price of 0).

## 8. Cleaning (`processing/cleaning.py`)
Pure functions with no I/O: `clean_text` (collapses all whitespace incl. `\xa0`, empty -> None), `strip_quotes`,
`clean_price` (`£51.77` -> 51.77, also tolerates mis-decoded `Â£`), `clean_rating` (`Three` -> 3),
`clean_tags`, `normalize_url` (absolute http/https or None). `response.encoding = "utf-8"` is set so `£` decodes correctly.
Scrapers return *raw* text; cleaning is a separate step.

## 9. Validation (`processing/validation.py`)
`validate_record` returns a list of problem codes (empty = valid): `unknown_source`, `missing_name`, `invalid_url`,
`missing_author` (quotes only), `invalid_price` (must be a number >= 0 if present), `invalid_rating` (1-5 if present).
Rejected records are logged as WARNING and counted per reason in the summary. A record with several problems counts once in
`rejected` but once per reason in `rejected_by_reason`.

## 10. Deduplication (`processing/deduplication.py`)
A SHA-256 fingerprint of normalized identifying fields (lowercase, punctuation removed, whitespace collapsed):
- **Books:** source + title
- **Quotes:** source + author + first 50 characters of the *normalized* quote text

So `"Example Book Title"`, `" Example Book Title "` and `"EXAMPLE BOOK TITLE"` are one record. The first occurrence is kept.
**Decision: remove (not flag).** The final CSV then has one row per real-world item and no extra column to filter; every removal is
logged and counted in the summary. Both practice sites contain unique items, so a real run should report 0 duplicates; the logic
is proven by unit tests with deliberately duplicated records.

## 11. Error handling
- Shared `requests.Session`: User-Agent, 10 s timeout, automatic retries with exponential backoff (1s, 2s, 4s) on 429/500/502/503/504.
- A failed page is logged (ERROR) and stops **that source only**; the other source still runs and files are still written.
- Each record is parsed in `try/except`; missing elements return `None` instead of crashing.
- A failed book detail page keeps the record with empty category/description (counted as `detail_page_failures`).
- A crash while cleaning one record rejects that record (`cleaning_error`); a crash in a whole source is recorded under `failed_sources`.
- Exit code is 1 if a whole source failed, else 0.

## 12. Output
- `output/final_dataset.csv` - fixed column order, UTF-8.
- `output/summary_report.json` - per source: raw collected, cleaned, rejected (+ reasons), duplicates removed, final, pages scraped/failed,
  parse failures; totals; `reconciles` (raw - rejected - duplicates == final); start/end time; duration.
- `logs/scraper.log` - every page, warning and error (overwritten each run).

## 13. Project structure
```
main.py            CLI + logging setup          pipeline.py   orchestration + file writing
config.py          URLs, delays, columns        scrapers/     base (session, pagination) + books + quotes
processing/        cleaning, validation, deduplication        tests/   offline pytest suite
```

## 14. Assumptions
- Prices are in GBP as shown on the site; only the number is stored.
- Quote `source_url` is the listing page of the quote (documented choice above).
- 0.5 s delay between requests (including detail pages) to avoid aggressive traffic.

## 15. Known limitations
- Full run is sequential, so book detail pages take roughly 10 minutes; use `--no-details` for a fast run.
- Whole-source stop on a failed listing page (later pages are not attempted); no checkpoint/resume.
- Duplicate detection is exact-after-normalization, not fuzzy (typos are not matched).
- Only the data visible on the sites is captured; author "about" pages are not scraped.

## 16. AI usage summary
Claude was used to generate and review the code, tests and docs; see `AI_USAGE.md`.

## 17. Production changes I would make
Checkpoint/resume, async or concurrent fetching with a shared rate limiter, a database with upserts for incremental runs,
scheduled runs with alerting on `failed_sources`/low counts, and a data-quality report.
