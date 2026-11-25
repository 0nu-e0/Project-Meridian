"""
Tests for the expanded task card: saving, cancelling, checklist auto-save, due
dates, and work logs. Runs offscreen against a temporary data directory.
"""
import logging
import os
from datetime import datetime

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import QDate, Qt
from PyQt5.QtWidgets import QApplication, QListWidgetItem, QMessageBox

from ui.custom_widgets import dialogs

logger = logging.getLogger("test_task_card")


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def messages(monkeypatch):
    shown = []
    for name in ("warning", "critical", "information"):
        monkeypatch.setattr(dialogs, name, lambda *a, _n=name, **k: shown.append((_n, a[1])))
    monkeypatch.setattr(dialogs, "question", lambda *a, **k: QMessageBox.Yes)
    return shown


def saved_task(**fields):
    from models.task import Task
    from utils.tasks_io import save_task_to_json
    task = Task(title=fields.pop("title", "Saved task"), category="Bug")
    for name, value in fields.items():
        setattr(task, name, value)
    save_task_to_json(task, logger)
    return task


def open_card(app, task=None):
    from ui.task_files.task_card_expanded import TaskCardExpanded
    from utils.data_manager import DataManager
    if task is not None:
        task = DataManager(logger).get_task(task.id)
    card = TaskCardExpanded(logger=logger, task=task, grid_id="g")
    card.resize(1000, 800)
    return card


def on_disk(task_id):
    from utils.tasks_io import load_tasks_from_json
    return load_tasks_from_json(logger, force_reload=True).get(task_id)


def test_picked_due_date_is_a_datetime(app):
    card = open_card(app, saved_task())
    card.updateDueDate(QDate(2026, 3, 4))
    assert card.task.due_date == datetime(2026, 3, 4)


def test_new_task_has_no_due_date_shown(app):
    card = open_card(app)
    assert card.due_date_label.text() == "Select due date"
    assert card.task.due_date is None


def test_a_task_needs_a_title(app, messages):
    card = open_card(app)
    card.title_edit.setText("   ")
    card._handleSaveClick()
    assert messages and messages[-1] == ("warning", "Missing Title")
    assert card.isNewTask


def test_failed_save_keeps_the_card_open(app, messages, monkeypatch):
    card = open_card(app, saved_task())
    emitted = []
    card.newTaskUpdate.connect(lambda *a: emitted.append(a))
    monkeypatch.setattr(card.data_manager, "save_task", lambda task: False)
    card._perform_save(is_new_task=False)
    assert messages[-1] == ("critical", "Save Failed")
    assert emitted == []


def test_checklist_autosave_saves_only_the_checklist(app):
    task = saved_task(title="Before", checklist=[{"text": "step", "checked": False}])
    card = open_card(app, task)

    card.updateTaskTitle("Unsaved title edit")
    card.updateCheckboxState("step", True)
    card._debounced_save()

    disk = on_disk(task.id)
    assert disk.checklist == [{"text": "step", "checked": True}]
    assert disk.title == "Before"

    # Cancel undoes the title edit but keeps the already-saved checklist change
    card.cancelTaskChanges()
    assert card.task.title == "Before"
    assert card.task.checklist == [{"text": "step", "checked": True}]


def test_checklist_on_a_new_task_does_not_save_it_early(app):
    from utils.tasks_io import load_tasks_from_json
    card = open_card(app)
    card.addChecklistItem("first step")
    card._debounced_save()
    assert load_tasks_from_json(logger, force_reload=True) == {}


def test_cancel_restores_every_field(app):
    task = saved_task(title="Original", checklist=[{"text": "a", "checked": False}], tags={"x"})
    card = open_card(app, task)
    card.task.title = "Changed"
    card.task.category = "Feature"
    card.task.tags.add("y")
    card.task.checklist[0]["checked"] = True  # changed in place, like the checkbox does
    card.cancelTaskChanges()
    assert card.task.title == "Original"
    assert card.task.category_name == "Bug"
    assert card.task.tags == {"x"}
    assert card.task.checklist == [{"text": "a", "checked": False}]


