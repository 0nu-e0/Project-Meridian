"""
Tests for searching everything (tasks, projects, notes, mind maps) from the banner,
and for opening what's found. Runs offscreen against a temporary data directory.
"""
import logging
import os
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import QCoreApplication, QEvent, Qt
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication

logger = logging.getLogger("test_search")


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def pump(app, seconds=0.3):
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    end = time.time() + seconds
    while time.time() < end:
        app.processEvents()


@pytest.fixture
def data():
    """One of each kind, sharing the word "chiller" in different places"""
    from models.task import Task
    from utils.mindmap_io import create_mindmap
    from utils.notes_io import save_note_to_json
    from utils.projects_io import create_project
    from utils.tasks_io import save_task_to_json

    task = Task(title="Chiller validation", category="Bug")
    task.description = "Record the coolant temperature"
    save_task_to_json(task, logger)
    other = Task(title="Order parts", category="Feature")
    other.description = "Spare pump for the chiller"
    save_task_to_json(other, logger)
    project = create_project("Lab upgrade", description="Replace the old chiller", logger=logger)
    from models.note import Note
    note = Note("Meeting notes", "<html><head><style>p {}</style></head><body><p>Chiller arrives Monday</p></body></html>")
    note.id = "note-1"
    save_note_to_json(note, logger)
    mindmap = create_mindmap("Plant room", logger=logger, nodes=[
        {"id": "n1", "text": "Boiler", "width": 170, "height": 70, "position": {"x": 0, "y": 0}},
        {"id": "n2", "text": "Chiller loop", "width": 170, "height": 70, "position": {"x": 600, "y": 400}}])
    return {"task": task, "other": other, "project": project, "mindmap": mindmap}


# ---------------------------------------------------------------- finding

def test_finds_every_kind(app, data):
    from utils.search import search_everything
    found = {(r.kind, r.title) for r in search_everything("chiller", logger)}
    assert found == {("task", "Chiller validation"), ("task", "Order parts"), ("project", "Lab upgrade"),
                     ("note", "Meeting notes"), ("mindmap", "Plant room")}


def test_title_matches_come_first(app, data):
    from utils.search import search_everything
    tasks = [r.title for r in search_everything("chiller", logger) if r.kind == "task"]
    assert tasks == ["Chiller validation", "Order parts"]


def test_every_word_must_match(app, data):
    from utils.search import search_everything
    assert [r.title for r in search_everything("chiller coolant", logger)] == ["Chiller validation"]
    assert search_everything("chiller nonsense", logger) == []


def test_body_matches_show_where_they_matched(app, data):
    from utils.search import search_everything
    (part,) = [r for r in search_everything("pump", logger)]
    assert "Spare pump" in part.detail


def test_note_text_is_searched_without_its_formatting(app, data):
    from utils.search import search_everything
    assert [r.kind for r in search_everything("monday", logger)] == ["note"]
    assert search_everything("style", logger) == []  # the note's hidden style block isn't text


def test_mind_map_results_point_at_the_matching_shape(app, data):
    from utils.search import search_everything
    (result,) = [r for r in search_everything("chiller", logger) if r.kind == "mindmap"]
    assert result.extra["node_id"] == "n2"


def test_an_empty_query_finds_nothing(app, data):
    from utils.search import search_everything
    assert search_everything("   ", logger) == []


# ---------------------------------------------------------------- the search box

@pytest.fixture
def window(app, data):
    import main
    w = main.MainWindow()
    w.resize(1400, 900)
    w.show()
    pump(app)
    yield w
    w.close()


def type_search(app, window, text):
    window.global_search.focus()
    window.global_search.box.setText(text)
    window.global_search.run_search()
    pump(app, 0.05)


def test_typing_shows_grouped_results(app, window):
    type_search(app, window, "chiller")
    results = window.global_search.results
    assert results.isVisible()
    headers = [results.list.item(i).text() for i in range(results.list.count())
               if results.list.item(i).data(Qt.UserRole + 1)]
    assert headers == ["TASKS", "PROJECTS", "NOTES", "MIND MAPS"]
    assert results.current_result().title == "Chiller validation"  # first result ready for Enter


def test_arrow_keys_skip_headings(app, window):
    type_search(app, window, "chiller")
    box = window.global_search.box
    QTest.keyClick(box, Qt.Key_Down)
    assert window.global_search.results.current_result().title == "Order parts"
    QTest.keyClick(box, Qt.Key_Down)  # past the PROJECTS heading
    assert window.global_search.results.current_result().kind == "project"
    QTest.keyClick(box, Qt.Key_Up)
    assert window.global_search.results.current_result().title == "Order parts"


def test_escape_closes_then_clears(app, window):
    type_search(app, window, "chiller")
    box = window.global_search.box
    QTest.keyClick(box, Qt.Key_Escape)
    assert not window.global_search.results.isVisible() and box.text() == "chiller"
    QTest.keyClick(box, Qt.Key_Escape)
    assert box.text() == ""


def test_no_matches_says_so(app, window):
    type_search(app, window, "zebra")
    item = window.global_search.results.list.item(0)
    assert "No matches" in item.text() and window.global_search.results.current_result() is None


def test_ctrl_k_focuses_the_search(app, window):
    QTest.keyClick(window, Qt.Key_K, Qt.ControlModifier)
    assert window.global_search.box.hasFocus()


# ---------------------------------------------------------------- opening results

def test_enter_opens_a_task_card(app, window, data):
    type_search(app, window, "chiller validation")
    QTest.keyClick(window.global_search.box, Qt.Key_Return)
    pump(app)
    assert window.stacked_widget.currentWidget() is window.dashboard_screen
    assert window.dashboard_screen.expanded_card.task.id == data["task"].id
    assert not window.global_search.results.isVisible()


def test_opening_a_project(app, window, data):
    from ui.project_files.project_detail_view import ProjectDetailView
    from utils.search import PROJECT, Result
    window.openSearchResult(Result(PROJECT, data["project"].id, "Lab upgrade"))
    pump(app)
    view = window.stacked_widget.currentWidget()
    assert isinstance(view, ProjectDetailView) and view.project_id == data["project"].id


def test_opening_a_note(app, window):
    from utils.search import NOTE, Result
    window.openSearchResult(Result(NOTE, "note-1", "Meeting notes"))
    pump(app)
    assert window.stacked_widget.currentWidget() is window.notes_screen
    assert window.notes_screen.current_note_id == "note-1"


def test_opening_a_mind_map_shows_the_shape(app, window, data):
    from utils.search import MINDMAP, Result
    window.openSearchResult(Result(MINDMAP, data["mindmap"].id, "Plant room", extra={"node_id": "n2"}))
    pump(app)
    screen = window.mindmaps_screen
    assert window.stacked_widget.currentWidget() is screen
    assert screen.current_mindmap_id == data["mindmap"].id
    (selected,) = screen.scene.selectedItems()
    assert selected.id == "n2"
    visible = screen.view.mapToScene(screen.view.viewport().rect()).boundingRect()
    assert visible.contains(selected.sceneBoundingRect())  # in view (centred when the map is big enough to scroll)
