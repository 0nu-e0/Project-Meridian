"""
Tests for the mind map tabs (one per saved map), colouring shapes and lines, and the
app's own dialogs. Runs offscreen against a temporary data directory.
"""
import logging
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import QPointF, Qt
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication, QMessageBox, QPushButton

from ui.custom_widgets import dialogs

# The real dialog functions, kept before conftest swaps in automatic answers for each test
REAL = {name: getattr(dialogs, name) for name in ("question", "information")}

logger = logging.getLogger("test_mindmap_tabs_colors")


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def screen(app):
    from ui.mindmap_screen import MindMapScreen
    screen = MindMapScreen(logger=logger)
    screen.resize(1400, 900)
    screen.show()
    app.processEvents()
    yield screen
    screen.close()


def make_map(title, text="Idea"):
    from utils.mindmap_io import create_mindmap
    return create_mindmap(title, logger=logger,
                          nodes=[{"id": f"{title}-n", "text": text, "width": 170, "height": 70,
                                  "position": {"x": 0, "y": 0}}])


def listed(screen):
    """Titles in the Mind maps tab, in order"""
    from PyQt5.QtWidgets import QLabel
    titles = []
    for i in range(screen.mapList.list.count()):
        card = screen.mapList.list.itemWidget(screen.mapList.list.item(i))
        titles.append(card.findChildren(QLabel)[0].text())
    return titles


def click_map(screen, title):
    ids = screen.mapList.ids()
    from utils.mindmap_io import load_mindmaps_from_json
    maps = load_mindmaps_from_json(logger)
    (mindmap_id,) = [i for i in ids if maps[i].title == title]
    item = screen.mapList.list.item(ids.index(mindmap_id))
    screen.mapList.list.itemClicked.emit(item)


def node_texts(screen):
    from ui.custom_widgets.mindmap_nodes import NodeItem
    return [item.text_item.toPlainText() for item in screen.scene.items() if isinstance(item, NodeItem)]


# ---------------------------------------------------------------- the Mind maps tab

def test_the_left_panel_has_design_and_mind_maps_tabs(screen):
    tabs = screen.panelTabs
    assert [tabs.tabText(i) for i in range(tabs.count())] == ["Design", "Mind maps"]
    assert tabs.currentIndex() == 0


def test_the_list_shows_every_saved_map_newest_edit_first(screen):
    from utils.mindmap_io import update_mindmap
    roadmap = make_map("Roadmap")
    make_map("Ideas")
    update_mindmap(roadmap.id, title="Roadmap", logger=logger)  # edited last
    screen.refresh_list()
    assert listed(screen) == ["Roadmap", "Ideas"]
    assert screen.mapTitle.text() == "Untitled mind map"


def test_clicking_a_map_opens_it(screen):
    make_map("Roadmap", "Q1 goals")
    make_map("Ideas", "Dark mode")
    screen.refresh_list()
    click_map(screen, "Ideas")
    assert node_texts(screen) == ["Dark mode"]
    assert screen.mapTitle.text() == "Ideas"
    click_map(screen, "Roadmap")
    assert node_texts(screen) == ["Q1 goals"]


def test_switching_with_unsaved_changes_asks_first(screen, monkeypatch):
    make_map("Roadmap", "Q1 goals")
    make_map("Ideas", "Dark mode")
    screen.refresh_list()
    click_map(screen, "Roadmap")
    screen.add_node("rounded", QPointF(200, 0))
    screen.checkpoint()

    answers = [QMessageBox.Cancel]
    monkeypatch.setattr(dialogs, "ask_to_save", lambda *a, **k: answers.pop(0))
    click_map(screen, "Ideas")
    assert "Q1 goals" in node_texts(screen)  # stayed on Roadmap

    answers.append(QMessageBox.Discard)
    click_map(screen, "Ideas")
    assert node_texts(screen) == ["Dark mode"]


def test_an_unsaved_change_shows_a_dot_on_the_title(screen):
    make_map("Roadmap")
    screen.refresh_list()
    click_map(screen, "Roadmap")
    assert screen.mapTitle.text() == "Roadmap"
    screen.add_node("rounded", QPointF(200, 0))
    screen.checkpoint()
    assert screen.mapTitle.text() == "Roadmap  ●"
    screen.save_mind_map()
    assert screen.mapTitle.text() == "Roadmap"
    assert screen.savedLabel.text().startswith("Saved at")


def test_saving_a_new_map_names_it_and_lists_it(screen, monkeypatch):
    monkeypatch.setattr(dialogs, "ask_text", lambda *a, **k: ("Launch plan", True))
    screen.add_node("rounded", QPointF(0, 0))
    screen.save_mind_map()
    assert listed(screen) == ["Launch plan"]
    assert screen.mapTitle.text() == "Launch plan"


def test_new_mind_map_button(screen):
    make_map("Roadmap")
    screen.refresh_list()
    click_map(screen, "Roadmap")
    screen.mapList.newButton.click()
    assert node_texts(screen) == [] and screen.current_mindmap_id is None
    assert screen.mapTitle.text() == "Untitled mind map"


def test_search_filters_the_list(screen):
    make_map("Roadmap")
    make_map("Ideas")
    screen.refresh_list()
    screen.mapList.search.setText("road")
    hidden = [screen.mapList.list.item(i).isHidden() for i in range(screen.mapList.list.count())]
    assert sorted(hidden) == [False, True]


