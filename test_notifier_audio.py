import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import notifier
from config import Config
from notifier import Notifier
from storage import Storage


class ImmediateThread:
    def __init__(self, target=None, daemon=None):
        self._target = target
        self.daemon = daemon

    def start(self):
        if self._target:
            self._target()


@pytest.fixture
def run_sound_loop_inline(monkeypatch):
    monkeypatch.setattr(notifier.threading, "Thread", ImmediateThread)
    times = iter([0, 0, 2])
    monkeypatch.setattr(notifier.time, "time", lambda: next(times))
    monkeypatch.setattr(notifier.time, "sleep", lambda _: None)


def test_play_alert_sound_uses_winsound_backend_on_windows(monkeypatch, run_sound_loop_inline):
    fake_winsound = SimpleNamespace(
        PlaySound=Mock(),
        MessageBeep=Mock(),
        SND_ALIAS=1,
        SND_ASYNC=2,
    )
    popen_mock = Mock()
    run_mock = Mock()

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setitem(sys.modules, "winsound", fake_winsound)
    monkeypatch.setattr(notifier.subprocess, "Popen", popen_mock)
    monkeypatch.setattr(notifier.subprocess, "run", run_mock)

    notifier_instance = Notifier(sound_enabled=True, sound_name="Glass")

    notifier_instance.play_alert_sound(duration=1)

    assert fake_winsound.PlaySound.called or fake_winsound.MessageBeep.called
    popen_mock.assert_not_called()
    run_mock.assert_not_called()


def test_play_alert_sound_prefers_custom_mp3_on_darwin(monkeypatch, run_sound_loop_inline):
    custom_mp3 = "/tmp/restock.mp3"
    process = SimpleNamespace(wait=Mock(), poll=Mock(return_value=0))
    popen_mock = Mock(return_value=process)
    run_mock = Mock()

    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(notifier.subprocess, "Popen", popen_mock)
    monkeypatch.setattr(notifier.subprocess, "run", run_mock)

    notifier_instance = Notifier(
        sound_enabled=True,
        sound_name="Glass",
        custom_sound_path=custom_mp3,
    )

    notifier_instance.play_alert_sound(duration=1)

    command = popen_mock.call_args.args[0]
    assert any("restock.mp3" in arg for arg in command)

def test_storage_load_audio_settings_returns_defaults_without_file(tmp_path):
    storage = Storage(str(tmp_path / "products.xlsx"))

    settings = storage._normalize_audio_settings(storage.load_notification_settings())

    assert settings["sound_enabled"] is True
    assert settings["sound_name"] == Config.DEFAULT_SOUND
    assert settings["custom_sound_path"] is None

def test_storage_audio_settings_round_trip(tmp_path):
    storage = Storage(str(tmp_path / "products.xlsx"))
    custom_mp3 = tmp_path / "restock.mp3"
    custom_mp3.write_bytes(b"ID3")

    settings = {
        "sound_enabled": False,
        "sound_name": "Ping",
        "custom_sound_path": str(custom_mp3),
    }

    assert storage.save_notification_settings(settings) is True

    loaded = storage._normalize_audio_settings(storage.load_notification_settings())
    assert loaded["sound_enabled"] is False
    assert loaded["sound_name"] == "Ping"
    assert loaded["custom_sound_path"] == str(custom_mp3)

def test_storage_save_audio_settings_rejects_missing_custom_mp3(tmp_path):
    storage = Storage(str(tmp_path / "products.xlsx"))
    missing_mp3 = tmp_path / "missing.mp3"

    with pytest.raises(ValueError):
        settings = {
            "sound_enabled": True,
            "sound_name": "Glass",
            "custom_sound_path": str(missing_mp3),
        }
        storage._normalize_audio_settings(settings)
        storage.save_notification_settings(settings)
