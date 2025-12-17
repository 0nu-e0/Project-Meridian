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
# File: planning_screen.py
# Description: Modern planning screen with task details and drag-and-drop scheduling
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

# Standard library imports
import json
from logging import Logger
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

# Third-party imports
from PyQt5.QtCore import QDate, QMimeData, Qt, pyqtSignal
from PyQt5.QtGui import QDrag, QFont
from PyQt5.QtWidgets import (QButtonGroup, QCalendarWidget, QGridLayout, QHBoxLayout,
                             QLabel, QListWidget, QListWidgetItem, QPushButton, QRadioButton,
                             QScrollArea, QSizePolicy, QSplitter, QTextEdit, QVBoxLayout, QWidget)

# Local application imports
from models.task import Task, TaskPriority, TaskCategory
from resources.styles import AppStyles
from ui.task_files.task_card_expanded import TaskCardExpanded
from utils.app_config import AppConfig
from utils.tasks_io import load_tasks_from_json


class ScheduledTask:
    """Represents a task scheduled for a specific date/time"""
    def __init__(self, task_id: str, scheduled_date: QDate, task_title: str):
        self.task_id = task_id
        self.scheduled_date = scheduled_date
        self.task_title = task_title
        self.schedule_id = str(uuid4())


class StyledTaskItem(QWidget):
    """Custom styled widget for task list items"""

    def __init__(self, task: Task, parent=None):
        super().__init__(parent)
        self.task = task
        self.initUI()

    def initUI(self):
        from PyQt5.QtCore import Qt

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(4)

        # Title with word wrap and dynamic font sizing
        title_label = QLabel(self.task.title)
        title_label.setWordWrap(True)  # Allow wrapping to multiple lines
        title_label.setMaximumWidth(230)  # Force wrapping at this width
        title_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)  # Allow vertical expansion
        # Auto-adjust font size to fit in available width (accounting for margins)
        available_width = 230  # Card width minus margins (10px left + 10px right)
        # Try to fit text - if a single word is too long, reduce font size
        font_size = self._calculateFontSizeForTitle(self.task.title, available_width, 11, bold=True)
        title_font = QFont()
        title_font.setPointSize(font_size)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: white;")
        layout.addWidget(title_label)

        # Info row (priority + category)
        info_layout = QHBoxLayout()
        info_layout.setSpacing(8)

        # Priority badge (fixed height)
        priority_label = QLabel(self.task.priority.name)
        priority_label.setStyleSheet(self._getPriorityStyle())
        priority_label.setFixedHeight(16)
        priority_label.setAlignment(Qt.AlignCenter)
        info_layout.addWidget(priority_label)

        # Category (fixed height)
        category_label = QLabel(self.task.category.value)
        category_label.setStyleSheet("color: #95a5a6; font-size: 10px;")
        category_label.setFixedHeight(16)
        category_label.setAlignment(Qt.AlignVCenter)
        info_layout.addWidget(category_label)

        info_layout.addStretch()
        layout.addLayout(info_layout)

        # NO fixed height - let card expand based on title wrapping

        # Set overall styling
        self.setStyleSheet("""
            StyledTaskItem {
                background-color: #2c3e50;
                border-radius: 5px;
                border: 1px solid #34495e;
            }
            StyledTaskItem:hover {
                background-color: #34495e;
                border: 1px solid #3498db;
            }
        """)

    def _getPriorityStyle(self) -> str:
        """Get style for priority badge"""
        colors = {
            TaskPriority.CRITICAL: "#c0392b",
            TaskPriority.HIGH: "#e74c3c",
            TaskPriority.MEDIUM: "#f39c12",
            TaskPriority.LOW: "#3498db",
            TaskPriority.TRIVIAL: "#95a5a6"
        }
        bg_color = colors.get(self.task.priority, "#95a5a6")
        return f"""
            padding: 2px 8px;
            background-color: {bg_color};
            color: white;
            border-radius: 3px;
            font-size: 9px;
            font-weight: bold;
        """

    def sizeHint(self):
        """Override sizeHint to return proper height for wrapped content"""
        from PyQt5.QtCore import QSize
        from PyQt5.QtGui import QFontMetrics

        # Calculate title height based on wrapped text
        title_font = QFont()
        available_width = 230  # Card width minus margins
        font_size = self._calculateFontSizeForTitle(self.task.title, available_width, 11, bold=True)
        title_font.setPointSize(font_size)
        title_font.setBold(True)

        metrics = QFontMetrics(title_font)
        # Calculate how many lines the text will wrap to
        from PyQt5.QtGui import QTextLayout
        from PyQt5.QtCore import QPointF

        layout = QTextLayout(self.task.title, title_font)
        layout.beginLayout()

        line_height = metrics.height()
        y = 0
        line_count = 0

        while True:
            line = layout.createLine()
            if not line.isValid():
                break
            line.setLineWidth(available_width)
            line.setPosition(QPointF(0, y))
            y += line_height
            line_count += 1

        layout.endLayout()

        # Calculate total height:
        # - Top margin: 6px
        # - Title height: line_count * line_height
        # - Spacing: 4px
        # - Info row height: 16px (fixed)
        # - Bottom margin: 6px
        # - Extra padding: 10px for safety
        total_height = 6 + (line_count * line_height) + 4 + 16 + 6 + 10

        return QSize(250, int(total_height))

    def _calculateFontSizeForTitle(self, text: str, max_width: int, default_size: int, bold: bool = False) -> int:
        """
        Calculate font size to ensure single words fit within max_width.
        If any word is too long, reduce font size until it fits.

        Args:
            text: The text to measure
            max_width: Maximum width in pixels
            default_size: Starting font size
            bold: Whether font is bold

        Returns:
            Font size to use
        """
        from PyQt5.QtGui import QFontMetrics

        if not text:
            return default_size

        min_font_size = 7  # Don't go below 7pt
        words = text.split()

        # Find the longest word
        longest_word = max(words, key=len) if words else text

        for test_size in range(default_size, min_font_size - 1, -1):
            test_font = QFont()
            test_font.setPointSize(test_size)
            test_font.setBold(bold)
            metrics = QFontMetrics(test_font)

            # Check if the longest word fits within max_width
            word_width = metrics.horizontalAdvance(longest_word)

            if word_width <= max_width:
                return test_size

        return min_font_size


