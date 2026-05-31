import json

from signal_watcher.config import expand_env, load_config
from signal_watcher.state import JsonStateStore


def test_state_store_writes_json_atomically(tmp_path):
    path = tmp_path / "state.json"
    store = JsonStateStore(path)
    store.monitor_state("demo")["last_seen_id"] = "123"
    store.save()

    assert json.loads(path.read_text(encoding="utf-8"))["monitors"]["demo"]["last_seen_id"] == "123"


def test_config_expands_env_values(monkeypatch, tmp_path):
    monkeypatch.setenv("SERVERCHAN_SENDKEY", "send-key")
    path = tmp_path / "config.yaml"
    path.write_text(
        """
state_file: .state/test.json
notifiers:
  - type: serverchan
    sendkey: ${SERVERCHAN_SENDKEY}
monitors:
  - name: demo
    type: web_keyword
    url: https://example.test
""",
        encoding="utf-8",
    )

    config = load_config(path)

    assert config["notifiers"][0]["sendkey"] == "send-key"


def test_expand_env_missing_values_become_empty_strings(monkeypatch):
    monkeypatch.delenv("MISSING_VALUE", raising=False)

    assert expand_env({"secret": "${MISSING_VALUE}"}) == {"secret": ""}
