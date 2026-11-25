"""
Tests for the Dashboard: groups stay in sync with projects and categories, filters
are remembered, and closing a task without saving really discards the edits.

Runs the real MainWindow offscreen against a temporary data directory.
"""
import logging
import os
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import QPoint, Qt
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication, QLabel, QMessageBox, QPushButton

from ui.custom_widgets import dialogs

logger = logging.getLogger("test_dashboard")


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def pump(app, seconds=0.2):
    end = time.time() + seconds
    while time.time() < end:
        app.processEvents()


@pytest.fixture
def make_window(app, monkeypatch):
    # Message boxes would block the test run
    shown = []
    monkeypatch.setattr(dialogs, "information", lambda *a, **k: shown.append(a[1:3]))
    monkeypatch.setattr(dialogs, "question", lambda *a, **k: QMessageBox.Yes)
    windows = []

    def make():
        import main
        w = main.MainWindow()
        w.resize(1400, 900)
        w.show()
        w.stacked_widget.setCurrentWidget(w.dashboard_screen)
        pump(app)
        w.messages = shown
        windows.append(w)
        return w

    yield make
    for w in windows:
        w.close()
        w.deleteLater()
    pump(app, 0.1)


def group_titles(dashboard):
    titles = []
    for grid in dashboard.grid_layouts:
        header = grid.parent().layout().itemAt(0).widget()
        titles.append(next(label.text() for label in header.findChildren(QLabel)))
    return sorted(titles)


def save_task(title, **fields):
    from models.task import Task
    from utils.tasks_io import save_task_to_json
    task = Task(title=title, category=fields.pop("category", "Bug"))
    for name, value in fields.items():
        setattr(task, name, value)
    save_task_to_json(task, logger)
    return task


def test_new_and_renamed_projects_show_up_without_a_restart(app, make_window):
    from utils.projects_io import create_project, load_projects_from_json, save_projects_to_json
    w = make_window()
    dashboard = w.dashboard_screen

    project = create_project("Fresh project", logger=logger)
    save_task("Project task", project_id=project.id)
    dashboard.refreshDashboard(); pump(app)
    assert "📦 Fresh project" in group_titles(dashboard)
    assert dashboard.project_filter_combo.findData(project.id) >= 0

    projects = load_projects_from_json(logger)
    projects[project.id].title = "Renamed project"
    save_projects_to_json(projects, logger)
    dashboard.refreshDashboard(); pump(app)
    assert "📦 Renamed project" in group_titles(dashboard)

    projects = load_projects_from_json(logger)
    projects[project.id].archived = True
    save_projects_to_json(projects, logger)
    dashboard.refreshDashboard(); pump(app)
    assert not any(title.startswith("📦") for title in group_titles(dashboard))
    assert dashboard.project_filter_combo.findData(project.id) == -1


def test_task_count_and_cards_update_when_returning_to_the_dashboard(app, make_window):
    save_task("First")
    w = make_window()
    assert w.dashboard_screen.card_count_label.text() == "Current Task Count: 1"

    w.stacked_widget.setCurrentWidget(w.notes_screen); pump(app)
    save_task("Saved on another screen")
    w.toggleDrawer(); pump(app, 0.6)
    dashboard_button = next(b for b in w.drawer.findChildren(QPushButton) if b.text() == "Dashboard")
    QTest.mouseClick(dashboard_button, Qt.LeftButton); pump(app, 1.0)

    titles = {card.task.title for grid in w.dashboard_screen.grid_layouts for card in grid.taskCards}
    assert titles == {"First", "Saved on another screen"}
    assert w.dashboard_screen.card_count_label.text() == "Current Task Count: 2"


def test_group_filters_are_remembered(app, make_window):
    from models.task import TaskStatus
    save_task("Blocked one", status=TaskStatus.BLOCKED)
    save_task("Open one")
    w = make_window()
    grid = w.dashboard_screen.grid_layouts[0]
    grid.filter_button.filtersChanged.emit({"status": ["Blocked"], "category": ["Bug"], "due": []})
    pump(app)

    w.dashboard_screen.refreshDashboard(); pump(app)
    grid = w.dashboard_screen.grid_layouts[0]
    assert [card.task.title for card in grid.visibleCards] == ["Blocked one"]


def test_clicking_outside_an_open_task_discards_unsaved_edits(app, make_window):
    task = save_task("Original title")
    w = make_window()
    dashboard = w.dashboard_screen
    dashboard.openExpandedCardOverlay(task=dashboard.data_manager.get_task(task.id), grid_id="g"); pump(app)

    # The card edits the shared task object as you type
    dashboard.expanded_card.task.title = "Half-typed edit"
    QTest.mouseClick(dashboard.overlay, Qt.LeftButton, pos=QPoint(5, 5)); pump(app)

    assert dashboard.expanded_card is None
    assert dashboard.data_manager.get_task(task.id).title == "Original title"


def test_removing_a_group_that_still_has_tasks_explains_instead(app, make_window):
    from utils.dashboard_config import DashboardConfigManager
    save_task("Keeps the Bug group alive")
    w = make_window()
    grid_id = w.dashboard_screen.grid_layouts[0].grid_id

    w.dashboard_screen.removeGridSection(grid_id); pump(app)
    assert w.messages and w.messages[-1][0] == "Group Has Tasks"
    assert any(g.id == grid_id for g in DashboardConfigManager.get_all_grid_layouts())


def test_an_open_task_follows_window_resizes(app, make_window):
    task = save_task("Resize me")
    w = make_window()
    dashboard = w.dashboard_screen
    dashboard.openExpandedCardOverlay(task=dashboard.data_manager.get_task(task.id), grid_id="g"); pump(app)

    w.resize(1800, 1000); pump(app)
    assert dashboard.dialog_container.geometry() == w.rect()
    assert dashboard.overlay.geometry() == dashboard.dialog_container.rect()
    card = dashboard.expanded_card.geometry()
    assert abs(card.center().x() - w.rect().center().x()) <= 1
    assert abs(card.center().y() - w.rect().center().y()) <= 1


def test_filter_menu_lists_custom_categories(app, make_window):
    from ui.custom_widgets.filter_image import FilterButton
    from utils.categories_config import CategoriesConfigManager
    CategoriesConfigManager.add_category("Configured Extra")
    save_task("Uses an unlisted category", category="Only On A Task")
    make_window()
    categories = FilterButton.availableCategories(selected=["Picked Earlier"])
    assert "Bug" in categories and "Configured Extra" in categories
    assert "Only On A Task" in categories and "Picked Earlier" in categories
