import re
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

from readpack.cover import generate_cover
from readpack.models import Book
from readpack.paths import book_dir


_EPUB_CSS = """\
body {
    font-family: Bookerly, Literata, "Charis SIL", Georgia, serif;
    font-size: 1em;
    line-height: 1.65em;
}
p {
    margin: 0.7em 0;
    text-align: justify;
    hyphens: auto;
}
h1, h2, h3, h4, h5, h6 {
    font-family: Bookerly, Literata, "Charis SIL", Georgia, serif;
    line-height: 1.25em;
    page-break-after: avoid;
}
h1 { font-size: 1.8em; margin-bottom: 0.4em; }
h2 { font-size: 1.4em; }
h3 { font-size: 1.2em; }
code {
    font-family: "Fira Code", "Cascadia Mono", "DejaVu Sans Mono", monospace;
    font-size: 0.85em;
    background-color: #f4f4f4;
    padding: 0.1em 0.3em;
    border-radius: 2px;
}
pre {
    background-color: #f4f4f4;
    padding: 0.8em 1em;
    overflow-x: auto;
    line-height: 1.4em;
}
pre code { background: none; padding: 0; }
blockquote {
    margin: 1em 2em;
    font-style: italic;
    color: #444;
    border-left: 3px solid #ccc;
    padding-left: 0.8em;
}
a { color: #1a5276; text-decoration: underline; }
img { max-width: 100%; height: auto; display: block; margin: 0.8em auto; }
table { width: 100%; border-collapse: collapse; margin: 1em 0; }
th, td { border: 1px solid #ccc; padding: 0.4em 0.6em; text-align: left; }
th { background-color: #f0f0f0; }
hr { border: none; border-top: 1px solid #ccc; margin: 2em 0; }
"""


class MissingPandoc(RuntimeError):
    pass


def build_epub(store: Path, book: Book, force: bool = False, force_cover: bool = False, log: Callable[[str], None] | None = None) -> Path:
    if not shutil.which("pandoc"):
        raise MissingPandoc(
            "pandoc not found. Install it from https://pandoc.org/installing.html"
        )

    bdir = book_dir(store, book.title)
    build_dir = bdir / "build"
    build_dir.mkdir(parents=True, exist_ok=True)

    epub_path = build_dir / f"{book.id}.epub"
    if log:
        log(f"📦 Preparing {book.title}")
    if epub_path.exists() and not force:
        if log:
            log(f"✅ Using cached {epub_path}")
        return epub_path

    css_path = build_dir / "epub.css"
    css_path.write_text(_EPUB_CSS)

    combined_md = _combine_articles(bdir, book)
    md_path = build_dir / f"{book.id}.md"
    if log:
        log("📝 Writing EPUB source")
    md_path.write_text(combined_md)

    if log:
        log("🎨 Generating cover image")
    cover_path = generate_cover(book.title, build_dir, force=force_cover)

    if log:
        log("🔨 Running pandoc")
    cmd = [
        "pandoc",
        str(md_path),
        "-o", str(epub_path),
        "--toc",
        "--number-sections",
        f"--metadata=title:{book.title}",
        "--metadata=author:Tejas Kale",
        "--metadata=lang:en",
        "--css", str(css_path),
        "--epub-cover-image", str(cover_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"pandoc failed: {result.stderr.strip()}")

    if log:
        log(f"✅ Built {epub_path}")
    return epub_path


def _combine_articles(bdir: Path, book: Book) -> str:
    parts = [f"% {book.title}\n\n"]
    for art in book.articles:
        if art.status != "ready":
            continue
        art_dir = bdir / art.path
        md_path = art_dir / "article.md"
        if md_path.exists():
            content = _rewrite_image_paths(md_path.read_text(), art_dir)
            parts.append(content)
            parts.append("\n\n---\n\n")
    return "".join(parts)


def _rewrite_image_paths(md: str, art_dir: Path) -> str:
    def replace(m: re.Match) -> str:
        alt, src = m.group(1), m.group(2)
        if src.startswith(("http://", "https://", "/")):
            return m.group(0)
        abs_path = (art_dir / src).resolve()
        return f"![{alt}]({abs_path})"

    return re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", replace, md)
