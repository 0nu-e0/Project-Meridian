"""
Smoke test: the real main window, with some data, driven through every screen.

It clicks through the drawer, opens a task, a project and its Gantt chart, visits
every Settings section, and resizes the window, failing on any error, including
errors inside Qt signal handlers (which would otherwise end the whole process).
Runs offscreen against a temporary data directory.
"""
import logging
import os
import sys
import time
from datetime import datetime

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication, QMessageBox, QPushButton

from ui.custom_widgets import dialogs

logger = logging.getLogger("test_smoke")


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def pump(app, seconds=0.2):
    end = time.time() + seconds
    while time.time() < end:
        app.processEvents()


@pytest.fixture
def errors(monkeypatch):
    """Collect exceptions raised inside Qt handlers instead of letting them end the process"""
    caught = []
    monkeypatch.setattr(sys, "excepthook", lambda *exc: caught.append(exc))
    for name in ("information", "warning", "critical"):
        monkeypatch.setattr(dialogs, name, lambda *a, **k: None)
    monkeypatch.setattr(dialogs, "question", lambda *a, **k: QMessageBox.Discard)
    return caught


def seed():
    from models.task import Task, TaskPriority, TaskStatus
    from utils.mindmap_io import create_mindmap
    from utils.notes_io import save_note_to_json
    from models.note import Note
    from utils.projects_io import create_phase, create_project, move_task_to_phase, schedule_project
    from utils.tasks_io import save_task_to_json

    project = create_project("Smoke project", logger=logger)
    phase = create_phase(project.id, "Phase A", logger=logger)
    for i, (category, status) in enumerate([("Bug", TaskStatus.IN_PROGRESS), ("Feature", TaskStatus.BLOCKED),
                                            ("Widgets", TaskStatus.NOT_STARTED), ("Bug", TaskStatus.COMPLETED)]):
        task = Task(title=f"Task {i}", description="Something to do", category=category)
        task.status = status
        task.priority = list(TaskPriority)[i]
        task.due_date = datetime(2026, 10, 20 + i)
        task.checklist = [{"text": "first step", "checked": False}]
        save_task_to_json(task, logger)
        if i == 1:
            move_task_to_phase(task.id, phase.id, logger)
    schedule_project(project.id, datetime.now().strftime("%Y-%m-%d"), logger)
    save_note_to_json(Note(title="A note", content="Body"), logger)
    create_mindmap("A mindmap", nodes=[{"id": "n1", "text": "Idea", "width": 120, "height": 75,
                                        "position": {"x": 0, "y": 0}}], logger=logger)
    return project


def test_click_through_the_whole_app(app, errors):
    import main
    project = seed()
    w = main.MainWindow()
    w.resize(1400, 900)
    w.show()
    pump(app)

    drawer_buttons = {b.text(): b for b in w.drawer.findChildren(QPushButton) if b.text()}
    gear = next(b for b in w.drawer.findChildren(QPushButton) if not b.text())

    # Every screen from the drawer, including Settings
    for name in ["Dashboard", "Planning", "Projects", "Notes", "Mindmaps"]:
        w.toggleDrawer(); pump(app, 0.5)
        QTest.mouseClick(drawer_buttons[name], Qt.LeftButton); pump(app, 0.8)
        assert w.banner_header.text() == name
    w.toggleDrawer(); pump(app, 0.5)
    QTest.mouseClick(gear, Qt.LeftButton); pump(app, 0.8)
    assert w.stacked_widget.currentWidget() is w.settings_screen
    for section in range(4):
        w.settings_screen.showSection(section); pump(app, 0.1)

    # A task card from the Dashboard, opened and cancelled
    dashboard = w.dashboard_screen
    w.stacked_widget.setCurrentWidget(dashboard); dashboard.refreshDashboard(); pump(app)
    task = next(iter(dashboard.data_manager.get_tasks().values()))
    dashboard.openExpandedCardOverlay(task=task, grid_id="g"); pump(app)
    dashboard.expanded_card.cancelTaskChanges(); pump(app)

    # A new task, typed and saved
    dashboard.openExpandedCardOverlay(task=None); pump(app)
    dashboard.expanded_card.title_edit.setText("Made by the smoke test")
    dashboard.expanded_card._handleSaveClick(); pump(app, 0.3)
    assert any(t.title == "Made by the smoke test" for t in dashboard.data_manager.get_tasks().values())

    # A project, its Gantt chart, and back out again
    w.showProjectDetail(project.id); pump(app)
    w.showGanttChart(project.id); pump(app)
    w.returnFromGanttChart(project.id); pump(app)
    w.returnToProjectsScreen(); pump(app)

    # Planning views
    planning = w.planning_screen
    for view_id in (0, 2, 1):
        planning.view_group.button(view_id).setChecked(True)
        planning.switchView(planning.view_group.button(view_id)); pump(app, 0.1)

    # Window sizes from the minimum up to an ultrawide monitor
    for size in [(960, 640), (1920, 1080), (3840, 1600), (1400, 900)]:
        w.resize(*size); pump(app, 0.2)

    w.close()
    pump(app, 0.2)
    assert errors == [], "errors inside Qt handlers:\n" + "\n".join(f"{e[0].__name__}: {e[1]}" for e in errors)
