"""
Tests for the main window's navigation: the drawer, screen transitions, and the
Project Detail / Gantt views that are created and thrown away as you move around.

Runs the real MainWindow offscreen against a temporary data directory.
"""
import logging
import os
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import QPoint, Qt
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication, QDialog, QPushButton

logger = logging.getLogger("test_navigation")


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def pump(app, seconds=0.2):
    end = time.time() + seconds
    while time.time() < end:
        app.processEvents()


@pytest.fixture
def window(app):
    import main
    from utils.projects_io import create_project

    project = create_project("Nav project", logger=logger)
    w = main.MainWindow()
    w.resize(1400, 900)
    w.show()
    pump(app)
    w.test_project = project
    w.drawer_buttons = {b.text(): b for b in w.drawer.findChildren(QPushButton) if b.text()}
    w.base_view_count = w.stacked_widget.count()
    yield w
    w.close()
    w.deleteLater()
    pump(app, 0.1)


def open_drawer(app, w):
    if not w.drawer_open:
        w.toggleDrawer()
    pump(app, 0.6)


def extra_views(w):
    return w.stacked_widget.count() - w.base_view_count


def test_detail_and_gantt_views_do_not_pile_up(app, window):
    project_id = window.test_project.id
    for _ in range(3):
        window.showProjectDetail(project_id); pump(app)
        window.showGanttChart(project_id); pump(app)
        window.returnFromGanttChart(project_id); pump(app)
    assert extra_views(window) == 1  # just the detail view on screen

    window.returnToProjectsScreen(); pump(app)
    assert extra_views(window) == 0


def test_leaving_project_detail_through_the_drawer_discards_it(app, window):
    window.showProjectDetail(window.test_project.id); pump(app)
    open_drawer(app, window)
    QTest.mouseClick(window.drawer_buttons["Notes"], Qt.LeftButton)
    pump(app, 1.0)
    assert window.stacked_widget.currentWidget() is window.notes_screen
    assert extra_views(window) == 0


def test_last_drawer_click_wins(app, window):
    open_drawer(app, window)
    QTest.mouseClick(window.drawer_buttons["Dashboard"], Qt.LeftButton)
    QTest.mouseClick(window.drawer_buttons["Mindmaps"], Qt.LeftButton)
    pump(app, 1.2)
    assert window.stacked_widget.currentWidget() is window.mindmaps_screen
    assert window.banner_header.text() == "Mindmaps"
    # The slide moves screens sideways; they must end up back in place
    assert window.stacked_widget.currentWidget().pos() == QPoint(0, 0)


def test_clicking_in_a_dialog_leaves_the_drawer_open(app, window):
    open_drawer(app, window)
    dialog = QDialog(window)
    dialog.setGeometry(window.geometry().x() + 900, window.geometry().y() + 300, 300, 200)
    dialog.show(); pump(app)
    QTest.mouseClick(dialog, Qt.LeftButton, pos=QPoint(50, 50)); pump(app, 0.6)
    assert window.drawer_open
    dialog.close()


def test_opening_a_project_mid_slide_is_not_undone(app, window):
    from ui.project_files.project_detail_view import ProjectDetailView
    open_drawer(app, window)
    QTest.mouseClick(window.drawer_buttons["Projects"], Qt.LeftButton)
    pump(app, 0.45)  # drawer closed, slide still under way
    window.showProjectDetail(window.test_project.id)
    pump(app, 1.0)
    assert isinstance(window.stacked_widget.currentWidget(), ProjectDetailView)
