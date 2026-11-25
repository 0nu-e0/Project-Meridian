"""
Tests for how tasks are displayed: the small Dashboard card, formatted
descriptions, the resizable task card, and the interface size setting.
Runs offscreen against a temporary data directory.
"""
import logging
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QTextListFormat
from PyQt5.QtWidgets import QApplication, QLabel, QTextEdit

logger = logging.getLogger("test_card_display")

LONG_TITLE = ("Thermo Scientific Reserve Chiller Operational Validation Test for the HI01 Validation Lab "
              "including electrical setup, coolant preparation, and low and high temperature performance")

PASTED = """Assigned To: Jeremy
Location: HI01 Validation Lab

Scope of Work
1. Equipment Identification and Inspection
Record the manufacturer, model number, serial number.

2. Electrical and Test Setup
Identify and verify an appropriate electrical connection."""


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def make_task(**fields):
    from models.task import Task
    task = Task(title=fields.pop("title", "A task"), category="Bug")
    for name, value in fields.items():
        setattr(task, name, value)
    return task


def nonblank_lines(text):
    return [line for line in text.splitlines() if line.strip()]


# ---------------------------------------------------------------- small card

def test_long_titles_are_cut_to_two_lines_with_the_full_title_on_hover(app):
    from ui.task_files.task_card_lite import TaskCardLite
    card = TaskCardLite(logger, make_task(title=LONG_TITLE))
    card.setCardWidth(300)
    shown = card.title_label.text()
    assert len(shown.splitlines()) == 2
    assert shown.endswith("…")
    assert card.title_label.toolTip() == LONG_TITLE


def test_the_small_card_no_longer_shows_completion(app):
    from ui.task_files.task_card_lite import TaskCardLite
    card = TaskCardLite(logger, make_task(percentage_complete=40))
    texts = [label.text() for label in card.compact_widget.findChildren(QLabel)]
    assert not any("%" in text for text in texts)


def test_card_height_fits_its_content(app):
    from ui.task_files.task_card_lite import TaskCardLite
    short = TaskCardLite(logger, make_task(title="Short"))
    long = TaskCardLite(logger, make_task(title=LONG_TITLE))
    for card in (short, long):
        card.setCardWidth(300)
    assert long.compact_height > short.compact_height
    assert short.height() == short.compact_height


def test_hover_preview_scrolls_long_descriptions(app):
    from ui.task_files.task_card_lite import DESCRIPTION_PREVIEW_MAX_HEIGHT, TaskCardLite
    card = TaskCardLite(logger, make_task(description=PASTED * 6))
    card.setCardWidth(320)
    assert card.desc_view.height() == DESCRIPTION_PREVIEW_MAX_HEIGHT
    assert card.desc_view.verticalScrollBar().maximum() > 0
    assert card.expanded_height > card.compact_height + DESCRIPTION_PREVIEW_MAX_HEIGHT - 1


# ---------------------------------------------------------------- formatted descriptions

def test_plain_descriptions_keep_every_line_through_a_save(app):
    from ui.custom_widgets.rich_text import load_description, save_description
    task = make_task(description=PASTED)  # older, plain-text description
    editor = QTextEdit()
    load_description(editor, task)
    save_description(editor, task)
    assert task.description_format == "markdown"

    reloaded = QTextEdit()
    load_description(reloaded, task)
    assert nonblank_lines(reloaded.toPlainText()) == nonblank_lines(PASTED)


def test_real_lists_survive_a_save(app):
    from ui.custom_widgets.rich_text import load_description, save_description
    editor = QTextEdit()
    editor.setPlainText("Record:")
    cursor = editor.textCursor()
    cursor.movePosition(cursor.End)
    for index, text in enumerate(["Initial fluid temperature.", "Requested temperature setpoint."]):
        cursor.insertBlock()
        if index == 0:
            list_format = QTextListFormat()
            list_format.setStyle(QTextListFormat.ListDisc)
            cursor.createList(list_format)
        cursor.insertText(text)

    task = make_task()
    save_description(editor, task)
    assert "- Initial fluid temperature." in task.description

    reloaded = QTextEdit()
    load_description(reloaded, task)
    assert reloaded.document().lastBlock().textList() is not None


def test_formatted_descriptions_are_saved_with_the_task(app):
    from utils.tasks_io import load_tasks_from_json, save_task_to_json
    task = make_task(description="- one\n- two", description_format="markdown")
    save_task_to_json(task, logger)
    loaded = load_tasks_from_json(logger, force_reload=True)[task.id]
    assert loaded.description_format == "markdown" and loaded.description == "- one\n- two"


