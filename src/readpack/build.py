import shutil
import subprocess
from pathlib import Path

from readpack.models import Book
from readpack.paths import book_dir


class MissingPandoc(RuntimeError):
    pass


def build_epub(store: Path, book: Book, force: bool = False) -> Path:
    if not shutil.which("pandoc"):
        raise MissingPandoc(
            "pandoc not found. Install it from https://pandoc.org/installing.html"
        )

    bdir = book_dir(store, book.title)
    build_dir = bdir / "build"
    build_dir.mkdir(parents=True, exist_ok=True)

    epub_path = build_dir / f"{book.id}.epub"
    if epub_path.exists() and not force:
        return epub_path

    combined_md = _combine_articles(bdir, book)
    md_path = build_dir / f"{book.id}.md"
    md_path.write_text(combined_md)

    cmd = [
        "pandoc",
        str(md_path),
        "-o", str(epub_path),
        "--toc",
        f"--metadata=title:{book.title}",
        "--metadata=lang:en",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"pandoc failed: {result.stderr.strip()}")

    return epub_path


def _combine_articles(book_dir: Path, book: Book) -> str:
    parts = [f"% {book.title}\n\n"]
    for art in book.articles:
        if art.status != "ready":
            continue
        md_path = book_dir / art.path / "article.md"
        if md_path.exists():
            parts.append(md_path.read_text())
            parts.append("\n\n---\n\n")
    return "".join(parts)
