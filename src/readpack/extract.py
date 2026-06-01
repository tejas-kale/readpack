import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import trafilatura
from bs4 import BeautifulSoup, NavigableString

from readpack.assets import process_images
from readpack.markdown import dedupe_title_heading



class ExtractionError(RuntimeError):
    pass


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

    if not body_text.strip():
        raise ExtractionError("could not extract article content")

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
    body_md = _normalise_markdown(body_md, html)
    clean_html = _build_article_html(title, author, published_at, url, body_html)
    (out_dir / "article.html").write_text(clean_html)

    md = dedupe_title_heading(_build_article_md(title, author, published_at, url, body_md), title)
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


def _normalise_markdown(md: str, html: str = "") -> str:
    md = re.sub(r"(`[^`\n]+`)\n\n([,.;:!?])", r"\1\2", md)
    md = re.sub(r"(`[^`\n]+`)\n\n(['’]s)", r"\1\2", md)
    md = re.sub(r"(`[^`\n]+`)\n\n([a-z])", r"\1 \2", md)
    md = re.sub(r"(?<=\w)(`(?=[A-Za-z0-9_.-])[^`\n]+`)", r" \1", md)
    md = re.sub(r"(`(?=[A-Za-z0-9_.-])[^`\n]+`)(?=\w)", r"\1 ", md)
    if html:
        md = _normalise_blockquotes(md, html)
        md = _normalise_footnotes(md, html)
    return md


def _normalise_blockquotes(md: str, html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all("blockquote"):
        text = " ".join(tag.get_text(" ", strip=True).split())
        if not text:
            continue
        pattern = re.escape(text).replace(r"\ ", r"\s+")
        md = re.sub(pattern, f"> {text}", md, count=1)
    return md


def _normalise_footnotes(md: str, html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    items = soup.select('li[id^="fn:"]')
    if not items:
        return md
    for item in items:
        n = item["id"].split(":", 1)[1]
        md = re.sub(rf"(?<=[.!?]){re.escape(n)}(?=\s|$)", f"[^{n}]", md, count=1)
    start = _footnote_start(md, items[0])
    if start != -1:
        md = md[:start].rstrip()
    notes = []
    for item in items:
        n = item["id"].split(":", 1)[1]
        for tag in item.select("a.footnote-backref"):
            tag.decompose()
        text = _html_to_md(item)
        text = re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()
        notes.append(f"[^{n}]: {text}")
    return f"{md}\n\n" + "\n\n".join(notes)


def _footnote_start(md: str, item) -> int:
    words = re.findall(r"\w+", item.get_text(" ", strip=True))[:4]
    if not words:
        return -1
    parts = [rf"`?{re.escape(words[0])}`?"] + [re.escape(w) for w in words[1:]]
    m = re.search(r"\s+".join(parts), md)
    return md.rfind("\n\n", 0, m.start()) if m else -1


def _html_to_md(node) -> str:
    if isinstance(node, NavigableString):
        return str(node)
    text = "".join(_html_to_md(c) for c in node.children)
    if node.name == "code":
        return f"`{text}`"
    if node.name in {"em", "i"}:
        return f"*{text}*"
    if node.name in {"strong", "b"}:
        return f"**{text}**"
    if node.name == "a" and node.get("href"):
        return f"[{text}]({node['href']})"
    if node.name == "br":
        return "\n"
    return text


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
