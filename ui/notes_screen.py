# -----------------------------------------------------------------------------
# Project Meridian
# Copyright (c) 2025 Jereme Shaver
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# -----------------------------------------------------------------------------
# File: notes_screen.py
# Description: Used to create and edit personal notes.
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

from datetime import datetime
from uuid import uuid4

from PyQt5.QtCore import QPoint, Qt, pyqtSignal
from PyQt5.QtGui import QKeySequence, QTextCharFormat, QTextCursor, QTextDocument
from PyQt5.QtWidgets import (QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMenu,
                             QMessageBox, QPushButton, QShortcut, QSizePolicy, QTextEdit, QVBoxLayout, QWidget)

from models.note import Note
from resources.styles import AppColors
from ui.custom_widgets import dialogs
from ui.custom_widgets.panel_styles import (CARD_LIST_STYLE, EMPTY_HINT_STYLE, MENU_STYLE, PANEL_BUTTON_STYLE,
                                            PRIMARY_BUTTON_STYLE, SEARCH_BOX_STYLE)
from ui.custom_widgets.rich_text import text_area_style
from ui.custom_widgets.text_edit_toolbar import TextEditToolbar
from utils.constants import MAIN_PANEL_STRETCH, SIDE_PANEL_STRETCH
from utils.data_history import history
from utils.notes_io import delete_note_from_json, load_notes_from_json, rename_note_in_json, save_note_to_json

DATE_FORMAT = '%Y-%m-%d, %H:%M:%S'
TITLE_ROLE = Qt.UserRole + 1   # the note's title
SEARCH_ROLE = Qt.UserRole + 2  # title and text, lower case, for the search box

TITLE_STYLE = f"""
    QLineEdit {{ background: transparent; color: {AppColors.text_primary}; border: none;
                 border-bottom: 2px solid transparent; padding: 2px 2px 4px 2px; font-size: 20px; font-weight: bold; }}
    QLineEdit:hover {{ border-bottom-color: {AppColors.surface_hover_alt}; }}
    QLineEdit:focus {{ border-bottom-color: {AppColors.accent}; }}"""
EDITOR_STYLE = text_area_style() + "QTextEdit { font-size: 13px; padding: 12px; }"


def _parse_date(text):
    try:
        return datetime.strptime(text, DATE_FORMAT)
    except (TypeError, ValueError):
        return None


def _short_date(when):
    return when.strftime("%b %d").replace(" 0", " ") if when else ""


def _clock(when):
    return when.strftime('%I:%M %p').lstrip('0')


def note_plain_text(note):
    """A saved note's text without formatting"""
    document = QTextDocument()
    document.setHtml(note.get("content", "") or "")
    return document.toPlainText()


def clear_dark_text(document):
    """Let text marked black (or nearly) take the editor's own light colour instead, so
    notes from the old white editor, or pasted from a white web page, stay readable"""
    dark = []  # (start, end, format): collected first, as changing formats reshapes the fragments
    block = document.begin()
    while block.isValid():
        iterator = block.begin()
        while not iterator.atEnd():
            fragment = iterator.fragment()
            fmt = fragment.charFormat()
            if fmt.hasProperty(QTextCharFormat.ForegroundBrush) and fmt.foreground().color().lightness() < 80:
                dark.append((fragment.position(), fragment.position() + fragment.length(), fmt))
            iterator += 1
        block = block.next()
    if not dark:
        return
    cursor = QTextCursor(document)
    if document.isUndoAvailable():
        cursor.joinPreviousEditBlock()  # e.g. a paste: one Undo takes back both
    else:
        cursor.beginEditBlock()
    for start, end, fmt in dark:
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.KeepAnchor)
        fmt.clearForeground()
        cursor.setCharFormat(fmt)
    cursor.endEditBlock()


class NoteEditor(QTextEdit):
    """The note's text. Pasted text keeps its formatting, but not a dark colour."""

    def insertFromMimeData(self, source):
        super().insertFromMimeData(source)
        if source.hasHtml():
            clear_dark_text(self.document())


