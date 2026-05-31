from signal_watcher.models import Notification
from signal_watcher.notifiers import NotificationDispatcher


def test_dispatcher_prints_when_no_notifier_is_configured(capsys):
    dispatcher = NotificationDispatcher([])

    dispatcher.send(Notification(title="Hello", body="World", url="https://example.test"))

    output = capsys.readouterr().out
    assert "Hello" in output
    assert "World" in output
    assert "https://example.test" in output
