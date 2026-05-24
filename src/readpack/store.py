import json
import tempfile
import os
from pathlib import Path
from readpack.models import Book, ArticleRef
from readpack.paths import book_dir, slugify


def _manifest_path(store: Path, title: str) -> Path:
    return book_dir(store, title) / "book.json"


def _book_to_dict(book: Book) -> dict:
    return {
        "schema_version": book.schema_version,
        "id": book.id,
        "title": book.title,
        "created_at": book.created_at,
        "updated_at": book.updated_at,
        "articles": [
            {
                "id": a.id,
                "url": a.url,
                "title": a.title,
                "author": a.author,
                "published_at": a.published_at,
                "added_at": a.added_at,
                "path": a.path,
                "status": a.status,
            }
            for a in book.articles
        ],
    }


def _dict_to_book(data: dict) -> Book:
    articles = [
        ArticleRef(
            id=a["id"],
            url=a["url"],
            title=a["title"],
            author=a.get("author", ""),
            published_at=a.get("published_at", ""),
            added_at=a.get("added_at", ""),
            path=a["path"],
            status=a["status"],
        )
        for a in data.get("articles", [])
    ]
    return Book(
        schema_version=data.get("schema_version", 1),
        id=data["id"],
        title=data["title"],
        created_at=data.get("created_at", ""),
        updated_at=data.get("updated_at", ""),
        articles=articles,
    )


def save_book(store: Path, book: Book) -> None:
    path = _manifest_path(store, book.title)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(_book_to_dict(book), indent=2)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        os.write(fd, data.encode())
        os.close(fd)
        os.replace(tmp, path)
    except Exception:
        os.close(fd)
        os.unlink(tmp)
        raise


def load_book(store: Path, title: str) -> Book:
    path = _manifest_path(store, title)
    if not path.exists():
        raise FileNotFoundError(f"No book found: {title!r}")
    return _dict_to_book(json.loads(path.read_text()))


def book_exists(store: Path, title: str) -> bool:
    return _manifest_path(store, title).exists()


def has_url(book: Book, url: str) -> bool:
    return any(a.url == url for a in book.articles)


def next_article_id(book: Book, slug: str) -> str:
    n = len(book.articles) + 1
    return f"{n:03d}-{slug}"


def list_books(store: Path) -> list[str]:
    books_dir = store / "books"
    if not books_dir.exists():
        return []
    return sorted(
        d.name for d in books_dir.iterdir()
        if d.is_dir() and (d / "book.json").exists()
    )
