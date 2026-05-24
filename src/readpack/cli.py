import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from readpack.paths import store_root, config_dir, slugify
from readpack.store import load_book, save_book, book_exists, has_url, next_article_id, list_books
from readpack.models import Book, ArticleRef


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_and_add(store: Path, title: str, url: str) -> None:
    from readpack.fetch import fetch_html
    from readpack.extract import extract_article
    from readpack.paths import slugify

    if book_exists(store, title):
        book = load_book(store, title)
    else:
        book = Book(id=slugify(title), title=title)

    url_slug = slugify(url.split("//")[-1].split("/")[0] + "-" + url.rstrip("/").split("/")[-1])[:40]
    article_id = next_article_id(book, url_slug)
    art_dir = store / "books" / slugify(title) / "articles" / article_id

    html = fetch_html(url)
    pkg = extract_article(html, url=url, out_dir=art_dir)

    ref = ArticleRef(
        id=article_id,
        url=url,
        title=pkg.title,
        author=pkg.author,
        published_at=pkg.published_at,
        added_at=_now(),
        path=f"articles/{article_id}",
        status="ready",
    )
    book.articles.append(ref)
    book.updated_at = _now()
    save_book(store, book)
    print(f"Added: {pkg.title}")
    print(f"  Words: {pkg.word_count}")
    print(f"  Path:  {art_dir}")


def cmd_list(store: Path, _args) -> int:
    books = list_books(store)
    if not books:
        print("No books.")
        return 0
    for b in books:
        print(b)
    return 0


def cmd_show(store: Path, args) -> int:
    if not book_exists(store, args.book):
        print(f"Book not found: {args.book!r}", file=sys.stderr)
        return 1
    book = load_book(store, args.book)
    print(f"Book: {book.title} ({book.id})")
    print(f"  Articles: {len(book.articles)}")
    for a in book.articles:
        print(f"  [{a.status}] {a.id}: {a.title or a.url}")
    return 0


def cmd_config(store: Path, _args) -> int:
    print(f"store:      {store}")
    print(f"config_dir: {config_dir()}")
    return 0


def cmd_add(store: Path, args) -> int:
    title = args.book
    url = args.url

    if book_exists(store, title):
        book = load_book(store, title)
        if has_url(book, url) and not args.force:
            print(f"URL already in book. Use --force to re-add.", file=sys.stderr)
            return 1

    try:
        fetch_and_add(store, title, url)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2
    return 0


def cmd_build(store: Path, args) -> int:
    from readpack.build import build_epub
    if not book_exists(store, args.book):
        print(f"Book not found: {args.book!r}", file=sys.stderr)
        return 1
    book = load_book(store, args.book)
    try:
        epub_path = build_epub(store, book, force=getattr(args, "force", False))
        print(f"Built: {epub_path}")
    except RuntimeError as e:
        print(f"Build error: {e}", file=sys.stderr)
        return 3
    return 0


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(prog="readpack", description="Build ePUB books from web articles.")
    parser.add_argument("--store", metavar="PATH", help="Override store path")

    sub = parser.add_subparsers(dest="command")

    sub.add_parser("list", help="List books")

    p_show = sub.add_parser("show", help="Show book details")
    p_show.add_argument("book", help="Book title")

    sub.add_parser("config", help="Show config paths")

    p_add = sub.add_parser("add", help="Add article to book")
    p_add.add_argument("book", help="Book title")
    p_add.add_argument("url", help="Article URL")
    p_add.add_argument("--force", action="store_true", help="Re-add duplicate URL")

    p_build = sub.add_parser("build", help="Build ePUB")
    p_build.add_argument("book", help="Book title")
    p_build.add_argument("--force", action="store_true", help="Rebuild even if up to date")

    args = parser.parse_args(argv)

    store = store_root(override=Path(args.store) if args.store else None)

    handlers = {
        "list": cmd_list,
        "show": cmd_show,
        "config": cmd_config,
        "add": cmd_add,
        "build": cmd_build,
    }

    if args.command is None:
        parser.print_help()
        raise SystemExit(0)

    fn = handlers.get(args.command)
    if fn is None:
        parser.print_help()
        raise SystemExit(1)

    raise SystemExit(fn(store, args))
