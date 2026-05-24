# readpack specification

## Summary

`readpack` is a terminal-first tool for turning one or more web articles into named ePUB books and sending those books to a Kindle using Amazon's Send to Kindle email workflow.

The core loop is:

```text
book name + article URL -> extracted article package -> book manifest -> ePUB -> Kindle delivery
```

The project prioritises dependable reading output over exact visual reproduction. A generated book should be clean, navigable, readable on Kindle devices, and robust against ordinary article layouts. It should preserve article text, headings, links, images, captions, and chart screenshots where possible.

## Goals

- Provide a completely terminal-based workflow.
- Let the user create named books by adding article links.
- Append to an existing book when the name already exists.
- Create a new book when the name does not exist.
- Extract article text, metadata, images, captions, and readable figures.
- Produce Kindle-compatible ePUB files.
- Send completed ePUB files directly to the user's Kindle email address.
- Keep all source article packages locally so books can be rebuilt.
- Work well with simple static pages first, then dynamic and logged-in pages.
- Make site-specific extraction fixes easy to add later.

## Non-goals

- Pixel-perfect reproduction of source web pages.
- Full browser CSS support inside Kindle ePUBs.
- Circumventing paywalls or access controls.
- Public hosted service or GUI.
- Library management beyond the local `readpack` store.
- DRM removal or processing of copyrighted e-books.
- A public Send to Kindle API integration, since Amazon does not provide a general-purpose API for this use case.

## User stories

### Add one article to a book

```bash
readpack add "Weekend reading" https://example.com/article
```

Expected behaviour:

- If `Weekend reading` does not exist, create it.
- Fetch and extract the article.
- Store the article package locally.
- Add the article to the book manifest.
- Do not build or send unless explicitly requested.

### Add and send in one command

```bash
readpack add "Weekend reading" https://example.com/article --build --send
```

Expected behaviour:

- Add the article.
- Build the ePUB.
- Send the ePUB to the configured Kindle address.

### Add multiple URLs

```bash
readpack add "AI essays" urls.txt
```

Expected behaviour:

- Treat each non-empty line as a URL.
- Add successful articles.
- Report failed URLs without losing successful work.

### Build a book

```bash
readpack build "Weekend reading"
```

Expected behaviour:

- Read the book manifest.
- Combine article packages into one ePUB.
- Generate title page, table of contents, chapters, metadata, and assets.
- Save the result under the book's build directory.

### Send a book

```bash
readpack send "Weekend reading"
```

Expected behaviour:

- Find the latest built ePUB.
- Email it to the configured Kindle address.
- Refuse to send if configuration is missing.
- Warn if the file is likely too large for email delivery.

### Inspect local state

```bash
readpack list
readpack show "Weekend reading"
readpack config
```

Expected behaviour:

- Show available books.
- Show articles inside a book.
- Show relevant configuration paths and Kindle delivery settings without revealing secrets.

## Command-line interface

### Global options

```bash
readpack --help
readpack --store PATH ...
readpack --verbose ...
readpack --quiet ...
```

- `--store PATH`: override the local data store path.
- `--verbose`: print extraction and build details.
- `--quiet`: minimise output for scripting.

### Commands

```bash
readpack add BOOK URL_OR_FILE [--build] [--send] [--force] [--profile PROFILE]
readpack build BOOK [--force] [--format epub]
readpack send BOOK [--file PATH]
readpack list
readpack show BOOK
readpack remove BOOK ARTICLE_ID_OR_URL
readpack refresh BOOK ARTICLE_ID_OR_URL
readpack config [--init]
```

### Exit codes

- `0`: success.
- `1`: user/configuration error.
- `2`: network or extraction failure.
- `3`: build failure.
- `4`: delivery failure.

For batch operations, partial success should return a non-zero code when any requested URL fails, while still persisting successful articles.

## Local storage model

Default store:

```text
~/.local/share/readpack/
```

Suggested layout:

```text
~/.local/share/readpack/
  config.toml
  books/
    weekend-reading/
      book.json
      articles/
        001-example-article/
          article.md
          article.html
          meta.json
          source.html
          assets/
            image-001.jpg
            chart-001.png
      build/
        weekend-reading.epub
```

The store path must be configurable via CLI flag and environment variable:

```bash
READPACK_STORE=/path/to/store
```

## Book manifest

`book.json` should be stable, human-readable JSON.

