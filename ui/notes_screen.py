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
from utils.tasks_io import load_tasks_from_json, save_task_to_json
from datetime import datetime
from pathlib import Path
from utils.directory_finder import resource_path
from models.task import Task, TaskCategory, TaskPriority, TaskStatus, Attachment, TaskEntry, TimeLog
from ui.custom_widgets.collapsable_section import CollapsibleSection
from resources.styles import AppColors
from resources.styles import AppStyles, AnimatedButton
from PyQt5.QtWidgets import (QApplication, QDesktopWidget, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSpacerItem, 
                             QSizePolicy, QGridLayout, QPushButton, QGraphicsDropShadowEffect, QStyle, QComboBox, QTextEdit,
                             QDateTimeEdit, QLineEdit, QCalendarWidget, QToolButton, QSpinBox, QListWidget, QTabWidget,
                             QMessageBox, QInputDialog, QListWidgetItem, QScrollArea, QTreeWidget, QTreeWidgetItem, QFileDialog,
                             QStyleFactory, QListView, QLayout
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

        self.initUI()

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
        panel_layout.addLayout(self.initLeftNotePanel(), 2)
        panel_layout.addLayout(self.initRightNotePanel(), 7)

        self.main_layout.addWidget(panel_widget)

    def initLeftNotePanel(self):
        left_notes_panel_layout = QVBoxLayout()
        left_notes_panel_layout.setContentsMargins(5, 0, 5, 0)
        left_notes_panel_layout.addLayout(self.initNotesPanelHeader())

        return left_notes_panel_layout

    def initNotesPanelHeader(self):
        header_panel_layout = QVBoxLayout()
        header_panel_layout.setAlignment(Qt.AlignTop)

        header_title_label = QLabel("Notes")
        header_title_label.setStyleSheet(AppStyles.label_normal())

        add_note_widget = QWidget()
        add_note_layout = QHBoxLayout(add_note_widget)

        add_note_label = QLabel("Add New Note")
        add_note_label.setStyleSheet(AppStyles.label_normal())

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
        add_note_button.clicked.connect(self.createNewNote)

        add_note_layout.addWidget(add_note_label)
        add_note_layout.addStretch(1)
        add_note_layout.addWidget(add_note_button)

        header_panel_layout.addWidget(header_title_label)
        header_panel_layout.addWidget(add_note_widget)
        # header_panel_layout.addStretch(1)

        return header_panel_layout

    def createNewNote(self):
        pass


    def initRightNotePanel(self):
        right_notes_panel_layout = QVBoxLayout()
        right_notes_panel_layout.setContentsMargins(5, 0, 5, 0)
        right_notes_panel_layout.addLayout(self.initNotesDisplayPanel())

        return right_notes_panel_layout

    def initNotesDisplayPanel(self):
        notes_display_layout = QVBoxLayout()


        return notes_display_layout