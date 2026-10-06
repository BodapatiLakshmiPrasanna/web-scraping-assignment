from processing.cleaning import (clean_book_record, clean_price, clean_quote_record, clean_rating,
                                 clean_tags, clean_text, normalize_url, strip_quotes)


def test_clean_text():
    assert clean_text("  Hello \n\t World\xa0! ") == "Hello World !"
    assert clean_text("   ") is None and clean_text(None) is None


def test_strip_quotes():
    assert strip_quotes("\u201cThe world as we have created it.\u201d") == "The world as we have created it."


def test_clean_price():
    assert clean_price("\u00a351.77") == 51.77
    assert clean_price("\u00c2\u00a351.77") == 51.77   # mis-decoded encoding
    assert clean_price("\u00a31,051.00") == 1051.0
    assert clean_price("free") is None and clean_price(None) is None


def test_clean_rating():
    assert clean_rating("star-rating Three") == 3
    assert clean_rating("Five") == 5
    assert clean_rating("star-rating") is None and clean_rating(None) is None


def test_clean_tags():
    assert clean_tags(["Love", " life ", "love"]) == "life;love"
    assert clean_tags([]) is None


def test_normalize_url():
    assert normalize_url("catalogue/x.html", "https://books.toscrape.com/") == "https://books.toscrape.com/catalogue/x.html"
    assert normalize_url("ftp://x.com/a") is None
    assert normalize_url("not a url") is None and normalize_url(None) is None


def test_book_record_has_all_columns_and_nulls():
    rec = clean_book_record({"title": " A  Book ", "href": "https://x.com/b", "price_raw": "\u00a310.50",
                             "rating_raw": "star-rating Two"}, "2026-01-01T00:00:00+00:00")
    assert rec["name_or_title"] == "A Book" and rec["price"] == 10.5 and rec["rating"] == 2
    assert rec["author"] is None and rec["tags"] is None and rec["category"] is None


def test_quote_record():
    rec = clean_quote_record({"text_raw": "\u201cHi\u201d", "author_raw": " Al ", "tags_raw": ["B", "a"],
                              "page_url": "https://quotes.toscrape.com/page/2/"})
    assert rec["name_or_title"] == "Hi" and rec["author"] == "Al" and rec["tags"] == "a;b"
    assert rec["price"] is None and rec["rating"] is None
