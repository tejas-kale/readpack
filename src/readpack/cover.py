import base64
import json
import os
import urllib.request
from pathlib import Path

_URL = "https://openrouter.ai/api/v1/chat/completions"
_MODEL = "openai/gpt-5.4-image-2"


def _prompt(title: str) -> str:
    return (
        f'Elegant ebook cover for "{title}". '
        "Include readable title text using the exact title. "
        "Distinct visual metaphor for the title. Minimalist, professional."
    )


def generate_cover(title: str, out_dir: Path, force: bool = False) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    cover_path = out_dir / "cover.png"
    if cover_path.exists() and not force:
        return cover_path

    payload = json.dumps({
        "model": _MODEL,
        "messages": [{"role": "user", "content": _prompt(title)}],
        "modalities": ["image", "text"],
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

    image = data["choices"][0]["message"]["images"][0]["image_url"]["url"]
    cover_path.write_bytes(base64.b64decode(image.rsplit(",", 1)[-1]))
    return cover_path
