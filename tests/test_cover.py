import base64
import io
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from readpack.cover import generate_cover


def _fake_png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (4, 4), (0, 0, 255)).save(buf, format="PNG")
    return buf.getvalue()


def _mock_urlopen() -> MagicMock:
    data = {"data": [{"b64_json": base64.b64encode(_fake_png()).decode()}]}
    m = MagicMock()
    m.__enter__ = MagicMock(return_value=m)
    m.__exit__ = MagicMock(return_value=False)
    m.read.return_value = json.dumps(data).encode()
    return m


def test_cover_creates_png(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    with patch("urllib.request.urlopen", return_value=_mock_urlopen()):
        p = generate_cover("AI Development", tmp_path)
    assert p.exists()
    assert p.suffix == ".png"


def test_cover_cached_skips_api(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    with patch("urllib.request.urlopen", return_value=_mock_urlopen()) as mock:
        generate_cover("AI Development", tmp_path)
        generate_cover("AI Development", tmp_path)
    assert mock.call_count == 1


def test_cover_force_regenerates(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    with patch("urllib.request.urlopen", return_value=_mock_urlopen()) as mock:
        generate_cover("AI Development", tmp_path)
        generate_cover("AI Development", tmp_path, force=True)
    assert mock.call_count == 2


def test_cover_creates_parent_dirs(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    with patch("urllib.request.urlopen", return_value=_mock_urlopen()):
        p = generate_cover("AI Development", tmp_path / "nested" / "deep")
    assert p.exists()


def test_cover_missing_key_raises(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(KeyError):
        generate_cover("AI Development", tmp_path)
