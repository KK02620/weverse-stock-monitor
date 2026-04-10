from pathlib import Path
from types import SimpleNamespace

import pytest

import gui
import notifier
from notifier import Notifier
from storage import Storage


class FakeProcess:
    def __init__(self):
        self.wait_called = False

    def wait(self, timeout=None):
        self.wait_called = True
        return 0

    def poll(self):
        return 0


class FakeNotifierBackend:
    def __init__(self):
        self.paths = []

    def set_custom_sound(self, file_path):
        self.paths.append(file_path)


class FakeStorageBackend:
    def __init__(self):
        self.saved_settings = []

    def save_notification_settings(self, settings):
        self.saved_settings.append(settings)
        return True


@pytest.fixture
def fake_gui_instance(monkeypatch):
    errors = []
    gui_instance = gui.SimpleGUI.__new__(gui.SimpleGUI)
    gui_instance.monitor = SimpleNamespace(notifier=FakeNotifierBackend())
    gui_instance.storage = FakeStorageBackend()
    gui_instance._update_status = lambda text, active=False: None
    monkeypatch.setattr(gui.messagebox, "showerror", lambda title, message: errors.append((title, message)))
    return gui_instance, errors


def test_notifier_uses_winsound_for_custom_mp3_on_windows(monkeypatch, tmp_path):
    mp3_file = tmp_path / "alert.mp3"
    mp3_file.write_bytes(b"id3")
    calls = []

    fake_winsound = SimpleNamespace(
        SND_FILENAME=0x00020000,
        SND_ASYNC=0x0001,
        PlaySound=lambda sound, flags: calls.append((sound, flags)),
    )

    monkeypatch.setattr(notifier.sys, "platform", "win32")
    monkeypatch.setattr(notifier.importlib, "import_module", lambda name: fake_winsound)
    monkeypatch.setattr(notifier.time, "sleep", lambda seconds: None)

    current_notifier = Notifier(custom_sound_path=str(mp3_file))
    current_notifier._play_custom_sound_once()

    assert calls == [(str(mp3_file), fake_winsound.SND_FILENAME | fake_winsound.SND_ASYNC)]


def test_notifier_uses_afplay_for_default_sound_on_macos(monkeypatch):
    popen_calls = []

    monkeypatch.setattr(notifier.sys, "platform", "darwin")
    monkeypatch.setattr(notifier.subprocess, "run", lambda *args, **kwargs: None)

    def fake_popen(command, stdout=None, stderr=None):
        popen_calls.append(command)
        return FakeProcess()

    monkeypatch.setattr(notifier.subprocess, "Popen", fake_popen)

    current_notifier = Notifier(sound_name="Glass")
    current_notifier._play_system_sound_once()

    assert popen_calls == [["afplay", "-v", "10", current_notifier.SYSTEM_SOUNDS["Glass"]]]


def test_storage_persists_notification_settings(tmp_path):
    excel_file = tmp_path / "products.xlsx"
    storage = Storage(str(excel_file))

    saved = storage.save_notification_settings({
        "sound_enabled": True,
        "custom_sound_path": "/tmp/alert.mp3",
    })

    reloaded = Storage(str(excel_file)).load_notification_settings()

    assert saved is True
    assert reloaded["sound_enabled"] is True
    assert reloaded["custom_sound_path"] == "/tmp/alert.mp3"


def test_gui_apply_custom_sound_rejects_invalid_and_saves_valid_path(fake_gui_instance, tmp_path):
    gui_instance, errors = fake_gui_instance
    invalid_file = tmp_path / "alert.wav"
    invalid_file.write_bytes(b"wav")

    assert gui_instance._apply_custom_sound(str(invalid_file)) is False
    assert errors

    valid_file = tmp_path / "alert.mp3"
    valid_file.write_bytes(b"id3")

    assert gui_instance._apply_custom_sound(str(valid_file)) is True
    assert gui_instance.monitor.notifier.paths == [str(valid_file)]
    assert gui_instance.storage.saved_settings == [{"custom_sound_path": str(valid_file)}]