def _edited(note):
    return _parse_date(note.get("modified_date")) or _parse_date(note.get("creation_date"))


class NoteList(QWidget):
    """The saved notes, newest edit first: click one to open it, right-click for more"""
    openRequested = pyqtSignal(str)  # note id
    menuRequested = pyqtSignal(str, QPoint)  # note id, global position

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.newButton = QPushButton("+  New note")
        self.newButton.setToolTip("Start a new note")
        self.newButton.setCursor(Qt.PointingHandCursor)
        self.newButton.setStyleSheet(PANEL_BUTTON_STYLE + PRIMARY_BUTTON_STYLE)
        layout.addWidget(self.newButton)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search notes")
        self.search.setClearButtonEnabled(True)
        self.search.setStyleSheet(SEARCH_BOX_STYLE)
        self.search.textChanged.connect(self._filter)
        layout.addWidget(self.search)

        self.list = QListWidget()
        self.list.setSpacing(3)
        self.list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list.setStyleSheet(CARD_LIST_STYLE)
        self.list.itemClicked.connect(lambda item: self.openRequested.emit(item.data(Qt.UserRole)))
        self.list.customContextMenuRequested.connect(self._menu)
        layout.addWidget(self.list, 1)

        self.empty = QLabel("No notes yet.\nWrite one on the right and press Save.")
        self.empty.setWordWrap(True)
        self.empty.setAlignment(Qt.AlignCenter)
        self.empty.setStyleSheet(EMPTY_HINT_STYLE)
        layout.addWidget(self.empty)

        self.noMatches = QLabel("No notes match your search.")
        self.noMatches.setWordWrap(True)
        self.noMatches.setAlignment(Qt.AlignCenter)
        self.noMatches.setStyleSheet(EMPTY_HINT_STYLE)
        layout.addWidget(self.noMatches)
        layout.addStretch(0)  # takes the space only while the list is hidden
        self._previews = []  # (label, full text), elided to the list's width

    def populate(self, notes, current_id, unsaved):
        """notes: (id, note dict) pairs, in the order to show them"""
        self.list.clear()
        self._previews = []
        for note_id, note in notes:
            title = note.get("title") or "Untitled"
            text = note_plain_text(note)
            preview = next((line.strip() for line in text.splitlines() if line.strip()), "")

            item = QListWidgetItem()
            item.setData(Qt.UserRole, note_id)
            item.setData(TITLE_ROLE, title)
            item.setData(SEARCH_ROLE, f"{title}\n{text}".lower())
            item.setToolTip(title)

            card = QWidget()
            card.setAttribute(Qt.WA_TransparentForMouseEvents)  # clicks go to the list item
            card.setStyleSheet("background: transparent;")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(10, 7, 10, 7)
            card_layout.setSpacing(2)
            current = note_id == current_id
            title_label = QLabel(title + ("  ●" if current and unsaved else ""))
            title_label.setStyleSheet(f"color: {AppColors.text_primary}; font-size: 13px; font-weight: bold;")
            card_layout.addWidget(title_label)
            if preview:
                preview_label = QLabel(preview)
                preview_label.setStyleSheet(f"color: {AppColors.text_muted}; font-size: 12px;")
                preview_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
                card_layout.addWidget(preview_label)
                self._previews.append((preview_label, preview))
            edited = _short_date(_edited(note))
            meta = QLabel("  ·  ".join(part for part in ("Open now" if current else "",
                                                          f"Edited {edited}" if edited else "") if part))
            meta.setStyleSheet(f"color: {AppColors.accent if current else AppColors.text_faint}; font-size: 11px;")
            meta.setVisible(bool(meta.text()))
            card_layout.addWidget(meta)

            self.list.addItem(item)
            item.setSizeHint(card.sizeHint())
            self.list.setItemWidget(item, card)
            if current:
                item.setSelected(True)
                self.list.setCurrentItem(item)
        self.list.setVisible(bool(notes))
        self.empty.setVisible(not notes)
        self._elidePreviews()
        self._filter(self.search.text())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._elidePreviews()

    def _elidePreviews(self):
        width = self.list.viewport().width() - 34  # the card's margins and border
        for label, text in self._previews:
            label.setText(label.fontMetrics().elidedText(text, Qt.ElideRight, max(width, 40)))

    def items(self):
        return [self.list.item(i) for i in range(self.list.count())]

    def _filter(self, text):
        text = text.strip().lower()
        shown = 0
        for item in self.items():
            hidden = bool(text) and text not in item.data(SEARCH_ROLE)
            item.setHidden(hidden)
            shown += not hidden
        self.noMatches.setVisible(bool(text) and self.list.count() > 0 and shown == 0)

    def _menu(self, pos):
        item = self.list.itemAt(pos)
        if item is not None:
            self.menuRequested.emit(item.data(Qt.UserRole), self.list.viewport().mapToGlobal(pos))


