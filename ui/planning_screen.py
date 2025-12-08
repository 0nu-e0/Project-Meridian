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
                             QSizePolicy, QSplitter, QVBoxLayout, QWidget)

# Local application imports
from models.task import Task, TaskPriority
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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        # Title
        title_label = QLabel(self.task.title)
        title_font = QFont()
        title_font.setPointSize(11)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setWordWrap(True)
        layout.addWidget(title_label)

        # Info row (priority + category)
        info_layout = QHBoxLayout()
        info_layout.setSpacing(8)

        # Priority badge
        priority_label = QLabel(self.task.priority.name)
        priority_label.setStyleSheet(self._getPriorityStyle())
        info_layout.addWidget(priority_label)

        # Category
        category_label = QLabel(self.task.category.value)
        category_label.setStyleSheet("color: #95a5a6; font-size: 10px;")
        info_layout.addWidget(category_label)

        info_layout.addStretch()
        layout.addLayout(info_layout)

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


class DraggableTaskList(QListWidget):
    """Custom QListWidget that supports drag operations with styled items"""
    taskClicked = pyqtSignal(str)  # task_id
    taskUnscheduled = pyqtSignal(str)  # task_id to unschedule

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)  # Accept drops to unschedule tasks
        self.setSelectionMode(QListWidget.SingleSelection)
        self.setSpacing(5)
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

    def startDrag(self, supportedActions):
        """Override to implement custom drag with task data"""
        item = self.currentItem()
        if not item:
            return

        task_id = item.data(Qt.UserRole)
        task_title = item.data(Qt.UserRole + 1)

        if not task_id or not task_title:
            return

        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(f"{task_id}|{task_title}")
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
            if len(parts) == 2:
                task_id, task_title = parts
                print(f"Emitting taskUnscheduled for: {task_id}")  # Debug
                # Emit signal to unschedule this task
                self.taskUnscheduled.emit(task_id)
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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Navigation
        nav_layout = QHBoxLayout()
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
        layout.addLayout(nav_layout)

        # Days grid
        self.days_layout = QGridLayout()
        self.days_layout.setSpacing(10)
        layout.addLayout(self.days_layout)

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
        for col, day_name in enumerate(days):
            date = self.current_week_start.addDays(col)

            # Day header
            header = QLabel(f"{day_name}\n{date.toString('MMM d')}")
            header.setAlignment(Qt.AlignCenter)
            header.setStyleSheet(AppStyles.label_bold())
            self.days_layout.addWidget(header, 0, col)

            # Drop zone
            drop_zone = DropZoneWidget(date)
            if self.planning_screen:
                drop_zone.taskDropped.connect(self.planning_screen.onTaskDropped)
                drop_zone.taskClicked.connect(self.planning_screen.onTaskClickedFromSchedule)
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

        # Update label
        self.date_label.setText(self.current_date.toString('dddd, MMMM d, yyyy'))

        # Create drop zone
        self.drop_zone = DropZoneWidget(self.current_date)
        if self.planning_screen:
            self.drop_zone.taskDropped.connect(self.planning_screen.onTaskDropped)
            self.drop_zone.taskClicked.connect(self.planning_screen.onTaskClickedFromSchedule)
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
    taskClicked = pyqtSignal(str)  # task_id

    def __init__(self, date: QDate, parent=None):
        super().__init__(parent)
        self.date = date
        self.scheduled_tasks = []
        self.setAcceptDrops(True)
        self.setMinimumHeight(150)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(5)

        # Custom list widget for dragging
        self.task_list = self._createDraggableList()
        self.task_list.setStyleSheet("""
            QListWidget {
                background-color: #1e2a38;
                border: 2px dashed #34495e;
                border-radius: 5px;
            }
            QListWidget::item {
                padding: 0px;
                background-color: #2c3e50;
                border: 1px solid #34495e;
                border-radius: 4px;
                margin: 3px;
                min-height: 55px;
            }
            QListWidget::item:hover {
                background-color: #34495e;
                border: 1px solid #3498db;
            }
            QListWidget::item:selected {
                background-color: #2980b9;
                border: 1px solid #3498db;
            }
        """)
        self.task_list.setSpacing(4)
        self.task_list.itemClicked.connect(self._onTaskClicked)
        self.layout.addWidget(self.task_list)

    def _createDraggableList(self):
        """Create a QListWidget with custom drag support"""
        class DraggableScheduledList(QListWidget):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.setDragEnabled(True)

            def startDrag(self, _supportedActions):
                """Override to provide task data for dragging"""
                item = self.currentItem()
                if not item:
                    return

                task_id = item.data(Qt.UserRole)
                if not task_id:
                    return

                # Get task title from the item
                parent_widget = self.parent()
                while parent_widget:
                    if isinstance(parent_widget, DropZoneWidget):
                        # Get task object to get title
                        task = parent_widget._getTaskById(task_id)
                        if task:
                            task_title = task.title
                        else:
                            task_title = item.text()
                        break
                    parent_widget = parent_widget.parent()
                else:
                    task_title = item.text() if item.text() else "Unknown Task"

                drag = QDrag(self)
                mime_data = QMimeData()
                mime_data.setText(f"{task_id}|{task_title}")
                drag.setMimeData(mime_data)
                drag.exec_(Qt.CopyAction)

        return DraggableScheduledList()

    def _onTaskClicked(self, item):
        """Handle task click"""
        task_id = item.data(Qt.UserRole)
        if task_id:
            self.taskClicked.emit(task_id)

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
                task_id, task_title = parts
                self.taskDropped.emit(self.date, task_id, task_title)
                event.acceptProposedAction()

    def addScheduledTask(self, task_id: str, task_title: str, show_checklist: bool = False):
        """Add a task to this day's schedule with enhanced display"""
        # Get the full task object to show more details
        task = self._getTaskById(task_id)

        item = QListWidgetItem()
        item.setData(Qt.UserRole, task_id)

        if task:
            # Create a styled widget for the scheduled task
            task_widget = QWidget()
            task_layout = QVBoxLayout(task_widget)
            task_layout.setContentsMargins(8, 6, 8, 6)
            task_layout.setSpacing(4)

            # Set border color based on completion status or priority
            border_color = self._getBorderColor(task)
            task_widget.setStyleSheet(f"""
                QWidget {{
                    background-color: #2c3e50;
                    border-left: 3px solid {border_color};
                    border-radius: 4px;
                }}
            """)

            # Title
            title_label = QLabel(task.title)
            title_font = QFont()
            title_font.setPointSize(10)
            title_font.setBold(True)
            title_label.setFont(title_font)
            title_label.setWordWrap(True)
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
                        task_layout.addWidget(checklist_label)

                    # Show count if there are more items
                    if len(unchecked_items) > 3:
                        more_label = QLabel(f"   +{len(unchecked_items) - 3} more...")
                        more_label.setStyleSheet("color: #7f8c8d; font-size: 8px; font-style: italic;")
                        task_layout.addWidget(more_label)

            item.setSizeHint(task_widget.sizeHint())
            self.task_list.addItem(item)
            self.task_list.setItemWidget(item, task_widget)
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

    def clearTasks(self):
        """Clear all scheduled tasks"""
        self.task_list.clear()


