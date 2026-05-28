import base64
import json
import os
import urllib.request
from pathlib import Path

_URL = "https://openrouter.ai/api/v1/images/generations"
_MODEL = "openai/gpt-5.4-image-2"


def _prompt(title: str) -> str:
    return (
        f'Elegant ebook cover for "{title}". '
        "Deep blue and purple gradient, abstract geometric light patterns. "
        "Minimalist, professional. No text in the image."
    )


def generate_cover(title: str, out_dir: Path, force: bool = False) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    cover_path = out_dir / "cover.png"
    if cover_path.exists() and not force:
        return cover_path

    payload = json.dumps({
        "model": _MODEL,
        "prompt": _prompt(title),
        "n": 1,
        "size": "1024x1024",
        "response_format": "b64_json",
    }).encode()

    req = urllib.request.Request(
        _URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())

    cover_path.write_bytes(base64.b64decode(data["data"][0]["b64_json"]))
    return cover_path