class StyledProjectItem(QWidget):
    """Custom styled widget for project list items in planning view"""

    def __init__(self, project_data: dict, logger, parent=None, show_tasks=False):
        super().__init__(parent)
        self.project_data = project_data
        self.project_id = project_data['project_id']
        self.logger = logger
        self.show_tasks = show_tasks  # True when scheduled to a day, False in left panel
        self.project = None
        self.phases = []
        self.current_phase = None
        self.tasks = []

        self.loadProjectData()
        self.initUI()

        # Enable mouse tracking for click events
        if self.show_tasks:
            from PyQt5.QtCore import Qt
            self.setCursor(Qt.PointingHandCursor)

    def loadProjectData(self):
        """Load full project, phases, and tasks data"""
        from utils.projects_io import load_projects_from_json, load_phases_from_json
        from utils.tasks_io import load_tasks_from_json

        # Ensure logger is available
        if not self.logger:
            import logging
            self.logger = logging.getLogger(__name__)

        # Load project
        projects = load_projects_from_json(self.logger)
        self.project = projects.get(self.project_id)

        if not self.project:
            self.logger.error(f"Project {self.project_id} not found")
            return

        # Load phases for this project
        all_phases = load_phases_from_json(self.logger)
        self.phases = [
            all_phases[phase_id]
            for phase_id in self.project.phases
            if phase_id in all_phases
        ]
        # Sort by order
        self.phases.sort(key=lambda p: p.order)

        # Find current phase (first incomplete phase)
        for phase in self.phases:
            # A phase is considered incomplete if it doesn't have a completion_date
            # or if it's marked as the current phase
            if not phase.completion_date or phase.is_current:
                self.current_phase = phase
                break

        # If no current phase, use first phase or None
        if not self.current_phase and self.phases:
            self.current_phase = self.phases[0]

        # Only load tasks if show_tasks is True (when scheduled to a day)
        if self.show_tasks and self.current_phase:
            from models.task import TaskStatus
            all_tasks = load_tasks_from_json(self.logger)
            phase_tasks = [
                task for task in all_tasks.values()
                if task.phase_id == self.current_phase.id
                and task.status != TaskStatus.COMPLETED  # Only show incomplete tasks
            ]
            # Sort by priority (no limit when showing tasks)
            phase_tasks.sort(key=lambda t: t.priority.value, reverse=True)
            self.tasks = phase_tasks

    def initUI(self):
        """Initialize the widget UI"""
        from PyQt5.QtCore import Qt

        # Set size policy for the widget itself to expand horizontally
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        # Set border style BEFORE creating layout
        if self.show_tasks:
            # Scheduled mode: no border on main widget, individual tasks will have their own borders
            self.setStyleSheet("""
                StyledProjectItem {
                    background-color: #2c3e50;
                    border-radius: 4px;
                }
                StyledProjectItem:hover {
                    background-color: #34495e;
                }
                QLabel {
                    background-color: transparent;
                }
                QCheckBox {
                    background-color: transparent;
                }
            """)
        else:
            # List mode: use standard border matching task cards
            self.setStyleSheet("""
                StyledProjectItem {
                    background-color: #2c3e50;
                    border-radius: 5px;
                    border: 1px solid #34495e;
                }
                StyledProjectItem:hover {
                    background-color: #34495e;
                    border: 1px solid #3498db;
                }
                QLabel {
                    background-color: transparent;
                }
            """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(4)

        if not self.project:
            # Error state
            error_label = QLabel("Project not found")
            error_label.setStyleSheet("color: #e74c3c; font-size: 11px;")
            layout.addWidget(error_label)
            return

        if self.show_tasks:
            # SCHEDULED MODE: Show project title + tasks
            # Project title - ONLY element with dynamic font sizing for long words
            title_label = QLabel(self.project.title)
            title_label.setWordWrap(True)  # Allow wrapping to multiple lines
            title_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)  # Allow horizontal and vertical expansion
            title_label.setMinimumWidth(200)  # Ensure minimum width
            # Auto-adjust font size to fit in available width (accounting for margins)
            # Available width = card width minus margins (10px left + 10px right = 20px)
            available_width = 230  # Approximate card width minus margins
            # Try to fit text - if a single word is too long, reduce font size
            font_size = self._calculateFontSizeForTitle(self.project.title, available_width, 11, bold=True)
            title_font = QFont()
            title_font.setPointSize(font_size)
            title_font.setBold(True)
            title_label.setFont(title_font)
            title_label.setStyleSheet("color: #27ae60;")
            title_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            # NO fixed height - let it expand vertically as needed for wrapped text
            layout.addWidget(title_label)

            # Current phase name - normal fixed style (no dynamic sizing)
            if self.current_phase:
                phase_label = QLabel(f"→ {self.current_phase.name}")
                phase_label.setStyleSheet("color: #3498db; font-size: 10px; font-weight: bold;")
                phase_label.setFixedHeight(16)
                phase_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                phase_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                layout.addWidget(phase_label)

            # Tasks list - each task with its own priority-based border
            if self.tasks:
                for task in self.tasks:
                    from PyQt5.QtWidgets import QCheckBox

                    # Create a container widget for this task with border
                    task_container = QWidget()
                    task_border_color = self._getTaskBorderColor(task)
                    task_container.setStyleSheet(f"""
                        QWidget {{
                            background-color: #2c3e50;
                            border-left: 3px solid {task_border_color};
                            border-radius: 4px;
                        }}
                    """)

                    task_layout = QHBoxLayout(task_container)
                    task_layout.setSpacing(6)
                    task_layout.setContentsMargins(8, 4, 8, 4)

                    # Checkbox for task completion
                    from models.task import TaskStatus
                    checkbox = QCheckBox()
                    checkbox.setChecked(task.status == TaskStatus.COMPLETED)
                    checkbox.setEnabled(False)  # Read-only display
                    checkbox.setStyleSheet("""
                        QCheckBox {
                            spacing: 0px;
                            background-color: transparent;
                            border: none;
                        }
                        QCheckBox::indicator {
                            width: 12px;
                            height: 12px;
                            border: 1px solid #95a5a6;
                            border-radius: 2px;
                            background-color: #2c3e50;
                        }
                        QCheckBox::indicator:checked {
                            background-color: #27ae60;
                            border-color: #27ae60;
                        }
                    """)
                    task_layout.addWidget(checkbox)

                    # Task title - normal style with word wrap
                    task_label = QLabel(task.title)
                    task_label.setStyleSheet("color: #bdc3c7; font-size: 10px; background-color: transparent; border: none;")
                    task_label.setWordWrap(True)
                    task_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
                    task_layout.addWidget(task_label)

                    # Add the task container to the main layout
                    layout.addWidget(task_container)
            else:
                no_tasks_label = QLabel("No incomplete tasks in current phase")
                no_tasks_label.setStyleSheet("color: #7f8c8d; font-size: 9px; font-style: italic;")
                no_tasks_label.setWordWrap(True)
                no_tasks_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
                layout.addWidget(no_tasks_label)
        else:
            # LIST MODE: Simple display - EXACTLY matching task card style
            # Title (COPIED FROM StyledTaskItem)
            title_label = QLabel(self.project.title)
            title_font = QFont()
            title_font.setPointSize(11)
            title_font.setBold(True)
            title_label.setFont(title_font)
            title_label.setWordWrap(False)
            title_label.setFixedHeight(18)
            # Truncate text if too long (EXACT COPY from StyledTaskItem)
            metrics = title_label.fontMetrics()
            elided_text = metrics.elidedText(self.project.title, Qt.ElideRight, 250)
            title_label.setText(elided_text)
            title_label.setStyleSheet("color: #27ae60;")
            layout.addWidget(title_label)

            # Set fixed height for list mode to match task cards
            self.setFixedHeight(50)

    def sizeHint(self):
        """Override sizeHint to return proper height for wrapped content"""
        # Get the base size hint
        hint = super().sizeHint()

        # For scheduled mode with tasks, ensure proper height calculation
        if self.show_tasks:
            # Let the layout calculate the natural height and add extra space
            layout_height = self.layout().sizeHint().height()
            # Add generous padding to prevent bottom cutoff
            hint.setHeight(layout_height + 30)
            # Ensure proper width - use at least 250px or parent width
            hint.setWidth(max(250, hint.width()))

        return hint

    def _getTaskBorderColor(self, task) -> str:
        """Get border color for individual task based on its priority"""
        from models.task import TaskPriority
        priority_colors = {
            TaskPriority.CRITICAL: "#c0392b",  # Dark red
            TaskPriority.HIGH: "#e74c3c",      # Red
            TaskPriority.MEDIUM: "#f39c12",    # Orange
            TaskPriority.LOW: "#3498db",       # Blue
            TaskPriority.TRIVIAL: "#95a5a6"    # Gray
        }
        return priority_colors.get(task.priority, "#95a5a6")

    def _calculateFontSizeForTitle(self, text: str, max_width: int, default_size: int, bold: bool = False) -> int:
        """
        Calculate font size to ensure single words fit within max_width.
        If any word is too long, reduce font size until it fits.
        """
        from PyQt5.QtGui import QFontMetrics

        if not text:
            return default_size

        min_font_size = 7  # Don't go below 7pt
        words = text.split()

        # Find the longest word
        longest_word = max(words, key=len) if words else text

        for test_size in range(default_size, min_font_size - 1, -1):
            test_font = QFont()
            test_font.setPointSize(test_size)
            test_font.setBold(bold)
            metrics = QFontMetrics(test_font)

            # Check if the longest word fits within max_width
            word_width = metrics.horizontalAdvance(longest_word)

            if word_width <= max_width:
                return test_size

        return min_font_size

    def mousePressEvent(self, event):
        """Handle mouse click to open project detail"""
        from PyQt5.QtCore import Qt

        if self.show_tasks and event.button() == Qt.LeftButton:
            # Find the PlanningScreen parent and call its method
            parent = self.parent()
            while parent:
                if isinstance(parent, PlanningScreen):
                    parent.onProjectClickedFromSchedule(self.project_id)
                    break
                parent = parent.parent()
        super().mousePressEvent(event)

    def _getStatusIcon(self, status):
        """Get icon for task status"""
        from models.task import TaskStatus
        status_icons = {
            TaskStatus.NOT_STARTED: "○",
            TaskStatus.IN_PROGRESS: "◐",
            TaskStatus.COMPLETED: "●",
            TaskStatus.IN_REVIEW: "◑",
            TaskStatus.BLOCKED: "✖",
            TaskStatus.ON_HOLD: "⊝",
            TaskStatus.CANCELLED: "⊗"
        }
        return status_icons.get(status, "○")


