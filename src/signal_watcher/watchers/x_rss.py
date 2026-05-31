from __future__ import annotations

import re
import time
import urllib.parse
import xml.etree.ElementTree as ET
from html import unescape
from typing import Any

from ..http_client import request_text
from ..models import Notification
from .base import Watcher, as_list


DEFAULT_RSS_URLS = [
    "https://nitter.net/{username}/rss",
    "https://xcancel.com/{username}/rss",
    "https://rss.xcancel.com/{username}/rss",
    "https://twiiit.com/{username}/rss",
    "https://rsshub.app/twitter/user/{username}",
]


class XRssWatcher(Watcher):
    def check(self, state: dict[str, Any], notify_on_first_run: bool = False) -> list[Notification]:
        username = str(self.config.get("username") or "").lstrip("@")
        if not username:
            raise RuntimeError(f"{self.name}: x_rss watcher requires username")

        posts = fetch_first_working_feed(username, self.feed_urls)
        max_posts = int(self.config.get("max_posts_per_check") or 10)
        posts = posts[:max_posts]
        now = int(time.time())
        if not posts:
            state["checked_at"] = now
            return []

        legacy_last_seen = state.get("last_seen_id")
        raw_seen_ids = state.get("seen_ids") or ([legacy_last_seen] if legacy_last_seen else [])
        seen_ids = list(dict.fromkeys(str(item) for item in raw_seen_ids if item))
        seen = set(seen_ids)
        current_ids = [post["id"] for post in posts if post.get("id")]
        first_run = not seen_ids and not state.get("last_seen_id")

        if first_run and not notify_on_first_run and not self.config.get("notify_on_first_run", False):
            state.update(
                {
                    "username": username,
                    "last_seen_id": current_ids[0],
                    "seen_ids": current_ids[:200],
                    "checked_at": now,
                }
            )
            print(f"[{self.name}] initialized @{username}; no notification sent")
            return []

        new_posts = [post for post in posts if post.get("id") and post["id"] not in seen]
        if not new_posts:
            state.update(
                {
                    "username": username,
                    "last_seen_id": current_ids[0],
                    "seen_ids": list(dict.fromkeys(current_ids + seen_ids))[:200],
                    "checked_at": now,
                }
            )
            print(f"[{self.name}] no new posts for @{username}")
            return []

        state.update(
            {
                "username": username,
                "last_seen_id": current_ids[0],
                "seen_ids": list(dict.fromkeys(current_ids + seen_ids))[:200],
                "checked_at": now,
            }
        )
        posts_to_send = list(reversed(new_posts))
        print(f"[{self.name}] found {len(posts_to_send)} new post(s) for @{username}")
        return [format_batch_notification(username, posts_to_send)]

    @property
    def feed_urls(self) -> list[str]:
        configured = as_list(self.config.get("feed_urls"))
        return configured or DEFAULT_RSS_URLS


def fetch_first_working_feed(username: str, feed_urls: list[str]) -> list[dict[str, str]]:
    last_error: Exception | None = None
    for feed_url in feed_urls:
        try:
            url = feed_url.format(username=urllib.parse.quote(username))
            xml_text = request_text(
                url,
                headers={
                    "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml",
                    "User-Agent": "Mozilla/5.0 SignalWatcher/0.2",
                },
            )
            posts = parse_rss_posts(xml_text)
            validate_posts(posts)
            print(f"Using RSS source: {feed_url}")
            return posts
        except Exception as exc:
            last_error = exc
            print(f"RSS source failed: {feed_url}: {exc}")
    raise RuntimeError(f"All RSS sources failed. Last error: {last_error}")


def parse_rss_posts(xml_text: str) -> list[dict[str, str]]:
    xml_text = xml_text.lstrip()
    if not xml_text.startswith(("<?xml", "<rss", "<feed")):
        raise RuntimeError("RSS source returned a non-RSS page")

    root = ET.fromstring(xml_text)
    posts: list[dict[str, str]] = []

    for item in root.findall("./channel/item"):
        title = item.findtext("title") or ""
        link = item.findtext("link") or ""
        guid = normalize_post_id(item.findtext("guid") or link or title)
        description = item.findtext("description") or ""
        posts.append(
            {
                "id": guid,
                "text": title or strip_html(description),
                "created_at": item.findtext("pubDate") or "",
                "url": link,
            }
        )

    if posts:
        return posts

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    for entry in root.findall("atom:entry", ns):
        title = entry.findtext("atom:title", default="", namespaces=ns)
        link_node = entry.find("atom:link", ns)
        link = link_node.attrib.get("href", "") if link_node is not None else ""
        guid = normalize_post_id(entry.findtext("atom:id", default=link or title, namespaces=ns))
        posts.append(
            {
                "id": guid,
                "text": title,
                "created_at": entry.findtext("atom:updated", default="", namespaces=ns),
                "url": link,
            }
        )
    return posts


def validate_posts(posts: list[dict[str, str]]) -> None:
    if not posts:
        raise RuntimeError("RSS source returned no posts")
    invalid_markers = [
        "RSS reader not yet whitelisted",
        "Making sure you're not a bot",
        "Please enable cookies",
        "Cloudflare",
    ]
    joined = "\n".join((post.get("text", "") + "\n" + post.get("url", "")) for post in posts[:3])
    if any(marker in joined for marker in invalid_markers):
        raise RuntimeError("RSS source returned a block/placeholder feed")


def normalize_post_id(value: str) -> str:
    match = re.search(r"/status/(\d+)", str(value or ""))
    if match:
        return match.group(1)
    match = re.search(r"\b(\d{15,25})\b", str(value or ""))
    if match:
        return match.group(1)
    return str(value or "")


def strip_html(value: str) -> str:
    return unescape(re.sub(r"<[^>]+>", "", value or "")).strip()


def format_batch_notification(username: str, posts: list[dict[str, Any]]) -> Notification:
    title = f"@{username} has {len(posts)} new post(s)"
    parts = [f"@{username} has {len(posts)} new public post(s)."]
    for index, post in enumerate(posts, start=1):
        url = post.get("url") or f"https://x.com/{username}/status/{post['id']}"
        created = post.get("created_at", "")
        text = str(post.get("text") or "").strip()
        parts.append(f"{index}. {created}\n{text}\n{url}")
    return Notification(title=title, body="\n\n".join(parts), meta={"username": username, "count": len(posts)})
