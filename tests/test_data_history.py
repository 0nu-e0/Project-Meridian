"""
Tests for undo / redo of saved changes on the Dashboard and Planning (Ctrl+Z, or
Undo on the notice). Runs offscreen against a temporary data directory.
"""
import logging
import os
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import QCoreApplication, QDate, QEvent, Qt
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication

logger = logging.getLogger("test_data_history")


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def pump(app, seconds=0.2):
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    end = time.time() + seconds
    while time.time() < end:
        app.processEvents()


def add_task(title, category="Bug"):
    from models.task import Task
    from utils.tasks_io import save_task_to_json
    task = Task(title=title, category=category)
    save_task_to_json(task, logger)
    return task


def tasks():
    from utils.tasks_io import load_tasks_from_json
    return load_tasks_from_json(logger, force_reload=True)


# ---------------------------------------------------------------- the history itself

def test_undo_puts_back_only_what_the_action_changed(app):
    from utils.data_history import history
    from utils.tasks_io import save_task_to_json
    first = add_task("First")
    second = add_task("Second")

    with history().action("Renamed First"):
        first.title = "First (renamed)"
        save_task_to_json(first, logger)
    second.title = "Second, edited later"  # not part of that action
    save_task_to_json(second, logger)

    assert history().undo() == "Renamed First"
    assert tasks()[first.id].title == "First"
    assert tasks()[second.id].title == "Second, edited later"  # kept

    assert history().redo() == "Renamed First"
    assert tasks()[first.id].title == "First (renamed)"


def test_undoing_an_add_removes_it_and_undoing_a_delete_brings_it_back(app):
    from utils.data_history import history
    from utils.tasks_io import delete_task_from_json
    with history().action("Added"):
        task = add_task("New one")
    history().undo()
    assert task.id not in tasks()
    history().redo()
    with history().action("Deleted"):
        delete_task_from_json(task.id, logger)
    history().undo()
    assert tasks()[task.id].title == "New one"


def test_an_action_that_changes_nothing_isnt_recorded(app):
    from utils.data_history import history
    with history().action("Nothing"):
        pass
    assert not history().canUndo()


def test_a_new_action_clears_redo(app):
    from utils.data_history import history
    with history().action("One"):
        add_task("One")
    history().undo()
    assert history().canRedo()
    with history().action("Two"):
        add_task("Two")
    assert not history().canRedo()


# ---------------------------------------------------------------- in the app

@pytest.fixture
def window(app):
    import main
    w = main.MainWindow()
    w.resize(1400, 900)
    w.show()
    pump(app)
    yield w
    w.close()


def test_planning_changes_can_be_undone(app, window):
    task = add_task("Plan me")
    planning = window.planning_screen
    window.showScreenNow("planning_screen")
    planning.refreshPlanningUI()
    planning.onTaskDropped(QDate.currentDate(), task.id, task.title)
    assert [st.task_id for st in planning.scheduled_tasks.values()] == [task.id]
    assert window.toast.isVisible() and "Plan me" in window.toast.label.text()

    QTest.keyClick(window, Qt.Key_Z, Qt.ControlModifier)
    pump(app)
    assert planning.scheduled_tasks == {}  # reloaded from the restored file
    assert window.toast.label.text().startswith("Undid: Scheduled")

    QTest.keyClick(window, Qt.Key_Y, Qt.ControlModifier)
    pump(app)
    assert [st.task_id for st in planning.scheduled_tasks.values()] == [task.id]


def test_a_deleted_task_comes_back(app, window):
    task = add_task("Delete me")
    dashboard = window.dashboard_screen
    window.showScreenNow("dashboard_screen")
    dashboard.openExpandedCardOverlay(task=tasks()[task.id], grid_id=None)
    dashboard.expanded_card.deleteTask()  # confirmation answered Yes by conftest
    pump(app)
    assert task.id not in tasks()
    assert window.toast.label.text() == "Deleted “Delete me”"

    window.toast.button.click()  # the notice's Undo
    pump(app)
    assert tasks()[task.id].title == "Delete me"
    assert any(c.task.id == task.id for g in dashboard.grid_layouts for c in g.taskCards)


def test_edits_in_a_task_card_are_one_step(app, window):
    task = add_task("Before")
    dashboard = window.dashboard_screen
    window.showScreenNow("dashboard_screen")
    dashboard.openExpandedCardOverlay(task=tasks()[task.id], grid_id=None)
    card = dashboard.expanded_card
    card.title_edit.setText("After")
    card._handleSaveClick()  # what the Save button does
    pump(app, 0.4)
    dashboard.closeExpandedCard()
    pump(app)
    assert tasks()[task.id].title == "After"

    window.undo()
    pump(app)
    assert tasks()[task.id].title == "Before"


def test_archiving_can_be_undone(app, window):
    task = add_task("Archive me")
    window.dashboard_screen.toggleTaskArchived(tasks()[task.id])
    assert tasks()[task.id].archived
    window.undo()
    assert not tasks()[task.id].archived


def test_nothing_to_undo_says_so(app, window):
    window.showScreenNow("dashboard_screen")
    window.undo()
    assert window.toast.label.text() == "Nothing to undo"


def test_ctrl_z_on_the_mind_map_uses_its_own_undo(app, window):
    from PyQt5.QtCore import QPointF
    window.showScreenNow("mindmaps_screen")
    screen = window.mindmaps_screen
    node = screen.add_node("rounded", QPointF(0, 0))
    node.text_item.stopEditing()
    screen.checkpoint()
    QTest.keyClick(window, Qt.Key_Z, Qt.ControlModifier)
    from ui.custom_widgets.mindmap_nodes import NodeItem
    assert not [item for item in screen.scene.items() if isinstance(item, NodeItem)]


# ---------------------------------------------------------------- guide, Ctrl+N, tooltips

def test_the_guide_covers_every_screen_and_shortcut(app):
    from ui.custom_widgets.guide import SECTIONS, SHORTCUTS, guide_html
    html = guide_html()
    for title, _ in SECTIONS:
        assert f"<h3>{title}</h3>" in html
    for keys, _ in SHORTCUTS:
        assert keys in html


def test_f1_opens_the_guide(app, window, monkeypatch):
    from ui.custom_widgets import dialogs
    shown = []
    monkeypatch.setattr(dialogs.StyledDialog, "ask", lambda dialog: shown.append(dialog.windowTitle()))
    QTest.keyClick(window, Qt.Key_F1)
    assert shown == ["Project Meridian, quickly"]


def test_ctrl_n_opens_a_new_task(app, window):
    window.showScreenNow("planning_screen")
    QTest.keyClick(window, Qt.Key_N, Qt.ControlModifier)
    pump(app)
    assert window.stacked_widget.currentWidget() is window.dashboard_screen
    assert window.dashboard_screen.expanded_card.isNewTask


def test_the_guide_is_offered_once(app, window):
    window.offerGuideOnce()
    assert window.toast.isVisible() and window.toast.button.text() == "Open guide"
    window.toast.hide()
    window.offerGuideOnce()
    assert not window.toast.isVisible()


def test_symbol_only_buttons_have_tooltips(app, window):
    from PyQt5.QtWidgets import QAbstractButton
    missing = [b.text() for b in window.findChildren(QAbstractButton)
               if b.text().strip() in ("?", "+", "-", "☰", "⋮", "▼", "▶", "✕", "") and b.isVisibleTo(window)
               and not b.toolTip() and b.icon().isNull() is False]
    assert missing == []
    assert window.toggle_drawer_button.toolTip() == "Menu"
