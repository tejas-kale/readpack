# readpack implementation plan

## Current repo state

The repository is intentionally minimal:

```text
readpack/
  pyproject.toml
```

`pyproject.toml` currently defines:

- project name: `readpack`
- version: `0.1.0`
- Python: `>=3.10`
- dependencies: none

The plan below assumes a new Python CLI application built in this repo.

## Guiding principles

- Keep the first version boring and terminal-native.
- Persist intermediate article packages so failures are inspectable.
- Prefer a working ePUB pipeline before perfect extraction.
- Use browser automation only when simple HTTP extraction is not enough.
- Treat Kindle delivery as SMTP email delivery, not a guaranteed Kindle ingestion API.
- Keep implementation small until the data model proves itself.

## Milestones

### Milestone 1: Project skeleton

Outcome: `readpack` can be installed and invoked from the terminal.

Tasks:

- Add package layout under `src/readpack/`.
- Add CLI entry point.
- Add basic command parsing.
- Add config and store path resolution.
- Add initial tests for path resolution and slug generation.

Suggested files:

```text
src/readpack/
  __init__.py
  __main__.py
  cli.py
  paths.py
  models.py
  store.py
```

Suggested `pyproject.toml` additions:

```toml
[project.scripts]
readpack = "readpack.cli:main"
```

Initial command behaviour:

```bash
readpack --help
readpack list
readpack config
```

Acceptance criteria:

- `uv run readpack --help` works.
- `readpack config` prints config and store paths.
- `readpack list` prints an empty state without error.

### Milestone 2: Book store and manifests

Outcome: named books can be created, listed, and inspected.

Tasks:

- Define `Book` and `ArticleRef` models.
- Implement safe slugging for book names.
- Implement `book.json` read/write.
- Implement duplicate URL detection.
- Implement `list` and `show` commands.
- Create book directories as needed.

Commands:

```bash
readpack list
readpack show "Weekend reading"
```

Internal behaviours:

- Store root defaults to `~/.local/share/readpack`.
- `READPACK_STORE` overrides the default.
- `--store` overrides both.
- Manifest writes should be atomic.

Acceptance criteria:

- Creating a book does not require network access.
- Existing manifests survive interrupted writes.
- Book names with spaces become stable directory slugs.

### Milestone 3: Minimal article extraction

Outcome: `readpack add BOOK URL` can fetch normal static articles and save article packages.

Tasks:

- Add HTTP fetcher.
- Add `trafilatura` or readability-based extraction.
- Extract title, author, published date when available.
- Produce `article.md`, `article.html`, `meta.json`, and `source.html`.
- Add article reference to `book.json`.
- Store failed extraction details without corrupting the book.

Candidate dependencies:

```toml
trafilatura
beautifulsoup4
lxml
python-slugify
```

Command:

```bash
readpack add "Weekend reading" https://example.com/article
```

Acceptance criteria:

- A simple article produces a readable `article.md`.
- The manifest is updated only after the article package is written.
- Adding the same URL twice is refused unless `--force` is passed.
- The command prints article title, word count, and package path.

### Milestone 4: MVP ePUB build

Outcome: a named book can be converted into an ePUB.

Two viable routes exist. Pick one before implementation.

#### Option A: Pandoc MVP

Tasks:

- Generate a combined Markdown build file.
- Copy/resolve image paths.
- Run `pandoc` to produce ePUB.
- Print a helpful error if Pandoc is missing.

Pros:

- Fastest route to end-to-end proof.
- Less ePUB code to write.

Cons:

- External binary dependency.
- Less control.

#### Option B: `ebooklib` MVP

Tasks:

- Convert article HTML into XHTML chapters.
- Add each article as one chapter.
- Add table of contents and spine.
- Add images to ePUB manifest.
- Add simple CSS.

Pros:

- Better long-term shape.
- Pure Python.

Cons:

- More code before the first working build.

