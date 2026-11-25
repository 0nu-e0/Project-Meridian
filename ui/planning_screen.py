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
from logging import Logger
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

# Third-party imports
from PyQt5.QtCore import QDate, QMimeData, QSize, Qt, pyqtSignal
from PyQt5.QtGui import QDrag, QFont, QFontMetrics
from PyQt5.QtWidgets import (QButtonGroup, QCalendarWidget, QFrame, QGridLayout, QHBoxLayout,
                             QLabel, QListWidget, QListWidgetItem, QPushButton, QRadioButton,
                             QSizePolicy, QSplitter, QVBoxLayout, QWidget)

# Local application imports
from models.task import Task, TaskPriority, TaskStatus
from resources.styles import AppStyles
from ui.task_files.task_card_expanded import TaskCardExpanded
from ui.task_files.task_card_lite import badge, elide_lines
from utils.app_config import AppConfig
from utils.tasks_io import load_tasks_from_json
from utils.constants import MAIN_PANEL_STRETCH, SIDE_PANEL_STRETCH
from utils.safe_io import parse_records, read_json, with_unparsed_records, write_json
from resources.styles import AppColors


def parse_drag_text(text):
    """
    Read drag data into (item_id, title, schedule_id, item_type).

    From the task list:  id|title|type
    From a day column:   id|title|schedule_id|date|type
    Titles may contain "|", so fields are read from both ends.
    """
    parts = text.split('|')
    item_id = parts[0]
    item_type = parts[-1] if parts[-1] in ('task', 'project') and len(parts) >= 3 else 'task'
    if item_type != parts[-1]:
        return item_id, '|'.join(parts[1:]), '', item_type
    if len(parts) >= 5 and QDate.fromString(parts[-2], Qt.ISODate).isValid():
        return item_id, '|'.join(parts[1:-3]), parts[-3], item_type
    return item_id, '|'.join(parts[1:-1]), '', item_type


