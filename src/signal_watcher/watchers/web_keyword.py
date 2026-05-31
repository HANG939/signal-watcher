from __future__ import annotations

import hashlib
import time
from typing import Any

from ..http_client import request_text
from ..models import Notification
from .base import Watcher, as_list


class WebKeywordWatcher(Watcher):
    def check(self, state: dict[str, Any], notify_on_first_run: bool = False) -> list[Notification]:
        url = self.config.get("url")
        if not url:
            raise RuntimeError(f"{self.name}: web_keyword watcher requires url")

        text = request_text(str(url), headers=self.config.get("headers") or {})
        fingerprint = hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()
        matched, reasons = evaluate_keywords(text, self.config)
        first_run = "fingerprint" not in state
        now = int(time.time())
        previous_matched = bool(state.get("matched"))
        previous_fingerprint = state.get("fingerprint")
        notify_on = self.config.get("notify_on", "match")

        state.update(
            {
                "fingerprint": fingerprint,
                "matched": matched,
                "reasons": reasons,
                "checked_at": now,
            }
        )

        if first_run and not notify_on_first_run and not self.config.get("notify_on_first_run", False):
            print(f"[{self.name}] initialized; matched={matched}")
            return []

        should_notify = False
        if notify_on == "change":
            should_notify = fingerprint != previous_fingerprint
        elif notify_on == "match":
            should_notify = matched and not previous_matched
        else:
            raise RuntimeError(f"{self.name}: notify_on must be 'match' or 'change'")

        if not should_notify:
            print(f"[{self.name}] no alert; matched={matched}")
            return []

        title = str(self.config.get("title") or f"{self.name} signal changed")
        body_lines = [
            str(self.config.get("message") or "A monitored web signal matched your alert rule."),
            f"URL: {url}",
        ]
        if reasons:
            body_lines.extend(["", "Matched rule details:"])
            body_lines.extend(f"- {reason}" for reason in reasons)
        return [Notification(title=title, body="\n".join(body_lines), url=str(url), meta={"matched": matched})]


def evaluate_keywords(text: str, config: dict[str, Any]) -> tuple[bool, list[str]]:
    present_any = as_list(config.get("present_any"))
    present_all = as_list(config.get("present_all"))
    absent_any = as_list(config.get("absent_any"))
    absent_all = as_list(config.get("absent_all"))
    reasons: list[str] = []
    matched = True

    if present_any:
        ok = any(keyword in text for keyword in present_any)
        matched = matched and ok
        if ok:
            reasons.append(f"at least one present: {', '.join(_found(text, present_any))}")

    if present_all:
        missing = [keyword for keyword in present_all if keyword not in text]
        matched = matched and not missing
        if not missing:
            reasons.append(f"all present: {', '.join(present_all)}")

    if absent_any:
        missing = [keyword for keyword in absent_any if keyword not in text]
        matched = matched and bool(missing)
        if missing:
            reasons.append(f"at least one absent: {', '.join(missing)}")

    if absent_all:
        still_present = [keyword for keyword in absent_all if keyword in text]
        matched = matched and not still_present
        if not still_present:
            reasons.append(f"all absent: {', '.join(absent_all)}")

    if not any([present_any, present_all, absent_any, absent_all]):
        reasons.append("no keyword rule configured; treating page fetch as match")
    return matched, reasons


def _found(text: str, keywords: list[str]) -> list[str]:
    return [keyword for keyword in keywords if keyword in text]