class DraggableTaskList(QListWidget):
    """Custom QListWidget that supports drag operations with styled items"""
    taskClicked = pyqtSignal(str)  # task_id
    taskUnscheduled = pyqtSignal(str, str)  # schedule_id, task_id to unschedule
    projectUnscheduled = pyqtSignal(str)  # schedule_id to unschedule

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)  # Accept drops to unschedule tasks
        self.setSelectionMode(QListWidget.SingleSelection)
        self.setSpacing(5)
        self.setResizeMode(QListWidget.Adjust)  # Adjust items to their size hints
        self.setStyleSheet("""
            QListWidget {
                background-color: #1e2a38;
                border: none;
                outline: none;
            }
            QListWidget::item {
                background-color: transparent;
                border: none;
            }
            QListWidget::item:selected {
                background-color: transparent;
            }
        """)
        self.itemClicked.connect(self._onItemClicked)

    def _onItemClicked(self, item):
        """Emit signal when item is clicked"""
        task_id = item.data(Qt.UserRole)
        if task_id:
            self.taskClicked.emit(task_id)

    def resizeEvent(self, event):
        """Update widget widths when list is resized"""
        super().resizeEvent(event)
        list_width = self.viewport().width()
        if list_width <= 0:
            return

        for i in range(self.count()):
            item = self.item(i)
            if not item:
                continue
            widget = self.itemWidget(item)
            if widget and (isinstance(widget, StyledTaskItem) or isinstance(widget, StyledProjectItem)):
                widget.setMinimumWidth(list_width - 10)
                widget.updateGeometry()
                item.setSizeHint(widget.sizeHint())

    def startDrag(self, supportedActions):
        """Override to implement custom drag with task/project data"""
        item = self.currentItem()
        if not item:
            return

        item_id = item.data(Qt.UserRole)
        item_title = item.data(Qt.UserRole + 1)
        item_type = item.data(Qt.UserRole + 2)  # 'project' or None (task)

        if not item_id or not item_title:
            return

        drag = QDrag(self)
        mime_data = QMimeData()
        # Include type in mime data
        if item_type == 'project':
            mime_data.setText(f"{item_id}|{item_title}|project")
        else:
            mime_data.setText(f"{item_id}|{item_title}|task")
        drag.setMimeData(mime_data)
        drag.exec_(Qt.CopyAction)

    def dragEnterEvent(self, event):
        """Accept drag events from scheduled tasks"""
        if event.mimeData().hasText():
            event.acceptProposedAction()
            # Visual feedback
            self.setStyleSheet("""
                QListWidget {
                    background-color: #243447;
                    border: 2px solid #3498db;
                    outline: none;
                }
                QListWidget::item {
                    background-color: transparent;
                    border: none;
                }
                QListWidget::item:selected {
                    background-color: transparent;
                }
            """)

    def dragMoveEvent(self, event):
        """Accept drag move events from scheduled tasks"""
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragLeaveEvent(self, _event):
        """Reset styling when drag leaves"""
        self.setStyleSheet("""
            QListWidget {
                background-color: #1e2a38;
                border: none;
                outline: none;
            }
            QListWidget::item {
                background-color: transparent;
                border: none;
            }
            QListWidget::item:selected {
                background-color: transparent;
            }
        """)

    def dropEvent(self, event):
        """Handle task drop to unschedule"""
        print(f"DraggableTaskList.dropEvent called!")  # Debug

        # Reset styling
        self.setStyleSheet("""
            QListWidget {
                background-color: #1e2a38;
                border: none;
                outline: none;
            }
            QListWidget::item {
                background-color: transparent;
                border: none;
            }
            QListWidget::item:selected {
                background-color: transparent;
            }
        """)

        if event.mimeData().hasText():
            data = event.mimeData().text()
            print(f"Drop data: {data}")  # Debug
            parts = data.split('|')

            # Handle different formats: old (2), medium (4), new (5)
            if len(parts) >= 2:
                item_id = parts[0]
                item_title = parts[1]
                schedule_id = parts[2] if len(parts) >= 3 else ""
                date_str = parts[3] if len(parts) >= 4 else ""
                item_type = parts[4] if len(parts) >= 5 else "task"  # Default to task

                print(f"Unscheduling {item_type}: schedule_id={schedule_id}, id={item_id}")  # Debug

                # Handle unscheduling based on type
                if item_type == 'project':
                    if schedule_id:
                        self.projectUnscheduled.emit(schedule_id)
                    event.acceptProposedAction()
                else:
                    # Task unscheduling
                    if schedule_id:
                        self.taskUnscheduled.emit(schedule_id, item_id)
                    else:
                        # Old behavior - emit empty schedule_id (will unschedule all)
                        self.taskUnscheduled.emit("", item_id)
                    event.acceptProposedAction()
            else:
                print(f"Invalid data format: {parts}")  # Debug
        else:
            print("No text in mime data")  # Debug


class WeeklyViewWidget(QWidget):
    """Custom widget for weekly view with 5-day work week"""

    def __init__(self, planning_screen=None, parent=None):
        super().__init__(parent)
        self.planning_screen = planning_screen
        self.current_week_start = self._getWeekStart(QDate.currentDate())
        self.drop_zones = []
        self.initUI()

    def _getWeekStart(self, date: QDate) -> QDate:
        """Get the Monday of the week containing the given date"""
        days_since_monday = (date.dayOfWeek() - 1) % 7
        return date.addDays(-days_since_monday)

    def initUI(self):
        self.central_widget = QWidget()
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # Navigation
        nav_widget = QWidget()
        nav_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        nav_layout = QHBoxLayout(nav_widget)
        prev_btn = QPushButton("◀ Previous Week")
        next_btn = QPushButton("Next Week ▶")
        prev_btn.setStyleSheet(AppStyles.save_button())
        next_btn.setStyleSheet(AppStyles.save_button())
        prev_btn.clicked.connect(self.previousWeek)
        next_btn.clicked.connect(self.nextWeek)

        self.week_label = QLabel()
        self.week_label.setAlignment(Qt.AlignCenter)
        self.week_label.setStyleSheet(AppStyles.label_lgfnt_bold())

        nav_layout.addWidget(prev_btn)
        nav_layout.addStretch()
        nav_layout.addWidget(self.week_label)
        nav_layout.addStretch()
        nav_layout.addWidget(next_btn)
        self.main_layout.addWidget(nav_widget)

        # Days grid
        days_widget = QWidget()
        days_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.days_layout = QGridLayout(days_widget)
        self.days_layout.setSpacing(10)
        self.main_layout.addWidget(days_widget)

        self.setLayout(self.main_layout)

        self.updateWeekView()

    def updateWeekView(self):
        """Update the week view with current week"""
        # Clear existing widgets
        while self.days_layout.count():
            child = self.days_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self.drop_zones.clear()

        # Update week label
        week_end = self.current_week_start.addDays(4)
        self.week_label.setText(
            f"{self.current_week_start.toString('MMM d')} - {week_end.toString('MMM d, yyyy')}"
        )

        # Create 5 columns (Mon-Fri)
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        today = QDate.currentDate()

        for col, day_name in enumerate(days):
            date = self.current_week_start.addDays(col)
            is_today = date == today

            # Day header
            header = QLabel(f"{day_name}\n{date.toString('MMM d')}")
            header.setAlignment(Qt.AlignCenter)
            header.setMaximumHeight(50)  # Limit header height

            # Apply special styling for today
            if is_today:
                header.setStyleSheet("""
                    QLabel {
                        color: #3498db;
                        font-weight: bold;
                        font-size: 12px;
                        background-color: rgba(52, 152, 219, 0.15);
                        border: 2px solid #3498db;
                        border-radius: 5px;
                        padding: 4px;
                        max-height: 50px;
                    }
                """)
            else:
                header.setStyleSheet("""
                    QLabel {
                        font-weight: bold;
                        font-size: 12px;
                        padding: 4px;
                        max-height: 50px;
                    }
                """)

            self.days_layout.addWidget(header, 0, col)

            # Drop zone
            drop_zone = DropZoneWidget(date, is_today=is_today)
            if self.planning_screen:
                drop_zone.taskDropped.connect(self.planning_screen.onTaskDropped)
                drop_zone.projectDropped.connect(self.planning_screen.onProjectDropped)
                drop_zone.taskClicked.connect(self.planning_screen.onTaskClickedFromSchedule)
                drop_zone.projectClicked.connect(self.planning_screen.onProjectClickedFromSchedule)
            self.drop_zones.append(drop_zone)
            self.days_layout.addWidget(drop_zone, 1, col)

    def previousWeek(self):
        self.current_week_start = self.current_week_start.addDays(-7)
        self.updateWeekView()
        if self.planning_screen:
            self.planning_screen.refreshScheduledTasks()

    def nextWeek(self):
        self.current_week_start = self.current_week_start.addDays(7)
        self.updateWeekView()
        if self.planning_screen:
            self.planning_screen.refreshScheduledTasks()