class ScheduledTask:
    """Represents a task scheduled for a specific date/time"""
    def __init__(self, task_id: str, scheduled_date: QDate, task_title: str):
        self.task_id = task_id
        self.scheduled_date = scheduled_date
        self.task_title = task_title
        self.schedule_id = str(uuid4())


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

        # Find current phase (phase marked as is_current)
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
            self.setStyleSheet(f"""
                StyledProjectItem {{
                    background-color: {AppColors.surface};
                    border-radius: 4px;
                }}
                StyledProjectItem:hover {{
                    background-color: {AppColors.surface_raised};
                }}
                QLabel {{
                    background-color: transparent;
                }}
                QCheckBox {{
                    background-color: transparent;
                }}
            """)
        else:
            # List mode: modern card styling matching task cards
            self.setStyleSheet(f"""
                StyledProjectItem {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 {AppColors.surface_raised}, stop:1 {AppColors.surface});
                    border-radius: 8px;
                    border: 1px solid {AppColors.surface_hover_alt};
                    border-left: 4px solid {AppColors.success};
                }}
                StyledProjectItem:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 {AppColors.surface_hover_alt}, stop:1 {AppColors.surface_raised});
                    border: 1px solid {AppColors.success_soft};
                    border-left: 4px solid {AppColors.success_soft};
                }}
                QLabel {{
                    background-color: transparent;
                }}
            """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        if not self.project:
            # Error state
            error_label = QLabel("Project not found")
            error_label.setStyleSheet(f"color: {AppColors.danger}; font-size: 11px;")
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
            title_label.setStyleSheet(f"color: {AppColors.success};")
            title_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            # NO fixed height - let it expand vertically as needed for wrapped text
            layout.addWidget(title_label)

            # Current phase name - normal fixed style (no dynamic sizing)
            if self.current_phase:
                phase_label = QLabel(f"→ {self.current_phase.name}")
                phase_label.setStyleSheet(f"color: {AppColors.accent}; font-size: 10px; font-weight: bold;")
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
                            background-color: {AppColors.surface};
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
                    checkbox.setStyleSheet(f"""
                        QCheckBox {{
                            spacing: 0px;
                            background-color: transparent;
                            border: none;
                        }}
                        QCheckBox::indicator {{
                            width: 12px;
                            height: 12px;
                            border: 1px solid {AppColors.text_muted};
                            border-radius: 2px;
                            background-color: {AppColors.surface};
                        }}
                        QCheckBox::indicator:checked {{
                            background-color: {AppColors.success};
                            border-color: {AppColors.success};
                        }}
                    """)
                    task_layout.addWidget(checkbox)

                    # Task title - normal style with word wrap
                    task_label = QLabel(task.title)
                    task_label.setStyleSheet(f"color: {AppColors.text_secondary}; font-size: 10px; background-color: transparent; border: none;")
                    task_label.setWordWrap(True)
                    task_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
                    task_layout.addWidget(task_label)

                    # Add the task container to the main layout
                    layout.addWidget(task_container)
            else:
                no_tasks_label = QLabel("No incomplete tasks in current phase")
                no_tasks_label.setStyleSheet(f"color: {AppColors.text_faint}; font-size: 9px; font-style: italic;")
                no_tasks_label.setWordWrap(True)
                no_tasks_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
                layout.addWidget(no_tasks_label)
        else:
            # LIST MODE: Display like task cards with status and progress info
            # Title - use pixel-based font for DPI consistency
            title_label = QLabel(self.project.title)
            title_label.setWordWrap(True)
            title_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
            title_label.setStyleSheet("color: white; font-size: 13px; font-weight: bold;")
            layout.addWidget(title_label)

            # Info row (status + progress) - matching task card info row
            info_layout = QHBoxLayout()
            info_layout.setSpacing(8)

            # Status badge (like priority badge in tasks)
            status_label = QLabel(self.project.status.value)
            status_label.setStyleSheet(self._getStatusStyle())
            status_label.setFixedHeight(20)
            status_label.setAlignment(Qt.AlignCenter)
            info_layout.addWidget(status_label)

            # Progress/Phase info (like category in tasks)
            if self.current_phase:
                phase_info = f"{self.current_phase.name}"
            else:
                phase_info = "No phases"

            phase_label = QLabel(phase_info)
            phase_label.setStyleSheet(f"color: {AppColors.text_secondary}; font-size: 11px;")
            phase_label.setFixedHeight(20)
            phase_label.setAlignment(Qt.AlignVCenter)
            info_layout.addWidget(phase_label)

            info_layout.addStretch()
            layout.addLayout(info_layout)

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

    def _getStatusStyle(self) -> str:
        """Get style for status badge (similar to priority badge in tasks)"""
        from models.project import ProjectStatus
        status_colors = {
            ProjectStatus.PLANNING: AppColors.accent,      # Blue
            ProjectStatus.ACTIVE: AppColors.warning,        # Orange
            ProjectStatus.ON_HOLD: AppColors.text_muted,       # Gray
            ProjectStatus.COMPLETED: AppColors.success,     # Green
            ProjectStatus.CANCELLED: AppColors.danger      # Red
        }
        bg_color = status_colors.get(self.project.status, AppColors.text_muted)
        return f"""
            padding: 2px 8px;
            background-color: {bg_color};
            color: white;
            border-radius: 3px;
            font-size: 10px;
            font-weight: bold;
        """

    def _getTaskBorderColor(self, task) -> str:
        """Get border color for individual task based on its priority"""
        priority_colors = {
            TaskPriority.CRITICAL: AppColors.danger_dark,  # Dark red
            TaskPriority.HIGH: AppColors.danger,      # Red
            TaskPriority.MEDIUM: AppColors.warning,    # Orange
            TaskPriority.LOW: AppColors.accent,       # Blue
            TaskPriority.TRIVIAL: AppColors.text_muted    # Gray
        }
        return priority_colors.get(task.priority, AppColors.text_muted)

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
        self.setStyleSheet(f"""
            QListWidget {{
                background-color: {AppColors.surface_sunken};
                border: none;
                outline: none;
            }}
            QListWidget::item {{
                background-color: transparent;
                border: none;
            }}
            QListWidget::item:selected {{
                background-color: transparent;
            }}
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
                widget.setMinimumWidth(list_width - 20)
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
            self.setStyleSheet(f"""
                QListWidget {{
                    background-color: {AppColors.surface_highlight};
                    border: 2px solid {AppColors.accent};
                    outline: none;
                }}
                QListWidget::item {{
                    background-color: transparent;
                    border: none;
                }}
                QListWidget::item:selected {{
                    background-color: transparent;
                }}
            """)

    def dragMoveEvent(self, event):
        """Accept drag move events from scheduled tasks"""
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragLeaveEvent(self, _event):
        """Reset styling when drag leaves"""
        self.setStyleSheet(f"""
            QListWidget {{
                background-color: {AppColors.surface_sunken};
                border: none;
                outline: none;
            }}
            QListWidget::item {{
                background-color: transparent;
                border: none;
            }}
            QListWidget::item:selected {{
                background-color: transparent;
            }}
        """)

    def dropEvent(self, event):
        """Dropping a scheduled task or project back on the list unschedules it"""
        # Reset styling
        self.dragLeaveEvent(event)

        if not event.mimeData().hasText():
            return

        item_id, _title, schedule_id, item_type = parse_drag_text(event.mimeData().text())

        # Items dragged within the list itself have no schedule; there's nothing to undo
        if not schedule_id:
            return

        if item_type == 'project':
            self.projectUnscheduled.emit(schedule_id)
        else:
            self.taskUnscheduled.emit(schedule_id, item_id)
        event.acceptProposedAction()


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
        prev_btn.setToolTip("Go back")
        next_btn = QPushButton("Next Week ▶")
        next_btn.setToolTip("Go forward")
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

    @staticmethod
    def dayCount():
        """5 (Mon-Fri) or 7, depending on Settings"""
        from utils.settings import Settings
        return 7 if Settings.instance().get("planning_show_weekends") else 5

    def updateWeekView(self):
        """Update the week view with current week"""
        # Clear existing widgets
        while self.days_layout.count():
            child = self.days_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self.drop_zones.clear()

        # Update week label
        week_end = self.current_week_start.addDays(self.dayCount() - 1)
        self.week_label.setText(
            f"{self.current_week_start.toString('MMM d')} - {week_end.toString('MMM d, yyyy')}"
        )

        # One column per day (Mon-Fri, or the whole week if weekends are on)
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][:self.dayCount()]
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
                header.setStyleSheet(f"""
                    QLabel {{
                        color: {AppColors.accent};
                        font-weight: bold;
                        font-size: 12px;
                        background-color: rgba(52, 152, 219, 0.15);
                        border: 2px solid {AppColors.accent};
                        border-radius: 5px;
                        padding: 4px;
                        max-height: 50px;
                    }}
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
                drop_zone.scheduleMoved.connect(self.planning_screen.onScheduleMoved)
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
        prev_btn.setToolTip("Go back")
        next_btn = QPushButton("Next Day ▶")
        next_btn.setToolTip("Go forward")
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
            self.date_label.setStyleSheet(f"""
                QLabel {{
                    color: {AppColors.accent};
                    font-weight: bold;
                    font-size: 16px;
                }}
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
            self.drop_zone.scheduleMoved.connect(self.planning_screen.onScheduleMoved)
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


# Room the day list keeps around each item (its stylesheet margins and border)
SCHEDULED_ITEM_MARGINS = 12
# Width to lay out for before a day column has been shown
SCHEDULED_CARD_FALLBACK_WIDTH = 220
SCHEDULED_TITLE_MAX_LINES = 3
SCHEDULED_CHECKLIST_MAX = 3


class ScheduledTaskCard(QFrame):
    """A task placed on a day: readable title, priority and status, category, and open checklist items"""

    def __init__(self, task: Task, show_checklist: bool = False, parent=None, show_comments: bool = True):
        super().__init__(parent)
        self.task = task
        self._fitted_width = None
        self.onHeightChanged = None  # set by the day list, to resize the row
        self.setObjectName("scheduledTaskCard")
        self.setToolTip(task.title)
        self.setStyleSheet(f"""
            QFrame#scheduledTaskCard {{
                background-color: {AppColors.surface};
                border: none;
                border-left: 4px solid {self._accentColor()};
                border-radius: 4px;
            }}
            QFrame#scheduledTaskCard QLabel {{ background: transparent; border: none; }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 8, 8)
        layout.setSpacing(7)

        self.title_label = QLabel()
        title_font = self.title_label.font()
        title_font.setPixelSize(13)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet(f"color: {AppColors.text_primary};")
        layout.addWidget(self.title_label)

        meta = QHBoxLayout()
        meta.setSpacing(6)
        meta.addWidget(badge(task.priority.name.title(), AppColors.get_priority_color(task.priority)))
        meta.addStretch(1)
        layout.addLayout(meta)

        self.detail_labels = []  # (label, text, font): single lines, cut to the width
        if task.status == TaskStatus.COMPLETED:
            self._addLine(layout, f"✓ Completed  ·  {task.category_name}", AppColors.success)
        else:
            self._addLine(layout, task.category_name, AppColors.text_muted)

        if show_checklist:
            unchecked = [entry for entry in (task.checklist or []) if not entry.get('checked', False)]
            for entry in unchecked[:SCHEDULED_CHECKLIST_MAX]:
                self._addLine(layout, f"☐  {entry.get('text', '')}", AppColors.text_secondary)
            if len(unchecked) > SCHEDULED_CHECKLIST_MAX:
                self._addLine(layout, f"+{len(unchecked) - SCHEDULED_CHECKLIST_MAX} more", AppColors.text_faint)

        comments = [entry for entry in (getattr(task, 'entries', None) or []) if entry.entry_type == "comment"]
        if comments and show_comments:
            count = f"{len(comments)} comments" if len(comments) > 1 else "1 comment"
            self._addLine(layout, f"💬  {count}: {' '.join(comments[-1].content.split())}", AppColors.text_secondary)

    def _accentColor(self):
        if self.task.status == TaskStatus.COMPLETED:
            return AppColors.success
        return AppColors.get_priority_color(self.task.priority)

    def _addLine(self, layout, text, color):
        label = QLabel()
        font = label.font()
        font.setPixelSize(11)
        label.setFont(font)
        label.setStyleSheet(f"color: {color};")
        layout.addWidget(label)
        self.detail_labels.append((label, text))

    def fitToWidth(self, width):
        """Wrap and cut the text for this width; returns the height the card needs"""
        self._fitted_width = width
        margins = self.layout().contentsMargins()
        text_width = max(60, width - margins.left() - margins.right())

        title = elide_lines(' '.join(self.task.title.split()), self.title_label.font(), text_width,
                            SCHEDULED_TITLE_MAX_LINES)
        self.title_label.setText(title)
        line_count = len(title.splitlines()) or 1
        self.title_label.setFixedHeight(QFontMetrics(self.title_label.font()).lineSpacing() * line_count + 2)

        for label, text in self.detail_labels:
            metrics = QFontMetrics(label.font())
            label.setText(metrics.elidedText(text, Qt.ElideRight, text_width))

        return self.layout().sizeHint().height()

    def resizeEvent(self, event):
        """Re-fit to the width the list actually gave the card, and grow the row if that needs more room"""
        super().resizeEvent(event)
        if self.width() != self._fitted_width:
            height = self.fitToWidth(self.width())
            if height != self.height():
                self._reportHeight(height)

    def _reportHeight(self, height):
        """Tell the day list this card's new height (so its row fits)"""
        if self.onHeightChanged is None:
            return
        try:
            self.onHeightChanged(height)
        except RuntimeError:
            # Its row was removed (the day was cleared) and the card is on its way out
            self.onHeightChanged = None


class StyledTaskItem(ScheduledTaskCard):
    """A task in the Priority Tasks list: the same card as on the days, without the
    checklist or comments, so long titles wrap (and end in …) instead of being cut off"""

    def __init__(self, task: Task, parent=None):
        super().__init__(task, show_checklist=False, parent=parent, show_comments=False)
        self.onHeightChanged = self._resizeRow

    def sizeHint(self):
        """Width the list gives it (its minimum width, set from the list's width); height to
        fit the text at that width. Not its current width: that's stale when the panel shrinks."""
        width = self.minimumWidth() or SCHEDULED_CARD_FALLBACK_WIDTH
        return QSize(width, self.fitToWidth(width))

    def _resizeRow(self, height):
        """Grow or shrink this card's row in the list when its text re-wraps"""
        owner = self.parent()
        while owner is not None and not isinstance(owner, QListWidget):
            owner = owner.parent()
        if owner is None:
            return
        for row in range(owner.count()):
            item = owner.item(row)
            if owner.itemWidget(item) is self:
                item.setSizeHint(QSize(item.sizeHint().width(), height))
                return


class DropZoneWidget(QWidget):
    """Widget that accepts task drops and displays scheduled tasks"""
    taskDropped = pyqtSignal(QDate, str, str)  # date, task_id, task_title
    projectDropped = pyqtSignal(QDate, str, str)  # date, project_id, project_title
    scheduleMoved = pyqtSignal(QDate, str, str)  # new date, schedule_id, 'task' or 'project'
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
        item_type = item.data(Qt.UserRole + 4)  # Type is stored at UserRole + 4

        if item_id:
            if item_type == 'project':
                self.projectClicked.emit(item_id)
            else:
                self.taskClicked.emit(item_id)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
            self.setStyleSheet(f"""
                DropZoneWidget {{
                    background-color: rgba(52, 152, 219, 0.2);
                    border: 2px solid {AppColors.accent};
                    border-radius: 5px;
                }}
            """)

    def dragLeaveEvent(self, event):
        self.setStyleSheet("")

    def dropEvent(self, event):
        self.setStyleSheet("")
        if not event.mimeData().hasText():
            return

        item_id, item_title, schedule_id, item_type = parse_drag_text(event.mimeData().text())
        if schedule_id:
            # Already scheduled on another day: move it here
            self.scheduleMoved.emit(self.date, schedule_id, item_type)
        elif item_type == 'project':
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
            card = ScheduledTaskCard(task, show_checklist=show_checklist)
            self.task_list.addItem(item)
            self.task_list.setItemWidget(item, card)
            self._fitItem(item, card)
        else:
            # Fallback if task not found
            item.setText(task_title)
            self.task_list.addItem(item)

    def _fitItem(self, item, card):
        """Size a scheduled task card to the column: full width, exactly as tall as its content"""
        width = self.task_list.viewport().width() - SCHEDULED_ITEM_MARGINS
        if width <= 0:
            width = SCHEDULED_CARD_FALLBACK_WIDTH
        item.setSizeHint(QSize(width, card.fitToWidth(width)))
        card.onHeightChanged = lambda height: item.setSizeHint(QSize(item.sizeHint().width(), height))

    def _getTaskById(self, task_id: str):
        """Get task by ID from parent planning screen"""
        parent_widget = self.parent()
        while parent_widget and not isinstance(parent_widget, PlanningScreen):
            parent_widget = parent_widget.parent()

        if parent_widget and hasattr(parent_widget, 'getTaskById'):
            return parent_widget.getTaskById(task_id)
        return None

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
            widget.setMaximumWidth(list_width - 20)  # Account for margins

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
        # The cards are deleted a little after their rows: unhook them first, so a late
        # resize can't reach a row that's already gone
        for row in range(self.task_list.count()):
            card = self.task_list.itemWidget(self.task_list.item(row))
            if isinstance(card, ScheduledTaskCard):
                card.onHeightChanged = None
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
                if isinstance(widget, ScheduledTaskCard):
                    self._fitItem(item, widget)
                elif widget:
                    # Set maximum width to prevent overflow
                    widget.setMaximumWidth(list_width - 20)
                    # Force the widget to recalculate its size
                    widget.updateGeometry()
                    item.setSizeHint(widget.sizeHint())
        except RuntimeError:
            # Item may have been deleted during iteration
            pass


class PlanningScreen(QWidget):
    """Modern planning screen for scheduling priority tasks"""


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

        # Start on the view chosen in Settings
        from utils.settings import Settings
        view_ids = {"daily": 0, "weekly": 1, "monthly": 2}
        default_view = view_ids.get(Settings.instance().get("planning_default_view"), 1)
        if default_view != 1:
            self.view_group.button(default_view).setChecked(True)
            self.switchView(self.view_group.button(default_view))

    def refreshPlanningUI(self):
        """Refresh the planning UI"""
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

        # Main content (two-panel layout)
        splitter = QSplitter(Qt.Horizontal)

        # Left panel: Task list
        left_panel = self.createLeftPanel()
        splitter.addWidget(left_panel)

        # Right panel: Calendar views
        right_panel = self.createRightPanel()
        splitter.addWidget(right_panel)

        # Split left/right using the same ratio as the Notes and Mindmaps screens
        splitter.setStretchFactor(0, SIDE_PANEL_STRETCH)
        splitter.setStretchFactor(1, MAIN_PANEL_STRETCH)
        splitter.setSizes([SIDE_PANEL_STRETCH * 1000, MAIN_PANEL_STRETCH * 1000])

        main_layout.addWidget(splitter)

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
        self.logger.info(f"loadTasks: Loaded {len(self.all_tasks)} total tasks from JSON")

        # Get current week date range (Monday to Friday)
        today = QDate.currentDate()
        days_since_monday = (today.dayOfWeek() - 1) % 7
        week_start = today.addDays(-days_since_monday)
        week_end = week_start.addDays(WeeklyViewWidget.dayCount() - 1)

        # Get set of task IDs scheduled for current week
        current_week_task_ids = set()
        for scheduled_task in self.scheduled_tasks.values():
            if week_start <= scheduled_task.scheduled_date <= week_end:
                current_week_task_ids.add(scheduled_task.task_id)

        # Filter for priority tasks (exclude tasks that belong to projects via phase_id)
        all_priority_tasks = sorted(
            (task for task in self.all_tasks if not task.archived and not task.phase_id),
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
            header_label.setStyleSheet(f"color: {AppColors.accent}; font-size: 12px; font-weight: bold; padding: 5px; background-color: transparent;")
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
                widget.setMinimumWidth(list_width - 20)

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
            separator_line.setStyleSheet(f"background-color: {AppColors.success};")  # Green for projects
            project_separator_layout.addWidget(separator_line)

            # Add label
            projects_label = QLabel("📁 Projects")
            projects_label.setStyleSheet(f"color: {AppColors.success}; font-size: 12px; font-weight: bold; padding: 5px; background-color: transparent;")
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
                    widget.setMinimumWidth(list_width - 20)

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
            separator_line.setStyleSheet(f"background-color: {AppColors.accent};")
            separator_layout.addWidget(separator_line)

            # Add label
            separator_label = QLabel("Other Tasks")
            separator_label.setStyleSheet(f"color: {AppColors.accent}; font-size: 12px; font-weight: bold; padding: 5px; background-color: transparent;")
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
                widget.setMinimumWidth(list_width - 20)

            widget.adjustSize()
            widget.updateGeometry()
            item.setSizeHint(widget.sizeHint())

            self.task_list.addItem(item)
            self.task_list.setItemWidget(item, widget)

    def loadScheduledTasks(self):
        """Load scheduled tasks from JSON"""
        app_config = AppConfig()
        file_path = Path(app_config.data_dir) / "scheduled_tasks.json"

        # Start from what's on disk so entries removed elsewhere don't linger
        self.scheduled_tasks = {}
        if not file_path.exists():
            return

        def parse(schedule_id, task_data):
            scheduled_task = ScheduledTask(
                task_id=task_data['task_id'],
                scheduled_date=QDate.fromString(task_data['date'], Qt.ISODate),
                task_title=task_data['title']
            )
            scheduled_task.schedule_id = schedule_id
            return scheduled_task

        data = read_json(str(file_path), self.logger)
        self.scheduled_tasks = parse_records(str(file_path), data, parse, self.logger)
        self.refreshScheduledTasks()

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

        write_json(str(file_path), with_unparsed_records(str(file_path), data), self.logger)

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

    # Each change to the plan is one undoable step (Ctrl+Z, or Undo on the notice)
    def _recorded(self, label, action, *args):
        from utils.data_history import history
        with history().action(label):
            action(*args)

    def onTaskDropped(self, date: QDate, task_id: str, task_title: str):
        self._recorded(f"Scheduled \u201c{task_title}\u201d", self._onTaskDropped, date, task_id, task_title)

    def onScheduleMoved(self, date: QDate, schedule_id: str, item_type: str):
        self._recorded(f"Moved to {date.toString('ddd MMM d')}", self._onScheduleMoved, date, schedule_id, item_type)

    def onProjectDropped(self, date: QDate, project_id: str, project_title: str):
        self._recorded(f"Scheduled \u201c{project_title}\u201d", self._onProjectDropped, date, project_id,
                       project_title)

    def onTaskUnscheduled(self, schedule_id: str, task_id: str):
        task = self.getTaskById(task_id)
        title = task.title if task else "task"
        self._recorded(f"Unscheduled \u201c{title}\u201d", self._onTaskUnscheduled, schedule_id, task_id)

    def onProjectUnscheduled(self, schedule_id: str):
        self._recorded("Unscheduled a project", self._onProjectUnscheduled, schedule_id)

    def _onTaskDropped(self, date: QDate, task_id: str, task_title: str):
        """Handle task drop event"""
        self.logger.info(f"onTaskDropped called: date={date.toString()}, task_id={task_id}, title={task_title}")

        # Already on this day: scheduling it again would just show it twice
        if any(st.task_id == task_id and st.scheduled_date == date for st in self.scheduled_tasks.values()):
            self.logger.info(f"Task {task_id} is already scheduled for {date.toString()}")
            return

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

    def _onScheduleMoved(self, date: QDate, schedule_id: str, item_type: str):
        """Move a scheduled task or project to another day"""
        if item_type == 'project':
            from utils.projects_io import move_scheduled_project
            if move_scheduled_project(schedule_id, date.toString("yyyy-MM-dd"), self.logger):
                self.loadScheduledProjects()
            return

        scheduled_task = self.scheduled_tasks.get(schedule_id)
        if scheduled_task is None or scheduled_task.scheduled_date == date:
            return

        # If the task is already on the target day, the moved copy is merged into it
        already_there = any(st.task_id == scheduled_task.task_id and st.scheduled_date == date
                            for sid, st in self.scheduled_tasks.items() if sid != schedule_id)
        if already_there:
            del self.scheduled_tasks[schedule_id]
        else:
            scheduled_task.scheduled_date = date

        self.saveScheduledTasks()
        self.loadTasks()  # The "Weekly Tasks" section may change
        self.refreshScheduledTasks()

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

    def _onProjectDropped(self, date: QDate, project_id: str, project_title: str):
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
        """Handle project click from schedule - open expanded project card"""
        from ui.project_files.project_card_expanded import ProjectCardExpanded

        self.logger.info(f"Project clicked from schedule: {project_id}")

        # Close any existing project detail first
        if hasattr(self, 'project_detail_dialog') and self.project_detail_dialog:
            self.closeProjectDetail()

        # Find the scheduled date for this project
        scheduled_date = QDate.currentDate()  # Default
        for project_data in self.scheduled_projects.values():
            if project_data['project_id'] == project_id:
                scheduled_date = project_data['scheduled_date']
                break

        # Get the main window
        window = self.window()

        # Create overlay
        self.overlay = QWidget(window)
        self.overlay.setStyleSheet("background-color: rgba(0, 0, 0, 0.5);")
        self.overlay.setGeometry(window.rect())
        self.overlay.setProperty("coversWindow", True)
        self.overlay.show()
        self.overlay.installEventFilter(self)

        # Create project detail dialog
        self.project_detail_dialog = ProjectCardExpanded(
            project_id=project_id,
            scheduled_date=scheduled_date,
            logger=self.logger,
            parent=window
        )
        self.project_detail_dialog.closeRequested.connect(self.closeProjectDetail)
        self.project_detail_dialog.taskClicked.connect(self.showTaskDetail)  # Open task detail when task is clicked
        self.project_detail_dialog.setObjectName("card_container")
        self.project_detail_dialog.setAttribute(Qt.WA_StyledBackground, True)
        self.project_detail_dialog.setStyleSheet(AppStyles.expanded_task_card())

        # Calculate size and center
        card_width, card_height = ProjectCardExpanded.calculate_optimal_card_size(window)
        center_x = (window.width() - card_width) // 2
        center_y = (window.height() - card_height) // 2
        self.project_detail_dialog.setGeometry(center_x, center_y, card_width, card_height)
        self.project_detail_dialog.setProperty("centeredInWindow", True)
        self.project_detail_dialog.setWindowFlags(Qt.FramelessWindowHint)

        self.project_detail_dialog.show()
        self.project_detail_dialog.raise_()

    def closeProjectDetail(self):
        """Close project detail view"""
        if self.project_detail_dialog:
            self.project_detail_dialog.close()
            self.project_detail_dialog.deleteLater()
            self.project_detail_dialog = None

        if self.overlay:
            self.overlay.hide()
            self.overlay.close()
            self.overlay.deleteLater()
            self.overlay = None

    def _onTaskUnscheduled(self, schedule_id: str, task_id: str):
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
            self.logger.warning("No schedules found to remove")
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

    def _onProjectUnscheduled(self, schedule_id: str):
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
        # Close any existing task detail first
        if hasattr(self, 'task_detail_dialog') and self.task_detail_dialog:
            self.closeTaskDetail()

        # Get the main window
        window = self.window()

        # Create task overlay (separate from project overlay)
        self.task_overlay = QWidget(window)
        self.task_overlay.setStyleSheet("background-color: rgba(0, 0, 0, 0.5);")
        self.task_overlay.setGeometry(window.rect())
        self.task_overlay.setProperty("coversWindow", True)
        self.task_overlay.show()
        self.task_overlay.installEventFilter(self)

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
        self.task_detail_dialog.setProperty("centeredInWindow", True)
        self.task_detail_dialog.setWindowFlags(Qt.FramelessWindowHint)

        # Connect close signals
        self.task_detail_dialog.cancelTask.connect(self.closeTaskDetail)
        self.task_detail_dialog.saveCompleted.connect(self.onTaskSaved)
        self.task_detail_dialog.newTaskUpdate.connect(self.onTaskSaved)
        self.task_detail_dialog.taskDeleted.connect(self.onTaskDeleted)

        self.task_detail_dialog.show()
        self.task_detail_dialog.raise_()

    def closeTaskDetail(self):
        """Close the task detail dialog"""
        if self.task_detail_dialog:
            self.task_detail_dialog.close()
            self.task_detail_dialog.deleteLater()
            self.task_detail_dialog = None

        if hasattr(self, 'task_overlay') and self.task_overlay:
            self.task_overlay.hide()  # Hide immediately
            self.task_overlay.close()
            self.task_overlay.deleteLater()
            self.task_overlay = None

    def _updateSingleTaskInList(self, task):
        """Update a single task in the task list without full reload"""
        # Skip if task is archived or belongs to a project (has phase_id)
        if task.archived or task.phase_id:
            # Task shouldn't be in list - remove it if present
            self._removeTaskFromList(task.id)
            return

        # Find the task in the list by ID
        found_index = None
        for i in range(self.task_list.count()):
            item = self.task_list.item(i)
            if item.data(Qt.UserRole) == task.id:
                found_index = i
                break

        if found_index is not None:
            # Task exists - update the widget
            item = self.task_list.item(found_index)
            widget = StyledTaskItem(task)
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

            list_width = self.task_list.viewport().width()
            if list_width > 0:
                widget.setMinimumWidth(list_width - 20)

            widget.adjustSize()
            widget.updateGeometry()
            item.setSizeHint(widget.sizeHint())

            self.task_list.setItemWidget(item, widget)
        else:
            # Task doesn't exist - do a full reload to properly sort and categorize
            # (This is rare - usually only when creating a new task)
            self.task_list.clear()
            self.loadTasks()

    def _removeTaskFromList(self, task_id):
        """Remove a task from the list by ID"""
        for i in range(self.task_list.count()):
            item = self.task_list.item(i)
            if item.data(Qt.UserRole) == task_id:
                self.task_list.takeItem(i)
                break

    def onTaskSaved(self, task, _grid_id):
        """Handle task save - refresh task list"""
        # Close the task detail and overlay
        self.closeTaskDetail()

        # Optimized: Only update the specific task instead of reloading everything
        self._updateSingleTaskInList(task)

        # Refresh scheduled tasks to update any changes
        self.refreshScheduledTasks()

    def onTaskDeleted(self, task_id_or_title: str):
        """Handle task deletion - refresh task list and close dialog"""
        self.logger.info(f"onTaskDeleted called with: {task_id_or_title}")

        # Close the task detail and overlay
        self.closeTaskDetail()

        # Reload tasks to reflect deletion in the left panel
        self.logger.info("Clearing task list and reloading tasks...")
        self.task_list.clear()
        self.loadTasks()

        # Refresh scheduled tasks in case the deleted task was scheduled
        self.refreshScheduledTasks()

        self.logger.info(f"Task {task_id_or_title} deleted, views refreshed")

    def eventFilter(self, obj, event):
        """Handle overlay clicks to close dialog"""
        from PyQt5.QtCore import QEvent
        if event.type() == QEvent.MouseButtonPress:
            # Handle task overlay clicks (task overlay takes priority)
            if hasattr(self, 'task_overlay') and obj == self.task_overlay:
                # Cancel like the Cancel button, so unsaved edits are undone
                if self.task_detail_dialog is not None:
                    self.task_detail_dialog.cancelTaskChanges()
                else:
                    self.closeTaskDetail()
                return True
            # Handle project overlay clicks
            elif hasattr(self, 'overlay') and obj == self.overlay:
                if hasattr(self, 'project_detail_dialog') and self.project_detail_dialog:
                    self.closeProjectDetail()
                return True
        return super().eventFilter(obj, event)
