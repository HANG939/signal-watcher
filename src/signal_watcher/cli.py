from __future__ import annotations

import argparse
import sys
import time

from .config import load_config
from .models import Notification
from .notifiers import NotificationDispatcher
from .state import JsonStateStore
from .watchers import build_watchers


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Self-hosted signal monitoring toolkit")
    parser.add_argument("--config", default="config.yaml", help="Path to config YAML")
    parser.add_argument("--once", action="store_true", help="Run enabled monitors once")
    parser.add_argument("--watch", action="store_true", help="Run enabled monitors continuously")
    parser.add_argument("--only", action="append", default=[], help="Run only a named monitor")
    parser.add_argument("--dry-run", action="store_true", help="Print notifications instead of sending them")
    parser.add_argument("--init-notify", action="store_true", help="Notify even on first observed state")
    args = parser.parse_args(argv)

    config = load_config(args.config)
    watchers = build_watchers(config)
    if args.only:
        wanted = set(args.only)
        watchers = [watcher for watcher in watchers if watcher.name in wanted]
    if not watchers:
        print("No enabled monitors to run.", file=sys.stderr)
        raise SystemExit(1)

    state = JsonStateStore(config.get("state_file", ".state/signal-watcher.json"))
    dispatcher = NotificationDispatcher(config.get("notifiers", []), dry_run=args.dry_run)

    if args.watch:
        run_forever(watchers, state, dispatcher, args.init_notify)
        return

    failures = run_once(watchers, state, dispatcher, args.init_notify, continue_on_error=False)
    raise SystemExit(1 if failures else 0)


def run_forever(watchers, state: JsonStateStore, dispatcher: NotificationDispatcher, init_notify: bool) -> None:
    next_run = {watcher.name: 0.0 for watcher in watchers}
    while True:
        now = time.time()
        for watcher in watchers:
            if now < next_run[watcher.name]:
                continue
            try:
                run_watcher(watcher, state, dispatcher, init_notify)
            except Exception:
                pass
            next_run[watcher.name] = time.time() + watcher.interval_seconds
        sleep_for = min(max(0.2, due - time.time()) for due in next_run.values())
        time.sleep(min(sleep_for, 1.0))


def run_once(
    watchers,
    state: JsonStateStore,
    dispatcher: NotificationDispatcher,
    init_notify: bool,
    continue_on_error: bool,
) -> int:
    failures = 0
    for watcher in watchers:
        try:
            run_watcher(watcher, state, dispatcher, init_notify)
        except Exception:
            failures += 1
            if not continue_on_error:
                break
    return failures


def run_watcher(watcher, state: JsonStateStore, dispatcher: NotificationDispatcher, init_notify: bool) -> None:
    try:
        monitor_state = state.monitor_state(watcher.name)
        notifications = watcher.check(monitor_state, notify_on_first_run=init_notify)
        state.save()
        for notification in notifications:
            dispatcher.send(notification)
    except Exception as exc:
        state.save()
        print(f"[{watcher.name}] failed: {exc}", file=sys.stderr)
        if watcher.config.get("notify_errors", False):
            dispatcher.send(
                Notification(
                    title=f"{watcher.name} failed",
                    body=str(exc),
                    meta={"monitor": watcher.name, "error": type(exc).__name__},
                )
            )
        raise