# ---------------------------------------------------------------- expanded card

def test_task_card_sections_resize_and_are_remembered(app):
    from ui.task_files.task_card_expanded import TaskCardExpanded
    from utils.settings import Settings
    card = TaskCardExpanded(logger=logger, task=make_task(description=PASTED))
    card.resize(1200, 800)
    card.show()
    card.left_splitter.setSizes([600, 200])
    card._saveSplitterSizes()
    assert Settings.instance().get("task_card_layout")["last"]["left"][0] == pytest.approx(0.75, abs=0.02)

    another = TaskCardExpanded(logger=logger, task=make_task())
    another.resize(1200, 800)
    another.show()
    first, second = another.left_splitter.sizes()
    assert first / (first + second) == pytest.approx(0.75, abs=0.05)
    card.close(); another.close()


def test_opening_a_task_does_not_convert_its_description(app):
    from ui.task_files.task_card_expanded import TaskCardExpanded
    task = make_task(description=PASTED)
    TaskCardExpanded(logger=logger, task=task)
    assert task.description_format == "plain" and task.description == PASTED


def test_long_titles_open_at_their_start(app):
    from ui.task_files.task_card_expanded import TaskCardExpanded
    card = TaskCardExpanded(logger=logger, task=make_task(title=LONG_TITLE))
    assert card.title_edit.cursorPosition() == 0


# ---------------------------------------------------------------- interface size

def test_interface_size_setting(monkeypatch):
    from utils import display_scale
    monkeypatch.setattr(display_scale, "detect_auto_scale", lambda: 1.125)
    assert display_scale.interface_scale("auto") == 1.125
    assert display_scale.interface_scale(150) == 1.5
    assert display_scale.interface_scale("nonsense") == 1.0

    # setenv first so pytest restores the variable afterwards, whatever this test sets
    monkeypatch.setenv("QT_SCALE_FACTOR", "1")
    monkeypatch.delenv("QT_SCALE_FACTOR")
    display_scale.apply_interface_scale(125)
    assert os.environ["QT_SCALE_FACTOR"] == "1.25"

    # A value set by hand wins
    monkeypatch.setenv("QT_SCALE_FACTOR", "2")
    assert display_scale.apply_interface_scale(125) == 2.0


# ---------------------------------------------------------------- follow-ups

def test_clicking_the_description_opens_the_task(app):
    from PyQt5.QtCore import QPoint
    from PyQt5.QtTest import QTest
    from ui.task_files.task_card_lite import TaskCardLite
    card = TaskCardLite(logger, make_task(description=PASTED))
    card.setCardWidth(320)
    opened = []
    card.cardClicked.connect(lambda task, grid_id: opened.append(task))
    QTest.mouseClick(card.desc_view.viewport(), Qt.LeftButton, pos=QPoint(20, 20))
    assert opened == [card.task]


def test_badges_stay_put_while_the_card_shrinks_back(app):
    from ui.task_files.task_card_lite import TaskCardLite
    card = TaskCardLite(logger, make_task(title=LONG_TITLE, description=PASTED))
    card.setCardWidth(300)
    card.show()
    app.processEvents()
    compact_height = card.compact_widget.height()

    # Halfway through collapsing: details still showing, card already at compact height
    card.detail_container.setMaximumHeight(16777215)
    card.setFixedHeight(card.compact_height)
    app.processEvents()
    assert card.compact_widget.height() == compact_height
    card.close()


def test_task_card_handles_are_thin(app):
    from ui.task_files.task_card_expanded import TaskCardExpanded
    card = TaskCardExpanded(logger=logger, task=make_task())
    assert card.columns_splitter.handleWidth() <= 4
    assert card.left_splitter.handleWidth() <= 4


@pytest.mark.parametrize("width", [160, 240, 400])
def test_planning_cards_fit_their_column(app, width):
    from PyQt5.QtGui import QFontMetrics
    from ui.planning_screen import SCHEDULED_TITLE_MAX_LINES, ScheduledTaskCard
    task = make_task(title=LONG_TITLE)
    task.checklist = [{"text": "Record the manufacturer, model number and serial number", "checked": False}]
    card = ScheduledTaskCard(task, show_checklist=True)
    height = card.fitToWidth(width)
    card.resize(width, height)
    card.show()
    app.processEvents()

    title = card.title_label.text()
    assert 1 <= len(title.splitlines()) <= SCHEDULED_TITLE_MAX_LINES
    assert card.toolTip() == LONG_TITLE
    for label in [card.title_label] + [label for label, _ in card.detail_labels]:
        metrics = QFontMetrics(label.font())
        assert max(metrics.horizontalAdvance(line) for line in label.text().splitlines()) <= label.width()
        assert label.geometry().bottom() <= card.height()
    card.close()


