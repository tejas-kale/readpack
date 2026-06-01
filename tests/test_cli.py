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


def test_cli_echoes_use_emojis(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    code, out = run(["config", "--init"], tmp_path)
    assert code == 0
    assert all(line[0] in "📦✅❌📖📬🔨📝🎨⚙️" for line in out.splitlines())


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


def test_add_with_force_overwrites_duplicate(tmp_path):
    from readpack.extract import ArticlePackage
    from readpack.store import load_book
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

    with patch("readpack.cli.fetch_html", return_value="<html></html>"), \
         patch("readpack.cli.extract_article", return_value=ArticlePackage("https://example.com/article", "Updated", "A", "2024", 10)) as mock_extract:
        code, out = run(["add", "--force", "My Book", "https://example.com/article"], tmp_path)
    loaded = load_book(tmp_path, "My Book")
    assert code == 0
    assert len(loaded.articles) == 1
    assert loaded.articles[0].id == "001-example"
    assert loaded.articles[0].title == "Updated"
    assert mock_extract.call_args.kwargs["out_dir"] == tmp_path / "books" / "my-book" / "articles" / "001-example"


def test_config_init_creates_file(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    code, out = run(["config", "--init"], tmp_path)
    assert code == 0
    assert "Config created" in out


def test_config_init_errors_if_exists(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    run(["config", "--init"], tmp_path)
    code, out = run(["config", "--init"], tmp_path)
    assert code != 0


def test_build_passes_force_cover(tmp_path):
    book = Book(id="my-book", title="My Book")
    save_book(tmp_path, book)
    fake_epub = tmp_path / "books" / "my-book" / "build" / "my-book.epub"
    with patch("readpack.cli.build_epub", return_value=fake_epub) as mock:
        code, out = run(["build", "--force", "--force-cover", "My Book"], tmp_path)
    assert code == 0
    assert mock.call_args.kwargs["force"] is True
    assert mock.call_args.kwargs["force_cover"] is True


def test_send_missing_book(tmp_path):
    code, out = run(["send", "Ghost Book"], tmp_path)
    assert code != 0


def test_send_no_config(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "no-config"))
    book = Book(id="my-book", title="My Book")
    save_book(tmp_path, book)
    code, out = run(["send", "My Book"], tmp_path)
    assert code != 0
    assert "config" in out.lower()


def test_send_calls_smtp(tmp_path, monkeypatch):
    from readpack.config import Config, KindleConfig, EmailConfig
    from unittest.mock import MagicMock

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    book = Book(id="my-book", title="My Book")
    save_book(tmp_path, book)

    fake_epub = tmp_path / "books" / "my-book" / "build" / "my-book.epub"
    fake_epub.parent.mkdir(parents=True, exist_ok=True)
    fake_epub.write_bytes(b"fake epub")

    fake_cfg = Config(
        kindle=KindleConfig(address="k@kindle.com"),
        email=EmailConfig(
            sender="me@example.com",
            smtp_host="smtp.example.com",
            password_command="echo pass",
        ),
    )
    smtp_instance = MagicMock()
    with patch("readpack.cli.load_config", return_value=fake_cfg), \
         patch("readpack.cli.build_epub", return_value=fake_epub), \
         patch("smtplib.SMTP") as mock_smtp:
        mock_smtp.return_value.__enter__ = MagicMock(return_value=smtp_instance)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
        code, out = run(["send", "My Book"], tmp_path)
    assert code == 0
    assert "Sent" in out