def test_rename_and_delete_from_the_list(screen, monkeypatch):
    roadmap = make_map("Roadmap")
    make_map("Ideas")
    screen.refresh_list()
    click_map(screen, "Roadmap")

    monkeypatch.setattr(dialogs, "ask_text", lambda *a, **k: ("2027 Roadmap", True))
    screen.rename_mindmap(roadmap.id)
    assert "2027 Roadmap" in listed(screen)
    assert screen.mapTitle.text() == "2027 Roadmap"

    screen.delete_mindmap(roadmap.id)  # it's the open one: the canvas starts fresh
    assert listed(screen) == ["Ideas"]
    assert node_texts(screen) == []


def test_cancelling_delete_keeps_the_map(screen, monkeypatch):
    roadmap = make_map("Roadmap")
    screen.refresh_list()
    monkeypatch.setattr(dialogs, "confirm", lambda *a, **k: False)
    screen.delete_mindmap(roadmap.id)
    assert "Roadmap" in listed(screen)


# ---------------------------------------------------------------- colours

def linked(screen):
    from ui.custom_widgets.mindmap_nodes import ConnectionItem
    first = screen.add_node("rounded", QPointF(-250, 0))
    second = screen.add_node("rounded", QPointF(250, 0))
    for node in (first, second):
        node.text_item.stopEditing()
    line = ConnectionItem(first, "right", second, "left")
    screen.scene.addItem(line)
    screen.scene.clearSelection()
    screen.checkpoint()
    return first, second, line


def test_swatches_are_off_until_something_is_selected(screen):
    first, second, line = linked(screen)
    assert not any(b.isEnabled() for b in screen.colorSwatches.buttons.values())
    first.setSelected(True)
    assert all(b.isEnabled() for b in screen.colorSwatches.buttons.values())
    assert screen.lineGreyButton.isHidden()  # only for lines
    line.setSelected(True)
    assert not screen.lineGreyButton.isHidden()


def test_a_swatch_colours_selected_shapes_and_lines(screen):
    first, second, line = linked(screen)
    first.setSelected(True)
    line.setSelected(True)
    screen.colorSwatches.buttons["Rose"].click()
    assert first.color == "#f43f5e" and line.color == "#f43f5e"
    assert second.color != "#f43f5e"

    screen.lineGreyButton.click()  # lines back to grey; shapes keep their colour
    assert line.color is None and first.color == "#f43f5e"


def test_line_colour_is_saved_and_undoable(screen, monkeypatch):
    first, second, line = linked(screen)
    line.setSelected(True)
    screen.colorSwatches.buttons["Green"].click()
    screen.save_mind_map()
    mindmap_id = screen.current_mindmap_id

    screen.clear_map()
    screen.load_mindmap_by_id(mindmap_id)
    from ui.custom_widgets.mindmap_nodes import ConnectionItem
    (reloaded,) = [item for item in screen.scene.items() if isinstance(item, ConnectionItem)]
    assert reloaded.color == "#22c55e"

    reloaded.setSelected(True)
    screen.colorSwatches.buttons["Indigo"].click()
    screen.undo()
    (restored,) = [item for item in screen.scene.items() if isinstance(item, ConnectionItem)]
    assert restored.color == "#22c55e"


def test_right_click_colours_a_line(screen):
    first, second, line = linked(screen)
    menu = screen.build_context_menu(line.path().pointAtPercent(0.5))
    colours = {a.text(): a for a in {a.text(): a for a in menu.actions()}["Colour"].menu().actions()}
    colours["Purple"].trigger()
    assert line.color == "#a855f7"
    colours["Standard grey"].trigger()
    assert line.color is None


# ---------------------------------------------------------------- the dialogs themselves

def buttons(dialog):
    return {b.text(): b for b in dialog.findChildren(QPushButton)}


def test_the_save_dialog_gives_each_answer(app):
    for label, expected in (("Save", QMessageBox.Save), ("Don't Save", QMessageBox.Discard),
                            ("Cancel", QMessageBox.Cancel)):
        dialog = dialogs.StyledDialog(None, "Save changes?", cancel_value=QMessageBox.Cancel)
        dialog.addButton("Don't Save", QMessageBox.Discard, dialogs.GHOST, left=True)
        dialog.addButton("Cancel", QMessageBox.Cancel)
        dialog.addButton("Save", QMessageBox.Save, dialogs.PRIMARY, default=True)
        dialog.show()
        buttons(dialog)[label].click()
        assert dialog.value == expected


def test_escape_cancels(app):
    dialog = dialogs.StyledDialog(None, "Save changes?", cancel_value=QMessageBox.Cancel)
    dialog.addButton("Save", QMessageBox.Save, dialogs.PRIMARY, default=True)
    dialog.show()
    QTest.keyClick(dialog, Qt.Key_Escape)
    assert dialog.value == QMessageBox.Cancel


def test_questions_get_clear_buttons(app, monkeypatch):
    seen = {}

    def answer_with(label):
        def ask(dialog):
            seen["buttons"] = sorted(buttons(dialog))
            buttons(dialog)[label].click()
            return dialog.value
        return ask

    monkeypatch.setattr(dialogs.StyledDialog, "ask", answer_with("Delete"))
    assert REAL["question"](None, "Delete Note", "Delete it?") == QMessageBox.Yes
    assert seen["buttons"] == ["Delete", "No"]  # "Delete", not a bare "Yes"

    monkeypatch.setattr(dialogs.StyledDialog, "ask", answer_with("No"))
    assert REAL["question"](None, "Delete Note", "Delete it?") == QMessageBox.No

    monkeypatch.setattr(dialogs.StyledDialog, "ask", answer_with("Yes"))
    assert REAL["question"](None, "Keep going?", "Continue?") == QMessageBox.Yes
    assert seen["buttons"] == ["No", "Yes"]

    monkeypatch.setattr(dialogs.StyledDialog, "ask", answer_with("OK"))
    assert REAL["information"](None, "Saved", "All done.") == QMessageBox.Ok
