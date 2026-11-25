"""
Tests for Settings: saved values, colours, and each behaviour setting reaching the
screen it controls, plus category management. Runs offscreen against a temporary
data directory.
"""
import logging
import os
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication, QMessageBox, QPushButton

from ui.custom_widgets import dialogs

logger = logging.getLogger("test_settings")


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def pump(app, seconds=0.2):
    end = time.time() + seconds
    while time.time() < end:
        app.processEvents()


@pytest.fixture
def make_window(app, monkeypatch):
    monkeypatch.setattr(dialogs, "information", lambda *a, **k: None)
    windows = []

    def make():
        import main
        w = main.MainWindow()
        w.resize(1400, 900)
        w.show()
        pump(app)
        windows.append(w)
        return w

    yield make
    for w in windows:
        w.close()
        w.deleteLater()
    pump(app, 0.1)


def settings():
    from utils.settings import Settings
    return Settings.instance()


def test_settings_are_saved_and_reloaded():
    from utils.settings import Settings
    settings().set("planning_show_weekends", True)
    settings().set_color("accent", "#112233")
    Settings._instance = None
    assert settings().get("planning_show_weekends") is True
    assert settings().color_overrides() == {"accent": "#112233"}


def test_colour_overrides_apply_and_bad_values_are_ignored(monkeypatch):
    from resources.styles import AppColors
    from utils.settings import apply_color_overrides, default_color
    monkeypatch.setattr(AppColors, "accent", AppColors.accent)
    monkeypatch.setattr(AppColors, "danger", AppColors.danger)
    original_danger = AppColors.danger

    settings().set("colors", {"accent": "#abcdef", "danger": "not a colour", "no_such_colour": "#000000"})
    apply_color_overrides()
    assert AppColors.accent == "#abcdef"
    assert AppColors.danger == original_danger
    assert default_color("accent") == "#3498db"


def test_startup_screen(make_window):
    settings().set("startup_screen", "planning_screen")
    w = make_window()
    assert w.stacked_widget.currentWidget() is w.planning_screen
    assert w.banner_header.text() == "Planning"


def test_weekends_in_the_weekly_view_follow_the_setting(make_window):
    w = make_window()
    assert len(w.planning_screen.weekly_view.drop_zones) == 5
    settings().set("planning_show_weekends", True)
    assert len(w.planning_screen.weekly_view.drop_zones) == 7


def test_planning_default_view(make_window):
    settings().set("planning_default_view", "monthly")
    w = make_window()
    assert w.planning_screen.current_view == "monthly"


def test_archived_group_can_be_hidden(app, make_window):
    from models.task import Task, TaskStatus
    from utils.tasks_io import save_task_to_json
    done = Task(title="Done", category="Bug")
    done.status = TaskStatus.COMPLETED
    save_task_to_json(done, logger)

    w = make_window()
    w.dashboard_screen.refreshDashboard(); pump(app)
    assert any(g.grid_title == "Archived" for g in w.dashboard_screen.grid_layouts)

    settings().set("dashboard_show_archived", False); pump(app)
    assert not any(g.grid_title == "Archived" for g in w.dashboard_screen.grid_layouts)


def test_mindmap_grid_defaults(make_window):
    settings().set("mindmap_show_grid", False)
    settings().set("mindmap_snap_to_grid", False)
    w = make_window()
    assert w.mindmaps_screen.scene.grid_visible is False
    assert w.mindmaps_screen.scene.snap_to_grid is False

    settings().set("mindmap_show_grid", True)
    assert w.mindmaps_screen.scene.grid_visible is True


def test_new_tasks_use_the_chosen_category(app):
    from ui.task_files.task_card_expanded import TaskCardExpanded
    settings().set("new_task_category", "Research")
    card = TaskCardExpanded(logger=logger)
    assert card.task.category_name == "Research"


def test_the_gear_opens_settings(app, make_window):
    w = make_window()
    w.toggleDrawer(); pump(app, 0.6)
    gear = next(b for b in w.drawer.findChildren(QPushButton) if not b.text())
    QTest.mouseClick(gear, Qt.LeftButton); pump(app, 1.0)
    assert w.stacked_widget.currentWidget() is w.settings_screen
    assert w.banner_header.text() == "Settings"


def test_renaming_a_category_renames_it_everywhere():
    from models.task import Task
    from utils.categories_config import CategoriesConfigManager, rename_category_everywhere
    from utils.dashboard_config import DashboardConfigManager
    from utils.project_dashboard_sync import ensure_category_groups_exist
    from utils.tasks_io import load_tasks_from_json, save_task_to_json
    CategoriesConfigManager.add_category("Widgets")
    task = Task(title="Uses widgets", category="Widgets")
    save_task_to_json(task, logger)
    ensure_category_groups_exist([task], logger)

    assert rename_category_everywhere("Widgets", "Gadgets", logger)
    assert "Gadgets" in CategoriesConfigManager.load_categories()
    assert "Widgets" not in CategoriesConfigManager.load_categories()
    assert load_tasks_from_json(logger, force_reload=True)[task.id].category_name == "Gadgets"
    grid, = DashboardConfigManager.get_all_grid_layouts()
    assert grid.filter.category == ["Gadgets"] and grid.name == "Gadgets"


def test_settings_screen_category_buttons(app, monkeypatch):
    from models.task import Task
    from ui.settings_screen import SettingsScreen
    from utils.categories_config import CategoriesConfigManager
    from utils.tasks_io import load_tasks_from_json, save_task_to_json
    shown = []
    monkeypatch.setattr(dialogs, "information", lambda *a, **k: shown.append(a[1]))
    monkeypatch.setattr(dialogs, "question", lambda *a, **k: QMessageBox.Yes)
    screen = SettingsScreen(logger)

    # Add, refusing duplicates
    monkeypatch.setattr(dialogs, "getText", lambda *a, **k: ("Lab Work", True))
    screen.addCategory()
    screen.addCategory()
    assert CategoriesConfigManager.load_categories().count("Lab Work") == 1
    assert shown[-1] == "Already Exists"

    # Removing keeps tasks that use it
    task = Task(title="T", category="Lab Work")
    save_task_to_json(task, logger)
    screen.refreshCategories(select="Lab Work")
    screen.removeCategory()
    assert "Lab Work" not in CategoriesConfigManager.load_categories()
    assert load_tasks_from_json(logger, force_reload=True)[task.id].category_name == "Lab Work"

    # Archived is protected
    screen.refreshCategories(select="Archived")
    screen.removeCategory()
    assert "Archived" in CategoriesConfigManager.load_categories()
    assert shown[-1] == "Can't Remove"