class DailyViewWidget(QWidget):
    """Widget for daily view"""

    def __init__(self, planning_screen=None, parent=None):
        super().__init__(parent)
        self.planning_screen = planning_screen
        self.current_date = QDate.currentDate()
        self.drop_zone = None
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Navigation
        nav_layout = QHBoxLayout()
        prev_btn = QPushButton("◀ Previous Day")
        next_btn = QPushButton("Next Day ▶")
        prev_btn.setStyleSheet(AppStyles.save_button())
        next_btn.setStyleSheet(AppStyles.save_button())
        prev_btn.clicked.connect(self.previousDay)
        next_btn.clicked.connect(self.nextDay)

        self.date_label = QLabel()
        self.date_label.setAlignment(Qt.AlignCenter)
        self.date_label.setStyleSheet(AppStyles.label_lgfnt_bold())

        nav_layout.addWidget(prev_btn)
        nav_layout.addStretch()
        nav_layout.addWidget(self.date_label)
        nav_layout.addStretch()
        nav_layout.addWidget(next_btn)
        layout.addLayout(nav_layout)

        # Drop zone container
        self.drop_zone_container = QVBoxLayout()
        layout.addLayout(self.drop_zone_container)

        self.updateDayView()

    def updateDayView(self):
        """Update the day view"""
        # Clear existing
        while self.drop_zone_container.count():
            child = self.drop_zone_container.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Check if current date is today
        is_today = self.current_date == QDate.currentDate()

        # Update label with special styling for today
        if is_today:
            self.date_label.setText(f"{self.current_date.toString('dddd, MMMM d, yyyy')} (Today)")
            self.date_label.setStyleSheet("""
                QLabel {
                    color: #3498db;
                    font-weight: bold;
                    font-size: 16px;
                }
            """)
        else:
            self.date_label.setText(self.current_date.toString('dddd, MMMM d, yyyy'))
            from resources.styles import AppStyles
            self.date_label.setStyleSheet(AppStyles.label_lgfnt_bold())

        # Create drop zone
        self.drop_zone = DropZoneWidget(self.current_date, is_today=is_today)
        if self.planning_screen:
            self.drop_zone.taskDropped.connect(self.planning_screen.onTaskDropped)
            self.drop_zone.projectDropped.connect(self.planning_screen.onProjectDropped)
            self.drop_zone.taskClicked.connect(self.planning_screen.onTaskClickedFromSchedule)
            self.drop_zone.projectClicked.connect(self.planning_screen.onProjectClickedFromSchedule)
        self.drop_zone_container.addWidget(self.drop_zone)

    def previousDay(self):
        self.current_date = self.current_date.addDays(-1)
        self.updateDayView()
        if self.planning_screen:
            self.planning_screen.refreshScheduledTasks()

    def nextDay(self):
        self.current_date = self.current_date.addDays(1)
        self.updateDayView()
        if self.planning_screen:
            self.planning_screen.refreshScheduledTasks()


