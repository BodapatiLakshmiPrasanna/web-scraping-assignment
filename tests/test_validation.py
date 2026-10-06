from processing.validation import validate_record

GOOD = {"source": "Books to Scrape", "source_url": "https://x.com/a", "name_or_title": "T",
        "price": 1.0, "rating": 3}


def test_valid():
    assert validate_record(GOOD) == []


def test_each_rule():
    assert "unknown_source" in validate_record({**GOOD, "source": "Other"})
    assert "missing_name" in validate_record({**GOOD, "name_or_title": None})
    assert "invalid_url" in validate_record({**GOOD, "source_url": "x.com"})
    assert "invalid_price" in validate_record({**GOOD, "price": -1})
    assert "invalid_price" in validate_record({**GOOD, "price": "10"})
    assert "invalid_rating" in validate_record({**GOOD, "rating": 6})


def test_quote_needs_author_but_no_price():
    q = {"source": "Quotes to Scrape", "source_url": "https://q.com/", "name_or_title": "x"}
    assert validate_record(q) == ["missing_author"]
    assert validate_record({**q, "author": "A"}) == []
