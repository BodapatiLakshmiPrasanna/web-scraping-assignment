"""Orchestrates Scrape -> Clean -> Validate -> Deduplicate -> Consolidate -> Save."""
from __future__ import annotations

import csv
import json
import logging
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import config
from processing.cleaning import clean_book_record, clean_quote_record, utc_now_iso
from processing.deduplication import find_duplicates
from processing.validation import validate_record

logger = logging.getLogger(__name__)

CLEANERS = {
    config.SOURCE_BOOKS: clean_book_record,
    config.SOURCE_QUOTES: clean_quote_record,
}


def clean_and_validate(source: str, raw_records: list[dict]):
    """Returns (valid_records, stats). Never raises for a bad record."""
    cleaner = CLEANERS[source]
    scraped_at = utc_now_iso()
    reasons: Counter = Counter()
    valid, cleaned_count, rejected = [], 0, 0
    for raw in raw_records:
        try:
            rec = cleaner(raw, scraped_at)
        except Exception:
            logger.exception("[%s] Cleaning crashed for record %r", source, raw)
            reasons["cleaning_error"] += 1
            rejected += 1
            continue
        cleaned_count += 1
        problems = validate_record(rec)
        if problems:
            rejected += 1
            reasons.update(problems)
            logger.warning("[%s] Rejected %r: %s", source, rec.get("name_or_title"), ", ".join(problems))
        else:
            valid.append(rec)
    return valid, {
        "raw_collected": len(raw_records),
        "cleaned": cleaned_count,
        "rejected": rejected,
        "rejected_by_reason": dict(reasons),
    }


def write_csv(records: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=config.COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)


def write_json(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def run_pipeline(scrapers: list, output_dir: str | Path = config.DEFAULT_OUTPUT_DIR) -> dict:
    output_dir = Path(output_dir)
    started = datetime.now(timezone.utc)
    t0 = time.monotonic()

    per_source: dict[str, dict] = {}
    all_valid: list[dict] = []
    failed_sources: dict[str, str] = {}

    for scraper in scrapers:
        name = scraper.source_name
        try:  # one failing source must not stop the other
            raw = scraper.scrape()
            valid, stats = clean_and_validate(name, raw)
            stats.update(
                pages_scraped=scraper.pages_scraped,
                pages_failed=scraper.pages_failed,
                parse_failures=scraper.parse_failures,
            )
            if hasattr(scraper, "detail_failures"):
                stats["detail_page_failures"] = scraper.detail_failures
            per_source[name] = stats
            all_valid.extend(valid)
        except Exception as exc:
            logger.exception("Source %s failed completely", name)
            failed_sources[name] = repr(exc)

    unique, dupes = find_duplicates(all_valid)
    dupes_by_source = Counter(d["source"] for d in dupes)
    final_by_source = Counter(u["source"] for u in unique)
    for name, stats in per_source.items():
        stats["duplicates_removed"] = dupes_by_source.get(name, 0)
        stats["final"] = final_by_source.get(name, 0)
    for d in dupes:
        logger.warning("Duplicate removed: [%s] %r", d["source"], d["name_or_title"])

    csv_path = output_dir / "final_dataset.csv"
    write_csv(unique, csv_path)

    ended = datetime.now(timezone.utc)
    total_raw = sum(s["raw_collected"] for s in per_source.values())
    total_rejected = sum(s["rejected"] for s in per_source.values())
    summary = {
        "per_source": per_source,
        "totals": {
            "raw_collected": total_raw,
            "cleaned": sum(s["cleaned"] for s in per_source.values()),
            "rejected": total_rejected,
            "duplicates_removed": len(dupes),
            "final_record_count": len(unique),
            # raw - rejected - duplicates must equal final
            "reconciles": total_raw - total_rejected - len(dupes) == len(unique),
        },
        "failed_sources": failed_sources,
        "start_time": started.isoformat(timespec="seconds"),
        "end_time": ended.isoformat(timespec="seconds"),
        "duration_seconds": round(time.monotonic() - t0, 1),
    }
    write_json(summary, output_dir / "summary_report.json")
    logger.info("Done. Final records: %d (rejected %d, duplicates %d). Files in %s",
                len(unique), total_rejected, len(dupes), output_dir)
    return summary
