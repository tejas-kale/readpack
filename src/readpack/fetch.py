import urllib.request
import urllib.error


class FetchError(RuntimeError):
    pass


def fetch_html(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "readpack/0.1 (https://github.com/tejas-kale/readpack)"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        html = resp.read().decode(charset, errors="replace")
    if _is_bot_challenge(html):
        raise FetchError("site returned a bot challenge or CAPTCHA")
    return html


def _is_bot_challenge(html: str) -> bool:
    low = html.lower()
    return "/.well-known/sgcaptcha/" in low or "captcha" in low and "meta http-equiv=\"refresh\"" in low
