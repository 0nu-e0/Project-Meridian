import logging
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.tasks_io import save_task_to_json, load_tasks_from_json, invalidate_tasks_cache
from utils.app_config import AppConfig
from models.task import Task


def test_save_and_load_team_members(tmp_path, monkeypatch):
    logger = logging.getLogger("test")
    app_config = AppConfig()
    # redirect tasks_file to temporary path
    temp_file = tmp_path / "saved_tasks.json"
    monkeypatch.setattr(app_config, "tasks_file", str(temp_file), raising=False)
    monkeypatch.setattr(AppConfig, "_instance", app_config, raising=False)
    invalidate_tasks_cache()

    task = Task(title="Team Task")
    task.collaborators = {"alice", "bob"}

    assert save_task_to_json(task, logger)

    # Tasks are keyed by ID, not title
    tasks = load_tasks_from_json(logger)
    assert task.id in tasks
    loaded_task = tasks[task.id]
    assert loaded_task.collaborators == {"alice", "bob"}
