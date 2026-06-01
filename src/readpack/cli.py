import sys
from datetime import datetime, timezone
from pathlib import Path

import click

from readpack.build import build_epub, MissingPandoc
from readpack.config import ConfigError, init_config, load_config
from readpack.extract import extract_article
from readpack.fetch import fetch_html
from readpack.models import Book, ArticleRef
from readpack.paths import store_root, config_dir, slugify
from readpack.send import send_to_kindle
from readpack.store import load_book, save_book, book_exists, has_url, next_article_id, list_books


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_and_add(store: Path, title: str, url: str, force: bool = False) -> None:
    if book_exists(store, title):
        book = load_book(store, title)
    else:
        book = Book(id=slugify(title), title=title)

    old = next((a for a in book.articles if a.url == url), None) if force else None
    url_slug = slugify(url.split("//")[-1].split("/")[0] + "-" + url.rstrip("/").split("/")[-1])[:40]
    article_id = old.id if old else next_article_id(book, url_slug)
    art_dir = store / "books" / slugify(title) / "articles" / article_id

    html = fetch_html(url)
    pkg = extract_article(html, url=url, out_dir=art_dir)

    ref = old or ArticleRef(id=article_id, url=url, title="", path=f"articles/{article_id}", status="ready")
    ref.title = pkg.title
    ref.author = pkg.author
    ref.published_at = pkg.published_at
    ref.status = "ready"
    if not old:
        book.articles.append(ref)
    book.updated_at = _now()
    save_book(store, book)
    click.echo(f"✅ Added: {pkg.title}")
    click.echo(f"📖 Words: {pkg.word_count}")
    click.echo(f"📦 Path:  {art_dir}")


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
        click.echo("📖 No books.")
        return
    for b in books:
        click.echo(f"📖 {b}")


@main.command("show")
@click.argument("book")
@click.pass_context
def cmd_show(ctx: click.Context, book: str) -> None:
    store: Path = ctx.obj["store"]
    if not book_exists(store, book):
        raise click.ClickException(f"Book not found: {book!r}")
    b = load_book(store, book)
    click.echo(f"📖 Book: {b.title} ({b.id})")
    click.echo(f"📦 Articles: {len(b.articles)}")
    for a in b.articles:
        click.echo(f"📄 [{a.status}] {a.id}: {a.title or a.url}")


@main.command("config")
@click.option("--init", "do_init", is_flag=True, help="Create config template")
@click.pass_context
def cmd_config(ctx: click.Context, do_init: bool) -> None:
    store: Path = ctx.obj["store"]
    if do_init:
        cdir = config_dir()
        try:
            path = init_config(cdir)
            click.echo(f"✅ Config created: {path}")
            click.echo("⚙️ Edit it to add your Kindle and SMTP settings.")
        except ConfigError as e:
            raise click.ClickException(str(e)) from e
        return
    click.echo(f"📦 store:      {store}")
    click.echo(f"⚙️ config_dir: {config_dir()}")


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
        fetch_and_add(store, book, url, force=force)
    except Exception as e:
        raise click.ClickException(str(e)) from e


@main.command("build")
@click.argument("book")
@click.option("--force", is_flag=True, help="Rebuild even if up to date")
@click.option("--force-cover", is_flag=True, help="Regenerate the cover image")
@click.pass_context
def cmd_build(ctx: click.Context, book: str, force: bool, force_cover: bool) -> None:
    store: Path = ctx.obj["store"]
    if not book_exists(store, book):
        raise click.ClickException(f"Book not found: {book!r}")
    b = load_book(store, book)
    try:
        build_epub(store, b, force=force, force_cover=force_cover, log=click.echo)
    except MissingPandoc as e:
        raise click.ClickException(str(e)) from e
    except RuntimeError:
        sys.exit(3)


@main.command("send")
@click.argument("book")
@click.option("--force-build", is_flag=True, help="Rebuild ePUB before sending")
@click.option("--force-cover", is_flag=True, help="Regenerate the cover image")
@click.pass_context
def cmd_send(ctx: click.Context, book: str, force_build: bool, force_cover: bool) -> None:
    store: Path = ctx.obj["store"]
    if not book_exists(store, book):
        raise click.ClickException(f"Book not found: {book!r}")
    b = load_book(store, book)
    try:
        cfg = load_config(config_dir())
    except ConfigError as e:
        raise click.ClickException(str(e)) from e
    try:
        epub_path = build_epub(store, b, force=force_build, force_cover=force_cover, log=click.echo)
    except MissingPandoc as e:
        raise click.ClickException(str(e)) from e
    except RuntimeError as e:
        raise click.ClickException(str(e)) from e
    try:
        send_to_kindle(cfg, epub_path)
        click.echo(f"📬 Sent: {epub_path.name} → {cfg.kindle.address}")
        click.echo("✅ SMTP accepted the message. Kindle delivery may take a few minutes.")
    except ConfigError as e:
        raise click.ClickException(str(e)) from e
