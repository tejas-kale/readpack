import io
import pytest
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch
from PIL import Image
from readpack.models import Book, ArticleRef
from readpack.store import save_book
from readpack.extract import extract_article
from readpack.build import build_epub, MissingPandoc

FIXTURES = Path(__file__).parent / "fixtures"
PANDOC_AVAILABLE = shutil.which("pandoc") is not None


def _make_book_with_article(store: Path) -> Book:
    book = Book(id="test-book", title="Test Book")
    art_dir = store / "books" / "test-book" / "articles" / "001-simple"
    html = (FIXTURES / "simple.html").read_text()
    extract_article(html, url="https://example.com/simple", out_dir=art_dir)
    ref = ArticleRef(
        id="001-simple",
        url="https://example.com/simple",
        title="Simple Test Article",
        path="articles/001-simple",
        status="ready",
    )
    book.articles.append(ref)
    save_book(store, book)
    return book


def _tiny_cover(out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / "cover.png"
    Image.new("RGB", (10, 10), (0, 0, 255)).save(p)
    return p


def test_missing_pandoc_raises(tmp_path, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: None)
    book = _make_book_with_article(tmp_path)
    with pytest.raises(MissingPandoc):
        build_epub(tmp_path, book)


def test_build_logs_progress(tmp_path, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/pandoc")
    book = _make_book_with_article(tmp_path)
    logs = []
    with patch("readpack.build.generate_cover") as mock_cov, \
         patch("subprocess.run", return_value=MagicMock(returncode=0, stderr="")) as run:
        mock_cov.side_effect = lambda title, out_dir, force=False: _tiny_cover(out_dir)
        build_epub(tmp_path, book, log=logs.append)
    assert "--number-sections" not in run.call_args.args[0]
    assert "--syntax-highlighting=tango" in run.call_args.args[0]
    assert logs == [
        "📦 Preparing Test Book",
        "📝 Writing EPUB source",
        "🎨 Generating cover image",
        "🔨 Running pandoc",
        f"✅ Built {tmp_path / 'books' / 'test-book' / 'build' / 'test-book.epub'}",
    ]


def test_force_rebuild_reuses_cover(tmp_path, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/pandoc")
    book = _make_book_with_article(tmp_path)
    with patch("readpack.build.generate_cover") as mock_cov, \
         patch("subprocess.run", return_value=MagicMock(returncode=0, stderr="")):
        mock_cov.side_effect = lambda title, out_dir, force=False: _tiny_cover(out_dir)
        build_epub(tmp_path, book, force=True)
    assert mock_cov.call_args.kwargs["force"] is False


def test_force_cover_regenerates_cover(tmp_path, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/pandoc")
    book = _make_book_with_article(tmp_path)
    with patch("readpack.build.generate_cover") as mock_cov, \
         patch("subprocess.run", return_value=MagicMock(returncode=0, stderr="")):
        mock_cov.side_effect = lambda title, out_dir, force=False: _tiny_cover(out_dir)
        build_epub(tmp_path, book, force=True, force_cover=True)
    assert mock_cov.call_args.kwargs["force"] is True


@pytest.mark.skipif(not PANDOC_AVAILABLE, reason="pandoc not installed")
def test_build_creates_epub(tmp_path):
    book = _make_book_with_article(tmp_path)
    with patch("readpack.build.generate_cover") as mock_cov:
        mock_cov.side_effect = lambda title, out_dir, force=False: _tiny_cover(out_dir)
        epub = build_epub(tmp_path, book)
    assert epub.exists()
    assert epub.suffix == ".epub"


@pytest.mark.skipif(not PANDOC_AVAILABLE, reason="pandoc not installed")
def test_build_epub_in_build_dir(tmp_path):
    book = _make_book_with_article(tmp_path)
    with patch("readpack.build.generate_cover") as mock_cov:
        mock_cov.side_effect = lambda title, out_dir, force=False: _tiny_cover(out_dir)
        epub = build_epub(tmp_path, book)
    assert "build" in str(epub)


@pytest.mark.skipif(not PANDOC_AVAILABLE, reason="pandoc not installed")
def test_build_combined_md_has_all_articles(tmp_path):
    book = _make_book_with_article(tmp_path)
    with patch("readpack.build.generate_cover") as mock_cov:
        mock_cov.side_effect = lambda title, out_dir, force=False: _tiny_cover(out_dir)
        build_epub(tmp_path, book)
    build_dir = tmp_path / "books" / "test-book" / "build"
    md_files = list(build_dir.glob("*.md"))
    assert md_files
    combined = md_files[0].read_text()
    assert "Simple Test Article" in combined


@pytest.mark.skipif(not PANDOC_AVAILABLE, reason="pandoc not installed")
def test_build_combined_md_deduplicates_article_heading(tmp_path):
    book = _make_book_with_article(tmp_path)
    with patch("readpack.build.generate_cover") as mock_cov:
        mock_cov.side_effect = lambda title, out_dir, force=False: _tiny_cover(out_dir)
        build_epub(tmp_path, book)
    combined = (tmp_path / "books" / "test-book" / "build" / "test-book.md").read_text()
    assert combined.count("# Simple Test Article") == 1


def test_build_rewrites_html_image_paths(tmp_path, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/pandoc")
    book = Book(id="test-book", title="Test Book")
    art_dir = tmp_path / "books" / "test-book" / "articles" / "001-img"
    assets = art_dir / "assets"
    assets.mkdir(parents=True)
    (assets / "pic.png").write_bytes(b"x")
    (art_dir / "article.md").write_text('# Pic\n\n<p><img src="assets/pic.png" alt="pic" /></p>')
    book.articles.append(ArticleRef(id="001-img", url="u", title="Pic", path="articles/001-img", status="ready"))
    with patch("readpack.build.generate_cover") as mock_cov, \
         patch("subprocess.run", return_value=MagicMock(returncode=0, stderr="")):
        mock_cov.side_effect = lambda title, out_dir, force=False: _tiny_cover(out_dir)
        build_epub(tmp_path, book)
    combined = (tmp_path / "books" / "test-book" / "build" / "test-book.md").read_text()
    assert str(assets / "pic.png") in combined
