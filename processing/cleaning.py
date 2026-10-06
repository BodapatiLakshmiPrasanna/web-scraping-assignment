"""Pure cleaning functions: value in, value out. No internet, no files."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

import config

RATING_MAP = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}
QUOTE_CHARS = "\u201c\u201d\u2018\u2019\"'"


def clean_text(value):
    """Collapse all whitespace (incl. non-breaking spaces); empty becomes None."""
    if value is None:
        return None
    text = " ".join(str(value).replace("\xa0", " ").split())
    return text or None


def strip_quotes(value):
    """Remove the curly/straight quotation marks wrapped around quote text."""
    if value is None:
        return None
    return clean_text(value.strip().strip(QUOTE_CHARS))


def clean_price(raw):
    """'£51.77' -> 51.77 ; also tolerates the mis-decoded 'Â£51.77' and thousands commas."""
    if not raw:
        return None
    match = re.search(r"\d+(?:\.\d+)?", str(raw).replace(",", ""))
    return float(match.group()) if match else None


def clean_rating(raw):
    """'star-rating Three' / 'Three' -> 3 ; unknown -> None."""
    for word in (raw or "").lower().split():
        if word in RATING_MAP:
            return RATING_MAP[word]
    return None


def clean_tags(tags):
    """Lowercase, trim, de-duplicate, sort, join with ';'. Empty -> None."""
    cleaned = {clean_text(t).lower() for t in (tags or []) if clean_text(t)}
    return ";".join(sorted(cleaned)) or None


def normalize_url(url, base=None):
    """Return an absolute http(s) URL, or None if it is missing/invalid-looking."""
    url = clean_text(url)
    if not url:
        return None
    if base:
        url = urljoin(base, url)
    parts = urlparse(url)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return None
    return url


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _blank_record(source: str) -> dict:
    rec = {col: None for col in config.COLUMNS}
    rec["source"] = source
    return rec


def clean_book_record(raw: dict, scraped_at: str | None = None) -> dict:
    rec = _blank_record(config.SOURCE_BOOKS)
    rec.update(
        source_url=normalize_url(raw.get("href")),
        name_or_title=clean_text(raw.get("title")),
        category=clean_text(raw.get("category_raw")),
        price=clean_price(raw.get("price_raw")),
        rating=clean_rating(raw.get("rating_raw")),
        description=clean_text(raw.get("description_raw")),
        availability=clean_text(raw.get("availability_raw")),
        scraped_at=scraped_at or utc_now_iso(),
    )
    return rec


def clean_quote_record(raw: dict, scraped_at: str | None = None) -> dict:
    rec = _blank_record(config.SOURCE_QUOTES)
    rec.update(
        source_url=normalize_url(raw.get("page_url")),
        name_or_title=strip_quotes(raw.get("text_raw")),
        author=clean_text(raw.get("author_raw")),
        tags=clean_tags(raw.get("tags_raw")),
        scraped_at=scraped_at or utc_now_iso(),
    )
    return rec
