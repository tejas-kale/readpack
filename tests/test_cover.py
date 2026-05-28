from pathlib import Path
from readpack.cover import generate_cover


def test_cover_creates_png(tmp_path):
    p = generate_cover("My Test Book", tmp_path)
    assert p.exists()
    assert p.suffix == ".png"


def test_cover_no_slug_form(tmp_path):
    p = generate_cover("ai-development", tmp_path)
    assert p.exists()


def test_cover_reproducible(tmp_path):
    p1 = generate_cover("Same Title", tmp_path / "a")
    p2 = generate_cover("Same Title", tmp_path / "b")
    assert p1.read_bytes() == p2.read_bytes()


def test_cover_differs_by_title(tmp_path):
    p1 = generate_cover("Book Alpha", tmp_path / "a")
    p2 = generate_cover("Book Beta", tmp_path / "b")
    assert p1.read_bytes() != p2.read_bytes()


def test_cover_creates_parent_dirs(tmp_path):
    p = generate_cover("Test", tmp_path / "nested" / "deep")
    assert p.exists()