def test_deleting_a_work_log_removes_its_hours(app, messages):
    card = open_card(app, saved_task())

    class Spin:
        def __init__(self, v): self.v = v
        def value(self): return self.v
        def setValue(self, v): self.v = v

    class Text:
        def __init__(self, t): self.t = t
        def text(self): return self.t
        def clear(self): self.t = ""

    card.add_work_log(Spin(2.5), Text("Wrote the report"))
    card.add_work_log(Spin(1.0), Text("Reviewed it"))
    assert card.task.actual_hours == 3.5

    entry = next(e for e in card.task.entries if e.content == "Wrote the report")
    item = QListWidgetItem()
    item.setData(Qt.UserRole, entry)
    card.delete_activity(item)

    assert card.task.actual_hours == 1.0
    assert [log.description for log in card.task.time_logs] == ["Reviewed it"]


def test_a_checklist_tick_just_before_cancel_is_kept(app):
    task = saved_task(checklist=[{"text": "step", "checked": False}])
    card = open_card(app, task)
    card.updateCheckboxState("step", True)   # debounce timer now running
    card.cancelTaskChanges()
    assert on_disk(task.id).checklist == [{"text": "step", "checked": True}]
    assert card.task.checklist == [{"text": "step", "checked": True}]


# ---------------------------------------------------------------- archiving by hand

def test_a_task_can_be_archived_without_completing(app):
    from models.task import Task, TaskStatus
    task = Task(title="Someday", category="Bug")
    task.status = TaskStatus.IN_PROGRESS
    task.set_archived_by_hand(True)
    assert task.archived and task.status == TaskStatus.IN_PROGRESS
    task.set_archived_by_hand(False)
    assert not task.archived


def test_archived_by_hand_is_saved(app):
    from models.task import Task, TaskStatus
    from utils.tasks_io import load_tasks_from_json, save_task_to_json
    task = Task(title="Someday", category="Bug")
    task.status = TaskStatus.IN_PROGRESS
    task.set_archived_by_hand(True)
    save_task_to_json(task, logger)
    loaded = load_tasks_from_json(logger, force_reload=True)[task.id]
    assert loaded.archived and loaded.archived_by_hand and loaded.status == TaskStatus.IN_PROGRESS


def test_older_files_keep_hand_archived_tasks_archived(app):
    from models.task import Task, TaskStatus
    data = Task(title="Old", category="Bug").to_dict()
    data.pop("archived_by_hand")
    data.update(archived=True, status=TaskStatus.IN_PROGRESS.value)
    task = Task.from_dict(data)
    assert task.archived_by_hand and task.archived


def test_completing_then_reopening_brings_a_hand_archived_task_back(app):
    from models.task import Task, TaskStatus
    task = Task(title="Someday", category="Bug")
    task.set_archived_by_hand(True)
    task.status = TaskStatus.COMPLETED
    task.update_archived()
    task.status = TaskStatus.IN_PROGRESS
    task.update_archived()
    assert not task.archived


def test_archive_button_in_the_task_card(app, monkeypatch):
    from models.task import Task, TaskStatus
    from ui.task_files.task_card_expanded import TaskCardExpanded
    task = Task(title="Someday", category="Bug")
    card = TaskCardExpanded(logger=logger, task=task)
    monkeypatch.setattr(card, "_handleSaveClick", lambda: None)
    assert card.archive_btn.text() == "🗄 Archive" and card.archive_btn.isEnabled()
    card.archive_btn.click()
    assert task.archived and card.archive_btn.text() == "↩ Unarchive"
    card.updateTaskStatus(TaskStatus.COMPLETED.value)
    assert not card.archive_btn.isEnabled()  # completed: archived automatically


def test_right_click_archive_on_the_dashboard(app):
    import main
    from models.task import Task
    from utils.tasks_io import load_tasks_from_json, save_task_to_json
    task = Task(title="Archive me", category="Bug")
    save_task_to_json(task, logger)
    window = main.MainWindow()
    dashboard = window.dashboard_screen
    dashboard.refreshDashboard()
    card = next(c for g in dashboard.grid_layouts for c in g.taskCards if c.task.id == task.id)
    card.archiveToggled.emit(card.task)
    assert load_tasks_from_json(logger, force_reload=True)[task.id].archived
    window.close()
