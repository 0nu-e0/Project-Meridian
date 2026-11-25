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

from utils.notes_io import save_note_to_json, load_notes_from_json, delete_note_from_json
from uuid import uuid4
from datetime import datetime
from utils.constants import MAIN_PANEL_STRETCH, SIDE_PANEL_STRETCH
from models.note import Note
from ui.custom_widgets.text_edit_toolbar import TextEditToolbar
from resources.styles import AppStyles
from ui.custom_widgets import dialogs
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSizePolicy, QPushButton, QTextEdit,
                             QLineEdit, QMessageBox, QListWidgetItem, QListWidget
                             )
from PyQt5.QtCore import Qt



class NotesScreen(QWidget):

    def __init__(self, logger, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.logger = logger

        self.title_editor = None
        self.editor = None
        # The note in the editors; None means a new note not saved yet
        self.current_note_id = None
        # True once the editors differ from what was last loaded or saved
        self._dirty = False

        self.initUI()
        self.updateNotesList()

    def initUI(self):
        self.initCentralWidget()
        self.addSeparator()
        self.initPanelHorizontalContainer()

    def initCentralWidget(self):
        central_widget = QWidget()
        central_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.setLayout(self.main_layout)

    def addSeparator(self):
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFixedHeight(2)
        self.main_layout.addWidget(separator)

    def initPanelHorizontalContainer(self):
        panel_widget = QWidget()
        panel_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        panel_layout = QHBoxLayout(panel_widget)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.addLayout(self.initLeftNotePanel(), SIDE_PANEL_STRETCH)
        panel_layout.addLayout(self.initRightNotePanel(), MAIN_PANEL_STRETCH)

        self.main_layout.addWidget(panel_widget)

    def initLeftNotePanel(self):
        left_notes_panel_layout = QVBoxLayout()
        left_notes_panel_layout.setContentsMargins(5, 15, 5, 0)
        left_notes_panel_layout.addLayout(self.initNotesPanelHeader())
        left_notes_panel_layout.addLayout(self.initNotesPanelList())

        return left_notes_panel_layout

    def initNotesPanelHeader(self):
        header_panel_layout = QHBoxLayout()
        header_panel_layout.setAlignment(Qt.AlignTop)

        header_title_label = QLabel("Notes")
        header_title_label.setContentsMargins(10, 0, 0, 0)
        header_title_label.setStyleSheet(AppStyles.label_normal())
        header_title_label.setAlignment(Qt.AlignCenter)

        add_note_button = QPushButton("+")
        add_note_button.setToolTip("New note")
        add_note_button.setStyleSheet("""
            QPushButton {
                font-size: 15px;
            }
            QPushButton:hover {
                font-size: 20px;
                font-weight: bold;
            }
        """)
        add_note_button.setFixedSize(20, 20)
        add_note_button.clicked.connect(self.createNewNote)

        header_panel_layout.addWidget(header_title_label)
        header_panel_layout.addStretch(1)
        header_panel_layout.addWidget(add_note_button)

        return header_panel_layout

    def _markDirty(self):
        self._dirty = True

    def _setEditors(self, title, html):
        """Fill the editors without counting it as an edit"""
        self.title_editor.blockSignals(True)
        self.editor.blockSignals(True)
        self.title_editor.setText(title)
        if html:
            self.editor.setHtml(html)
        else:
            self.editor.clear()
        self.title_editor.blockSignals(False)
        self.editor.blockSignals(False)
        self._dirty = False

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

    def _selectCurrentNoteInList(self):
        self.notes_list.blockSignals(True)
        self.notes_list.clearSelection()
        self.notes_list.setCurrentRow(-1)
        for row in range(self.notes_list.count()):
            if self.notes_list.item(row).data(Qt.UserRole) == self.current_note_id:
                self.notes_list.setCurrentRow(row)
                break
        self.notes_list.blockSignals(False)

    def createNewNote(self):
        """Start a new, blank note. It's saved (and listed) when Save is pressed."""
        if not self._confirmDiscardChanges():
            return
        # Forget the previous note, so saving can't overwrite it
        self.current_note_id = None
        self._selectCurrentNoteInList()
        self._setEditors("", "")
        self.title_editor.setFocus()

    def saveCurrentNote(self):
        """Save the note in the editors, preserving rich text formatting.
        A new note gets a new ID. Returns True if saved."""
        notes_data = self.loadNotes()

        # The editors always belong to current_note_id; None means a new note
        note_id = self.current_note_id or str(uuid4())

        # Create or update a Note object using the current editor contents.
        # Use toHtml() to preserve formatting.
        note = Note(
            title=self.title_editor.text().strip() or "Untitled",
            content=self.editor.toHtml()
        )
        note.id = note_id

        # If updating an existing note, preserve its creation_date if available.
        if note_id in notes_data:
            try:
                note.creation_date = datetime.strptime(
                    notes_data[note_id]["creation_date"], '%Y-%m-%d, %H:%M:%S'
                )
            except Exception:
                note.creation_date = datetime.now()

        if not save_note_to_json(note, self.logger):
            self.logger.error("Failed to save note.")
            dialogs.critical(self, "Save Failed", "The note could not be saved. See app.log for details.")
            return False

        self.current_note_id = note_id
        self._dirty = False
        self.updateNotesList()
        return True

    def deleteCurrentNote(self):
        if not self.current_note_id:
            # A new note that was never saved: just clear it
            self._setEditors("", "")
            return

        title = self.title_editor.text().strip() or "Untitled"
        reply = dialogs.question(
            self, "Delete Note", f"Delete the note '{title}'? This can't be undone.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        if delete_note_from_json(self.current_note_id, self.logger):
            # Clear the editors, so Save can't bring the deleted note back
            self.current_note_id = None
            self._setEditors("", "")
            self.updateNotesList()
        else:
            self.logger.error("Failed to delete note.")

    def loadSelectedNote(self, item):
        """Loads the selected note into the editors, preserving formatting."""
        note_id = item.data(Qt.UserRole)
        if note_id == self.current_note_id:
            return
        if not self._confirmDiscardChanges():
            # Stay on the note being edited
            self._selectCurrentNoteInList()
            return

        notes = self.loadNotes()
        if note_id in notes:
            self.current_note_id = note_id
            self._setEditors(notes[note_id].get("title", ""), notes[note_id].get("content", ""))

    def initNotesPanelList(self):
        # Create the list widget that displays note titles.
        notes_list_layout = QVBoxLayout()
        self.notes_list = QListWidget(self)
        self.notes_list.setStyleSheet(AppStyles.list_notes())
        self.notes_list.itemClicked.connect(self.loadSelectedNote)

        notes_list_layout.addWidget(self.notes_list)

        return notes_list_layout

    def updateNotesList(self):
        """Refresh the notes list with the latest notes from storage."""
        notes = self.loadNotes()
        current_id = self.current_note_id
        self.notes_list.clear()
        selected_row = None
        for idx, (note_id, note) in enumerate(notes.items()):
            item = QListWidgetItem(note.get("title", "Untitled"))
            item.setData(Qt.UserRole, note_id)
            self.notes_list.addItem(item)
            if note_id == current_id:
                selected_row = idx
        if selected_row is not None:
            self.notes_list.setCurrentRow(selected_row)

    def loadNotes(self):
        """Load notes using the helper function from notes_io.py."""
        return load_notes_from_json(self.logger)

    def initRightNotePanel(self):
        right_notes_panel_layout = QVBoxLayout()
        right_notes_panel_layout.setContentsMargins(5, 15, 15, 15)
        right_notes_panel_layout.addLayout(self.initNotesDisplayPanel())

        return right_notes_panel_layout

    def initNotesDisplayPanel(self):
        notes_display_layout = QVBoxLayout()
        # Add the toolbar at the top
        # Then add your title editor and content editor
        self.title_editor = QLineEdit()
        self.title_editor.setStyleSheet(AppStyles.line_edit_norm())
        self.title_editor.setPlaceholderText("Enter note title here")
        self.title_editor.textChanged.connect(self._markDirty)

        self.editor = QTextEdit()
        self.editor.setStyleSheet(AppStyles.text_edit_norm())
        self.editor.textChanged.connect(self._markDirty)

        toolbar_widget = QWidget()
        toolbar_layout = QHBoxLayout(toolbar_widget)

        toolbar = TextEditToolbar(self.editor)

        save_button = QPushButton("Save")
        save_button.setToolTip("Save this note")
        save_button.setStyleSheet(AppStyles.save_button())
        save_button.clicked.connect(self.saveCurrentNote)

        delete_button = QPushButton("Delete")
        delete_button.setToolTip("Delete this note")
        delete_button.setStyleSheet(AppStyles.save_button())
        delete_button.clicked.connect(self.deleteCurrentNote)

        toolbar_layout.addWidget(toolbar)
        toolbar_layout.addStretch(1)
        toolbar_layout.addWidget(save_button)
        toolbar_layout.addWidget(delete_button)

        notes_display_layout.addWidget(self.title_editor)
        notes_display_layout.addWidget(toolbar_widget)
        notes_display_layout.addWidget(self.editor)
        return notes_display_layout
