from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


class JsonStateStore:
    """Small JSON state store with atomic writes."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.data: dict[str, Any] = self._load()

    def monitor_state(self, name: str) -> dict[str, Any]:
        monitors = self.data.setdefault("monitors", {})
        state = monitors.setdefault(name, {})
        if not isinstance(state, dict):
            state = {}
            monitors[name] = state
        return state

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.",
            suffix=".tmp",
            dir=str(self.path.parent),
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(self.data, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")
            os.replace(tmp_name, self.path)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"State file is not valid JSON: {self.path}") from exc
        if not isinstance(loaded, dict):
            raise RuntimeError(f"State file must contain a JSON object: {self.path}")
        return loaded
