"""
Tests for the Gantt chart: dragging and resizing bars set the right dates, changes
save automatically, and the edit dialog only applies changes on Save.
Runs offscreen against a temporary data directory.
"""
import logging
import os
from datetime import datetime

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import QDate, QPointF
from PyQt5.QtWidgets import QApplication

from ui.custom_widgets import dialogs

logger = logging.getLogger("test_gantt")


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def chart_view(app, monkeypatch):
    from models.gantt_item import GanttChart, GanttChartItem
    from ui.gantt_chart_view import GanttChartView
    from utils.gantt_io import save_gantt_chart
    monkeypatch.setattr(dialogs, "warning", lambda *a, **k: None)

    chart = GanttChart("project-1")
    item = GanttChartItem("Build")
    item.start_date = datetime(2026, 3, 10)
    item.end_date = datetime(2026, 3, 20)
    chart.add_item(item)
    save_gantt_chart(chart, logger)

    view = GanttChartView("project-1", logger)
    view.resize(1200, 700)
    return view


def the_bar(view):
    from ui.gantt_chart_view import GanttBarItem
    return next(i for i in view.timeline.scene.items() if isinstance(i, GanttBarItem))


class FakeMouseEvent:
    """Stands in for QGraphicsSceneMouseEvent, which PyQt5 can't construct"""
    def __init__(self, scene_pos, press_pos, bar):
        self._scene = QPointF(*scene_pos)
        self._press = QPointF(*press_pos)
        self._pos = bar.mapFromScene(self._scene)

    def scenePos(self): return self._scene
    def pos(self): return self._pos
    def buttonDownScenePos(self, _button): return self._press
    def accept(self): pass


@pytest.fixture(autouse=True)
def no_base_mouse_handling(monkeypatch):
    # The bar's own resize logic is under test; Qt's base handlers can't take the fake event
    from PyQt5.QtWidgets import QGraphicsRectItem
    for name in ("mousePressEvent", "mouseMoveEvent", "mouseReleaseEvent"):
        monkeypatch.setattr(QGraphicsRectItem, name, lambda self, event: None)


def drag(bar, start, moves):
    """Press at start (scene coords), move through each x offset, release"""
    bar.mousePressEvent(FakeMouseEvent(start, start, bar))
    for dx in moves:
        bar.mouseMoveEvent(FakeMouseEvent((start[0] + dx, start[1]), start, bar))
    bar.mouseReleaseEvent(FakeMouseEvent((start[0] + moves[-1], start[1]), start, bar))


def saved_item():
    from utils.gantt_io import load_gantt_chart_for_project
    return load_gantt_chart_for_project("project-1", logger).items[0]


def test_resizing_the_right_edge_grows_by_the_mouse_distance(chart_view):
    bar = the_bar(chart_view)
    rect = bar.sceneBoundingRect()
    start = (rect.right() - 2, rect.center().y())

    # 3 pixels per day: 30 px is 10 days, however many moves it takes
    drag(bar, start, [6, 12, 18, 24, 30])
    item = saved_item()
    assert item.start_date.date() == datetime(2026, 3, 10).date()
    assert abs((item.end_date - datetime(2026, 3, 30)).total_seconds()) < 86400


def test_resizing_the_left_edge_keeps_the_right_edge(chart_view):
    bar = the_bar(chart_view)
    rect = bar.sceneBoundingRect()
    drag(bar, (rect.left() + 2, rect.center().y()), [-9, -15])  # 5 days earlier
    item = saved_item()
    assert abs((item.start_date - datetime(2026, 3, 5)).total_seconds()) < 86400
    assert abs((item.end_date - datetime(2026, 3, 20)).total_seconds()) < 86400


def test_moving_a_bar_shifts_both_dates(chart_view):
    bar = the_bar(chart_view)
    bar.setPos(bar.pos().x() + 30, bar.pos().y())  # what Qt does while dragging: 10 days later
    chart_view.timeline.updateItemDatesFromPosition(bar.gantt_item, bar)
    item = saved_item()
    assert abs((item.start_date - datetime(2026, 3, 20)).total_seconds()) < 86400
    assert abs((item.end_date - datetime(2026, 3, 30)).total_seconds()) < 86400


def test_text_fields_and_colour_change_only_on_save(chart_view, monkeypatch):
    from PyQt5.QtGui import QColor
    from PyQt5.QtWidgets import QColorDialog
    from ui.gantt_chart_view import GanttItemEditDialog
    item = chart_view.gantt_chart.items[0]
    monkeypatch.setattr(QColorDialog, "getColor", lambda *a, **k: QColor("#ff0000"))

    dialog = GanttItemEditDialog(item)
    dialog.pickColor()
    dialog.reject()
    assert item.color == "#3498db"

    dialog = GanttItemEditDialog(item)
    dialog.pickColor()
    dialog.save()
    assert item.color == "#ff0000"


def test_end_date_before_start_is_refused(chart_view):
    from ui.gantt_chart_view import GanttItemEditDialog
    item = chart_view.gantt_chart.items[0]
    dialog = GanttItemEditDialog(item)
    dialog.start_date_input.setDate(QDate(2026, 4, 10))
    dialog.end_date_input.setDate(QDate(2026, 4, 1))
    dialog.save()
    assert item.start_date == datetime(2026, 3, 10)
