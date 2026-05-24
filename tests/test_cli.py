import pytest
from pathlib import Path
from unittest.mock import patch
from click.testing import CliRunner

from readpack.cli import main
from readpack.models import Book, ArticleRef
from readpack.store import save_book

_runner = CliRunner()


def run(args: list[str], store: Path) -> tuple[int, str]:
    result = _runner.invoke(main, ["--store", str(store)] + args)
    return result.exit_code, result.output


def test_help(tmp_path):
    code, out = run(["--help"], tmp_path)
    assert code == 0


def test_list_empty(tmp_path):
    code, out = run(["list"], tmp_path)
    assert code == 0


def test_config_shows_paths(tmp_path):
    code, out = run(["config"], tmp_path)
    assert code == 0
    assert str(tmp_path) in out


def test_list_with_books(tmp_path):
    book = Book(id="my-book", title="My Book")
    save_book(tmp_path, book)
    code, out = run(["list"], tmp_path)
    assert code == 0
    assert "my-book" in out or "My Book" in out


def test_show_missing_book(tmp_path):
    code, out = run(["show", "Ghost Book"], tmp_path)
    assert code != 0


def test_show_existing_book(tmp_path):
    book = Book(id="my-book", title="My Book")
    save_book(tmp_path, book)
    code, out = run(["show", "My Book"], tmp_path)
    assert code == 0
    assert "My Book" in out


def test_add_duplicate_url_rejected(tmp_path):
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

    with patch("readpack.cli.fetch_and_add") as mock_add:
        code, out = run(["add", "My Book", "https://example.com/article"], tmp_path)
    assert code != 0
    mock_add.assert_not_called()


def test_add_with_force_allows_duplicate(tmp_path):
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

    with patch("readpack.cli.fetch_and_add") as mock_add:
        mock_add.return_value = None
        code, out = run(["add", "--force", "My Book", "https://example.com/article"], tmp_path)
    mock_add.assert_called_once()
