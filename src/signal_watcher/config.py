from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml


ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        raise RuntimeError(f"Config file not found: {config_path}")

    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise RuntimeError("Config root must be a mapping")

    config = expand_env(raw)
    monitors = config.get("monitors", [])
    if not isinstance(monitors, list):
        raise RuntimeError("Config field 'monitors' must be a list")

    names = [monitor.get("name") for monitor in monitors if isinstance(monitor, dict)]
    duplicates = sorted({name for name in names if name and names.count(name) > 1})
    if duplicates:
        raise RuntimeError(f"Monitor names must be unique: {', '.join(duplicates)}")
    return config


def expand_env(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: expand_env(item) for key, item in value.items()}
    if isinstance(value, list):
        return [expand_env(item) for item in value]
    if isinstance(value, str):
        return ENV_PATTERN.sub(lambda match: os.environ.get(match.group(1), ""), value)
    return value
