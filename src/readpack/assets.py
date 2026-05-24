import hashlib
import re
import urllib.request
import urllib.error
from io import BytesIO
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from PIL import Image


_MAX_IMAGE_BYTES = 10 * 1024 * 1024
_MAX_DIMENSION = 2048
_SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


def process_images(
    html_body: str, md_body: str, base_url: str, out_dir: Path
) -> tuple[str, str, list[dict]]:
    """Download images in html_body, rewrite src in both html and md."""
    assets_dir = out_dir / "assets"
    soup = BeautifulSoup(html_body, "lxml")
    assets: list[dict] = []
    url_to_local: dict[str, str] = {}

    for img in soup.find_all("img"):
        src = img.get("src", "")
        if not src or src.startswith("data:"):
            continue
        abs_url = urljoin(base_url, src)
        cached = url_to_local.get(abs_url)
        if cached:
            img["src"] = cached
            continue
        result = _download_image(abs_url, assets_dir)
        if result:
            local = f"assets/{result['filename']}"
            img["src"] = local
            url_to_local[abs_url] = local
            url_to_local[src] = local
            assets.append(result)
        else:
            img.decompose()

    new_html = str(soup)
    new_md = _rewrite_md_images(md_body, base_url, url_to_local)
    return new_html, new_md, assets


def _download_image(url: str, assets_dir: Path) -> dict | None:
    parsed = urlparse(url)
    ext = Path(parsed.path).suffix.lower()
    if ext not in _SUPPORTED_EXTS:
        ext = ".jpg"

    name = hashlib.md5(url.encode()).hexdigest()[:16] + ext
    assets_dir.mkdir(parents=True, exist_ok=True)
    dest = assets_dir / name

    if dest.exists():
        return {"filename": name, "url": url, "size": dest.stat().st_size, "ext": ext}

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "readpack/0.1"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read(_MAX_IMAGE_BYTES)
        if ext not in {".gif", ".svg"}:
            data = _resize_if_needed(data, ext)
        dest.write_bytes(data)
        return {"filename": name, "url": url, "size": len(data), "ext": ext}
    except Exception:
        return None


def _resize_if_needed(data: bytes, ext: str) -> bytes:
    try:
        img = Image.open(BytesIO(data))
        if max(img.size) <= _MAX_DIMENSION:
            return data
        img.thumbnail((_MAX_DIMENSION, _MAX_DIMENSION), Image.LANCZOS)
        buf = BytesIO()
        fmt = "JPEG" if ext in {".jpg", ".jpeg"} else "PNG"
        if img.mode in ("RGBA", "P") and fmt == "JPEG":
            img = img.convert("RGB")
        img.save(buf, fmt)
        return buf.getvalue()
    except Exception:
        return data


def _rewrite_md_images(md: str, base_url: str, url_to_local: dict[str, str]) -> str:
    def replace(m: re.Match) -> str:
        alt, src = m.group(1), m.group(2)
        abs_url = urljoin(base_url, src)
        local = url_to_local.get(abs_url) or url_to_local.get(src)
        return f"![{alt}]({local})" if local else m.group(0)

    return re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", replace, md)
