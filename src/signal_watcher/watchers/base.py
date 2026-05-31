from __future__ import annotations

from typing import Any

from ..models import Notification


class Watcher:
    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.name = str(config.get("name") or config.get("type") or self.__class__.__name__)
        self.interval_seconds = int(config.get("interval_seconds") or 60)

    def check(self, state: dict[str, Any], notify_on_first_run: bool = False) -> list[Notification]:
        raise NotImplementedError


def as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    return [str(value)]
