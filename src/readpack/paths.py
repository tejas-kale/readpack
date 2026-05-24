import os
from pathlib import Path
from slugify import slugify as _slugify


def slugify(name: str) -> str:
    return _slugify(name)


def store_root(override: Path | None = None) -> Path:
    if override:
        return Path(override)
    env = os.environ.get("READPACK_STORE")
    if env:
        return Path(env)
    return Path.home() / ".local" / "share" / "readpack"


def config_dir() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "readpack"


def book_dir(store: Path, title: str) -> Path:
    return store / "books" / slugify(title)


def article_dir(store: Path, title: str, article_id: str) -> Path:
    return book_dir(store, title) / "articles" / article_id
