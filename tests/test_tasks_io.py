import logging
import os
import sys
import types

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Provide minimal PyQt5 stubs for Task import
qtcore = types.ModuleType("PyQt5.QtCore")
qtcore.QObject = object
qtcore.pyqtSignal = lambda *args, **kwargs: None
sys.modules.setdefault("PyQt5", types.ModuleType("PyQt5"))
sys.modules["PyQt5.QtCore"] = qtcore

from utils.tasks_io import save_task_to_json, load_tasks_from_json
from utils.app_config import AppConfig
from models.task import Task


def test_save_and_load_team_members(tmp_path, monkeypatch):
    logger = logging.getLogger("test")
    app_config = AppConfig()
    # redirect tasks_file to temporary path
    temp_file = tmp_path / "saved_tasks.json"
    monkeypatch.setattr(app_config, "tasks_file", str(temp_file), raising=False)
    monkeypatch.setattr(AppConfig, "_instance", app_config, raising=False)

    task = Task(title="Team Task")
    task.collaborators = {"alice", "bob"}

    assert save_task_to_json(task, logger)

    tasks = load_tasks_from_json(logger)
    assert "Team Task" in tasks
    loaded_task = tasks["Team Task"]
    assert loaded_task.collaborators == {"alice", "bob"}
