import pytest
from pathlib import Path
from readpack.extract import extract_article, ArticlePackage

FIXTURES = Path(__file__).parent / "fixtures"


def test_extract_returns_package(tmp_path):
    html = (FIXTURES / "simple.html").read_text()
    pkg = extract_article(html, url="https://example.com/article", out_dir=tmp_path)
    assert isinstance(pkg, ArticlePackage)


def test_extract_creates_files(tmp_path):
    html = (FIXTURES / "simple.html").read_text()
    extract_article(html, url="https://example.com/article", out_dir=tmp_path)
    assert (tmp_path / "article.md").exists()
    assert (tmp_path / "article.html").exists()
    assert (tmp_path / "meta.json").exists()
    assert (tmp_path / "source.html").exists()


def test_extract_source_html(tmp_path):
    html = (FIXTURES / "simple.html").read_text()
    extract_article(html, url="https://example.com/article", out_dir=tmp_path)
    assert (tmp_path / "source.html").read_text() == html


def test_extract_title(tmp_path):
    html = (FIXTURES / "simple.html").read_text()
    pkg = extract_article(html, url="https://example.com/article", out_dir=tmp_path)
    assert pkg.title


def test_extract_word_count(tmp_path):
    html = (FIXTURES / "simple.html").read_text()
    pkg = extract_article(html, url="https://example.com/article", out_dir=tmp_path)
    assert pkg.word_count > 0


def test_extract_meta_json(tmp_path):
    import json
    html = (FIXTURES / "simple.html").read_text()
    extract_article(html, url="https://example.com/article", out_dir=tmp_path)
    meta = json.loads((tmp_path / "meta.json").read_text())
    assert meta["schema_version"] == 1
    assert meta["url"] == "https://example.com/article"
    assert meta["word_count"] > 0


def test_extract_article_md_has_header(tmp_path):
    html = (FIXTURES / "simple.html").read_text()
    pkg = extract_article(html, url="https://example.com/article", out_dir=tmp_path)
    md = (tmp_path / "article.md").read_text()
    assert md.startswith("# ")
    assert "https://example.com/article" in md
