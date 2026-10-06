"""Fingerprint-based duplicate detection (tolerates case, spacing and punctuation differences)."""
import hashlib
import re

import config


def _normalize(value) -> str:
    text = re.sub(r"[^\w\s]", "", str(value or "").lower())
    return " ".join(text.split())


def make_fingerprint(rec: dict) -> str:
    """Books: source + title.  Quotes: source + author + first 50 chars of normalized quote."""
    if rec.get("source") == config.SOURCE_QUOTES:
        key = " ".join([
            _normalize(rec.get("source")),
            _normalize(rec.get("author")),
            _normalize(rec.get("name_or_title"))[:50],
        ])
    else:
        key = f'{_normalize(rec.get("source"))} {_normalize(rec.get("name_or_title"))}'
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def find_duplicates(records: list[dict]) -> tuple[list[dict], list[dict]]:
    """Return (unique, duplicates). The first occurrence is kept; later ones are duplicates."""
    seen, unique, dupes = set(), [], []
    for rec in records:
        fp = make_fingerprint(rec)
        (dupes if fp in seen else unique).append(rec)
        seen.add(fp)
    return unique, dupes
