from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


DEFAULT_USER_AGENT = "SignalWatcher/0.2 (+https://github.com/HANG939/signal-watcher)"


def request_text(url: str, headers: dict[str, str] | None = None, timeout: int = 25) -> str:
    req = urllib.request.Request(url, headers=_headers(headers))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {url}: {detail[:500]}") from exc


def request_json(
    url: str,
    headers: dict[str, str] | None = None,
    method: str = "GET",
    body: Any | None = None,
    timeout: int = 25,
) -> Any:
    data = None
    request_headers = _headers(headers)
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        request_headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {url}: {detail[:500]}") from exc


def _headers(headers: dict[str, str] | None = None) -> dict[str, str]:
    merged = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "*/*",
    }
    merged.update(headers or {})
    return merged
