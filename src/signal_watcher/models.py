from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Notification:
    """A message produced by a watcher and sent by one or more notifiers."""

    title: str
    body: str
    url: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    def as_payload(self) -> dict[str, Any]:
        payload = {
            "title": self.title,
            "body": self.body,
            "url": self.url,
            "meta": self.meta,
        }
        return {key: value for key, value in payload.items() if value not in (None, {}, "")}