class NotesScreen(QWidget):

    def __init__(self, logger, parent=None):
        super().__init__(parent)
        self.logger = logger

        # The note in the editors; None means a new note not saved yet
        self.current_note_id = None
        # True once the editors differ from what was last loaded or saved
        self._dirty = False
        self._saved_at = None  # when this note was last saved here, for the status line

        self.initUI()
        QShortcut(QKeySequence.Save, self, self.saveCurrentNote)
        self.updateNotesList()
        self._updateStatus()

    # -- layout -----------------------------------------------------------------
    def initUI(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFixedHeight(2)
        main_layout.addWidget(separator)

        panel_widget = QWidget()
        panel_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        panel_layout = QHBoxLayout(panel_widget)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.addLayout(self.initLeftPanel(), SIDE_PANEL_STRETCH)
        panel_layout.addLayout(self.initRightPanel(), MAIN_PANEL_STRETCH)
        main_layout.addWidget(panel_widget)

    def initLeftPanel(self):
        self.noteList = NoteList()
        self.noteList.newButton.clicked.connect(self.createNewNote)
        self.noteList.openRequested.connect(self.openNote)
        self.noteList.menuRequested.connect(self.showNoteMenu)
        # Kept for callers that walk the list (e.g. opening a search result)
        self.notes_list = self.noteList.list

        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 5, 15)
        layout.addWidget(self.noteList)
        return layout

    def initRightPanel(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)

        self.title_editor = QLineEdit()
        self.title_editor.setPlaceholderText("Untitled note")
        self.title_editor.setStyleSheet(TITLE_STYLE)
        self.title_editor.textChanged.connect(self._markDirty)
        layout.addWidget(self.title_editor)

        self.statusLabel = QLabel()
        self.statusLabel.setStyleSheet(f"color: {AppColors.text_muted}; font-size: 11px; padding-left: 3px;")
        layout.addWidget(self.statusLabel)

        self.editor = NoteEditor()
        self.editor.setAcceptRichText(True)
        self.editor.setPlaceholderText("Start writing…")
        self.editor.setStyleSheet(EDITOR_STYLE)
        self.editor.textChanged.connect(self._markDirty)

        toolbar_row = QHBoxLayout()
        toolbar_row.setSpacing(6)
        self.toolbar = TextEditToolbar(self.editor)
        toolbar_row.addWidget(self.toolbar)
        toolbar_row.addStretch(1)

        self.deleteButton = QPushButton("Delete")
        self.deleteButton.setToolTip("Delete this note")
        self.deleteButton.setStyleSheet(PANEL_BUTTON_STYLE)
        self.deleteButton.clicked.connect(self.deleteCurrentNote)
        self.saveButton = QPushButton("Save")
        self.saveButton.setToolTip("Save this note (Ctrl+S)")
        self.saveButton.setStyleSheet(PANEL_BUTTON_STYLE + PRIMARY_BUTTON_STYLE)
        self.saveButton.clicked.connect(self.saveCurrentNote)
        for button in (self.deleteButton, self.saveButton):
            button.setCursor(Qt.PointingHandCursor)
            toolbar_row.addWidget(button)

        layout.addLayout(toolbar_row)
        layout.addWidget(self.editor, 1)
        return layout

    # -- state --------------------------------------------------------------------
    def _markDirty(self):
        if self._dirty:
            return
        self._dirty = True
        self._updateStatus()
        self.updateNotesList()  # shows ● on the open note

    def _setEditors(self, title, html):
        """Fill the editors without counting it as an edit"""
        self.title_editor.blockSignals(True)
        self.editor.blockSignals(True)
        self.title_editor.setText(title)
        if html:
            self.editor.setHtml(html)
            clear_dark_text(self.editor.document())
            self.editor.document().clearUndoRedoStacks()  # opening a note isn't an edit to undo
        else:
            self.editor.clear()
        self.editor.setCurrentCharFormat(QTextCharFormat())
        self.title_editor.blockSignals(False)
        self.editor.blockSignals(False)
        self.toolbar.syncToCursor()
        self._dirty = False
        self._saved_at = None

    def _updateStatus(self):
        if self._dirty:
            text, color = "●  Unsaved changes", AppColors.accent
        elif self._saved_at is not None:
            text, color = f"Saved at {_clock(self._saved_at)}", AppColors.text_muted
        elif self.current_note_id is None:
            text, color = "New note · press Save (Ctrl+S) to keep it", AppColors.text_muted
        else:
            note = self.loadNotes().get(self.current_note_id, {})
            edited = _edited(note)
            text = f"Edited {_short_date(edited)}, {_clock(edited)}" if edited else ""
            color = AppColors.text_muted
        self.statusLabel.setText(text)
        self.statusLabel.setStyleSheet(f"color: {color}; font-size: 11px; padding-left: 3px;")
        self.deleteButton.setEnabled(self.current_note_id is not None or self._dirty)

    def _confirmDiscardChanges(self):
        """Ask what to do with unsaved edits. Returns False if the user cancels."""
        if not self._dirty:
            return True
        reply = dialogs.ask_to_save(self, "note", self.title_editor.text().strip() or None)
        if reply == QMessageBox.Cancel:
            return False
        if reply == QMessageBox.Save:
            return self.saveCurrentNote()
        return True

    def confirm_discard_changes(self):
        """Offer to save unsaved edits (used when the app closes)"""
        return self._confirmDiscardChanges()

    # -- the list -------------------------------------------------------------------
    def loadNotes(self):
        return load_notes_from_json(self.logger)

    def updateNotesList(self):
        """Refill the list from storage, newest edit first, with the open note selected"""
        notes = sorted(self.loadNotes().items(),
                       key=lambda pair: _edited(pair[1]) or datetime.min, reverse=True)
        self.noteList.populate(notes, self.current_note_id, self._dirty)

    def _titleOf(self, note_id):
        return (self.loadNotes().get(note_id, {}).get("title") or "Untitled")

    def openNote(self, note_id):
        if note_id == self.current_note_id:
            return
        if not self._confirmDiscardChanges():
            self.updateNotesList()  # keep the open note selected
            return
        note = self.loadNotes().get(note_id)
        if note is not None:
            self.current_note_id = note_id
            self._setEditors(note.get("title", ""), note.get("content", ""))
        self.updateNotesList()
        self._updateStatus()

    def loadSelectedNote(self, item):
        """Open the note behind a list item"""
        self.openNote(item.data(Qt.UserRole))

    def showNoteMenu(self, note_id, global_pos):
        menu = QMenu(self)
        menu.setStyleSheet(MENU_STYLE)
        if note_id != self.current_note_id:
            menu.addAction("Open", lambda: self.openNote(note_id))
        menu.addAction("Rename…", lambda: self.renameNote(note_id))
        menu.addSeparator()
        menu.addAction("Delete…", lambda: self.deleteNote(note_id))
        menu.exec_(global_pos)

    def showEvent(self, event):
        super().showEvent(event)
        self.updateNotesList()  # notes may have changed elsewhere (undo, another screen)
        self.toolbar.syncToCursor()  # the editor's text size is known once it's styled

    def reloadFromStorage(self):
        """After undo or redo: show what's in the file now, keeping any unsaved edits"""
        notes = self.loadNotes()
        if self.current_note_id is not None:
            if self.current_note_id not in notes:
                if self._dirty:
                    self.current_note_id = None  # keep the edits; Save makes them a new note
                else:
                    self.current_note_id = None
                    self._setEditors("", "")
            elif not self._dirty:
                note = notes[self.current_note_id]
                self._setEditors(note.get("title", ""), note.get("content", ""))
        self.updateNotesList()
        self._updateStatus()

    # -- actions ----------------------------------------------------------------------
    def createNewNote(self):
        """Start a new, blank note. It's saved (and listed) when Save is pressed."""
        if not self._confirmDiscardChanges():
            return
        # Forget the previous note, so saving can't overwrite it
        self.current_note_id = None
        self._setEditors("", "")
        self.updateNotesList()
        self._updateStatus()
        self.title_editor.setFocus()

    def saveCurrentNote(self):
        """Save the note in the editors, keeping its formatting.
        A new note gets a new ID. Returns True if saved."""
        notes_data = self.loadNotes()
        note_id = self.current_note_id or str(uuid4())

        note = Note(title=self.title_editor.text().strip() or "Untitled", content=self.editor.toHtml())
        note.id = note_id
        if note_id in notes_data:
            note.creation_date = _parse_date(notes_data[note_id].get("creation_date")) or datetime.now()

        if not save_note_to_json(note, self.logger):
            self.logger.error("Failed to save note.")
            dialogs.critical(self, "Save Failed", "The note could not be saved. See app.log for details.")
            return False

        self.current_note_id = note_id
        self._dirty = False
        self._saved_at = datetime.now()
        self.updateNotesList()
        self._updateStatus()
        return True

    def renameNote(self, note_id):
        old_title = self._titleOf(note_id)
        title, ok = dialogs.ask_text(self, "Rename note", "Give it a new name.", old_title, ok_label="Rename")
        title = (title or "").strip()
        if not ok or not title or title == old_title:
            return
        with history().action(f"Renamed note “{old_title}”"):
            renamed = rename_note_in_json(note_id, title, self.logger)
        if renamed and note_id == self.current_note_id:
            # Show the new name, without counting it as an unsaved edit
            dirty = self._dirty
            self.title_editor.blockSignals(True)
            self.title_editor.setText(title)
            self.title_editor.blockSignals(False)
            self._dirty = dirty
        self.updateNotesList()
        self._updateStatus()

    def deleteNote(self, note_id):
        """Delete a saved note, after asking. Undo (the notice, or Ctrl+Z) brings it back."""
        title = self._titleOf(note_id)
        if not dialogs.confirm(self, f"Delete “{title}”?",
                               "The note will be removed. You can bring it back with Undo.", "Delete"):
            return
        with history().action(f"Deleted note “{title}”"):
            deleted = delete_note_from_json(note_id, self.logger)
        if not deleted:
            self.logger.error("Failed to delete note.")
            dialogs.critical(self, "Delete Failed", "The note could not be deleted. See app.log for details.")
            return
        if note_id == self.current_note_id:
            # Clear the editors, so Save can't bring the deleted note back
            self.current_note_id = None
            self._setEditors("", "")
        self.updateNotesList()
        self._updateStatus()

    def deleteCurrentNote(self):
        if self.current_note_id is None:
            # A new note that was never saved: just clear it
            self._setEditors("", "")
            self.updateNotesList()
            self._updateStatus()
            return
        self.deleteNote(self.current_note_id)
