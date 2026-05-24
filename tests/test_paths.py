import os
import pytest
from readpack.paths import slugify, store_root, config_dir, book_dir, article_dir


def test_slugify_basic():
    assert slugify("Weekend reading") == "weekend-reading"


def test_slugify_special_chars():
    assert slugify("AI & ML: 2024") == "ai-ml-2024"


def test_slugify_stable():
    assert slugify("Test Book") == slugify("Test Book")


def test_store_root_default(tmp_path, monkeypatch):
    monkeypatch.delenv("READPACK_STORE", raising=False)
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    root = store_root()
    assert root == tmp_path / ".local" / "share" / "readpack"


def test_store_root_env(tmp_path, monkeypatch):
    monkeypatch.setenv("READPACK_STORE", str(tmp_path / "custom"))
    assert store_root() == tmp_path / "custom"


def test_store_root_override(tmp_path):
    assert store_root(override=tmp_path / "override") == tmp_path / "override"


def test_config_dir_default(tmp_path, monkeypatch):
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    assert config_dir() == tmp_path / ".config" / "readpack"


def test_book_dir(tmp_path):
    d = book_dir(tmp_path, "Weekend reading")
    assert d == tmp_path / "books" / "weekend-reading"


def test_article_dir(tmp_path):
    d = article_dir(tmp_path, "Weekend reading", "001-my-article")
    assert d == tmp_path / "books" / "weekend-reading" / "articles" / "001-my-article"
