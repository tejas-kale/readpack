import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import trafilatura
from bs4 import BeautifulSoup

from readpack.assets import process_images



@dataclass
class ArticlePackage:
    url: str
    title: str
    author: str
    published_at: str
    word_count: int
    extractor: str = "trafilatura"
    assets: list[dict] = field(default_factory=list)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def extract_article(html: str, url: str, out_dir: Path) -> ArticlePackage:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "source.html").write_text(html)

    _raw = trafilatura.bare_extraction(
        html,
        url=url,
        include_tables=True,
        include_comments=False,
        favor_precision=True,
        with_metadata=True,
    )
    meta = _raw.as_dict() if _raw is not None else {}

    title = meta.get("title") or _extract_title_fallback(html)
    author = meta.get("author") or ""
    published_at = meta.get("date") or ""
    body_text = meta.get("text") or ""
    word_count = len(body_text.split()) if body_text else 0

    body_html_raw = trafilatura.extract(
        html,
        url=url,
        output_format="html",
        include_tables=True,
        include_comments=False,
        favor_precision=True,
    ) or f"<p>{body_text}</p>"

    body_md_raw = trafilatura.extract(
        html,
        url=url,
        output_format="markdown",
        include_tables=True,
        include_comments=False,
        favor_precision=True,
    ) or body_text

    body_html, body_md, image_assets = process_images(
        body_html_raw, body_md_raw, url, out_dir
    )

    clean_html = _build_article_html(title, author, published_at, url, body_html)
    (out_dir / "article.html").write_text(clean_html)

    md = _build_article_md(title, author, published_at, url, body_md)
    (out_dir / "article.md").write_text(md)

    pkg = ArticlePackage(
        url=url,
        title=title,
        author=author,
        published_at=published_at,
        word_count=word_count,
        assets=image_assets,
    )

    meta_data = {
        "schema_version": 1,
        "url": url,
        "canonical_url": url,
        "title": title,
        "author": author,
        "published_at": published_at,
        "extracted_at": _now(),
        "extractor": pkg.extractor,
        "word_count": word_count,
        "image_count": len(image_assets),
        "assets": image_assets,
    }
    (out_dir / "meta.json").write_text(json.dumps(meta_data, indent=2))

    return pkg


def _extract_title_fallback(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    tag = soup.find("title") or soup.find("h1")
    return tag.get_text(strip=True) if tag else "Untitled"


def _build_article_html(title: str, author: str, published_at: str, url: str, body: str) -> str:
    parts = [f"<h1>{title}</h1>"]
    if author:
        parts.append(f"<p>By {author}</p>")
    if published_at:
        parts.append(f"<p>Published: {published_at}</p>")
    parts.append(f'<p><a href="{url}">Read original article</a></p>')
    parts.append(body)
    return "\n".join(parts)


def _build_article_md(title: str, author: str, published_at: str, url: str, body: str) -> str:
    lines = [f"# {title}", ""]
    if author:
        lines.append(f"By {author}  ")
    if published_at:
        lines.append(f"Published: {published_at}  ")
    lines.append(f"[Read original article]({url})")
    lines.append("")
    lines.append(body)
    return "\n".join(lines)