```json
{
  "schema_version": 1,
  "id": "weekend-reading",
  "title": "Weekend reading",
  "created_at": "2026-05-24T10:00:00Z",
  "updated_at": "2026-05-24T10:15:00Z",
  "articles": [
    {
      "id": "001-example-article",
      "url": "https://example.com/article",
      "title": "Example article",
      "author": "Example Author",
      "published_at": "2026-05-20",
      "added_at": "2026-05-24T10:15:00Z",
      "path": "articles/001-example-article",
      "status": "ready"
    }
  ]
}
```

Article status values:

- `ready`: extraction succeeded.
- `failed`: extraction failed, with details in `meta.json`.
- `stale`: source should be refreshed before the next build.

Article IDs should be stable once assigned. Reordering the manifest should not rename article directories.

## Article package

Each article package contains normalised content plus extraction evidence.

```text
article.md
article.html
meta.json
source.html
assets/
```

### `meta.json`

```json
{
  "schema_version": 1,
  "url": "https://example.com/article",
  "canonical_url": "https://example.com/article",
  "title": "Example article",
  "author": "Example Author",
  "published_at": "2026-05-20",
  "extracted_at": "2026-05-24T10:15:00Z",
  "extractor": "trafilatura",
  "word_count": 1200,
  "image_count": 3,
  "assets": [
    {
      "source_url": "https://example.com/image.jpg",
      "path": "assets/image-001.jpg",
      "mime_type": "image/jpeg",
      "alt": "A useful figure",
      "caption": "A useful figure"
    }
  ]
}
```

### `article.md`

Used for easy inspection and potential Pandoc builds.

Expected Markdown conventions:

```markdown
# Article title

By Example Author  
Published: 2026-05-20  
URL: <https://example.com/article>

First paragraph.

![Alt text](assets/image-001.jpg)

_Caption text._
```

### `article.html`

Used as the canonical build input when using a Python ePUB builder. It should be simple XHTML-compatible HTML, not raw source HTML.

Allowed structural elements:

- `h1` through `h6`
- `p`
- `a`
- `blockquote`
- `ul`, `ol`, `li`
- `figure`, `figcaption`
- `img`
- `table`, `thead`, `tbody`, `tr`, `th`, `td`
- `hr`

Disallowed build input:

- Scripts.
- Remote assets.
- Tracking pixels.
- Forms.
- Cookie banners.
- Navigation and footer blocks.

## Extraction strategy

Use a hybrid extractor.

### Phase 1: HTTP extraction

Try simple HTTP fetch plus readability extraction first.

Candidate libraries:

- `trafilatura`
- `readability-lxml`
- `beautifulsoup4`
- `lxml`

This should handle normal news articles and blog posts quickly.

### Phase 2: Browser extraction

Fall back to Playwright when:

- HTTP fetch fails.
- The article appears JavaScript-rendered.
- The extracted body is too short.
- The page requires a logged-in browser profile.
- Important images are lazy-loaded.

Browser extraction should support persistent profiles:

```bash
readpack add "Book" URL --profile economist
```

Profiles should live outside individual books:

```text
~/.local/share/readpack/profiles/economist/
```

The tool must not bypass paywalls. It may use a logged-in browser profile created by the user.

### Extraction quality checks

An extracted article is suspicious if:

- Word count is below a configurable threshold, default `250`.
- No title is detected.
- The body contains login, subscribe, cookie, or bot-check text.
- The source URL and canonical URL differ unexpectedly.
- More than half the body consists of navigation-like links.

Suspicious extraction should fail loudly unless the user passes an override such as:

```bash
readpack add "Book" URL --allow-poor-extraction
```

## Images and figures

The Kindle path is image-sensitive. Images should be local, compressed, and referenced relatively.

Requirements:

- Download remote `img` assets.
- Preserve useful `alt` text.
- Preserve captions where available.
- Convert unsupported formats where necessary.
- Prefer JPEG/PNG for final ePUB compatibility.
- Downscale extremely large images.
- Avoid remote image references in the ePUB.

Recommended image processing:

- Use `Pillow`.
- Convert WebP/AVIF/SVG where possible.
- Set maximum width around `1600px` for Kindle-friendly output.
- Preserve aspect ratio.
- Use JPEG for photos and PNG for charts/screenshots.

### Charts and complex figures

Interactive charts, iframes, canvas charts, and complex SVGs should be screenshotted through Playwright and embedded as static images.

This mirrors the existing approach used in the Economist Graphic Detail scraper.

Expected behaviour:

