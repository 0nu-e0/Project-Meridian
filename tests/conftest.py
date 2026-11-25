"""Shared test setup. Every test gets its own empty data directory, never the real one."""
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    """Point AppConfig (and anything else using LOCALAPPDATA/HOME) at tmp_path"""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))

    from utils import app_config, safe_io, settings, tasks_io, data_manager, data_history
    monkeypatch.setattr(settings.Settings, "_instance", None)
    monkeypatch.setattr(data_history.DataHistory, "_instance", None)
    monkeypatch.setattr(app_config.AppConfig, "_instance", None)
    monkeypatch.setattr(data_manager.DataManager, "_instance", None)
    monkeypatch.setattr(data_manager.DataManager, "_initialized", False)
    monkeypatch.setattr(safe_io, "_quarantined_files", [])
    monkeypatch.setattr(safe_io, "_unreadable_paths", set())
    monkeypatch.setattr(safe_io, "_unparsed_records", {})
    monkeypatch.setattr(safe_io, "_quarantine_handler", None)
    tasks_io.invalidate_tasks_cache()

    # The app's own dialogs would wait for a click; answer them unless a test does
    from PyQt5.QtWidgets import QMessageBox
    from ui.custom_widgets import dialogs
    monkeypatch.setattr(dialogs, "ask_to_save", lambda *a, **k: QMessageBox.Discard)
    monkeypatch.setattr(dialogs, "confirm", lambda *a, **k: True)
    monkeypatch.setattr(dialogs, "ask_text", lambda *a, **k: ("Untitled", True))
    monkeypatch.setattr(dialogs, "question", lambda *a, **k: QMessageBox.Yes)
    for name in ("information", "warning", "critical"):
        monkeypatch.setattr(dialogs, name, lambda *a, **k: QMessageBox.Ok)
    monkeypatch.setattr(dialogs, "getText", lambda *a, **k: ("Untitled", True))
    monkeypatch.setattr(dialogs, "getMultiLineText", lambda *a, **k: ("", False))
    monkeypatch.setattr(dialogs, "getInt", lambda *a, **k: (0, False))

    config = app_config.AppConfig()
    assert config.data_dir.startswith(str(tmp_path))
    yield config
    tasks_io.invalidate_tasks_cache()
