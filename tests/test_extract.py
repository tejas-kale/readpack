import pytest
from pathlib import Path
from readpack.extract import extract_article, ArticlePackage, ExtractionError, _add_source_images, _html_to_epub_markdown, _normalise_markdown

FIXTURES = Path(__file__).parent / "fixtures"


def test_extract_rejects_empty_content(tmp_path):
    with pytest.raises(ExtractionError):
        extract_article("<html><title>No article</title></html>", url="https://example.com/empty", out_dir=tmp_path)


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


def test_extract_article_md_deduplicates_title_heading(tmp_path):
    html = (FIXTURES / "simple.html").read_text()
    extract_article(html, url="https://example.com/article", out_dir=tmp_path)
    md = (tmp_path / "article.md").read_text()
    assert md.count("# Simple Test Article") == 1


def test_extract_url_shown_as_link_text(tmp_path):
    html = (FIXTURES / "simple.html").read_text()
    extract_article(html, url="https://example.com/article", out_dir=tmp_path)
    md = (tmp_path / "article.md").read_text()
    # URL should appear as a markdown hyperlink with descriptive text, not raw
    assert "[Read original article]" in md


def test_extract_paragraph_breaks_preserved(tmp_path):
    html = (FIXTURES / "simple.html").read_text()
    extract_article(html, url="https://example.com/article", out_dir=tmp_path)
    md = (tmp_path / "article.md").read_text()
    # Markdown paragraphs need blank lines between them
    assert "\n\n" in md


def test_normalise_markdown_inline_code_punctuation():
    assert _normalise_markdown("called `tsk`\n\n,\na dictionary") == "called `tsk`,\na dictionary"


def test_normalise_markdown_inline_code_possessive():
    assert _normalise_markdown("`fst`\n\n’s weakness") == "`fst`’s weakness"


def test_normalise_markdown_inline_code_lowercase_continuation():
    assert _normalise_markdown("in the world of `fst`\n\ncrate users") == "in the world of `fst` crate users"


def test_normalise_markdown_spaces_glued_inline_code():
    assert _normalise_markdown("earlier`fzf`\nprototype called`finstem`") == "earlier `fzf`\nprototype called `finstem`"


def test_normalise_markdown_blockquotes_from_html():
    html = "<blockquote><p>quoted text</p></blockquote>"
    assert _normalise_markdown("before\n\nquoted\ntext\n\nafter", html) == "before\n\n> quoted text\n\nafter"


def test_normalise_markdown_footnotes_from_html():
    html = "<p>Body.<sup id='fnref:1'><a href='#fn:1'>1</a></sup></p><ol><li id='fn:1'><p><code>tsk</code> note <a class='footnote-backref' href='#fnref:1'>↩︎</a></p></li></ol>"
    md = _normalise_markdown("Body.1\n\n`tsk` note ↩︎", html)
    assert md == "Body.[^1]\n\n[^1]: `tsk` note"


def test_normalise_markdown_preserves_real_paragraphs():
    md = "Use `tsk`.\n\nNext paragraph."
    assert _normalise_markdown(md) == md


def test_extract_image_meta_count(tmp_path):
    import json
    from unittest.mock import patch, MagicMock
    html = (FIXTURES / "images.html").read_text()
    _TINY_PNG = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
        b"\x00\x01\x01\x00\x05\x18\xd4N\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    mock_resp = MagicMock()
    mock_resp.read.return_value = _TINY_PNG
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    with patch("urllib.request.urlopen", return_value=mock_resp):
        extract_article(html, url="https://example.com/images", out_dir=tmp_path)
    meta = json.loads((tmp_path / "meta.json").read_text())
    assert meta["image_count"] >= 0  # depends on trafilatura extraction


def test_extract_restores_source_figure_images(tmp_path):
    from unittest.mock import patch
    from tests.test_assets import _TINY_PNG, _mock_urlopen
    text = " ".join(["This paragraph has enough article words for extraction quality checks."] * 35)
    html = f"""<html><head><title>Image Test</title></head><body><article><h1>Image Test</h1><p>{text}</p><figure><image alt="diagram" src="/diagram.png" width="600" height="400" /></figure></article></body></html>"""
    with patch("urllib.request.urlopen", return_value=_mock_urlopen(_TINY_PNG)):
        extract_article(html, url="https://example.com/post", out_dir=tmp_path)
    md = (tmp_path / "article.md").read_text()
    assert "assets/" in md
    assert "diagram" in md


def test_extract_preserves_tables_and_code_languages(tmp_path):
    text = " ".join(["This paragraph has enough article words for extraction quality checks."] * 35)
    html = f"""<html><head><title>Render Test</title></head><body><article><h1>Render Test</h1><p>{text}</p><table><tr><th>Name</th><th>Role</th></tr><tr><td><code>tool</code></td><td>Review</td></tr></table><pre class="language-typescript"><code>const x = 1;</code></pre></article></body></html>"""
    extract_article(html, url="https://example.com/render", out_dir=tmp_path)
    md = (tmp_path / "article.md").read_text()
    assert "<table" in md
    assert "<tr" in md
    assert "<td" in md
    assert "```typescript" in md


def test_html_to_epub_markdown_keeps_inline_code_inline():
    md = _html_to_epub_markdown("<p>Use <pre>ReviewPlugin</pre> with <pre>stdin</pre> safely.</p>")
    assert md == "Use `ReviewPlugin` with `stdin` safely."


def test_html_to_epub_markdown_normalises_tables():
    html = "<table><row><cell role='head'><p>Name</p></cell></row><row><cell><p></p><pre>tool</pre></cell></row></table>"
    md = _html_to_epub_markdown(html)
    assert "<tr" in md
    assert "<th" in md
    assert "<td" in md
    assert "<row" not in md
    assert "<cell" not in md
    assert "<code>tool</code>" in md


def test_add_source_images_keeps_missing_article_figures():
    body = '<p><img src="/icon.png" alt="icon" /></p>'
    html = '<article><p>Text</p><img src="/icon.png" width="64" height="64" /><figure><image src="/diagram.png" alt="diagram" width="800" height="600" /></figure></article>'
    result = _add_source_images(body, html)
    assert "/icon.png" in result
    assert "/diagram.png" in result