class PlanningScreen(QWidget):
    """Modern planning screen for scheduling priority tasks"""

    refreshPlanningUI = pyqtSignal()

    def __init__(self, logger: Logger, parent=None):
        super().__init__(parent)
        self.logger = logger
        self.all_tasks: List[Task] = []
        self.scheduled_tasks: Dict[str, ScheduledTask] = {}
        self.current_view = "weekly"

        # For task detail dialog
        self.task_detail_dialog = None
        self.overlay = None

        self.initUI()
        self.loadTasks()
        self.loadScheduledTasks()

    def refreshPlanningUI(self):
        """Refresh the planning UI"""
        self.task_list.clear()
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
        splitter.setSizes([300, 700])

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

        # Title
        title = QLabel("Priority Tasks")
        title.setStyleSheet(AppStyles.label_lgfnt_bold())
        layout.addWidget(title)

        # Task list
        self.task_list = DraggableTaskList()
        self.task_list.taskClicked.connect(self.onTaskClickedFromList)
        self.task_list.taskUnscheduled.connect(self.onTaskUnscheduled)
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
        """Load all tasks and filter for high/medium priority"""
        tasks_dict = load_tasks_from_json(self.logger)
        self.all_tasks = list(tasks_dict.values())

        # Filter for priority tasks
        priority_tasks = [
            task for task in self.all_tasks
            if task.priority in [TaskPriority.HIGH, TaskPriority.MEDIUM, TaskPriority.CRITICAL]
        ]

        # Populate list with styled items
        for task in priority_tasks:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, task.id)
            item.setData(Qt.UserRole + 1, task.title)

            styled_widget = StyledTaskItem(task)
            item.setSizeHint(styled_widget.sizeHint())

            self.task_list.addItem(item)
            self.task_list.setItemWidget(item, styled_widget)

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
        """Refresh all drop zones with scheduled tasks"""
        # Clear all drop zones
        if self.daily_view.drop_zone:
            self.daily_view.drop_zone.clearTasks()

        for drop_zone in self.weekly_view.drop_zones:
            drop_zone.clearTasks()

        # Add scheduled tasks to appropriate drop zones
        for scheduled_task in self.scheduled_tasks.values():
            date = scheduled_task.scheduled_date

            # Daily view - no checklist
            if self.daily_view.drop_zone and self.daily_view.drop_zone.date == date:
                self.daily_view.drop_zone.addScheduledTask(
                    scheduled_task.task_id,
                    scheduled_task.task_title,
                    show_checklist=False
                )

            # Weekly view - show checklist
            for drop_zone in self.weekly_view.drop_zones:
                if drop_zone.date == date:
                    drop_zone.addScheduledTask(
                        scheduled_task.task_id,
                        scheduled_task.task_title,
                        show_checklist=True
                    )

    def onTaskDropped(self, date: QDate, task_id: str, task_title: str):
        """Handle task drop event"""
        self.logger.info(f"onTaskDropped called: date={date.toString()}, task_id={task_id}, title={task_title}")

        # Create scheduled task
        scheduled_task = ScheduledTask(task_id, date, task_title)
        self.scheduled_tasks[scheduled_task.schedule_id] = scheduled_task

        self.logger.info(f"Created scheduled task with ID: {scheduled_task.schedule_id}")
        self.logger.info(f"Total scheduled tasks: {len(self.scheduled_tasks)}")

        # Save first, then refresh views
        self.saveScheduledTasks()
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

    def onTaskUnscheduled(self, task_id: str):
        """Handle task being dragged back to the left panel to unschedule"""
        self.logger.info(f"onTaskUnscheduled called for task_id: {task_id}")
        self.logger.info(f"Current scheduled tasks before removal: {len(self.scheduled_tasks)}")

        # Find and remove all scheduled instances of this task
        schedules_to_remove = []
        for schedule_id, scheduled_task in self.scheduled_tasks.items():
            if scheduled_task.task_id == task_id:
                schedules_to_remove.append(schedule_id)
                self.logger.info(f"Found schedule to remove: {schedule_id} for task {task_id}")

        if not schedules_to_remove:
            self.logger.warning(f"No schedules found for task {task_id}")
            return

        # Remove the schedules
        for schedule_id in schedules_to_remove:
            del self.scheduled_tasks[schedule_id]
            self.logger.info(f"Removed schedule: {schedule_id}")

        # Save and refresh
        self.logger.info("Saving scheduled tasks...")
        self.saveScheduledTasks()

        self.logger.info("Refreshing scheduled tasks display...")
        self.refreshScheduledTasks()

        self.logger.info(f"Task {task_id} unscheduled. Remaining scheduled tasks: {len(self.scheduled_tasks)}")

    def onMonthlyDateClicked(self, date: QDate):
        """Handle date click in monthly calendar"""
        # Switch to daily view for clicked date
        self.daily_view.current_date = date
        self.daily_view.updateDayView()
        self.view_group.button(0).setChecked(True)
        self.switchView(self.view_group.button(0))

        # Refresh scheduled tasks for the new date
        self.refreshScheduledTasks()

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
        card_width, card_height = self.task_detail_dialog.calculate_optimal_card_size()
        center_x = (window.width() - card_width) // 2
        center_y = (window.height() - card_height) // 2
        self.task_detail_dialog.setGeometry(center_x, center_y, card_width, card_height)
        self.task_detail_dialog.setWindowFlags(Qt.FramelessWindowHint)

        # Connect close signals
        self.task_detail_dialog.cancelTask.connect(self.closeTaskDetail)
        self.task_detail_dialog.saveCompleted.connect(self.onTaskSaved)

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
            self.closeTaskDetail()
            return True
        return super().eventFilter(obj, event)
