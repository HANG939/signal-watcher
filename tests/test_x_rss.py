from signal_watcher.watchers.x_rss import XRssWatcher, normalize_post_id, parse_rss_posts


RSS_TEXT = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>third</title>
      <link>https://x.com/example/status/103</link>
      <guid>https://x.com/example/status/103</guid>
      <pubDate>Wed, 01 Jan 2026 00:03:00 GMT</pubDate>
    </item>
    <item>
      <title>second</title>
      <link>https://x.com/example/status/102</link>
      <guid>https://x.com/example/status/102</guid>
      <pubDate>Wed, 01 Jan 2026 00:02:00 GMT</pubDate>
    </item>
    <item>
      <title>first</title>
      <link>https://x.com/example/status/101</link>
      <guid>https://x.com/example/status/101</guid>
      <pubDate>Wed, 01 Jan 2026 00:01:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""


def test_parse_rss_posts_normalizes_status_ids():
    posts = parse_rss_posts(RSS_TEXT)

    assert [post["id"] for post in posts] == ["103", "102", "101"]
    assert posts[0]["text"] == "third"
    assert normalize_post_id("https://x.com/u/status/1234567890123456789") == "1234567890123456789"


def test_x_rss_first_run_initializes_without_notification(monkeypatch):
    monkeypatch.setattr(
        "signal_watcher.watchers.x_rss.fetch_first_working_feed",
        lambda username, feed_urls: parse_rss_posts(RSS_TEXT),
    )
    watcher = XRssWatcher({"name": "x", "type": "x_rss", "username": "example"})
    state = {}

    notifications = watcher.check(state)

    assert notifications == []
    assert state["last_seen_id"] == "103"
    assert state["seen_ids"] == ["103", "102", "101"]


def test_x_rss_notifies_every_unseen_post_in_chronological_order(monkeypatch):
    monkeypatch.setattr(
        "signal_watcher.watchers.x_rss.fetch_first_working_feed",
        lambda username, feed_urls: parse_rss_posts(RSS_TEXT),
    )
    watcher = XRssWatcher({"name": "x", "type": "x_rss", "username": "example"})
    state = {"seen_ids": ["101"], "last_seen_id": "101"}

    notifications = watcher.check(state)

    assert len(notifications) == 1
    body = notifications[0].body
    assert body.index("second") < body.index("third")
    assert "first" not in body
    assert state["last_seen_id"] == "103"
    assert state["seen_ids"][:3] == ["103", "102", "101"]