Recommended path: start with Pandoc if the goal is fastest validation, then replace or supplement with `ebooklib` once extraction and storage are stable.

Command:

```bash
readpack build "Weekend reading"
```

Acceptance criteria:

- Generated `.epub` opens in Apple Books, Calibre, or Kindle Previewer.
- Table of contents contains one entry per article.
- Each article starts on a new chapter/section.
- Source URL is included near the article title.

### Milestone 5: Image handling

Outcome: images referenced by extracted articles are stored locally and included in the ePUB.

Tasks:

- Download image assets.
- Preserve alt text and captions.
- Rewrite image references to local paths.
- Convert or skip unsupported image formats.
- Resize very large images.
- Add file size reporting.

Candidate dependency:

```toml
Pillow
```

Acceptance criteria:

- ePUB contains no remote image references.
- Broken image downloads are reported but do not crash the whole book unless strict mode is enabled.
- Large image-heavy books are visibly smaller after compression.

### Milestone 6: Kindle delivery

Outcome: `readpack send BOOK` emails the built ePUB to the user's Kindle address.

Tasks:

- Define TOML config schema.
- Implement `readpack config --init`.
- Implement secret lookup through `password_command`.
- Implement SMTP email with TLS.
- Attach ePUB.
- Redact secrets in logs and config output.
- Add file size warnings.

Config example:

```toml
[kindle]
address = "name_abc@kindle.com"

[email]
sender = "you@example.com"
smtp_host = "smtp.gmail.com"
smtp_port = 587
username = "you@example.com"
password_command = "security find-generic-password -s readpack-smtp -w"
```

Command:

```bash
readpack send "Weekend reading"
```

Acceptance criteria:

- Missing config produces actionable errors.
- SMTP password is never printed.
- Successful send says SMTP accepted the email, not that Kindle delivered it.

### Milestone 7: Playwright fallback

Outcome: dynamic and logged-in pages can be extracted through a real browser session.

Tasks:

- Add Playwright dependency.
- Add browser profile support.
- Implement `readpack login PROFILE URL` or equivalent.
- Fall back to browser extraction when HTTP extraction is poor.
- Screenshot complex figures and charts.
- Store screenshots as assets.

Commands:

```bash
readpack login economist https://www.economist.com
readpack add "Graphic detail" URL --profile economist
```

Acceptance criteria:

- Browser profile persists logins across runs.
- The tool waits for the user when a login or bot check is visible.
- Complex charts are represented as static images.
- Extraction remains legal and user-controlled; no paywall bypass logic is added.

### Milestone 8: Maintenance commands

Outcome: users can manage books without hand-editing JSON.

Tasks:

- Implement `remove`.
- Implement `refresh`.
- Implement `build --force`.
- Implement URL batch input from files.
- Implement article order controls if needed.

Commands:

```bash
readpack remove "Weekend reading" https://example.com/article
readpack refresh "Weekend reading" https://example.com/article
readpack add "Weekend reading" urls.txt
```

Acceptance criteria:

- Removing an article updates the manifest safely.
- Refreshing re-extracts into a temporary package before replacing the old package.
- Batch add reports per-URL success/failure.

### Milestone 9: Quality and packaging

Outcome: the tool is reliable enough for regular personal use.

Tasks:

- Add unit tests around manifests, paths, config, and ePUB assembly.
- Add fixture-based extraction tests.
- Add integration test for a tiny local HTML page.
- Add linting/formatting if desired.
- Add README with installation and Kindle setup.
- Add examples.

Acceptance criteria:

- Tests run with one command.
- A new user can configure Send to Kindle from the README.
- The repository can be installed with `uv tool install` or equivalent.

## Proposed implementation order

Recommended order for a useful first vertical slice:

1. CLI skeleton.
2. Store and manifests.
3. Static article extraction.
4. Pandoc ePUB build.
5. SMTP Kindle send.
6. Image handling polish.
7. Playwright fallback.
8. Browser profiles and chart screenshots.

This gives a working end-to-end path early:

