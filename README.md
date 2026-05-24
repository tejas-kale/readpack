# readpack

Turn web articles into ePUB books and send them to Kindle.

## Install

```bash
uv tool install git+https://github.com/tejas-kale/readpack
```

Requires [pandoc](https://pandoc.org/installing.html) for `build`.

## Usage

```bash
readpack add "Weekend reading" https://example.com/article
readpack list
readpack show "Weekend reading"
readpack build "Weekend reading"   # requires pandoc
readpack config
```

## Store location

Default: `~/.local/share/readpack/`

Override: `READPACK_STORE=/path/to/store` or `--store PATH`

## Options

```
readpack --help
readpack add --force BOOK URL   # re-add duplicate URL
readpack build --force BOOK     # rebuild existing epub
```

## Run tests

```bash
uv run pytest
```
