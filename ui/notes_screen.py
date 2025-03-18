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

import sys, os, json, copy
from utils.notes_io import save_note_to_json, load_notes_from_json, delete_note_from_json
from uuid import uuid4
from datetime import datetime
from pathlib import Path
from utils.directory_finder import resource_path
from models.note import Note
from models.task import Task, TaskCategory, TaskPriority, TaskStatus, Attachment, TaskEntry, TimeLog
from ui.custom_widgets.text_edit_toolbar import TextEditToolbar
from ui.custom_widgets.collapsable_section import CollapsibleSection
from resources.styles import AppColors
from resources.styles import AppStyles, AnimatedButton
from PyQt5.QtWidgets import (QApplication, QDesktopWidget, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSpacerItem, 
                             QSizePolicy, QGridLayout, QPushButton, QGraphicsDropShadowEffect, QStyle, QComboBox, QTextEdit,
                             QDateTimeEdit, QLineEdit, QCalendarWidget, QToolButton, QSpinBox, QListWidget, QTabWidget,
                             QMessageBox, QInputDialog, QListWidgetItem, QScrollArea, QTreeWidget, QTreeWidgetItem, QFileDialog,
                             QStyleFactory, QListView, QLayout, QListWidget
                             )
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QEvent, QSize, QDateTime, QUrl, QTimer
from PyQt5.QtGui import (QColor, QPainter, QBrush, QPen, QMovie, QTextCharFormat, QColor, QIcon, QPixmap, QDesktopServices,
                        
                        )
from PyQt5.QtSvg import QSvgWidget



class NotesScreen(QWidget):

    def __init__(self, logger, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.logger = logger

        self.title_editor = None
        self.editor = None

        self.initUI()
        self.updateNotesList()

    def initUI(self):
        self.initCentralWidget()
        self.initBannerSpacer()
        self.addSeparator()
        self.initPanelHorizontalContainer()

    def initCentralWidget(self):
        central_widget = QWidget()
        central_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.setLayout(self.main_layout)

    def initBannerSpacer(self):
        self.banner_widget = QWidget()
        self.banner_layout = QVBoxLayout(self.banner_widget)
        banner_height = int(self.height()*0.15) 
        self.banner_spacer = QSpacerItem(1, banner_height, QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.banner_layout.addSpacerItem(self.banner_spacer)
        self.main_layout.addWidget(self.banner_widget)

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
        panel_layout.addLayout(self.initLeftNotePanel(), 1)
        panel_layout.addLayout(self.initRightNotePanel(), 5)

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
        header_title_label.setStyleSheet(AppStyles.label_normal())
        header_title_label.setAlignment(Qt.AlignCenter)

        add_note_button = QPushButton("+")
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
        # Disconnect any previous connections to avoid duplicate calls.
        try:
            add_note_button.clicked.disconnect()
        except Exception:
            pass
        add_note_button.clicked.connect(self.createNewNote)

        header_panel_layout.addWidget(header_title_label)
        header_panel_layout.addStretch(1)
        header_panel_layout.addWidget(add_note_button)

        return header_panel_layout

    def createNewNote(self):
        """Creates a new blank note."""
        new_note = {
            "id": str(uuid4()),
            "title": "Untitled",
            "content": "",
            "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "modified_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        notes = self.loadNotes()
        notes[new_note["id"]] = new_note
        self.updateNotesList()
        # Clear both editors for a fresh note.
        self.title_editor.setText("")
        self.editor.setText("")

    def saveCurrentNote(self):
        """Save the currently selected note, preserving rich text formatting.
        If no note is selected, create a new note."""
        selected_item = self.notes_list.currentItem()
        notes_data = self.loadNotes()
        
        # If no note is selected, create a new note ID
        if selected_item:
            note_id = selected_item.data(Qt.UserRole)
        else:
            note_id = str(uuid4())
        
        # Create or update a Note object using the current editor contents.
        # Use toHtml() to preserve formatting.
        note = Note(
            title=self.title_editor.text(),
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
        
        # Save the note using your helper function
        if save_note_to_json(note, self.logger):
            self.logger.info("Note saved successfully using the helper function.")
            self.updateNotesList()
        else:
            self.logger.error("Failed to save note.")

    def deleteCurrentNote(self):
        selected_item = self.notes_list.currentItem()
        if not selected_item:
            self.logger.error("No note selected for deletion.")
            return

        note_id = selected_item.data(Qt.UserRole)
        if delete_note_from_json(note_id, self.logger):
            self.updateNotesList()
        else:
            self.logger.error("Failed to delete note.")

    def loadSelectedNote(self, item):
        """Loads the selected note into the editors, preserving formatting."""
        note_id = item.data(Qt.UserRole)
        notes = self.loadNotes()
        if note_id in notes:
            self.title_editor.setText(notes[note_id]["title"])
            # Restore rich text formatting
            self.editor.setHtml(notes[note_id]["content"])

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
        # print(f"Adding notes: {notes}")
        self.notes_list.clear()
        for note_id, note in notes.items():
            item = QListWidgetItem(note.get("title", "Untitled"))
            item.setData(Qt.UserRole, note_id)
            self.notes_list.addItem(item)

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
        
        self.editor = QTextEdit()
        self.editor.setStyleSheet(AppStyles.text_edit_norm())

        toolbar_widget = QWidget()
        toolbar_layout = QHBoxLayout(toolbar_widget)
        
        toolbar = TextEditToolbar(self.editor)

        save_button = QPushButton("Save")
        save_button.setStyleSheet(AppStyles.save_button())
        save_button.clicked.connect(self.saveCurrentNote)

        delete_button = QPushButton("Delete")
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
