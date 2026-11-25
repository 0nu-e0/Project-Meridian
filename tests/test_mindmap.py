"""
Tests for mindmaps: connections between nodes survive a save and reload.
Runs offscreen against a temporary data directory.
"""
import logging
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication, QMessageBox

from ui.custom_widgets import dialogs

logger = logging.getLogger("test_mindmap")


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def screen(app, monkeypatch):
    from ui.mindmap_screen import MindMapScreen
    monkeypatch.setattr(dialogs, "information", lambda *a, **k: None)
    monkeypatch.setattr(dialogs, "warning", lambda *a, **k: None)
    monkeypatch.setattr(dialogs, "ask_text", lambda *a, **k: ("Plan", True))
    return MindMapScreen(logger=logger)


def connections_in(screen):
    from ui.custom_widgets.mindmap_nodes import ConnectionItem
    return [(c.start_node.id, c.start_handle, c.end_node.id, c.end_handle)
            for c in screen.scene.items() if isinstance(c, ConnectionItem)]


def test_connections_survive_save_and_reload(screen):
    from ui.custom_widgets.mindmap_nodes import ConnectionItem, NodeItem
    first = NodeItem(text="First", logger=logger)
    second = NodeItem(text="Second", logger=logger)
    second.setPos(300, 0)
    for node in (first, second):
        screen.scene.addItem(node)
    screen.scene.addItem(ConnectionItem(first, "right", second, "left"))

    screen.save_mind_map()
    mindmap_id = screen.current_mindmap_id
    expected = connections_in(screen)

    screen.clear_map()
    assert connections_in(screen) == []

    screen.load_mindmap_by_id(mindmap_id)
    assert connections_in(screen) == expected == [(first.id, "right", second.id, "left")]


def test_a_connection_to_a_missing_node_is_skipped(screen):
    from utils.mindmap_io import create_mindmap
    mindmap = create_mindmap(
        "Partial",
        nodes=[{"id": "n1", "text": "Only", "width": 120, "height": 80, "position": {"x": 0, "y": 0}}],
        connections=[{"from": "n1", "from_handle": "right", "to": "gone", "to_handle": "left"}],
        logger=logger,
    )
    screen.load_mindmap_by_id(mindmap.id)
    assert connections_in(screen) == []


def test_loading_or_starting_fresh_offers_to_save_first(screen, monkeypatch):
    from ui.custom_widgets.mindmap_nodes import NodeItem
    answers = []
    monkeypatch.setattr(dialogs, "ask_to_save", lambda *a, **k: answers.pop(0))

    assert not screen.has_unsaved_changes()
    screen.scene.addItem(NodeItem(text="Unsaved", logger=logger))
    assert screen.has_unsaved_changes()

    answers.append(QMessageBox.Cancel)
    screen.new_mind_map()
    assert screen.has_unsaved_changes()  # kept

    answers.append(QMessageBox.Save)
    screen.new_mind_map()  # saves as "Plan" (stubbed title), then clears
    from utils.mindmap_io import load_mindmaps_from_json
    assert [m.title for m in load_mindmaps_from_json(logger).values()] == ["Plan"]
    assert not screen.has_unsaved_changes()


def test_a_freshly_loaded_mindmap_has_no_unsaved_changes(screen):
    from utils.mindmap_io import create_mindmap
    mindmap = create_mindmap(
        "Loaded",
        nodes=[{"id": "n1", "text": "Only", "width": 120, "height": 75, "position": {"x": 0, "y": 0}}],
        logger=logger,
    )
    screen.load_mindmap_by_id(mindmap.id)
    assert not screen.has_unsaved_changes()
