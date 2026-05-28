# readpack

Turn web articles into ePUB books and send them to Kindle.

## Install

```bash
uv tool install git+https://github.com/tejas-kale/readpack
```

Requires [pandoc](https://pandoc.org/installing.html) for `build`.

Requires an `OPENROUTER_API_KEY` environment variable for cover image generation (uses `openai/gpt-5.4-image-2` via [OpenRouter](https://openrouter.ai)).

## Usage

```bash
readpack add "Weekend reading" https://example.com/article
readpack list
readpack show "Weekend reading"
readpack build "Weekend reading" --force
readpack send "Weekend reading"
readpack config --init
```

## What it does

- Fetches article HTML.
- Extracts readable article content with metadata.
- Stores `source.html`, `article.html`, `article.md`, and `meta.json`.
- Downloads article images when possible.
- Normalises Markdown for cleaner EPUB output, including inline code, blockquotes, and footnotes.
- Generates an AI cover image with visible book title text (`openai/gpt-5.4-image-2` via OpenRouter) on first `build`; cached and reused unless `--force-cover`.
- Shows emoji-prefixed progress logs while building, including cover generation and pandoc steps.
- Builds styled EPUBs with pandoc.
- Sends EPUBs to Kindle over SMTP when configured.

## Store location

Default: `~/.local/share/readpack/`

Override:

```bash
READPACK_STORE=/path/to/store readpack list
readpack --store /path/to/store list
```

## Commands

```bash
readpack --help
readpack add BOOK URL
readpack add --force BOOK URL       # re-add duplicate URL
readpack list
readpack show BOOK
readpack build BOOK
readpack build --force BOOK         # rebuild existing EPUB
readpack build --force-cover BOOK   # regenerate cover image
readpack send BOOK
readpack send --force-build BOOK
readpack send --force-cover BOOK
readpack config
readpack config --init
```

## Limitations

Some sites block non-browser fetches with CAPTCHA or bot-challenge pages. `readpack` rejects these instead of saving empty articles.

If extraction finds no article text, `add` fails rather than storing an `Untitled` zero-word article.

## Run tests

```bash
uv run pytest
```
