# readpack

Python CLI: web articles → ePUB → Kindle.

## Dev rules

- **TDD**: Write a failing test first. Red → Green → Refactor. Never write production code without a test.
- **Atomic commits**: one logical change per commit. Tests + implementation in the same commit.
- **Terse code**: shortest correct solution. No abstraction tax, no premature helpers.
- **No try-catch**: let errors propagate naturally. Catch only at CLI boundaries (Click handles it).
- **Emoji logs**: all `click.echo` lines get an emoji prefix (📦 ✅ ❌ 📖 📬 etc.).
- **README**: keep `README.md` up to date with every user-facing change (new flags, dependencies, behaviour).

## Stack

Python 3.11+, click, trafilatura, Pillow, pandoc (external binary).

## Key flows

- `add` → `fetch_html` → `extract_article` → `save_book`
- `build` → `generate_cover` + `_combine_articles` → pandoc → `.epub`
- `send` → `build_epub` → SMTP → Kindle

## Tests

```
uv run pytest
```
