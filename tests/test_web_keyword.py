from signal_watcher.watchers.web_keyword import WebKeywordWatcher, evaluate_keywords


def test_evaluate_keywords_supports_absent_all_stock_signal():
    matched, reasons = evaluate_keywords("Product is available now", {"absent_all": ["Unavailable"]})

    assert matched is True
    assert reasons == ["all absent: Unavailable"]


def test_web_keyword_notifies_on_transition_to_match(monkeypatch):
    monkeypatch.setattr("signal_watcher.watchers.web_keyword.request_text", lambda url, headers=None: "Buy now")
    watcher = WebKeywordWatcher(
        {
            "name": "stock",
            "type": "web_keyword",
            "url": "https://example.test/product",
            "present_any": ["Buy now"],
            "title": "Stock alert",
        }
    )
    state = {"matched": False, "fingerprint": "old"}

    notifications = watcher.check(state)

    assert len(notifications) == 1
    assert notifications[0].title == "Stock alert"
    assert state["matched"] is True


def test_web_keyword_first_run_does_not_notify_by_default(monkeypatch):
    monkeypatch.setattr("signal_watcher.watchers.web_keyword.request_text", lambda url, headers=None: "Buy now")
    watcher = WebKeywordWatcher(
        {
            "name": "stock",
            "type": "web_keyword",
            "url": "https://example.test/product",
            "present_any": ["Buy now"],
        }
    )

    assert watcher.check({}) == []
