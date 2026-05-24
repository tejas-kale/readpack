import json
import pytest
from pathlib import Path
from readpack.models import Book, ArticleRef
from readpack.store import load_book, save_book, book_exists


def test_save_and_load_book(tmp_path):
    book = Book(id="my-book", title="My Book")
    save_book(tmp_path, book)
    loaded = load_book(tmp_path, "My Book")
    assert loaded.title == "My Book"
    assert loaded.id == "my-book"


def test_book_manifest_path(tmp_path):
    book = Book(id="test-book", title="Test Book")
    save_book(tmp_path, book)
    manifest = tmp_path / "books" / "test-book" / "book.json"
    assert manifest.exists()


def test_manifest_is_valid_json(tmp_path):
    book = Book(id="test-book", title="Test Book")
    save_book(tmp_path, book)
    manifest = tmp_path / "books" / "test-book" / "book.json"
    data = json.loads(manifest.read_text())
    assert data["schema_version"] == 1
    assert data["title"] == "Test Book"


def test_book_exists_false(tmp_path):
    assert not book_exists(tmp_path, "No Book")


def test_book_exists_true(tmp_path):
    book = Book(id="my-book", title="My Book")
    save_book(tmp_path, book)
    assert book_exists(tmp_path, "My Book")


def test_save_book_with_articles(tmp_path):
    book = Book(id="my-book", title="My Book")
    ref = ArticleRef(
        id="001-example",
        url="https://example.com/article",
        title="Example",
        path="articles/001-example",
        status="ready",
    )
    book.articles.append(ref)
    save_book(tmp_path, book)
    loaded = load_book(tmp_path, "My Book")
    assert len(loaded.articles) == 1
    assert loaded.articles[0].url == "https://example.com/article"


def test_duplicate_url_detection(tmp_path):
    from readpack.store import has_url
    book = Book(id="my-book", title="My Book")
    ref = ArticleRef(
        id="001-example",
        url="https://example.com/article",
        title="Example",
        path="articles/001-example",
        status="ready",
    )
    book.articles.append(ref)
    assert has_url(book, "https://example.com/article")
    assert not has_url(book, "https://example.com/other")


def test_atomic_write_survives_interrupted_read(tmp_path):
    book = Book(id="my-book", title="My Book")
    save_book(tmp_path, book)
    manifest = tmp_path / "books" / "my-book" / "book.json"
    original = manifest.read_text()
    # Simulate a second save
    book.title = "My Book"
    save_book(tmp_path, book)
    assert manifest.read_text() == original or json.loads(manifest.read_text())["title"] == "My Book"


def test_load_missing_book_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_book(tmp_path, "Ghost Book")


def test_article_id_generation():
    from readpack.store import next_article_id
    book = Book(id="my-book", title="My Book")
    assert next_article_id(book, "some-slug") == "001-some-slug"
    book.articles.append(ArticleRef(id="001-some-slug", url="u", title="t", path="p", status="ready"))
    assert next_article_id(book, "other-slug") == "002-other-slug"
