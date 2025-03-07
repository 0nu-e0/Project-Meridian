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
# File: task_card_lite.py
# Description: Used to display the most basic form of the task cards in the 
#              grid layout.
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

import sys
from pathlib import Path
from resources.styles import AppColors
from resources.styles import AppStyles, AnimatedButton
from PyQt5.QtWidgets import (QApplication, QDesktopWidget, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSpacerItem, 
                             QSizePolicy, QGridLayout, QPushButton, QGraphicsDropShadowEffect, QStyle
                             )
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QColor, QPainter, QBrush, QPen, QMovie
from PyQt5.QtSvg import QSvgWidget

from PyQt5.QtWidgets import QStyleFactory

class TaskCardLite(QWidget):
    card_count = 0
    cardClicked = pyqtSignal(object)
    cardHovered = pyqtSignal(bool, int) 
    removeTaskCardSignal = pyqtSignal(str)

    @classmethod
    def calculate_optimal_card_size(cls):
        # Get screen dimensions
        screen = QDesktopWidget().screenGeometry()
        screen_width = screen.width()
        screen_height = screen.height()
        
        # Base calculations
        min_readable_width = 200
        optimal_character_count = 25
        min_height_for_content = 120
        
        # Calculate width
        target_cards_per_row = max(4, screen_width // 400)
        available_width = screen_width - (40 * (target_cards_per_row + 1))
        card_width = max(min_readable_width, available_width // target_cards_per_row)
        
        # Calculate height
        card_height = min(int(card_width / 1.5), min_height_for_content)
        
        return card_width, card_height

    def __init__(self, logger, task, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        TaskCardLite.card_count += 1
        self.logger = logger
        self.task = task  # This is now a Task object that contains all the info
            
        # Calculate size first
        self.card_width, self.card_height = self.calculate_optimal_card_size()
        
        # Then set expansion properties
        self.expanded = False
        self.row_position = 0
        self.original_height = self.card_height
        self.expanded_height = self.original_height * 1.5
        
        # Add shadow effect
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setColor(QColor(AppColors.accent_background_color_dark))
        self.shadow.setBlurRadius(15)
        self.shadow.setXOffset(2)
        self.shadow.setYOffset(2)
        self.setGraphicsEffect(self.shadow)
        
        # Set size
        self.setFixedSize(self.card_width, self.card_height)
        
        self.installEventFilter(self)
        # self.setStyleSheet(AppStyles.task_card())
        self.initUI()

    def enterEvent(self, event):
        self.expanded = True
        self.shadow.setBlurRadius(25)
        self.cardHovered.emit(True, self.row_position)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.expanded = False
        self.shadow.setBlurRadius(15)
        self.cardHovered.emit(False, self.row_position)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.cardClicked.emit(self.task)
        super().mousePressEvent(event)
        
    def setRowPosition(self, row):
        self.row_position = row

    def setExpanded(self, expanded):
        if expanded:
            self.setMinimumHeight(int(self.expanded_height))
            self.setMaximumHeight(int(self.expanded_height))
        else:
            self.setMinimumHeight(int(self.original_height))
            self.setMaximumHeight(int(self.original_height))

        self.updateContent(expanded)
        self.update()  # Force a repaint


    def task_routine(self, task_name, description, creation_date, due_date, status, assigned, catagory, priority):
        self.task_name = task_name

    def subtask_routine(self, parent, subtask_name, description, creation_date, due_date, status, assigned, catagory, priority):
        self.subtask_name = subtask_name

    def initUI(self):
        self.initCentralWidget()
        # Set initial state
        self.expanded = False
        # Generate initial collapsed view
        self.generateUI()
        # Cache expanded view dimensions for transitions
        self.card_width, self.card_height = self.calculate_optimal_card_size()
        self.original_height = int(self.card_height)
        self.expanded_height = int(self.card_height * 2)  # Double height when expanded

    def initCentralWidget(self):
        self.central_widget = QWidget()
        self.central_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0) 
        self.main_layout.setSpacing(0)  
        self.setLayout(self.main_layout)

    def updateContent(self, expanded):
        # Clear the current layout
        while self.main_layout.count():
            item = self.main_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Rebuild UI based on the expanded state
        if expanded:
            self.generateExpandedUI()
        else:
            self.generateUI()

        # Ensure layout refreshes properly
        self.main_layout.invalidate()  # Invalidate current layout
        self.main_layout.activate()    # Force re-layout only on this widget
        self.updateGeometry()          # Notify parent layout of size change


    def generateUI(self):
        card_layout_widget = QWidget()
        card_layout_widget.setObjectName("card_container") 
        card_layout = QGridLayout(card_layout_widget)
        card_layout.setContentsMargins(8, 8, 8, 8)
        card_layout.setSpacing(4)

        # Title from Task
        title_label = QLabel(self.task.title)
        title_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 16px;
                background-color: #2C3E50;
                padding: 5px;
            }
        """)
        card_layout.addWidget(title_label, 0, 0, 1, 2)
        
        # Status (using TaskStatus enum)
        status_label = QLabel()
        status_icon = self.style().standardIcon(QStyle.SP_DialogApplyButton)
        status_label.setPixmap(status_icon.pixmap(16, 16))
        status_label.setText(f"  {self.task.status.value}")  # Using enum value
        status_label.setStyleSheet(f"""
            QLabel {{
                color: white;
                font-size: 14px;
                background-color: {AppColors.get_status_color(self.task.status)};
                padding: 5px;
            }}
        """)
        card_layout.addWidget(status_label, 1, 0)
    
        # Priority (using TaskPriority enum)
        priority_label = QLabel()
        priority_icon = self.style().standardIcon(QStyle.SP_TitleBarContextHelpButton)
        priority_label.setPixmap(priority_icon.pixmap(16, 16))
        priority_label.setText(f"  {self.task.priority.name}")  # Using enum name
        priority_label.setStyleSheet(f"""
            QLabel {{
                color: white;
                font-size: 14px;
                background-color: {AppColors.get_priority_color(self.task.priority)};
                padding: 5px;
            }}
        """)
        card_layout.addWidget(priority_label, 1, 1)
        
        # Category (using TaskCategory enum)
        category_label = QLabel()
        category_icon = self.style().standardIcon(QStyle.SP_DirIcon)
        category_label.setPixmap(category_icon.pixmap(16, 16))
        category_label.setText(f"  {self.task.category.value}")  # Using enum value
        category_label.setStyleSheet(f"""
            QLabel {{
                color: white;
                font-size: 14px;
                background-color: {AppColors.get_category_color(self.task.category)};
                padding: 5px;
            }}
        """)
        card_layout.addWidget(category_label, 2, 0)
        
        # Completion percentage
        complete_label = QLabel()
        complete_icon = self.style().standardIcon(QStyle.SP_BrowserReload)
        complete_label.setPixmap(complete_icon.pixmap(16, 16))
        complete_label.setText(f"  {self.task.percentage_complete}%")  # Using integer percentage
        complete_label.setStyleSheet(f"""
            QLabel {{
                color: white;
                font-size: 14px;
                background-color: {AppColors.get_progress_color(self.task.percentage_complete)};
                padding: 5px;
            }}
        """)
        card_layout.addWidget(complete_label, 2, 1)

        self.main_layout.addWidget(card_layout_widget)

    def generateExpandedUI(self):
        card_layout_widget = QWidget()
        card_layout_widget.setObjectName("card_container") 
        card_layout = QGridLayout(card_layout_widget)
        card_layout.setContentsMargins(8, 8, 8, 8)
        card_layout.setSpacing(4)

        # Set column stretch factors to make columns equal width
        card_layout.setColumnStretch(0, 1)
        card_layout.setColumnStretch(1, 1)

        # Title - Compact
        title_label = QLabel(self.task.title)
        title_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 16px;
                font-weight: bold;
                background-color: #2C3E50;
                padding: 5px;
            },
            QLabel:hover {
                background-color: #2C3E50;  /* Same as non-hover */
                border: none;
            }
        """)
        title_label.setMaximumHeight(30)
        card_layout.addWidget(title_label, 0, 0, 1, 2)

        # Status and Priority - Split into two columns
        status_label = QLabel(f"Status: {self.task.status.value}")
        status_label.setStyleSheet(f"""
        QLabel {{
            color: white;
            font-size: 12px;
            background-color: {AppColors.get_status_color(self.task.status)};
            padding: 3px;
        }}
        """)
        status_label.setMaximumHeight(25)
        card_layout.addWidget(status_label, 1, 0)  # First column

        priority_label = QLabel(f"Priority: {self.task.priority.name}")
        priority_label = QLabel(f"Priority: {self.task.priority.name}")
        priority_label.setStyleSheet(f"""
            QLabel {{
                color: white;
                font-size: 12px;
                background-color: {AppColors.get_priority_color(self.task.priority)};
                padding: 3px;
                border-radius: 8px;
            }}
        """)
        priority_label.setMaximumHeight(25)
        card_layout.addWidget(priority_label, 1, 1)  # Second column

        # Description - More space
        desc_label = QLabel(self.task.description)
        desc_label.setAlignment(Qt.AlignLeft | Qt.AlignTop) 
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 14px;
                background-color: #34495E;
                padding: 8px;
            }
        """)
        desc_label.setMinimumHeight(60)
        card_layout.addWidget(desc_label, 2, 0, 1, 2)

        # Progress info - Compact but informative
        progress_info = []
        progress_info.append(f"Progress: {self.task.percentage_complete}%")
        if hasattr(self.task, 'estimated_hours') and self.task.estimated_hours:
            progress_info.append(f"Est: {self.task.estimated_hours}h")
        if hasattr(self.task, 'actual_hours') and self.task.actual_hours:
            progress_info.append(f"Actual: {self.task.actual_hours}h")
        
        progress_label = QLabel(" | ".join(progress_info))
        progress_label.setStyleSheet(f"""
            QLabel {{
                color: white;
                font-size: 12px;
                background-color: {AppColors.get_progress_color(self.task.percentage_complete)};
                padding: 3px;
            }}
        """)
        progress_label.setMaximumHeight(25)
        card_layout.addWidget(progress_label, 3, 0, 1, 2)

         # Dates - Split into two columns (modified)
        if self.task.start_date is not None:
            started_label = QLabel(f"Started: {self.task.start_date.strftime('%m/%d/%y')}")
            started_label.setStyleSheet("""
                QLabel {
                    color: white;
                    font-size: 12px;
                    background-color: #2980B9;
                    padding: 3px;
                }
            """)
            started_label.setMaximumHeight(25)
            card_layout.addWidget(started_label, 4, 0)  # First column
        
        if self.task.due_date is not None:
            due_label = QLabel(f"Due: {self.task.due_date.strftime('%m/%d/%y')}")
            due_label.setStyleSheet(f"""
                QLabel {{
                    color: white;
                    font-size: 12px;
                    background-color: {AppColors.get_due_date_color(self.task.due_date)};
                    padding: 3px;
                }}
            """)
            due_label.setMaximumHeight(25)
            card_layout.addWidget(due_label, 4, 1)  # Second column

        # Team info - Single line
        team_info = []
        if hasattr(self.task, 'assignee') and self.task.assignee:
            team_info.append(f"Assignee: {self.task.assignee}")
        if hasattr(self.task, 'watchers') and self.task.watchers:
            team_info.append(f"Watchers: {len(self.task.watchers)}")
        
        if team_info:
            team_label = QLabel(" | ".join(team_info))
            team_label.setStyleSheet("""
                QLabel {
                    color: white;
                    font-size: 12px;
                    background-color: #8E44AD;
                    padding: 3px;
                }
            """)
            team_label.setMaximumHeight(25)
            card_layout.addWidget(team_label, 5, 0, 1, 2)

        self.main_layout.addWidget(card_layout_widget)