- Detect `figure`, `iframe`, `canvas`, `svg`, chart containers, and site-specific chart classes.
- Scroll element into view.
- Wait briefly for rendering.
- Screenshot the element.
- Store the image as a local asset.
- Insert it into the article at the approximate source position.

## ePUB generation

Two approaches are acceptable.

### MVP approach: Pandoc

Generate one combined Markdown file and run Pandoc:

```bash
pandoc book.md -o book.epub --toc --metadata title="Weekend reading"
```

Benefits:

- Simple.
- Fast to implement.
- Good enough for early validation.

Costs:

- Less control over per-chapter structure.
- More dependence on an external binary.

### Preferred mature approach: Python ePUB builder

Use `ebooklib` or direct OPF/NCX generation.

Benefits:

- Full control over chapters, manifest, spine, CSS, cover, and assets.
- Easier to keep one article per chapter.
- No external Pandoc dependency.

Costs:

- More implementation work.

### ePUB structure

Generated book should include:

- Title page.
- Table of contents.
- One chapter per article.
- Optional source URL line per article.
- Embedded images.
- Minimal CSS.
- Metadata title and language.

Suggested chapter order is manifest order.

### Kindle-friendly CSS

CSS should be conservative:

```css
body { line-height: 1.35; }
h1, h2, h3 { line-height: 1.15; }
img { max-width: 100%; height: auto; }
figure { margin: 1em 0; }
figcaption { font-size: 0.85em; font-style: italic; }
blockquote { margin-left: 1em; border-left: 0.2em solid #999; padding-left: 0.8em; }
```

Avoid layout-dependent CSS such as grids, complex floats, fixed widths, and JavaScript.

## Kindle delivery

Use Send to Kindle by email.

The user must configure:

- Kindle destination email address.
- Approved sender email address in Amazon settings.
- SMTP host, port, username, and password or app password.

Example config:

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

Secrets should not be stored in plain text by default. Prefer `password_command` so the user can integrate with macOS Keychain, `pass`, `op`, or another credential manager.

### Delivery constraints

- Email attachment limits apply.
- Amazon may silently reject malformed files.
- The sender address must be approved in Amazon's Kindle document settings.
- Delivery may take minutes.

Before sending, `readpack` should:

- Verify the ePUB exists.
- Check file size.
- Construct a plain email with the ePUB attachment.
- Send via SMTP with TLS.
- Print a clear success message indicating that SMTP accepted the message, not that Kindle ingestion is guaranteed.

## Configuration

Configuration file:

```text
~/.config/readpack/config.toml
```

Environment overrides:

```bash
READPACK_STORE
READPACK_KINDLE_ADDRESS
READPACK_EMAIL_SENDER
READPACK_SMTP_HOST
READPACK_SMTP_PORT
READPACK_SMTP_USERNAME
READPACK_SMTP_PASSWORD
READPACK_SMTP_PASSWORD_COMMAND
```

Config inspection must redact secrets.

```bash
readpack config
```

Should print paths and non-secret values, with passwords shown as `<redacted>`.

## Dependency candidates

Python dependencies:

- `typer` or `argparse` for CLI.
- `trafilatura` for extraction.
- `beautifulsoup4` and `lxml` for cleanup.
- `playwright` for browser fallback and screenshots.
- `Pillow` for image conversion and resizing.
- `python-slugify` for stable paths.
- `ebooklib` for mature ePUB generation.
- `tomli-w` for writing TOML on Python versions that need it.

External optional dependencies:

- `pandoc` for MVP ePUB generation.

## Error handling principles

- Do not corrupt existing books when extraction or build fails.
- Write new article packages to a temporary directory, then atomically move them into place.
- Avoid duplicate URLs in a book unless explicitly forced.
- Preserve failed extraction metadata for debugging.
- Make recovery commands explicit: `refresh`, `remove`, `build --force`.

## Security and privacy

- Source URLs may be sensitive reading history; store locally only.
- Do not send telemetry.
- Do not upload article content to third-party services.
- Do not log SMTP passwords.
- Do not store browser profile data inside generated books.
- Respect robots, terms, paywalls, and access controls.

## Open decisions

- Whether the MVP should require Pandoc or start directly with `ebooklib`.
- Whether the initial CLI should use `argparse` for zero dependencies or `typer` for better UX.
- Whether article packages should store both Markdown and XHTML from day one.
- How aggressively images should be compressed before Kindle delivery.
- Whether book titles should be case-sensitive.
- Whether a URL can appear in multiple books with shared article storage or duplicated packages.