def test_task_card_sizes_are_remembered_per_screen_size(app, monkeypatch):
    from ui.task_files.task_card_expanded import TaskCardExpanded

    def open_card(screen):
        monkeypatch.setattr(TaskCardExpanded, "_screenKey", lambda self: screen)
        card = TaskCardExpanded(logger=logger, task=make_task())
        card.resize(2400, 1000)  # wide enough that both columns can move freely
        card.show()
        return card

    def left_share(card):
        first, second = card.columns_splitter.sizes()
        return first / (first + second)

    big = open_card("3840x1600")
    big.columns_splitter.setSizes([1080, 1320])
    big._saveSplitterSizes()
    big.close()

    laptop = open_card("1920x1080")  # new size: starts from the latest layout
    assert left_share(laptop) == pytest.approx(0.45, abs=0.03)
    laptop.columns_splitter.setSizes([1560, 840])
    laptop._saveSplitterSizes()
    laptop.close()

    big = open_card("3840x1600")
    assert left_share(big) == pytest.approx(0.45, abs=0.03)
    big.close()
    laptop = open_card("1920x1080")
    assert left_share(laptop) == pytest.approx(0.65, abs=0.03)
    laptop.close()


def test_old_single_layouts_still_load(app):
    from ui.task_files.task_card_expanded import TaskCardExpanded
    from utils.settings import Settings
    Settings.instance().set("task_card_layout", {"columns": [0.45, 0.55], "left": [0.5, 0.5]})
    card = TaskCardExpanded(logger=logger, task=make_task())
    card.resize(2400, 1000)  # wide enough that both columns can move freely
    card.show()
    first, second = card.columns_splitter.sizes()
    assert first / (first + second) == pytest.approx(0.45, abs=0.03)
    card.close()


def test_collapsed_groups_show_an_arrow_and_count(app):
    from types import SimpleNamespace
    from PyQt5.QtWidgets import QLabel, QPushButton
    from ui.dashboard_screen import DashboardScreen
    grid = QLabel()  # stands in for a group's card grid
    grid.toggle_button, grid.collapsed_note = QPushButton(), QLabel()
    grid.visibleCards = [object(), object(), object()]
    screen = SimpleNamespace(_isCollapsed=DashboardScreen._isCollapsed)

    grid.hide()
    DashboardScreen._updateToggleButton(screen, grid)
    assert grid.toggle_button.text() == "▶" and not grid.toggle_button.isHidden()
    assert grid.collapsed_note.text() == "3 tasks" and not grid.collapsed_note.isHidden()

    grid.show()
    DashboardScreen._updateToggleButton(screen, grid)
    assert grid.toggle_button.text() == "▼" and grid.toggle_button.isHidden()
    assert grid.collapsed_note.isHidden()


def test_a_cleared_day_ignores_late_card_resizes(app):
    """Refreshing Planning deletes a day's rows before their cards; a card resized in
    between used to reach its deleted row and crash"""
    from PyQt5.QtCore import QDate, QSize
    from PyQt5.QtWidgets import QListWidgetItem
    from ui.planning_screen import DropZoneWidget, ScheduledTaskCard
    zone = DropZoneWidget(QDate.currentDate())
    zone.resize(300, 400)
    zone.show()
    card = ScheduledTaskCard(make_task(title=LONG_TITLE))
    item = QListWidgetItem()
    zone.task_list.addItem(item)
    zone.task_list.setItemWidget(item, card)
    zone._fitItem(item, card)

    zone.clearTasks()
    assert card.onHeightChanged is None
    card._fitted_width = None
    card.resize(QSize(120, 50))  # a late resize after the row is gone: no crash

    # Even with the hook still set, a deleted row is ignored rather than raising
    other = ScheduledTaskCard(make_task(title=LONG_TITLE))
    gone = QListWidgetItem()
    zone.task_list.addItem(gone)
    zone.task_list.setItemWidget(gone, other)
    zone._fitItem(gone, other)
    hook = other.onHeightChanged
    zone.task_list.clear()  # deletes the row
    other.onHeightChanged = hook
    other._reportHeight(200)
    assert other.onHeightChanged is None
