import re


def dedupe_title_heading(md: str, title: str) -> str:
    seen = False

    def repl(m: re.Match) -> str:
        nonlocal seen
        if seen:
            return ""
        seen = True
        return m.group(0)

    pat = rf"(?m)^[ \t]*#[ \t]+{re.escape(title.strip())}[ \t]*\n+"
    return re.sub(pat, repl, md)
