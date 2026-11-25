"""
Tests for the Planning screen: scheduling, moving between days, unscheduling, and
the drag data format. Runs offscreen against a temporary data directory.
"""
import logging
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import QDate, QMimeData
from PyQt5.QtWidgets import QApplication

logger = logging.getLogger("test_planning")


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def planning(app):
    from ui.planning_screen import PlanningScreen
    screen = PlanningScreen(logger=logger)
    screen.resize(1200, 800)
    yield screen
    screen.deleteLater()


def saved_task(title="Task"):
    from models.task import Task
    from utils.tasks_io import save_task_to_json
    task = Task(title=title, category="Bug")
    save_task_to_json(task, logger)
    return task


def schedule_on_disk():
    from utils.app_config import AppConfig
    from utils.safe_io import read_json
    return read_json(os.path.join(AppConfig().data_dir, "scheduled_tasks.json"))


class FakeDropEvent:
    def __init__(self, text):
        self.data = QMimeData()
        self.data.setText(text)
        self.accepted = False

    def mimeData(self):
        return self.data

    def acceptProposedAction(self):
        self.accepted = True


@pytest.mark.parametrize("text, expected", [
    ("id1|Plain title|task", ("id1", "Plain title", "", "task")),
    ("id1|A | B|project", ("id1", "A | B", "", "project")),
    ("id1|A | B|sched9|2026-01-05|task", ("id1", "A | B", "sched9", "task")),
    ("id1|Old two-part", ("id1", "Old two-part", "", "task")),
])
def test_drag_text_parsing(text, expected):
    from ui.planning_screen import parse_drag_text
    assert parse_drag_text(text) == expected


def test_a_task_is_only_scheduled_once_per_day(planning):
    task = saved_task()
    monday = QDate(2026, 1, 5)
    planning.onTaskDropped(monday, task.id, task.title)
    planning.onTaskDropped(monday, task.id, task.title)
    assert len(schedule_on_disk()) == 1


def test_moving_a_task_to_another_day(planning):
    task = saved_task()
    monday, tuesday = QDate(2026, 1, 5), QDate(2026, 1, 6)
    planning.onTaskDropped(monday, task.id, task.title)
    schedule_id = next(iter(planning.scheduled_tasks))

    planning.onScheduleMoved(tuesday, schedule_id, "task")
    assert [entry["date"] for entry in schedule_on_disk().values()] == ["2026-01-06"]

    # Moving onto a day that already has it merges the two
    planning.onTaskDropped(monday, task.id, task.title)
    planning.onScheduleMoved(monday, schedule_id, "task")
    assert [entry["date"] for entry in schedule_on_disk().values()] == ["2026-01-05"]


def test_dropping_a_scheduled_task_on_another_day_moves_it(planning):
    from ui.planning_screen import DropZoneWidget
    task = saved_task("Title | with pipe")
    monday = QDate(2026, 1, 5)
    planning.onTaskDropped(monday, task.id, task.title)
    schedule_id = next(iter(planning.scheduled_tasks))

    zone = DropZoneWidget(QDate(2026, 1, 7))
    zone.scheduleMoved.connect(planning.onScheduleMoved)
    event = FakeDropEvent(f"{task.id}|{task.title}|{schedule_id}|2026-01-05|task")
    zone.dropEvent(event)
    assert event.accepted
    assert [entry["date"] for entry in schedule_on_disk().values()] == ["2026-01-07"]


def test_dragging_within_the_task_list_does_not_unschedule_anything(planning):
    task = saved_task()
    planning.onTaskDropped(QDate(2026, 1, 5), task.id, task.title)
    planning.onTaskDropped(QDate(2026, 1, 6), task.id, task.title)

    planning.task_list.dropEvent(FakeDropEvent(f"{task.id}|{task.title}|task"))
    assert len(schedule_on_disk()) == 2

    # Dropping one scheduled copy back on the list removes just that copy
    schedule_id = next(iter(planning.scheduled_tasks))
    planning.task_list.dropEvent(FakeDropEvent(f"{task.id}|{task.title}|{schedule_id}|2026-01-05|task"))
    assert len(schedule_on_disk()) == 1


def test_projects_are_scheduled_once_per_day_and_can_move(planning):
    from utils.projects_io import create_project, load_scheduled_projects, move_scheduled_project, schedule_project
    project = create_project("P", logger=logger)
    first = schedule_project(project.id, "2026-01-05", logger)
    assert schedule_project(project.id, "2026-01-05", logger) == first
    assert len(load_scheduled_projects(logger)) == 1

    assert move_scheduled_project(first, "2026-01-08", logger)
    assert load_scheduled_projects(logger)[first]["scheduled_date"] == "2026-01-08"


def test_clicking_outside_an_open_task_discards_unsaved_edits(planning):
    from PyQt5.QtCore import QEvent, QPointF, Qt
    from PyQt5.QtGui import QMouseEvent
    task = saved_task("Original")
    planning.loadTasks()
    planning.showTaskDetail(planning.getTaskById(task.id))
    planning.task_detail_dialog.task.title = "Half-typed"

    press = QMouseEvent(QEvent.MouseButtonPress, QPointF(1, 1), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
    planning.eventFilter(planning.task_overlay, press)
    assert planning.task_detail_dialog is None
    assert planning.getTaskById(task.id).title == "Original"
