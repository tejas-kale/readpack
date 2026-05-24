import sys
from datetime import datetime, timezone
from pathlib import Path

import click

from readpack.build import build_epub, MissingPandoc
from readpack.extract import extract_article
from readpack.fetch import fetch_html
from readpack.models import Book, ArticleRef
from readpack.paths import store_root, config_dir, slugify
from readpack.store import load_book, save_book, book_exists, has_url, next_article_id, list_books


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_and_add(store: Path, title: str, url: str) -> None:
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
    click.echo(f"Added: {pkg.title}")
    click.echo(f"  Words: {pkg.word_count}")
    click.echo(f"  Path:  {art_dir}")


@click.group()
@click.option("--store", "store_path", default=None, metavar="PATH", help="Override store path")
@click.pass_context
def main(ctx: click.Context, store_path: str | None) -> None:
    ctx.ensure_object(dict)
    ctx.obj["store"] = store_root(override=Path(store_path) if store_path else None)


@main.command("list")
@click.pass_context
def cmd_list(ctx: click.Context) -> None:
    store: Path = ctx.obj["store"]
    books = list_books(store)
    if not books:
        click.echo("No books.")
        return
    for b in books:
        click.echo(b)


@main.command("show")
@click.argument("book")
@click.pass_context
def cmd_show(ctx: click.Context, book: str) -> None:
    store: Path = ctx.obj["store"]
    if not book_exists(store, book):
        raise click.ClickException(f"Book not found: {book!r}")
    b = load_book(store, book)
    click.echo(f"Book: {b.title} ({b.id})")
    click.echo(f"  Articles: {len(b.articles)}")
    for a in b.articles:
        click.echo(f"  [{a.status}] {a.id}: {a.title or a.url}")


@main.command("config")
@click.pass_context
def cmd_config(ctx: click.Context) -> None:
    store: Path = ctx.obj["store"]
    click.echo(f"store:      {store}")
    click.echo(f"config_dir: {config_dir()}")


@main.command("add")
@click.argument("book")
@click.argument("url")
@click.option("--force", is_flag=True, help="Re-add duplicate URL")
@click.pass_context
def cmd_add(ctx: click.Context, book: str, url: str, force: bool) -> None:
    store: Path = ctx.obj["store"]
    if book_exists(store, book):
        b = load_book(store, book)
        if has_url(b, url) and not force:
            raise click.ClickException("URL already in book. Use --force to re-add.")
    try:
        fetch_and_add(store, book, url)
    except Exception as e:
        raise click.ClickException(str(e)) from e


@main.command("build")
@click.argument("book")
@click.option("--force", is_flag=True, help="Rebuild even if up to date")
@click.pass_context
def cmd_build(ctx: click.Context, book: str, force: bool) -> None:
    store: Path = ctx.obj["store"]
    if not book_exists(store, book):
        raise click.ClickException(f"Book not found: {book!r}")
    b = load_book(store, book)
    try:
        epub_path = build_epub(store, b, force=force)
        click.echo(f"Built: {epub_path}")
    except MissingPandoc as e:
        raise click.ClickException(str(e)) from e
    except RuntimeError as e:
        sys.exit(3)