```bash
readpack add "Weekend reading" URL
readpack build "Weekend reading"
readpack send "Weekend reading"
```

## Initial dependency decision

For the first implementation pass, prefer:

```toml
dependencies = [
  "beautifulsoup4>=4.12",
  "lxml>=5",
  "python-slugify>=8",
  "trafilatura>=2",
]
```

Defer these until needed:

```toml
"Pillow>=10"
"playwright>=1.52"
"ebooklib>=0.18"
```

Use standard library `argparse`, `email`, `smtplib`, `json`, `pathlib`, `subprocess`, and `tomllib` initially.

Rationale:

- Fewer dependencies make the storage and CLI easier to stabilise.
- Pandoc can provide the first ePUB backend without introducing ePUB-specific Python code.
- Browser automation should be added only after simple extraction proves insufficient.

## Risks and mitigations

### Extraction quality varies by site

Mitigation:

- Store source HTML for debugging.
- Add quality checks.
- Make site-specific extractors pluggable.
- Add Playwright fallback.

### Kindle rejects files silently

Mitigation:

- Validate generated ePUB locally where possible.
- Keep CSS conservative.
- Warn about large attachments.
- Document Amazon setup precisely.

### Images make books too large

Mitigation:

- Resize images.
- Convert unsuitable formats.
- Add `--no-images` or `--compress-images` later if required.

### Paywalled pages are ambiguous

Mitigation:

- Never bypass access controls.
- Support user-owned browser profiles.
- Fail clearly when content is unavailable.

### Pandoc availability

Mitigation:

- Detect missing binary with a clear install message.
- Keep the ePUB builder interface abstract enough to swap in `ebooklib`.

## Suggested module boundaries

```text
cli.py          command parsing and user-facing output
config.py       config loading, env overrides, secret commands
paths.py        store paths and slugging
models.py       dataclasses or typed dictionaries
store.py        manifest and article package persistence
extract.py      extraction orchestration and quality checks
fetch.py        HTTP fetch and browser fetch interfaces
assets.py       image download, conversion, and path rewriting
build.py        ePUB build interface
build_pandoc.py Pandoc implementation
send.py         SMTP Kindle delivery
```

Keep module APIs narrow. For example:

```python
extract_article(url, options) -> ArticlePackage
load_book(store, title) -> Book
save_book(store, book) -> None
build_epub(store, book) -> Path
send_to_kindle(config, epub) -> None
```

## Testing strategy

### Unit tests

- Slug generation.
- Manifest read/write.
- Duplicate URL detection.
- Config precedence.
- Secret redaction.
- Article package path generation.

### Fixture tests

Use local HTML fixtures:

```text
tests/fixtures/simple.html
tests/fixtures/images.html
tests/fixtures/noisy.html
tests/fixtures/table.html
```

Test expected extraction output without network access.

### Integration tests

- Start a local HTTP server serving fixtures.
- Run `readpack add` against local URLs.
- Run `readpack build` when Pandoc is available.
- Skip delivery tests unless SMTP test configuration is explicitly provided.

## Definition of done for MVP

The MVP is done when this works on at least three ordinary article URLs:

```bash
readpack add "Test book" URL_1
readpack add "Test book" URL_2
readpack build "Test book"
readpack send "Test book"
```

And:

- The ePUB opens locally.
- The article text is readable.
- The table of contents is usable.
- Images are either included or explicitly reported as skipped.
- Kindle email delivery is accepted by SMTP.

## Post-MVP ideas

- `readpack add BOOK --from-pocket-export FILE`.
- `readpack add BOOK --from-instapaper-export FILE`.
- `readpack reorder BOOK`.
- Automatic cover generation.
- Per-site extractors.
- Readability score in extraction reports.
- `readpack doctor` for config, Pandoc, SMTP, and Playwright checks.
- OPML/RSS support for recurring article packs.
- Optional summaries or front matter, generated locally or by user-selected LLM tooling.
