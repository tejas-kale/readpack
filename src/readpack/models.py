from dataclasses import dataclass, field
from datetime import datetime, timezone


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class ArticleRef:
    id: str
    url: str
    title: str
    path: str
    status: str  # ready | failed | stale
    author: str = ""
    published_at: str = ""
    added_at: str = field(default_factory=_now)


@dataclass
class Book:
    id: str
    title: str
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    articles: list[ArticleRef] = field(default_factory=list)
    schema_version: int = 1
