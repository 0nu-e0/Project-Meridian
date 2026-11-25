"""
Tests for the Notes screen: a new note never overwrites another, deleting is
confirmed and final, and unsaved edits aren't silently thrown away.
Runs offscreen against a temporary data directory.
"""
import logging
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication, QMessageBox

logger = logging.getLogger("test_notes")


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def answers(monkeypatch):
    """Queue of answers for the app's questions; defaults to Yes"""
    from ui.custom_widgets import dialogs
    queue = []
    monkeypatch.setattr(dialogs, "question", lambda *a, **k: queue.pop(0) if queue else QMessageBox.Yes)
    monkeypatch.setattr(dialogs, "ask_to_save", lambda *a, **k: queue.pop(0) if queue else QMessageBox.Discard)
    monkeypatch.setattr(dialogs, "critical", lambda *a, **k: None)
    return queue


@pytest.fixture
def screen(app):
    from ui.notes_screen import NotesScreen
    return NotesScreen(logger=logger)


def stored():
    from utils.notes_io import load_notes_from_json
    return {note["title"]: note for note in load_notes_from_json(logger).values()}


def write(screen, title, body):
    screen.title_editor.setText(title)
    screen.editor.setPlainText(body)


def select(screen, title):
    item = next(screen.notes_list.item(i) for i in range(screen.notes_list.count())
                if screen.notes_list.item(i).text() == title)
    screen.loadSelectedNote(item)


def test_a_new_note_never_overwrites_the_previous_one(screen, answers):
    write(screen, "First", "first body")
    screen.saveCurrentNote()

    screen.createNewNote()
    write(screen, "Second", "second body")
    screen.saveCurrentNote()

    notes = stored()
    assert set(notes) == {"First", "Second"}
    assert "first body" in notes["First"]["content"]


def test_deleting_asks_and_clears_the_editor(screen, answers):
    write(screen, "Doomed", "x")
    screen.saveCurrentNote()

    answers.append(QMessageBox.No)
    screen.deleteCurrentNote()
    assert "Doomed" in stored()

    answers.append(QMessageBox.Yes)
    screen.deleteCurrentNote()
    assert stored() == {}
    assert screen.title_editor.text() == ""

    # Save afterwards starts a new note rather than reviving the deleted one
    write(screen, "Fresh", "y")
    screen.saveCurrentNote()
    assert set(stored()) == {"Fresh"}


def test_switching_notes_offers_to_save_unsaved_edits(screen, answers):
    write(screen, "A", "a")
    screen.saveCurrentNote()
    screen.createNewNote()
    write(screen, "B", "b")
    screen.saveCurrentNote()

    select(screen, "A")
    screen.editor.setPlainText("a edited")

    answers.append(QMessageBox.Cancel)
    select(screen, "B")
    assert screen.title_editor.text() == "A"  # stayed put

    answers.append(QMessageBox.Save)
    select(screen, "B")
    assert screen.title_editor.text() == "B"
    assert "a edited" in stored()["A"]["content"]


def test_loading_a_note_is_not_an_edit(screen, answers):
    write(screen, "Only", "body")
    screen.saveCurrentNote()
    screen.createNewNote()
    select(screen, "Only")
    assert screen._dirty is False
