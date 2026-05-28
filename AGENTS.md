# readpack — Agent Guidelines

Python CLI that turns web articles into ePUB books and delivers them to Kindle.

## Rules

- **TDD only**: failing test first, then make it pass. No production code without a prior red test.
- **Atomic commits**: one change per commit; include the test and implementation together.
- **Terse**: fewest lines that are still clear. Resist extracting helpers that are only used once.
- **No try-catch**: raise and let it fail. Only Click's `ClickException` at command boundaries.
- **Emoji in logs**: every `click.echo` call uses an emoji (📦 ✅ ❌ 📖 📬 🔨 etc.).
- **README**: update `README.md` whenever you add or change user-facing behaviour, flags, or dependencies.

## Layout

```
src/readpack/   # cli, models, fetch, extract, assets, build, cover, send, store, config, paths
tests/          # mirrors src layout; fixtures/ holds HTML test data
```

## Run tests

```
uv run pytest
```

## Branch

Always develop on `claude/repo-docs-book-cover-cpqp1`. Commit and push when done.
