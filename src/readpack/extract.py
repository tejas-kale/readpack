import json
import re
import textwrap
from dataclasses import dataclass, field
from html import escape
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
        include_images=True,
        include_formatting=True,
        include_links=True,
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
        _add_source_images(_restore_code_languages(body_html_raw, html), html), body_md_raw, url, out_dir
    )
    body_md = _html_to_epub_markdown(body_html) if _rich_html(body_html) else _normalise_markdown(body_md, html)
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


def _rich_html(html: str) -> bool:
    soup = BeautifulSoup(html, "lxml")
    return bool(soup.find(["table", "pre", "img", "image"]))


def _add_source_images(body: str, html: str) -> str:
    seen = {img.get("src", "") for img in BeautifulSoup(body, "lxml").find_all(["img", "image"])}
    soup = BeautifulSoup(html, "lxml")
    root = soup.find("article") or soup.body or soup
    parts = []
    for img in root.find_all(["img", "image"]):
        src = img.get("src", "")
        w, h = img.get("width", ""), img.get("height", "")
        if not src or src.startswith("data:") or src in seen:
            continue
        if img.name == "img" and w.isdigit() and h.isdigit() and max(int(w), int(h)) <= 128:
            continue
        alt = img.get("alt", "")
        parts.append(f'<p><img src="{escape(src, quote=True)}" alt="{escape(alt, quote=True)}" /></p>')
        seen.add(src)
    return body + "\n" + "\n".join(parts) if parts else body


def _restore_code_languages(body: str, html: str) -> str:
    soup = BeautifulSoup(body, "lxml")
    src = []
    for pre in BeautifulSoup(html, "lxml").find_all("pre"):
        lang = _code_lang(pre)
        if lang:
            src.append((pre.get_text(" ", strip=True), lang))
    for pre in soup.find_all("pre"):
        if _code_lang(pre):
            continue
        text = pre.get_text(" ", strip=True)
        lang = next((lang for old, lang in src if text and (text == old or old in text or len(text) > 40 and text in old)), "")
        if lang:
            pre["class"] = [f"language-{lang}"]
    return str(soup)


def _html_to_epub_markdown(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    md = "\n\n".join(x for x in (_node_to_md(c) for c in soup.children) if x).strip()
    return _compact_inline_code(md)


def _node_to_md(node) -> str:
    if isinstance(node, NavigableString):
        return str(node).strip()
    if node.name in {"html", "body", "div", "section", "article", "blockquote"}:
        return "\n\n".join(x for x in (_node_to_md(c) for c in node.children) if x)
    if node.name == "p":
        return _inline_md(node)
    if node.name == "table":
        return _table_html(node)
    if node.name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
        return f"{'#' * int(node.name[1])} {node.get_text(' ', strip=True)}"
    if node.name in {"img", "image"}:
        return f"![{node.get('alt', '')}]({node.get('src', '')})"
    if node.name == "pre":
        code = node.find("code")
        lang = _code_lang(node)
        text = textwrap.dedent((code or node).get_text()).strip("\n")
        if not lang:
            return f"`{text}`" if "\n" not in text else f"<pre><code>{escape(text)}</code></pre>"
        fence = "````" if "```" in text else "```"
        return f"{fence}{lang}\n{text}\n{fence}"
    return _inline_md(node)


def _inline_md(node) -> str:
    parts = []
    for child in node.children:
        if isinstance(child, NavigableString):
            parts.append(str(child))
        elif child.name == "pre" and not _code_lang(child):
            parts.append(f"`{child.get_text(strip=True)}`")
        elif child.name == "code":
            parts.append(f"`{child.get_text(strip=True)}`")
        elif child.name in {"strong", "b"}:
            parts.append(f"**{_inline_md(child)}**")
        elif child.name in {"em", "i"}:
            parts.append(f"*{_inline_md(child)}*")
        elif child.name == "a" and child.get("href"):
            parts.append(f"[{_inline_md(child)}]({child['href']})")
        elif child.name == "br":
            parts.append("\n")
        else:
            parts.append(_node_to_md(child))
    return re.sub(r"[ \t\n]+", " ", "".join(parts)).strip()


def _table_html(node) -> str:
    soup = BeautifulSoup(str(node), "lxml")
    table = soup.find("table")
    for row in table.find_all("row"):
        row.name = "tr"
    for cell in table.find_all("cell"):
        cell.name = "th" if cell.get("role") == "head" else "td"
        cell.attrs.pop("role", None)
    for pre in table.find_all("pre"):
        if not _code_lang(pre) and "\n" not in pre.get_text():
            code = soup.new_tag("code")
            code.string = pre.get_text(strip=True)
            pre.replace_with(code)
    return str(table)


def _compact_inline_code(md: str) -> str:
    old = ""
    while old != md:
        old = md
        md = re.sub(r"(?<=[^\n.!?])\n\n(`[^`\n]+`)\n\n(?=[a-z,.;:!?])", r" \1 ", md)
    return md


def _code_lang(node) -> str:
    code = node.find("code") if hasattr(node, "find") else None
    classes = node.get("class", []) + (code.get("class", []) if code else [])
    return next((c.split("-", 1)[1].lower() for c in classes if c.lower().startswith("language-")), "")


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
