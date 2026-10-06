from processing.deduplication import find_duplicates

BASE = {"source": "Books to Scrape", "author": None}


def test_books_ignore_case_spacing_punctuation():
    recs = [{**BASE, "name_or_title": "Example Book Title"},
            {**BASE, "name_or_title": "  Example Book Title "},
            {**BASE, "name_or_title": "EXAMPLE BOOK TITLE"},
            {**BASE, "name_or_title": "Example: Book Title!"}]
    unique, dupes = find_duplicates(recs)
    assert len(unique) == 1 and len(dupes) == 3


def test_same_title_different_source_is_not_duplicate():
    recs = [{**BASE, "name_or_title": "X"}, {"source": "Quotes to Scrape", "author": "A", "name_or_title": "X"}]
    assert len(find_duplicates(recs)[0]) == 2


def test_quotes_use_author_and_first_50_chars():
    q = {"source": "Quotes to Scrape", "author": "Al", "name_or_title": "a" * 60}
    q2 = {**q, "name_or_title": "A" * 50 + "different ending"}
    q3 = {**q, "author": "Bo"}
    unique, dupes = find_duplicates([q, q2, q3])
    assert len(unique) == 2 and len(dupes) == 1
