from __future__ import annotations

from typing import Any

from .damai import DamaiWatcher
from .web_keyword import WebKeywordWatcher
from .x_rss import XRssWatcher


WATCHER_TYPES = {
    "damai": DamaiWatcher,
    "web_keyword": WebKeywordWatcher,
    "x_rss": XRssWatcher,
}


def build_watchers(config: dict[str, Any]):
    watchers = []
    for monitor in config.get("monitors", []):
        if not monitor.get("enabled", True):
            continue
        watcher_type = monitor.get("type")
        cls = WATCHER_TYPES.get(watcher_type)
        if cls is None:
            raise RuntimeError(f"Unknown watcher type: {watcher_type}")
        watchers.append(cls(monitor))
    return watchers