class DropZoneWidget(QWidget):
    """Widget that accepts task drops and displays scheduled tasks"""
    taskDropped = pyqtSignal(QDate, str, str)  # date, task_id, task_title
    projectDropped = pyqtSignal(QDate, str, str)  # date, project_id, project_title
    taskClicked = pyqtSignal(str)  # task_id
    projectClicked = pyqtSignal(str)  # project_id

    def __init__(self, date: QDate, is_today: bool = False, parent=None):
        super().__init__(parent)
        self.date = date
        self.is_today = is_today
        self.scheduled_tasks = []
        self.scheduled_projects = []
        self.setAcceptDrops(True)
        self.setMinimumHeight(150)
        self.setMaximumHeight(600)  # Limit height to make scrolling work
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(5)

        # Custom list widget for dragging
        self.task_list = self._createDraggableList()

        # Apply special styling for today's drop zone
        if self.is_today:
            self.task_list.setStyleSheet(AppStyles.day_column_list_today())
        else:
            self.task_list.setStyleSheet(AppStyles.day_column_list_regular())
        self.task_list.setSpacing(4)
        self.task_list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.task_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.task_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.task_list.itemClicked.connect(self._onTaskClicked)
        self.layout.addWidget(self.task_list)

    def _createDraggableList(self):
        """Create a QListWidget with custom drag support"""
        class DraggableScheduledList(QListWidget):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.setDragEnabled(True)

            def startDrag(self, _supportedActions):
                """Override to provide task/project data for dragging"""
                item = self.currentItem()
                if not item:
                    return

                item_id = item.data(Qt.UserRole)
                if not item_id:
                    return

                # Get schedule_id, date, and type from item data
                schedule_id = item.data(Qt.UserRole + 2) or ""
                date_str = item.data(Qt.UserRole + 3) or ""
                item_type = item.data(Qt.UserRole + 4) or "task"  # Default to task

                # Get title from the item
                parent_widget = self.parent()
                item_title = ""
                while parent_widget:
                    if isinstance(parent_widget, DropZoneWidget):
                        if item_type == 'project':
                            # For projects, title is already in UserRole + 1
                            item_title = item.data(Qt.UserRole + 1) or "Unknown Project"
                        else:
                            # For tasks, try to get from task object
                            task = parent_widget._getTaskById(item_id)
                            if task:
                                item_title = task.title
                            else:
                                item_title = item.text()
                        break
                    parent_widget = parent_widget.parent()
                else:
                    item_title = item.text() if item.text() else "Unknown Item"

                drag = QDrag(self)
                mime_data = QMimeData()
                # Include schedule_id, date, and type in the drag data
                mime_data.setText(f"{item_id}|{item_title}|{schedule_id}|{date_str}|{item_type}")
                drag.setMimeData(mime_data)
                drag.exec_(Qt.CopyAction)

        return DraggableScheduledList()

    def _onTaskClicked(self, item):
        """Handle task or project click"""
        item_id = item.data(Qt.UserRole)
        item_type = item.data(Qt.UserRole + 2)

        if item_id:
            if item_type == 'project':
                self.projectClicked.emit(item_id)
            else:
                self.taskClicked.emit(item_id)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
            self.setStyleSheet("""
                DropZoneWidget {
                    background-color: rgba(52, 152, 219, 0.2);
                    border: 2px solid #3498db;
                    border-radius: 5px;
                }
            """)

    def dragLeaveEvent(self, event):
        self.setStyleSheet("")

    def dropEvent(self, event):
        self.setStyleSheet("")
        if event.mimeData().hasText():
            data = event.mimeData().text()
            parts = data.split('|')
            if len(parts) == 2:
                item_id, item_title = parts
                # Check if this is a project or task by looking at the source item
                # Projects are marked with Qt.UserRole + 2 = 'project' in the source list
                # For now, we'll emit taskDropped and handle project detection in the parent
                self.taskDropped.emit(self.date, item_id, item_title)
                event.acceptProposedAction()
            elif len(parts) == 3:
                # New format: id|title|type (where type is 'project' or 'task')
                item_id, item_title, item_type = parts
                if item_type == 'project':
                    self.projectDropped.emit(self.date, item_id, item_title)
                else:
                    self.taskDropped.emit(self.date, item_id, item_title)
                event.acceptProposedAction()

    def addScheduledTask(self, task_id: str, task_title: str, show_checklist: bool = False, schedule_id: str = None):
        """Add a task to this day's schedule with enhanced display"""
        # Get the full task object to show more details
        task = self._getTaskById(task_id)

        item = QListWidgetItem()
        item.setData(Qt.UserRole, task_id)
        # Store schedule_id and date for unscheduling
        if schedule_id:
            item.setData(Qt.UserRole + 2, schedule_id)  # Store schedule_id
        item.setData(Qt.UserRole + 3, self.date.toString(Qt.ISODate))  # Store date

        if task:
            # Create a styled widget for the scheduled task
            task_widget = QWidget()
            task_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
            task_layout = QVBoxLayout(task_widget)
            task_layout.setContentsMargins(8, 6, 8, 6)
            task_layout.setSpacing(6)
            # Enable the layout to respect heightForWidth from child widgets
            task_layout.setSizeConstraint(QVBoxLayout.SetMinimumSize)

            # Set border color based on completion status or priority
            border_color = self._getBorderColor(task)
            task_widget.setStyleSheet(f"""
                QWidget {{
                    background-color: #2c3e50;
                    border-left: 3px solid {border_color};
                    border-radius: 4px;
                }}
            """)

            # Title - normalize whitespace and create label with dynamic font sizing
            # Normalize multiple spaces to single space and strip trailing/leading spaces
            normalized_title = ' '.join(task.title.split())
            title_label = QLabel(normalized_title)

            # Calculate font size to ensure long words fit
            available_width = 230  # Approximate width accounting for margins and border
            font_size = self._calculateScheduledTaskFontSize(normalized_title, available_width, 10, bold=True)

            title_font = QFont()
            title_font.setPointSize(font_size)
            title_font.setBold(True)
            title_label.setFont(title_font)
            title_label.setWordWrap(True)
            # This is critical: QLabel with wordWrap needs Preferred horizontal policy
            # and the layout needs to respect heightForWidth
            title_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
            # Don't set a fixed height - let it expand based on content
            title_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            task_layout.addWidget(title_label)

            # Info row (priority + category)
            info_layout = QHBoxLayout()
            info_layout.setSpacing(6)

            # Priority badge
            priority_label = QLabel(task.priority.name)
            priority_label.setStyleSheet(self._getPriorityStyle(task.priority))
            info_layout.addWidget(priority_label)

            # Category
            if task.category:
                category_label = QLabel(task.category.value)
                category_label.setStyleSheet("color: #95a5a6; font-size: 9px;")
                info_layout.addWidget(category_label)

            info_layout.addStretch()
            task_layout.addLayout(info_layout)

            # Add unchecked checklist items (only in weekly view)
            if show_checklist and hasattr(task, 'checklist') and task.checklist:
                unchecked_items = [item for item in task.checklist if not item.get('checked', False)]

                if unchecked_items:
                    # Limit to first 3 items to avoid overflow
                    display_items = unchecked_items[:3]

                    for checklist_item in display_items:
                        checklist_label = QLabel(f"☐ {checklist_item['text']}")
                        checklist_label.setStyleSheet("""
                            color: #bdc3c7;
                            font-size: 9px;
                            padding-left: 4px;
                        """)
                        checklist_label.setWordWrap(True)
                        checklist_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
                        task_layout.addWidget(checklist_label)

                    # Show count if there are more items
                    if len(unchecked_items) > 3:
                        more_label = QLabel(f"   +{len(unchecked_items) - 3} more...")
                        more_label.setStyleSheet("color: #7f8c8d; font-size: 8px; font-style: italic;")
                        task_layout.addWidget(more_label)

            # Add comments section
            if hasattr(task, 'entries') and task.entries:
                # Filter only comment entries
                comments = [entry for entry in task.entries if entry.entry_type == "comment"]

                if comments:
                    # Comments header
                    comments_header = QLabel("Comments:")
                    comments_header.setStyleSheet("""
                        color: #95a5a6;
                        font-size: 11px;
                        font-weight: bold;
                        margin-top: 4px;
                    """)
                    task_layout.addWidget(comments_header)

                    # Wrapper to isolate scroll area from parent border
                    scroll_wrapper = QWidget()
                    scroll_wrapper.setStyleSheet("QWidget { border: none; }")
                    scroll_wrapper_layout = QVBoxLayout(scroll_wrapper)
                    scroll_wrapper_layout.setContentsMargins(0, 0, 0, 0)
                    scroll_wrapper_layout.setSpacing(0)

                    # Scrollable comments area
                    comments_scroll = QScrollArea()
                    comments_scroll.setWidgetResizable(True)
                    comments_scroll.setMaximumHeight(60)  # Limit height to keep cards compact
                    comments_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                    comments_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
                    comments_scroll.setStyleSheet(AppStyles.scroll_area())

                    # Container for comments
                    comments_container = QWidget()
                    comments_layout = QVBoxLayout(comments_container)
                    comments_layout.setContentsMargins(4, 4, 4, 4)
                    comments_layout.setSpacing(3)

                    # Show recent comments (last 3)
                    recent_comments = comments[-3:]
                    for entry in recent_comments:
                        comment_label = QLabel(f"• {entry.content}")
                        comment_label.setStyleSheet("""
                            color: #bdc3c7;
                            font-size: 10px;
                            padding: 2px;
                        """)
                        comment_label.setWordWrap(True)
                        comment_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
                        comments_layout.addWidget(comment_label)

                    # Show count if there are more comments
                    if len(comments) > 3:
                        more_comments_label = QLabel(f"+{len(comments) - 3} more comment(s)")
                        more_comments_label.setStyleSheet("""
                            color: #7f8c8d;
                            font-size: 7px;
                            font-style: italic;
                            padding: 2px;
                        """)
                        comments_layout.addWidget(more_comments_label)

                    comments_layout.addStretch()
                    comments_scroll.setWidget(comments_container)
                    scroll_wrapper_layout.addWidget(comments_scroll)
                    task_layout.addWidget(scroll_wrapper)

            # Set proper size policy and constraints
            # Use Expanding horizontally so it fills the width, Minimum vertically to fit content
            task_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

            # Set a maximum width to prevent the widget from expanding beyond the list
            # This will be dynamically updated, but set an initial constraint
            task_widget.setMaximumWidth(16777215)  # Qt's QWIDGETSIZE_MAX

            # Add to list
            self.task_list.addItem(item)
            self.task_list.setItemWidget(item, task_widget)

            # Calculate size hint with proper width constraint
            # The list widget's viewport width is the maximum width available
            list_width = self.task_list.viewport().width()
            if list_width > 0:
                task_widget.setMaximumWidth(list_width - 10)  # Account for margins

            # Force layout to recalculate with the width constraint
            task_layout.activate()
            task_widget.adjustSize()

            # Now get the size hint which should have proper height for wrapped text
            item.setSizeHint(task_widget.sizeHint())
        else:
            # Fallback if task not found
            item.setText(task_title)
            self.task_list.addItem(item)

    def _getTaskById(self, task_id: str):
        """Get task by ID from parent planning screen"""
        parent_widget = self.parent()
        while parent_widget and not isinstance(parent_widget, PlanningScreen):
            parent_widget = parent_widget.parent()

        if parent_widget and hasattr(parent_widget, 'getTaskById'):
            return parent_widget.getTaskById(task_id)
        return None

    def _calculateScheduledTaskFontSize(self, text: str, max_width: int, default_size: int, bold: bool = False) -> int:
        """
        Calculate font size to ensure single words fit within max_width for scheduled tasks.
        If any word is too long, reduce font size until it fits.
        """
        from PyQt5.QtGui import QFontMetrics

        if not text:
            return default_size

        min_font_size = 7  # Don't go below 7pt
        words = text.split()

        # Find the longest word
        longest_word = max(words, key=len) if words else text

        for test_size in range(default_size, min_font_size - 1, -1):
            test_font = QFont()
            test_font.setPointSize(test_size)
            test_font.setBold(bold)
            metrics = QFontMetrics(test_font)

            # Check if the longest word fits within max_width
            word_width = metrics.horizontalAdvance(longest_word)

            if word_width <= max_width:
                return test_size

        return min_font_size

    def _getBorderColor(self, task) -> str:
        """Get border color based on task status and priority"""
        from models.task import TaskStatus

        # If task is completed, return green
        if task.status == TaskStatus.COMPLETED:
            return "#27ae60"  # Green

        # Otherwise, return color based on priority
        priority_colors = {
            TaskPriority.CRITICAL: "#c0392b",  # Dark red
            TaskPriority.HIGH: "#e74c3c",      # Red
            TaskPriority.MEDIUM: "#f39c12",    # Orange
            TaskPriority.LOW: "#3498db",       # Blue
            TaskPriority.TRIVIAL: "#95a5a6"    # Gray
        }
        return priority_colors.get(task.priority, "#95a5a6")

    def _getPriorityStyle(self, priority) -> str:
        """Get style for priority badge"""
        colors = {
            TaskPriority.CRITICAL: "#c0392b",
            TaskPriority.HIGH: "#e74c3c",
            TaskPriority.MEDIUM: "#f39c12",
            TaskPriority.LOW: "#3498db",
            TaskPriority.TRIVIAL: "#95a5a6"
        }
        bg_color = colors.get(priority, "#95a5a6")
        return f"""
            padding: 2px 6px;
            background-color: {bg_color};
            color: white;
            border-radius: 3px;
            font-size: 8px;
            font-weight: bold;
        """

    def addScheduledProject(self, project_data: dict, schedule_id: str = None):
        """Add a project to this day's schedule"""
        item = QListWidgetItem()
        item.setData(Qt.UserRole, project_data['project_id'])
        item.setData(Qt.UserRole + 1, project_data['title'])
        # Store schedule_id and date for unscheduling (same positions as tasks)
        if schedule_id:
            item.setData(Qt.UserRole + 2, schedule_id)
        item.setData(Qt.UserRole + 3, self.date.toString(Qt.ISODate))
        item.setData(Qt.UserRole + 4, 'project')  # Mark as project

        # Create StyledProjectItem widget (show_tasks=True for scheduled projects)
        widget = StyledProjectItem(project_data, self._getLogger(), show_tasks=True)

        # Set proper size policy to fill the list width
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        # Calculate size hint with proper width constraint
        list_width = self.task_list.viewport().width()
        if list_width > 0:
            widget.setMaximumWidth(list_width - 10)  # Account for margins

        # Force widget to calculate its proper size (important for wrapped text)
        widget.adjustSize()
        widget.updateGeometry()

        # Set size hint to match widget's calculated size
        item.setSizeHint(widget.sizeHint())

        self.task_list.addItem(item)
        self.task_list.setItemWidget(item, widget)

    def _getLogger(self):
        """Get logger from parent PlanningScreen"""
        parent_widget = self.parent()
        while parent_widget:
            if isinstance(parent_widget, PlanningScreen):
                return parent_widget.logger
            parent_widget = parent_widget.parent()
        return None

    def clearTasks(self):
        """Clear all scheduled tasks and projects"""
        self.task_list.clear()

    def resizeEvent(self, event):
        """Handle resize to update item sizes"""
        super().resizeEvent(event)
        # Update all list items to recalculate their sizes based on new width
        try:
            list_width = self.task_list.viewport().width()
            if list_width <= 0:
                return

            for i in range(self.task_list.count()):
                item = self.task_list.item(i)
                if not item:
                    continue
                widget = self.task_list.itemWidget(item)
                if widget:
                    # Set maximum width to prevent overflow
                    widget.setMaximumWidth(list_width - 10)
                    # Force the widget to recalculate its size
                    widget.updateGeometry()
                    item.setSizeHint(widget.sizeHint())
        except RuntimeError:
            # Item may have been deleted during iteration
            pass


