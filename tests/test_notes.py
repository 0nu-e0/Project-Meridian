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
    monkeypatch.setattr(dialogs, "confirm", lambda *a, **k: (queue.pop(0) if queue else QMessageBox.Yes) == QMessageBox.Yes)
    monkeypatch.setattr(dialogs, "ask_to_save", lambda *a, **k: queue.pop(0) if queue else QMessageBox.Discard)
    monkeypatch.setattr(dialogs, "critical", lambda *a, **k: None)
    return queue


@pytest.fixture
def screen(app):
    from PyQt5 import sip
    from ui.notes_screen import NotesScreen
    screen = NotesScreen(logger=logger)
    yield screen
    # Delete it now, rather than whenever Python's garbage collector gets to it
    sip.delete(screen)


def stored():
    from utils.notes_io import load_notes_from_json
    return {note["title"]: note for note in load_notes_from_json(logger).values()}


def write(screen, title, body):
    screen.title_editor.setText(title)
    screen.editor.setPlainText(body)


def listed(screen, visible_only=False):
    """Titles in the list, top to bottom"""
    from ui.notes_screen import TITLE_ROLE
    return [item.data(TITLE_ROLE) for item in screen.noteList.items()
            if not (visible_only and item.isHidden())]


def select(screen, title):
    from ui.notes_screen import TITLE_ROLE
    item = next(item for item in screen.noteList.items() if item.data(TITLE_ROLE) == title)
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


def test_deleting_can_be_undone(screen, answers):
    from utils.data_history import history
    write(screen, "Keep me", "precious")
    screen.saveCurrentNote()

    screen.deleteCurrentNote()
    assert stored() == {}
    assert history().undoLabel() == "Deleted note \u201cKeep me\u201d"

    history().undo()
    screen.reloadFromStorage()
    assert "precious" in stored()["Keep me"]["content"]
    assert listed(screen) == ["Keep me"]


def test_newest_edit_is_listed_first(screen, answers, monkeypatch):
    import utils.notes_io as notes_io
    from datetime import datetime

    class Clock(datetime):
        now_value = datetime(2026, 1, 1, 9, 0, 0)

        @classmethod
        def now(cls, tz=None):
            return cls.now_value

    monkeypatch.setattr(notes_io, "datetime", Clock)
    for hour, title in ((9, "Old"), (10, "Middle"), (11, "New")):
        Clock.now_value = datetime(2026, 1, 1, hour)
        screen.createNewNote()
        write(screen, title, title)
        screen.saveCurrentNote()
    assert listed(screen) == ["New", "Middle", "Old"]

    # Editing an old note moves it to the top
    Clock.now_value = datetime(2026, 1, 1, 12)
    select(screen, "Old")
    screen.editor.setPlainText("changed")
    screen.saveCurrentNote()
    assert listed(screen) == ["Old", "New", "Middle"]


def test_search_matches_titles_and_text(screen, answers):
    for title, body in (("Groceries", "milk and eggs"), ("Work", "call the plumber")):
        screen.createNewNote()
        write(screen, title, body)
        screen.saveCurrentNote()

    screen.noteList.search.setText("plumb")
    assert listed(screen, visible_only=True) == ["Work"]
    screen.noteList.search.setText("GROC")
    assert listed(screen, visible_only=True) == ["Groceries"]
    screen.noteList.search.setText("nothing like this")
    assert listed(screen, visible_only=True) == []
    assert not screen.noteList.noMatches.isHidden()
    screen.noteList.search.clear()
    assert sorted(listed(screen, visible_only=True)) == ["Groceries", "Work"]


def test_renaming_keeps_the_text_and_unsaved_state(screen, answers, monkeypatch):
    from ui.custom_widgets import dialogs
    write(screen, "Draft", "body")
    screen.saveCurrentNote()
    note_id = screen.current_note_id

    monkeypatch.setattr(dialogs, "ask_text", lambda *a, **k: ("Final", True))
    screen.renameNote(note_id)
    assert set(stored()) == {"Final"}
    assert "body" in stored()["Final"]["content"]
    assert screen.title_editor.text() == "Final"
    assert screen._dirty is False


def test_unsaved_edits_are_marked(screen, answers):
    write(screen, "Marked", "x")
    screen.saveCurrentNote()
    assert "Saved at" in screen.statusLabel.text()

    screen.editor.setPlainText("y")
    assert "Unsaved" in screen.statusLabel.text()
    assert screen.noteList.list.itemWidget(screen.noteList.items()[0]).findChildren(
        type(screen.statusLabel))[0].text().endswith("●")


def test_old_black_text_is_made_readable(screen, answers):
    from utils.notes_io import save_note_to_json
    from models.note import Note
    note = Note(title="Old", content='<p><span style="color:#000000;">dark</span> '
                                     '<span style="color:#e74c3c;">red</span></p>')
    save_note_to_json(note, logger)
    screen.updateNotesList()
    select(screen, "Old")

    def colour_of(word):
        from PyQt5.QtGui import QTextDocument
        cursor = screen.editor.document().find(word, 0, QTextDocument.FindCaseSensitively)
        cursor.setPosition(cursor.selectionStart() + 1)
        return cursor.charFormat()

    assert not colour_of("dark").hasProperty(colour_of("dark").ForegroundBrush)
    assert colour_of("red").foreground().color().name() == "#e74c3c"
    assert screen._dirty is False


def test_pasted_dark_text_is_made_readable_and_undoes_in_one_step(screen, answers):
    from PyQt5.QtCore import QMimeData
    data = QMimeData()
    data.setHtml('<span style="color:#111111;">pasted</span>')
    screen.editor.insertFromMimeData(data)

    fmt = screen.editor.document().begin().begin().fragment().charFormat()
    assert not fmt.hasProperty(fmt.ForegroundBrush)
    screen.editor.undo()
    assert screen.editor.toPlainText() == ""
