"""
Tests for clearing a task's due date, editing a work log's hours, and removing
items from a Gantt chart. Runs offscreen against a temporary data directory.
"""
import logging
import os
from datetime import datetime

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMessageBox

from ui.custom_widgets import dialogs

logger = logging.getLogger("test_due_dates_worklogs_gantt")


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def make_task(**fields):
    from models.task import Task
    task = Task(title=fields.pop("title", "A task"), category="Bug")
    for name, value in fields.items():
        setattr(task, name, value)
    return task


# ---------------------------------------------------------------- due date

def test_a_due_date_can_be_cleared(app):
    from ui.task_files.task_card_expanded import TaskCardExpanded
    task = make_task(due_date=datetime(2026, 10, 20))
    card = TaskCardExpanded(logger=logger, task=task)
    assert not card.clear_due_date_button.isHidden()

    card.clear_due_date_button.click()
    assert task.due_date is None
    assert card.due_date_label.text() == "Select due date"
    assert card.clear_due_date_button.isHidden()
    assert task.to_dict()["due_date"] is None


def test_the_clear_button_is_hidden_without_a_due_date(app):
    from ui.task_files.task_card_expanded import TaskCardExpanded
    card = TaskCardExpanded(logger=logger, task=make_task())
    assert card.clear_due_date_button.isHidden()


# ---------------------------------------------------------------- work logs

def logged_card(hours=2):
    from PyQt5.QtWidgets import QLineEdit, QSpinBox
    from ui.task_files.task_card_expanded import TaskCardExpanded
    card = TaskCardExpanded(logger=logger, task=make_task())
    hours_input, description = QSpinBox(), QLineEdit()
    hours_input.setValue(hours)
    description.setText("Set up the chiller")
    card.add_work_log(hours_input, description)
    return card


def work_log_item(card):
    return card.work_logs_list.item(0)


def test_editing_a_work_log_changes_its_hours(app, monkeypatch):
    from ui.task_files.task_card_expanded import WorkLogDialog
    card = logged_card(hours=2)
    assert card.task.actual_hours == 2

    monkeypatch.setattr(WorkLogDialog, "edit", classmethod(lambda cls, parent, text, hours: ("Set up and tested", 3.5)))
    card.edit_activity(work_log_item(card))

    assert card.task.actual_hours == 3.5
    assert card.task.time_logs[0].hours == 3.5
    assert card.task.time_logs[0].description == "Set up and tested"
    assert card.task.entries[0].content == "Set up and tested"


def test_cancelling_a_work_log_edit_changes_nothing(app, monkeypatch):
    from ui.task_files.task_card_expanded import WorkLogDialog
    card = logged_card(hours=2)
    monkeypatch.setattr(WorkLogDialog, "edit", classmethod(lambda cls, parent, text, hours: None))
    card.edit_activity(work_log_item(card))
    assert card.task.actual_hours == 2 and card.task.entries[0].content == "Set up the chiller"


def test_work_logs_show_their_hours(app):
    from PyQt5.QtWidgets import QLabel
    card = logged_card(hours=2)
    widget = card.work_logs_list.itemWidget(work_log_item(card))
    assert any(label.text().startswith("2 h") for label in widget.findChildren(QLabel))


def test_the_work_log_dialog_returns_both_values(app):
    from ui.task_files.task_card_expanded import WorkLogDialog
    dialog = WorkLogDialog(None, "Calibrate", 1.0)
    dialog.description_edit.setPlainText("Calibrate twice")
    dialog.hours_input.setValue(1.75)
    assert dialog.values() == ("Calibrate twice", 1.75)


# ---------------------------------------------------------------- Gantt

def gantt_with_items(*titles):
    from models.gantt_item import GanttChart, GanttChartItem
    from ui.gantt_chart_view import GanttTimeline
    chart = GanttChart("project-1")
    for order, title in enumerate(titles):
        item = GanttChartItem(title)
        item.start_date, item.end_date = datetime(2026, 10, 1), datetime(2026, 10, 10)
        item.order = order
        chart.add_item(item)
    return GanttTimeline(chart)


def test_removing_a_gantt_item(app):
    timeline = gantt_with_items("Design", "Build", "Test")
    changed = []
    timeline.itemsChanged.connect(lambda: changed.append(True))

    timeline.removeItem(timeline.gantt_chart.items[1], confirm=False)
    assert [item.title for item in timeline.gantt_chart.items] == ["Design", "Test"]
    assert [item.order for item in timeline.gantt_chart.items] == [0, 1]
    assert changed  # saved by the view


def test_rows_map_to_their_items(app):
    timeline = gantt_with_items("Design", "Build")
    assert timeline.itemAtRow(60 + 10).title == "Design"
    assert timeline.itemAtRow(60 + timeline.row_height + 10).title == "Build"
    assert timeline.itemAtRow(20) is None  # header
    assert timeline.itemAtRow(60 + 5 * timeline.row_height) is None


def test_delete_key_removes_the_selected_bar(app, monkeypatch):
    from PyQt5.QtTest import QTest
    from ui.gantt_chart_view import GanttBarItem
    monkeypatch.setattr(dialogs, "question", lambda *args, **kwargs: QMessageBox.Yes)
    timeline = gantt_with_items("Design", "Build")
    bar = next(item for item in timeline.scene.items()
               if isinstance(item, GanttBarItem) and item.gantt_item.title == "Build")
    bar.setSelected(True)
    QTest.keyClick(timeline, Qt.Key_Delete)
    assert [item.title for item in timeline.gantt_chart.items] == ["Design"]


def test_the_edit_dialog_can_remove(app, monkeypatch):
    from ui.gantt_chart_view import GanttItemEditDialog
    monkeypatch.setattr(dialogs, "question", lambda *args, **kwargs: QMessageBox.Yes)
    monkeypatch.setattr(GanttItemEditDialog, "exec_", lambda self: GanttItemEditDialog.REMOVE)
    timeline = gantt_with_items("Design", "Build")
    timeline.editItem(timeline.gantt_chart.items[0])
    assert [item.title for item in timeline.gantt_chart.items] == ["Build"]
