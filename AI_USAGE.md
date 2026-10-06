# AI Usage

**Tool:** Claude (Anthropic), via the claude.ai chat interface.

**Used for:** reading the assignment and reference document, generating the initial project structure and code
(scrapers, cleaning, validation, deduplication, pipeline, CLI), writing the unit tests and drafting README.md / this file.

**Representative prompts**
1. "With the reference material, complete the assignment exactly as asked" (assignment + reference document pasted in).
2. (Follow-up ideas to try) "Why does the fingerprint slice the quote before normalizing?" / "What if a detail page fails?"

**AI-assisted parts:** essentially all code and documentation was AI-generated, following the reference document's structure and snippets.

**Changes made after reviewing the output / issues found**
- The reference snippet sliced the first 50 characters of the *raw* quote before normalizing, so extra spaces could shift the cut
  and break matching. The final code normalizes first, then slices.
- Added `missing_author` (quotes), bool-rejection for price/rating, and `reconciles` in the summary so the counts are checkable.
- A first attempt to create folders with brace expansion failed under `/bin/sh` and created a literal folder; I removed it.

**Verification**
- 18 offline pytest tests pass (cleaning, validation, deduplication, pagination via a fake HTTP session, page-failure handling,
  full pipeline file output and count reconciliation, failed-source isolation).
- **Not verified:** the AI sandbox could not reach books.toscrape.com / quotes.toscrape.com (HTTP 403 from its network proxy),
  so **a live run against the real sites has not been done**. The CSS selectors follow the reference document's inspection table.
  **Before submitting, run `python main.py` yourself**, check the CSV (~1,100 rows), that `summary_report.json` has `"reconciles": true`,
  and update this section with what you observed. Only then include the real `output/` files and `logs/scraper.log`.
- Be ready to explain every line in the interview; edit this file to honestly reflect your own review.
