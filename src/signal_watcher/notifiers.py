from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .http_client import request_json
from .models import Notification


class NotificationDispatcher:
    def __init__(self, configs: list[dict[str, Any]] | None, dry_run: bool = False):
        self.configs = [item for item in configs or [] if item.get("enabled", True)]
        self.dry_run = dry_run

    def send(self, notification: Notification) -> None:
        if self.dry_run or not self.configs:
            print_notification(notification, prefix="[dry-run]" if self.dry_run else "[print]")
            return

        sent = False
        for config in self.configs:
            notifier_type = config.get("type", "print")
            if notifier_type == "print":
                print_notification(notification)
            elif notifier_type == "serverchan":
                send_serverchan(config, notification)
            elif notifier_type == "telegram":
                send_telegram(config, notification)
            elif notifier_type == "wecom":
                send_wecom(config, notification)
            elif notifier_type == "webhook":
                send_webhook(config, notification)
            else:
                raise RuntimeError(f"Unknown notifier type: {notifier_type}")
            sent = True

        if not sent:
            print_notification(notification, prefix="[print]")


def print_notification(notification: Notification, prefix: str = "[signal]") -> None:
    print(f"{prefix} {notification.title}")
    print(notification.body)
    if notification.url:
        print(notification.url)


def send_serverchan(config: dict[str, Any], notification: Notification) -> None:
    sendkey = config.get("sendkey") or config.get("send_key")
    if not sendkey:
        raise RuntimeError("serverchan notifier requires 'sendkey'")
    base_url = str(config.get("base_url") or "https://sctapi.ftqq.com").rstrip("/")
    url = f"{base_url}/{urllib.parse.quote(sendkey)}.send"
    body = urllib.parse.urlencode(
        {
            "title": notification.title,
            "desp": notification.body if not notification.url else f"{notification.body}\n\n{notification.url}",
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"ServerChan failed with HTTP {exc.code}: {detail}") from exc
    if payload.get("code") not in (0, None):
        raise RuntimeError(f"ServerChan failed: {payload}")


def send_telegram(config: dict[str, Any], notification: Notification) -> None:
    token = config.get("bot_token")
    chat_id = config.get("chat_id")
    if not token or not chat_id:
        raise RuntimeError("telegram notifier requires 'bot_token' and 'chat_id'")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    text = notification.body if not notification.url else f"{notification.body}\n\n{notification.url}"
    request_json(
        url,
        method="POST",
        body={
            "chat_id": chat_id,
            "text": f"{notification.title}\n\n{text}",
            "disable_web_page_preview": False,
        },
    )


def send_wecom(config: dict[str, Any], notification: Notification) -> None:
    webhook_url = config.get("webhook_url")
    if not webhook_url:
        raise RuntimeError("wecom notifier requires 'webhook_url'")
    text = notification.body if not notification.url else f"{notification.body}\n\n{notification.url}"
    request_json(
        webhook_url,
        method="POST",
        body={
            "msgtype": "markdown",
            "markdown": {"content": f"**{notification.title}**\n\n{text}"},
        },
    )


def send_webhook(config: dict[str, Any], notification: Notification) -> None:
    webhook_url = config.get("url") or config.get("webhook_url")
    if not webhook_url:
        raise RuntimeError("webhook notifier requires 'url'")
    request_json(webhook_url, method="POST", body=notification.as_payload())