class PlanningScreen(QWidget):
    """Modern planning screen for scheduling priority tasks"""

    refreshPlanningUI = pyqtSignal()

    def __init__(self, logger: Logger, parent=None):
        super().__init__(parent)
        self.logger = logger
        self.all_tasks: List[Task] = []
        self.scheduled_tasks: Dict[str, ScheduledTask] = {}
        self.scheduled_projects: Dict[str, dict] = {}  # schedule_id -> project data
        self.current_view = "weekly"

        # For task detail dialog
        self.task_detail_dialog = None
        self.overlay = None

        self.initUI()
        self.loadScheduledTasks()
        self.loadScheduledProjects()
        self.loadTasks()
        self.refreshScheduledTasks()

    def refreshPlanningUI(self):
        """Refresh the planning UI"""
        print("PlanningScreen.refreshPlanningUI called!")  # Debug
        self.task_list.clear()
        self.loadScheduledTasks()
        self.loadScheduledProjects()
        self.loadTasks()
        self.refreshScheduledTasks()

    def initUI(self):
        """Initialize the UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header
        header = self.createHeader()
        main_layout.addWidget(header)

        # Main content (two-panel layout)
        splitter = QSplitter(Qt.Horizontal)

        # Left panel: Task list
        left_panel = self.createLeftPanel()
        splitter.addWidget(left_panel)

        # Right panel: Calendar views
        right_panel = self.createRightPanel()
        splitter.addWidget(right_panel)

        # Set initial sizes (30% left, 70% right)
        splitter.setSizes([250, 750])

        main_layout.addWidget(splitter)

    def createHeader(self) -> QWidget:
        """Create the header with title"""
        header = QWidget()
        header.setFixedHeight(100)
        header.setStyleSheet("background-color: #1e2a38;")

        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 10, 20, 10)

        title = QLabel("Planning")
        title.setStyleSheet(AppStyles.label_xlgfnt_bold_dark())
        layout.addWidget(title)
        layout.addStretch()

        return header

    def createLeftPanel(self) -> QWidget:
        """Create the left panel with task list"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(15, 15, 15, 15)
        panel.setStyleSheet(AppStyles.scroll_area())

        # Title
        title = QLabel("Priority Tasks")
        title.setStyleSheet(AppStyles.label_lgfnt_bold())
        layout.addWidget(title)

        # Task list
        self.task_list = DraggableTaskList()
        self.task_list.taskClicked.connect(self.onTaskClickedFromList)
        self.task_list.taskUnscheduled.connect(self.onTaskUnscheduled)
        self.task_list.projectUnscheduled.connect(self.onProjectUnscheduled)
        layout.addWidget(self.task_list)

        return panel

    def createRightPanel(self) -> QWidget:
        """Create the right panel with calendar views"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(15, 15, 15, 15)

        # View selector
        view_selector = self.createViewSelector()
        layout.addWidget(view_selector)

        # View container
        self.view_container = QWidget()
        self.view_layout = QVBoxLayout(self.view_container)
        self.view_layout.setContentsMargins(0, 0, 0, 0)

        # Create views (pass self as planning_screen)
        self.daily_view = DailyViewWidget(planning_screen=self)
        self.weekly_view = WeeklyViewWidget(planning_screen=self)
        self.monthly_view = self.createMonthlyView()

        # Show weekly view by default
        self.view_layout.addWidget(self.weekly_view)
        self.daily_view.hide()
        self.monthly_view.hide()

        layout.addWidget(self.view_container)

        return panel

    def createViewSelector(self) -> QWidget:
        """Create view mode selector"""
        selector = QWidget()
        layout = QHBoxLayout(selector)
        layout.setContentsMargins(0, 0, 0, 10)

        label = QLabel("View:")
        label.setStyleSheet(AppStyles.label_bold())
        layout.addWidget(label)

        self.view_group = QButtonGroup(self)

        daily_radio = QRadioButton("Daily")
        weekly_radio = QRadioButton("Weekly")
        monthly_radio = QRadioButton("Monthly")

        weekly_radio.setChecked(True)

        for radio in [daily_radio, weekly_radio, monthly_radio]:
            radio.setStyleSheet(AppStyles.save_button())
            layout.addWidget(radio)

        self.view_group.addButton(daily_radio, 0)
        self.view_group.addButton(weekly_radio, 1)
        self.view_group.addButton(monthly_radio, 2)
        self.view_group.buttonClicked.connect(self.switchView)

        layout.addStretch()

        return selector

    def createMonthlyView(self) -> QWidget:
        """Create monthly calendar view"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.calendar = QCalendarWidget()
        self.calendar.setStyleSheet(AppStyles.calendar_norm())
        self.calendar.clicked.connect(self.onMonthlyDateClicked)

        layout.addWidget(self.calendar)

        return widget

    def switchView(self, button):
        """Switch between different calendar views"""
        view_id = self.view_group.id(button)

        # Hide all views
        self.daily_view.setParent(None)
        self.weekly_view.setParent(None)
        self.monthly_view.setParent(None)

        # Show selected view
        if view_id == 0:  # Daily
            self.view_layout.addWidget(self.daily_view)
            self.daily_view.show()
            self.current_view = "daily"
        elif view_id == 1:  # Weekly
            self.view_layout.addWidget(self.weekly_view)
            self.weekly_view.show()
            self.current_view = "weekly"
        else:  # Monthly
            self.view_layout.addWidget(self.monthly_view)
            self.monthly_view.show()
            self.current_view = "monthly"

    def loadTasks(self):
        """Load only non-archived tasks into the left panel"""
        self.task_list.clear()

        tasks_dict = load_tasks_from_json(self.logger)
        self.all_tasks = list(tasks_dict.values())

        # Get current week date range (Monday to Friday)
        today = QDate.currentDate()
        days_since_monday = (today.dayOfWeek() - 1) % 7
        week_start = today.addDays(-days_since_monday)
        week_end = week_start.addDays(4)  # Friday

        # Get set of task IDs scheduled for current week
        current_week_task_ids = set()
        for scheduled_task in self.scheduled_tasks.values():
            if week_start <= scheduled_task.scheduled_date <= week_end:
                current_week_task_ids.add(scheduled_task.task_id)

        # Filter for priority tasks
        all_priority_tasks = sorted(
            (task for task in self.all_tasks if not task.archived),
            key=lambda t: t.priority.value,
            reverse=True  # highest priority first
        )

        # Separate tasks into current week and others
        current_week_tasks = [task for task in all_priority_tasks if task.id in current_week_task_ids]
        other_tasks = [task for task in all_priority_tasks if task.id not in current_week_task_ids]

        # Add "Weekly Tasks" header if we have current week tasks
        if current_week_tasks:
            header_item = QListWidgetItem()
            header_widget = QWidget()
            header_widget.setStyleSheet("background-color: transparent;")
            header_layout = QVBoxLayout(header_widget)
            header_layout.setContentsMargins(0, 5, 0, 5)

            header_label = QLabel("Weekly Tasks")
            header_label.setStyleSheet("color: #3498db; font-size: 12px; font-weight: bold; padding: 5px; background-color: transparent;")
            header_label.setAlignment(Qt.AlignLeft)
            header_layout.addWidget(header_label)

            header_item.setSizeHint(header_widget.sizeHint())
            self.task_list.addItem(header_item)
            self.task_list.setItemWidget(header_item, header_widget)

        # Add current week tasks first
        for task in current_week_tasks:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, task.id)
            item.setData(Qt.UserRole + 1, task.title)

            widget = StyledTaskItem(task)
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

            # Set width to fill list
            list_width = self.task_list.viewport().width()
            if list_width > 0:
                widget.setMinimumWidth(list_width - 10)

            widget.adjustSize()
            widget.updateGeometry()
            item.setSizeHint(widget.sizeHint())

            self.task_list.addItem(item)
            self.task_list.setItemWidget(item, widget)

        # Add Projects section (right after Weekly Tasks, before Other Tasks)
        # Load all active projects from projects screen
        from utils.projects_io import load_projects_from_json
        all_projects = load_projects_from_json(self.logger)

        # Filter out archived projects
        active_projects = {
            proj_id: proj for proj_id, proj in all_projects.items()
            if not getattr(proj, 'archived', False)
        }

        if active_projects:
            # Add separator
            project_separator_item = QListWidgetItem()
            project_separator_widget = QWidget()
            project_separator_widget.setStyleSheet("background-color: transparent;")
            project_separator_layout = QVBoxLayout(project_separator_widget)
            project_separator_layout.setContentsMargins(0, 15, 0, 5)
            project_separator_layout.setSpacing(5)

            # Create separator line
            separator_line = QWidget()
            separator_line.setFixedHeight(2)
            separator_line.setStyleSheet("background-color: #27ae60;")  # Green for projects
            project_separator_layout.addWidget(separator_line)

            # Add label
            projects_label = QLabel("📁 Projects")
            projects_label.setStyleSheet("color: #27ae60; font-size: 12px; font-weight: bold; padding: 5px; background-color: transparent;")
            projects_label.setAlignment(Qt.AlignLeft)
            project_separator_layout.addWidget(projects_label)

            project_separator_item.setSizeHint(project_separator_widget.sizeHint())
            self.task_list.addItem(project_separator_item)
            self.task_list.setItemWidget(project_separator_item, project_separator_widget)

            # Add project items
            for project_id, project in active_projects.items():
                item = QListWidgetItem()
                item.setData(Qt.UserRole, project_id)
                item.setData(Qt.UserRole + 1, project.title)
                item.setData(Qt.UserRole + 2, 'project')  # Mark as project

                # Create project data dict for StyledProjectItem
                project_data = {
                    'project_id': project_id,
                    'title': project.title,
                    'scheduled_date': None  # Not scheduled yet
                }

                # Left panel list - simple display without tasks (show_tasks=False)
                widget = StyledProjectItem(project_data, self.logger, show_tasks=False)
                widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

                # Set width to fill list
                list_width = self.task_list.viewport().width()
                if list_width > 0:
                    widget.setMinimumWidth(list_width - 10)

                item.setSizeHint(widget.sizeHint())

                self.task_list.addItem(item)
                self.task_list.setItemWidget(item, widget)

        # Add separator before other tasks if we have both projects and other tasks
        if active_projects and other_tasks:
            separator_item = QListWidgetItem()
            separator_widget = QWidget()
            separator_widget.setStyleSheet("background-color: transparent;")
            separator_layout = QVBoxLayout(separator_widget)
            separator_layout.setContentsMargins(0, 10, 0, 5)
            separator_layout.setSpacing(5)

            # Create separator line
            separator_line = QWidget()
            separator_line.setFixedHeight(2)
            separator_line.setStyleSheet("background-color: #3498db;")
            separator_layout.addWidget(separator_line)

            # Add label
            separator_label = QLabel("Other Tasks")
            separator_label.setStyleSheet("color: #3498db; font-size: 12px; font-weight: bold; padding: 5px; background-color: transparent;")
            separator_label.setAlignment(Qt.AlignLeft)
            separator_layout.addWidget(separator_label)

            separator_item.setSizeHint(separator_widget.sizeHint())
            self.task_list.addItem(separator_item)
            self.task_list.setItemWidget(separator_item, separator_widget)

        # Add other tasks
        for task in other_tasks:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, task.id)
            item.setData(Qt.UserRole + 1, task.title)

            widget = StyledTaskItem(task)
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

            # Set width to fill list
            list_width = self.task_list.viewport().width()
            if list_width > 0:
                widget.setMinimumWidth(list_width - 10)

            widget.adjustSize()
            widget.updateGeometry()
            item.setSizeHint(widget.sizeHint())

            self.task_list.addItem(item)
            self.task_list.setItemWidget(item, widget)

    def loadScheduledTasks(self):
        """Load scheduled tasks from JSON"""
        app_config = AppConfig()
        file_path = Path(app_config.data_dir) / "scheduled_tasks.json"

        if not file_path.exists():
            return

        try:
            with open(file_path, 'r') as f:
                data = json.load(f)

            for schedule_id, task_data in data.items():
                scheduled_task = ScheduledTask(
                    task_id=task_data['task_id'],
                    scheduled_date=QDate.fromString(task_data['date'], Qt.ISODate),
                    task_title=task_data['title']
                )
                scheduled_task.schedule_id = schedule_id
                self.scheduled_tasks[schedule_id] = scheduled_task

            self.refreshScheduledTasks()
        except Exception as e:
            self.logger.error(f"Error loading scheduled tasks: {e}")

    def loadScheduledProjects(self):
        """Load scheduled projects from JSON"""
        from utils.projects_io import load_scheduled_projects

        scheduled_projects_data = load_scheduled_projects(self.logger)
        self.scheduled_projects = {}

        for schedule_id, project_data in scheduled_projects_data.items():
            # Store with QDate for consistency
            self.scheduled_projects[schedule_id] = {
                'project_id': project_data['project_id'],
                'title': project_data['title'],
                'scheduled_date': QDate.fromString(project_data['scheduled_date'], Qt.ISODate),
                'schedule_id': schedule_id
            }

        self.refreshScheduledTasks()  # This also refreshes projects

    def saveScheduledTasks(self):
        """Save scheduled tasks to JSON"""
        app_config = AppConfig()
        file_path = Path(app_config.data_dir) / "scheduled_tasks.json"

        data = {}
        for schedule_id, scheduled_task in self.scheduled_tasks.items():
            data[schedule_id] = {
                'task_id': scheduled_task.task_id,
                'title': scheduled_task.task_title,
                'date': scheduled_task.scheduled_date.toString(Qt.ISODate)
            }

        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving scheduled tasks: {e}")

    def refreshScheduledTasks(self):
        """Refresh all drop zones with scheduled tasks and projects"""
        # Clear all drop zones
        if self.daily_view.drop_zone:
            self.daily_view.drop_zone.clearTasks()

        for drop_zone in self.weekly_view.drop_zones:
            drop_zone.clearTasks()

        # Add scheduled tasks to appropriate drop zones
        for schedule_id, scheduled_task in self.scheduled_tasks.items():
            date = scheduled_task.scheduled_date

            # Daily view - no checklist
            if self.daily_view.drop_zone and self.daily_view.drop_zone.date == date:
                self.daily_view.drop_zone.addScheduledTask(
                    scheduled_task.task_id,
                    scheduled_task.task_title,
                    show_checklist=False,
                    schedule_id=schedule_id
                )

            # Weekly view - show checklist
            for drop_zone in self.weekly_view.drop_zones:
                if drop_zone.date == date:
                    drop_zone.addScheduledTask(
                        scheduled_task.task_id,
                        scheduled_task.task_title,
                        show_checklist=True,
                        schedule_id=schedule_id
                    )

        # Add scheduled projects to appropriate drop zones
        for schedule_id, project_data in self.scheduled_projects.items():
            date = project_data['scheduled_date']

            # Daily view
            if self.daily_view.drop_zone and self.daily_view.drop_zone.date == date:
                self.daily_view.drop_zone.addScheduledProject(
                    project_data,
                    schedule_id=schedule_id
                )

            # Weekly view
            for drop_zone in self.weekly_view.drop_zones:
                if drop_zone.date == date:
                    drop_zone.addScheduledProject(
                        project_data,
                        schedule_id=schedule_id
                    )

    def onTaskDropped(self, date: QDate, task_id: str, task_title: str):
        """Handle task drop event"""
        self.logger.info(f"onTaskDropped called: date={date.toString()}, task_id={task_id}, title={task_title}")

        # Create scheduled task
        scheduled_task = ScheduledTask(task_id, date, task_title)
        self.scheduled_tasks[scheduled_task.schedule_id] = scheduled_task

        self.logger.info(f"Created scheduled task with ID: {scheduled_task.schedule_id}")
        self.logger.info(f"Total scheduled tasks: {len(self.scheduled_tasks)}")

        # Save first, then refresh views and task list
        self.saveScheduledTasks()
        self.loadTasks()  # Refresh the left panel task list
        self.refreshScheduledTasks()

        self.logger.info(f"Successfully scheduled task '{task_title}' for {date.toString()}")

    def onTaskClickedFromList(self, task_id: str):
        """Handle task click from left panel list"""
        task = self.getTaskById(task_id)
        if task:
            self.showTaskDetail(task)

    def onTaskClickedFromSchedule(self, task_id: str):
        """Handle task click from schedule"""
        task = self.getTaskById(task_id)
        if task:
            self.showTaskDetail(task)

    def onProjectDropped(self, date: QDate, project_id: str, project_title: str):
        """Handle project drop event"""
        from utils.projects_io import schedule_project

        self.logger.info(f"onProjectDropped called: date={date.toString()}, project_id={project_id}, title={project_title}")

        # Schedule the project
        date_string = date.toString("yyyy-MM-dd")
        schedule_id = schedule_project(project_id, date_string, self.logger)

        if schedule_id:
            # Reload scheduled projects
            self.loadScheduledProjects()
            # Refresh views
            self.refreshScheduledTasks()
            self.logger.info(f"Successfully scheduled project '{project_title}' for {date.toString()}")
        else:
            self.logger.error(f"Failed to schedule project '{project_title}'")

    def onProjectClickedFromSchedule(self, project_id: str):
        """Handle project click from schedule - open project detail view"""
        from ui.project_files.project_detail_view import ProjectDetailView

        self.logger.info(f"Project clicked from schedule: {project_id}")

        # Get the main window
        window = self.window()

        # Create overlay to dim background
        self.overlay = QWidget(window)
        self.overlay.setStyleSheet("background-color: rgba(0, 0, 0, 0.5);")
        self.overlay.setGeometry(window.rect())
        self.overlay.show()
        self.overlay.installEventFilter(self)

        # Create project detail view
        self.project_detail_dialog = ProjectDetailView(project_id, self.logger, parent=window)
        self.project_detail_dialog.backClicked.connect(self.closeProjectDetail)

        # Size and position
        width = int(window.width() * 0.8)
        height = int(window.height() * 0.9)
        x = (window.width() - width) // 2
        y = (window.height() - height) // 2
        self.project_detail_dialog.setGeometry(x, y, width, height)
        self.project_detail_dialog.show()
        self.project_detail_dialog.raise_()

    def closeProjectDetail(self):
        """Close project detail view"""
        if hasattr(self, 'project_detail_dialog') and self.project_detail_dialog:
            self.project_detail_dialog.close()
            self.project_detail_dialog.deleteLater()
            self.project_detail_dialog = None

        if hasattr(self, 'overlay') and self.overlay:
            self.overlay.hide()
            self.overlay.close()
            self.overlay.deleteLater()
            self.overlay = None

        # Refresh scheduled tasks to update project cards with any task changes
        self.refreshScheduledTasks()

    def onTaskUnscheduled(self, schedule_id: str, task_id: str):
        """Handle task being dragged back to the left panel to unschedule"""
        self.logger.info(f"onTaskUnscheduled called for schedule_id: {schedule_id}, task_id: {task_id}")
        self.logger.info(f"Current scheduled tasks before removal: {len(self.scheduled_tasks)}")

        schedules_to_remove = []

        if schedule_id:
            # Remove only the specific scheduled instance
            if schedule_id in self.scheduled_tasks:
                schedules_to_remove.append(schedule_id)
                self.logger.info(f"Found specific schedule to remove: {schedule_id}")
            else:
                self.logger.warning(f"Schedule ID {schedule_id} not found in scheduled tasks")
        else:
            # Fallback: Find and remove all scheduled instances of this task (old behavior)
            for sched_id, scheduled_task in self.scheduled_tasks.items():
                if scheduled_task.task_id == task_id:
                    schedules_to_remove.append(sched_id)
                    self.logger.info(f"Found schedule to remove: {sched_id} for task {task_id}")

        if not schedules_to_remove:
            self.logger.warning(f"No schedules found to remove")
            return

        # Remove the schedules
        for sched_id in schedules_to_remove:
            del self.scheduled_tasks[sched_id]
            self.logger.info(f"Removed schedule: {sched_id}")

        # Save and refresh
        self.logger.info("Saving scheduled tasks...")
        self.saveScheduledTasks()

        self.logger.info("Refreshing task list and scheduled tasks display...")
        self.loadTasks()  # Refresh the left panel task list
        self.refreshScheduledTasks()

        self.logger.info(f"Unscheduled {len(schedules_to_remove)} instance(s). Remaining scheduled tasks: {len(self.scheduled_tasks)}")

    def onMonthlyDateClicked(self, date: QDate):
        """Handle date click in monthly calendar"""
        # Switch to daily view for clicked date
        self.daily_view.current_date = date
        self.daily_view.updateDayView()
        self.view_group.button(0).setChecked(True)
        self.switchView(self.view_group.button(0))

        # Refresh scheduled tasks for the new date
        self.refreshScheduledTasks()

    def onProjectUnscheduled(self, schedule_id: str):
        """Handle project being dragged back to the left panel to unschedule"""
        from utils.projects_io import unschedule_project

        self.logger.info(f"onProjectUnscheduled called for schedule_id: {schedule_id}")

        if not schedule_id:
            self.logger.warning("No schedule_id provided for project unscheduling")
            return

        # Unschedule the project
        success = unschedule_project(schedule_id, self.logger)

        if success:
            # Reload and refresh
            self.loadScheduledProjects()
            self.refreshScheduledTasks()
            self.logger.info(f"Successfully unscheduled project with schedule_id: {schedule_id}")
        else:
            self.logger.error(f"Failed to unschedule project with schedule_id: {schedule_id}")

    def getTaskById(self, task_id: str) -> Optional[Task]:
        """Get task object by ID"""
        for task in self.all_tasks:
            if task.id == task_id:
                return task
        return None

    def showTaskDetail(self, task: Task):
        """Show task detail using existing TaskCardExpanded widget"""
        # Get the main window
        window = self.window()

        # Create overlay
        self.overlay = QWidget(window)
        self.overlay.setStyleSheet("background-color: rgba(0, 0, 0, 0.5);")
        self.overlay.setGeometry(window.rect())
        self.overlay.show()
        self.overlay.installEventFilter(self)

        # Create task detail dialog
        self.task_detail_dialog = TaskCardExpanded(
            logger=self.logger,
            task=task,
            grid_id=None,
            parent_view=self,
            parent=window
        )

        self.task_detail_dialog.setObjectName("card_container")
        self.task_detail_dialog.setAttribute(Qt.WA_StyledBackground, True)
        self.task_detail_dialog.setStyleSheet(AppStyles.expanded_task_card())

        # Calculate size and center
        card_width, card_height = self.task_detail_dialog.calculate_optimal_card_size(window)
        center_x = (window.width() - card_width) // 2
        center_y = (window.height() - card_height) // 2
        self.task_detail_dialog.setGeometry(center_x, center_y, card_width, card_height)
        self.task_detail_dialog.setWindowFlags(Qt.FramelessWindowHint)

        # Connect close signals
        self.task_detail_dialog.cancelTask.connect(self.closeTaskDetail)
        self.task_detail_dialog.saveCompleted.connect(self.onTaskSaved)
        self.task_detail_dialog.newTaskUpdate.connect(self.onTaskSaved)

        self.task_detail_dialog.show()
        self.task_detail_dialog.raise_()

    def closeTaskDetail(self):
        """Close the task detail dialog"""
        if self.task_detail_dialog:
            self.task_detail_dialog.close()
            self.task_detail_dialog.deleteLater()
            self.task_detail_dialog = None

        if self.overlay:
            self.overlay.hide()  # Hide immediately
            self.overlay.close()
            self.overlay.deleteLater()
            self.overlay = None

    def onTaskSaved(self, _task, _grid_id):
        """Handle task save - refresh task list"""
        # Close the task detail and overlay
        self.closeTaskDetail()

        # Reload tasks to reflect changes in the left panel
        self.task_list.clear()
        self.loadTasks()

        # Refresh scheduled tasks to update any changes
        self.refreshScheduledTasks()

    def eventFilter(self, obj, event):
        """Handle overlay clicks to close dialog"""
        if obj == self.overlay and event.type() == event.MouseButtonPress:
            # Check which dialog is open and close the appropriate one
            if hasattr(self, 'project_detail_dialog') and self.project_detail_dialog:
                self.closeProjectDetail()
            elif hasattr(self, 'task_detail_dialog') and self.task_detail_dialog:
                self.closeTaskDetail()
            return True
        return super().eventFilter(obj, event)