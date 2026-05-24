import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from readpack.assets import process_images, _rewrite_md_images


def _mock_urlopen(data: bytes):
    resp = MagicMock()
    resp.read.return_value = data
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


_TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
    b"\x00\x01\x01\x00\x05\x18\xd4N\x00\x00\x00\x00IEND\xaeB`\x82"
)


def test_process_images_downloads_and_rewrites(tmp_path):
    html = '<img src="https://example.com/img.png" alt="test">'
    md = "![test](https://example.com/img.png)"
    with patch("urllib.request.urlopen", return_value=_mock_urlopen(_TINY_PNG)):
        new_html, new_md, assets = process_images(html, md, "https://example.com", tmp_path)
    assert "assets/" in new_html
    assert "assets/" in new_md
    assert len(assets) == 1
    assert (tmp_path / "assets" / assets[0]["filename"]).exists()


def test_process_images_skips_data_url(tmp_path):
    html = '<img src="data:image/png;base64,abc" alt="inline">'
    md = ""
    new_html, new_md, assets = process_images(html, md, "https://example.com", tmp_path)
    assert len(assets) == 0


def test_process_images_handles_broken_image(tmp_path):
    html = '<img src="https://example.com/broken.png" alt="x">'
    md = "![x](https://example.com/broken.png)"
    with patch("urllib.request.urlopen", side_effect=Exception("timeout")):
        new_html, new_md, assets = process_images(html, md, "https://example.com", tmp_path)
    assert len(assets) == 0
    assert "<img" not in new_html


def test_process_images_no_images(tmp_path):
    html = "<p>Just text</p>"
    md = "Just text"
    new_html, new_md, assets = process_images(html, md, "https://example.com", tmp_path)
    assert assets == []
    assert "Just text" in new_html


def test_process_images_deduplicates(tmp_path):
    html = (
        '<img src="https://example.com/img.png" alt="a">'
        '<img src="https://example.com/img.png" alt="b">'
    )
    md = ""
    with patch("urllib.request.urlopen", return_value=_mock_urlopen(_TINY_PNG)):
        _, _, assets = process_images(html, md, "https://example.com", tmp_path)
    filenames = [a["filename"] for a in assets]
    assert len(set(filenames)) == 1


def test_rewrite_md_images_relative_url():
    url_map = {"https://example.com/img.png": "assets/abc.png"}
    md = "Before\n![alt text](https://example.com/img.png)\nAfter"
    result = _rewrite_md_images(md, "https://example.com", url_map)
    assert "assets/abc.png" in result
    assert "https://example.com/img.png" not in result
