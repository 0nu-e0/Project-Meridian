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
# File: task_card_expanded.py
# Description: Used to view and modify tasks.
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

# Standard library imports
import os
from datetime import datetime
from functools import partial

# Third-party imports
from PyQt5.QtCore import QDateTime, QSize, Qt, QTimer, QUrl, pyqtSignal
from PyQt5.QtGui import QColor, QDesktopServices, QGuiApplication, QIcon, QKeySequence, QPixmap, QResizeEvent
from PyQt5.QtWidgets import (QApplication, QCalendarWidget, QComboBox, QDialog, QDialogButtonBox,
                             QDoubleSpinBox, QFileDialog,
                             QGridLayout, QHBoxLayout, QLabel, QLineEdit,
                             QListView, QListWidget, QListWidgetItem, QMenu, QMessageBox,
                             QPushButton, QScrollArea, QShortcut, QSizePolicy, QSpinBox, QSplitter, QStackedWidget,
                             QTabWidget, QTextEdit, QToolButton, QVBoxLayout, QWidget)

# Local application imports
from ui.custom_widgets import dialogs
from models.task import Attachment, Task, TaskCategory, TaskEntry, TaskPriority, TaskStatus, TimeLog
from resources.styles import AppStyles
from ui.custom_widgets.collapsable_section import CollapsibleSection
from utils.categories_config import CategoriesConfigManager
from utils.directory_finder import resource_path
from utils.data_manager import DataManager
from utils.tasks_io import update_task_fields
from ui.custom_widgets.rich_text import FormattingToolbar, load_description, save_description, text_area_style
from resources.styles import AppColors

class TaskCardExpanded(QWidget):
    taskDeleted = pyqtSignal(str)
    saveCompleted = pyqtSignal(object, str)  # (task, grid_id)
    cancelTask = pyqtSignal()
    newTaskUpdate = pyqtSignal(object, str)  # (task, grid_id)

    @classmethod
    def calculate_optimal_card_size(cls, parent_window=None):
        # If parent window is provided, use its dimensions instead of screen
        if parent_window:
            window_width = parent_window.width()
            window_height = parent_window.height()
        else:
            # Fallback to screen dimensions
            screen = QGuiApplication.primaryScreen().availableGeometry()
            window_width, window_height = screen.width(), screen.height()

        min_width = 600
        min_height_for_content = 400

        # Use 75% of window width and 85% of window height for better fit
        card_width = int(max(min_width, window_width * 0.75))
        card_height = int(max(min_height_for_content, window_height * 0.85))

        # Ensure card doesn't exceed window dimensions
        card_width = min(card_width, window_width - 40)  # Leave 40px margin
        card_height = min(card_height, window_height - 40)

        return card_width, card_height

    def __init__(self, logger, task=None, grid_id=None, parent_view=None, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.logger = logger
        self.data_manager = DataManager(logger)
        self.task = task
        self.grid_id = grid_id
        self.logger.debug(f"Expanded card grid_id: {self.grid_id}")
        self.parent_view = parent_view
        self.initial_state = None
        self.isNewTask = False
        # Everything saved while the card is open becomes one undoable step when it closes
        from utils.data_history import snapshot
        self._history_before = snapshot()
        self._history_recorded = False
        self._opened_as_new = task is None
        if self.task is not None:
            self.store_initial_task_state()
        else:
            from utils.settings import Settings
            self.task = Task(title="", category=Settings.instance().get("new_task_category"))
            self.isNewTask = True

        self._dirty = False
        self._initial_snapshot = None
        self._changes = {}

        # Initialize widget references to None for proper cleanup
        self._calendar_widget = None

        # Section widget refs — populated during initUI; used by apply_section_visibility()
        self.description_section_widget = None
        self.activity_section_widget = None
        self.status_priority_widget = None
        self.details_section = None
        self.dependencies_section = None
        self.category_section_widget = None
        self.project_phase_section_widget = None

        # Debounce timer for auto-saving checklist changes
        self._save_debounce_timer = QTimer(self)  # Parented, so it dies with the card
        self._save_debounce_timer.setSingleShot(True)
        self._save_debounce_timer.timeout.connect(self._debounced_save)

        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setWindowModality(Qt.ApplicationModal)
        self.setObjectName("card_container")

        screen = QGuiApplication.screenAt(self.geometry().center())
        if not screen:
            screen = QGuiApplication.primaryScreen()
        self._current_screen = screen
        self._current_dpi = screen.logicalDotsPerInch()

        self.initUI()

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        self.checkForDPIChange()

    def showEvent(self, event):
        super().showEvent(event)
        # Saved sizes set while the card was still small get bent by the columns' minimum
        # widths, so apply them again once the card has its real size
        if not getattr(self, '_splitters_restored', False):
            self._splitters_restored = True
            self._restoreSplitterSizes()

    def checkForDPIChange(self):
        """Check if we've moved to a screen with different DPI and update text accordingly"""
        screen = QGuiApplication.screenAt(self.geometry().center())

        if not screen:
            return

        new_dpi = screen.logicalDotsPerInch()

        # Check if screen or DPI has changed
        if not hasattr(self, '_current_dpi'):
            self._current_dpi = new_dpi
            self._current_screen = screen
            return

        if screen != self._current_screen or abs(new_dpi - self._current_dpi) > 1:
            self.logger.debug(f"DPI changed from {self._current_dpi} to {new_dpi}")
            self._current_dpi = new_dpi
            self._current_screen = screen
            self.refreshTextForDPI()

    def refreshTextForDPI(self):
        """Refresh all text elements to match the new screen's DPI"""
        # Force reapply all stylesheets to recalculate font sizes
        self.style().unpolish(self)
        self.style().polish(self)

        # Update all child widgets
        for widget in self.findChildren(QWidget):
            widget.style().unpolish(widget)
            widget.style().polish(widget)

        # Force a complete update
        self.updateGeometry()
        self.update()

    def store_initial_task_state(self):
        """Snapshot the whole task so Cancel can put back every field.

        The card edits the shared task object as you type, so anything left out of
        this snapshot would stay changed after Cancel.
        """
        self.initial_state = self.task.to_dict()

    def initUI(self):
        self.initCentralWidget()
        self.initLeftPanelWidget()
        self.initRightPanelWidget()
        self.apply_section_visibility()

    def initCentralWidget(self):
        self.setObjectName("card_container")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        outer_layout.addWidget(self.stacked_widget)

        # Page 0: main task edit view
        self._main_view_widget = QWidget()
        self._main_view_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.main_layout = QHBoxLayout(self._main_view_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.stacked_widget.addWidget(self._main_view_widget)  # index 0

        # Left and right columns, resizable with the handle between them
        self.columns_splitter = self._makeSplitter(Qt.Horizontal)
        self.main_layout.addWidget(self.columns_splitter)

    def _makeSplitter(self, orientation):
        splitter = QSplitter(orientation)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(4)
        splitter.setStyleSheet(f"""
            QSplitter::handle {{ background: {AppColors.surface_raised}; margin: 1px; border-radius: 1px; }}
            QSplitter::handle:hover {{ background: {AppColors.accent}; }}
        """)
        splitter.splitterMoved.connect(self._saveSplitterSizes)
        return splitter

    def _screenKey(self):
        """Layouts are remembered per screen size, e.g. "3840x1600" """
        screen = self.screen() if self.window().windowHandle() else None
        screen = screen or QApplication.primaryScreen()
        size = screen.availableGeometry().size() if screen else None
        return f"{size.width()}x{size.height()}" if size else "default"

    def _savedLayouts(self):
        from utils.settings import Settings
        saved = Settings.instance().get("task_card_layout") or {}
        if "columns" in saved:  # one layout for every screen, from before sizes were per screen
            saved = {"last": saved}
        saved.setdefault("screens", {})
        return saved

    def _restoreSplitterSizes(self):
        """Reuse the layout from the last time a task was open on a screen this size
        (sizes as shares of the space), or the most recent layout on a new screen size"""
        saved = self._savedLayouts()
        layout = saved["screens"].get(self._screenKey()) or saved.get("last") or {}
        defaults = {"columns": [3, 2], "left": [3, 2]}
        for key, splitter in (("columns", self.columns_splitter), ("left", self.left_splitter)):
            shares = layout.get(key) or defaults[key]
            if len(shares) == splitter.count():
                # Shares become real pixel sizes: Qt doesn't scale sizes that don't add up
                # to the space it has, it hands out the difference its own way
                total = sum(splitter.sizes()) or 1000
                splitter.setSizes([int(share / sum(shares) * total) for share in shares])

    def _saveSplitterSizes(self, *_args):
        from utils.settings import Settings
        layout = {}
        for key, splitter in (("columns", self.columns_splitter), ("left", self.left_splitter)):
            sizes = splitter.sizes()
            total = sum(sizes) or 1
            layout[key] = [round(size / total, 3) for size in sizes]
        saved = self._savedLayouts()
        saved = {"screens": dict(saved["screens"], **{self._screenKey(): layout}), "last": layout}
        Settings.instance().set("task_card_layout", saved)

    def initLeftPanelWidget(self):
        main_widget = QWidget()
        main_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        left_layout = QVBoxLayout(main_widget)
        left_layout.setContentsMargins(15, 15, 10, 0)
        left_layout.addLayout(self.createTitleSection(), 0)

        # Add project/phase section if task has project_id or phase_id
        if hasattr(self.task, 'project_id') and (self.task.project_id or self.task.phase_id):
            left_layout.addLayout(self.createProjectPhaseSection())

        # Description — wrap in a widget so setVisible() works for toggling
        self.description_section_widget = QWidget()
        self.description_section_widget.setStyleSheet("background-color: transparent;")
        self.description_section_widget.setLayout(self.createDescriptionSection())

        # Activity — already returns a QWidget
        self.activity_section_widget = self.createActivitySection()

        # Drag the handle between them to give either more room
        self.left_splitter = self._makeSplitter(Qt.Vertical)
        self.left_splitter.addWidget(self.description_section_widget)
        self.left_splitter.addWidget(self.activity_section_widget)
        left_layout.addWidget(self.left_splitter, 1)

        self.columns_splitter.addWidget(main_widget)

    def initRightPanelWidget(self):
        main_widget = QWidget()
        main_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        right_layout = QVBoxLayout(main_widget)
        right_layout.setContentsMargins(14, 15, 15, 0)

        # Status/Priority — wrap for visibility toggling
        self.status_priority_widget = QWidget()
        self.status_priority_widget.setStyleSheet("background-color: transparent;")
        self.status_priority_widget.setLayout(self.createStatusPrioritySection())
        right_layout.addWidget(self.status_priority_widget)

        # Collapsible sections (details, dependencies, attachments, checklist)
        # Individual section widget refs are stored inside create*Section methods
        right_layout.addLayout(self.initCollapsableSections())

        # Category — wrap for visibility toggling
        self.category_section_widget = QWidget()
        self.category_section_widget.setStyleSheet("background-color: transparent;")
        self.category_section_widget.setLayout(self.createCategorySection())
        right_layout.addWidget(self.category_section_widget)

        # Project/Phase selection — wrap for visibility toggling
        self.project_phase_section_widget = QWidget()
        self.project_phase_section_widget.setStyleSheet("background-color: transparent;")
        self.project_phase_section_widget.setLayout(self.createProjectPhaseSelectionSection())
        right_layout.addWidget(self.project_phase_section_widget)

        right_layout.addLayout(self.createButtonSection())

        self.columns_splitter.addWidget(main_widget)
        self._restoreSplitterSizes()

    def createTitleSection(self):
        title_layout = QVBoxLayout()
        title_layout.setContentsMargins(0, 0, 5, 8)
        title_layout.setSpacing(0)

        # Title input with modern styling
        self.title_edit = QLineEdit(self.task.title if self.task is not None else "")
        self.title_edit.setPlaceholderText("Enter task name...")
        self.title_edit.setStyleSheet(f"""
            QLineEdit {{
                background-color: {AppColors.surface};
                border: 2px solid {AppColors.surface_raised};
                border-radius: 6px;
                padding: 10px 14px;
                color: {AppColors.text_primary};
                font-size: 14px;
                font-weight: bold;
            }}
            QLineEdit:focus {{
                border: 2px solid {AppColors.accent};
                background-color: {AppColors.surface_raised};
            }}
            QLineEdit::placeholder {{
                color: {AppColors.text_faint};
            }}
        """)
        self.title_edit.setCursorPosition(0)  # Show the start of a long title, not the end
        self.title_edit.editingFinished.connect(self._on_title_edit_finished)
        title_layout.addWidget(self.title_edit)

        return title_layout

    def _on_title_edit_finished(self):
        """Wrapper for title edit signal"""
        self.updateTaskTitle(self.title_edit.text())

    def updateTaskTitle(self, new_title):
        """Update the task title in memory"""
        if self.task is not None:
            self.task.title = new_title

    def createProjectPhaseSection(self):
        """Create section showing project and phase information"""
        section_layout = QHBoxLayout()
        section_layout.setContentsMargins(0, 0, 5, 10)
        section_layout.setSpacing(8)

        # Load project and phase names from DataManager
        project_name = None
        phase_name = None

        if self.task.project_id:
            projects = self.data_manager.get_projects()
            project = projects.get(self.task.project_id)
            if project:
                project_name = project.title

        if self.task.phase_id:
            phases = self.data_manager.get_phases()
            phase = phases.get(self.task.phase_id)
            if phase:
                phase_name = phase.name

        # Project label with modern styling
        if project_name:
            project_label = QLabel(f"Project: 📁 {project_name}")
            project_label.setStyleSheet(f"""
                QLabel {{
                    font-size: 11px;
                    color: {AppColors.text_primary};
                    padding: 6px 12px;
                    background-color: rgba(52, 152, 219, 0.15);
                    border: 1px solid {AppColors.accent};
                    border-radius: 5px;
                    font-weight: bold;
                }}
            """)
            section_layout.addWidget(project_label)

        # Phase label with modern styling
        if phase_name:
            phase_label = QLabel(f"▸ {phase_name}")
            phase_label.setStyleSheet(f"""
                QLabel {{
                    font-size: 11px;
                    color: {AppColors.text_primary};
                    padding: 6px 12px;
                    background-color: rgba(39, 174, 96, 0.15);
                    border: 1px solid {AppColors.success};
                    border-radius: 5px;
                    font-weight: bold;
                }}
            """)
            section_layout.addWidget(phase_label)

        section_layout.addStretch()
        return section_layout

    def createStatusPrioritySection(self):
        # Container with horizontal layout
        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(0, 0, 5, 15)
        container_layout.setSpacing(8)

        # Horizontal layout for Status and Priority side by side
        status_priority_layout = QHBoxLayout()
        status_priority_layout.setSpacing(10)

        # Status section
        status_widget = QWidget()
        status_section = QVBoxLayout(status_widget)
        status_section.setContentsMargins(0, 0, 0, 0)
        status_section.setSpacing(6)

        status_label = QLabel("Status")
        status_label.setStyleSheet(f"""
            QLabel {{
                color: {AppColors.text_secondary};
                font-size: 11px;
                font-weight: bold;
            }}
        """)
        status_section.addWidget(status_label)

        status_combo = QComboBox()
        status_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {AppColors.surface};
                border: 2px solid {AppColors.surface_raised};
                border-radius: 5px;
                padding: 8px 12px;
                color: {AppColors.text_primary};
                font-size: 11px;
            }}
            QComboBox:hover {{
                border: 2px solid {AppColors.accent};
            }}
            QComboBox::drop-down {{
                width: 20px;
                border: none;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {AppColors.text_primary};
                margin-right: 5px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {AppColors.surface};
                border: 2px solid {AppColors.accent};
                selection-background-color: {AppColors.accent};
                color: {AppColors.text_primary};
                padding: 4px;
            }}
        """)
        status_combo.addItems([status.value for status in TaskStatus])
        status_combo.setCurrentText(self.task.status.value if self.task is not None else status_combo.itemText(0))
        status_combo.currentTextChanged.connect(self.updateTaskStatus)
        status_combo.setView(QListView())
        status_section.addWidget(status_combo)

        # Priority section
        priority_widget = QWidget()
        priority_section = QVBoxLayout(priority_widget)
        priority_section.setContentsMargins(0, 0, 0, 0)
        priority_section.setSpacing(6)

        priority_label = QLabel("Priority")
        priority_label.setStyleSheet(f"""
            QLabel {{
                color: {AppColors.text_secondary};
                font-size: 11px;
                font-weight: bold;
            }}
        """)
        priority_section.addWidget(priority_label)

        priority_combo = QComboBox()
        priority_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {AppColors.surface};
                border: 2px solid {AppColors.surface_raised};
                border-radius: 5px;
                padding: 8px 12px;
                color: {AppColors.text_primary};
                font-size: 11px;
            }}
            QComboBox:hover {{
                border: 2px solid {AppColors.accent};
            }}
            QComboBox::drop-down {{
                width: 20px;
                border: none;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {AppColors.text_primary};
                margin-right: 5px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {AppColors.surface};
                border: 2px solid {AppColors.accent};
                selection-background-color: {AppColors.accent};
                color: {AppColors.text_primary};
                padding: 4px;
            }}
        """)
        priority_combo.addItems([priority.name for priority in TaskPriority])
        priority_combo.setCurrentText(self.task.priority.name if self.task is not None else priority_combo.itemText(0))
        priority_combo.currentTextChanged.connect(self.updateTaskPriority)
        priority_combo.setView(QListView())
        priority_section.addWidget(priority_combo)

        # Add both to horizontal layout
        status_priority_layout.addWidget(status_widget)
        status_priority_layout.addWidget(priority_widget)

        container_layout.addLayout(status_priority_layout)
        return container_layout

    def updateTaskStatus(self, new_status: str):
        if self.task is not None:
            for st in TaskStatus:
                if st.value == new_status:
                    self.task.status = st
                    break
            if hasattr(self, 'archive_btn'):
                self._updateArchiveButton()

    def updateTaskPriority(self, new_priority: str):
        if self.task is not None:
            for pr in TaskPriority:
                if pr.name == new_priority:
                    self.task.priority = pr
                    break

    def createDescriptionSection(self):
        desc_layout = QVBoxLayout()
        desc_layout.setContentsMargins(0, 0, 5, 8)
        desc_layout.setSpacing(6)

        header = QHBoxLayout()
        desc_label = QLabel("Description")
        desc_label.setStyleSheet(f"""
            QLabel {{
                color: {AppColors.text_secondary};
                font-size: 11px;
                font-weight: bold;
                padding: 0px;
            }}
        """)
        header.addWidget(desc_label)
        header.addStretch(1)

        # Formatting is kept: pasted lists and paragraphs survive, stored as Markdown
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("Add a description... (pasted lists and formatting are kept)")
        self.desc_edit.setStyleSheet(text_area_style())
        if self.task is not None:
            load_description(self.desc_edit, self.task)
        # Connected after loading, so just opening a task isn't counted as an edit
        self.desc_edit.textChanged.connect(self._on_description_changed)
        QShortcut(QKeySequence("Ctrl+B"), self.desc_edit, context=Qt.WidgetShortcut).activated.connect(
            lambda: self.desc_toolbar.toggleBold())
        QShortcut(QKeySequence("Ctrl+I"), self.desc_edit, context=Qt.WidgetShortcut).activated.connect(
            lambda: self.desc_toolbar.toggleItalic())

        self.desc_toolbar = FormattingToolbar(self.desc_edit)
        header.addWidget(self.desc_toolbar)
        desc_layout.addLayout(header)
        desc_layout.addWidget(self.desc_edit, 1)

        return desc_layout

    def _on_description_changed(self):
        """Keep the task's description in step with the editor"""
        if self.task is not None:
            save_description(self.desc_edit, self.task)

    def updateTaskDescription(self, new_description):
        """Update the task description in memory"""
        if self.task is not None:
            self.task.description = new_description

    def createDatesSection(self):
        dates_layout = QGridLayout()

        # Creation Date (Read-only)
        creation_date_label = QLabel(f"Created: {self.task.creation_date.strftime('%m / %d / %Y') if self.task is not None else datetime.now().strftime('%m / %d / %Y')}")
        dates_layout.addWidget(creation_date_label, 0, 0)

        # Due Date with Calendar Icon
        due_date_container = QWidget()
        due_date_layout = QHBoxLayout(due_date_container)
        due_date_layout.setContentsMargins(0, 0, 0, 0)

        # Label to display selected date
        self.due_date_label = QLabel("Select due date")
        if self.task is not None and self.task.due_date:
            self.due_date_label.setText(self.task.due_date.strftime('%m / %d / %Y'))

        # Calendar Button with icon
        calendar_button = QPushButton()
        calendar_button.setToolTip("Pick the due date")
        image_path = resource_path('resources/images/Calendar.png')
        pixmap = QPixmap(image_path)
        calendar_icon = QIcon(pixmap)
        calendar_button.setIcon(calendar_icon)
        calendar_button.setFixedSize(30, 30)
        calendar_button.setIconSize(QSize(30, 30))
        calendar_button.setStyleSheet(AppStyles.button_transparent())
        calendar_button.clicked.connect(self.showCalendar)

        # Removes the due date; only shown while there is one
        self.clear_due_date_button = QPushButton("✕ Clear")
        self.clear_due_date_button.setToolTip("Remove the due date")
        self.clear_due_date_button.setCursor(Qt.PointingHandCursor)
        self.clear_due_date_button.setStyleSheet(f"""
            QPushButton {{ border: none; background: transparent; color: {AppColors.text_muted}; font-size: 11px; }}
            QPushButton:hover {{ color: {AppColors.danger}; }}
        """)
        self.clear_due_date_button.clicked.connect(self.clearDueDate)
        self.clear_due_date_button.setVisible(self.task is not None and self.task.due_date is not None)

        due_date_layout.addWidget(QLabel("Due Date:"))
        due_date_layout.addWidget(self.due_date_label)
        due_date_layout.addWidget(calendar_button)
        due_date_layout.addWidget(self.clear_due_date_button)
        due_date_layout.addStretch()

        dates_layout.addWidget(due_date_container, 1, 0, 1, 2)

        return dates_layout

    def showCalendar(self):
        # Close any existing instance
        if hasattr(self, '_calendar_widget') and self._calendar_widget is not None:
            self._calendar_widget.close()
            self._calendar_widget = None

        calendar = QCalendarWidget(self)
        calendar.setAttribute(Qt.WA_DeleteOnClose)
        self._calendar_widget = calendar
        calendar.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        calendar.setGridVisible(True)
        calendar.setSelectionMode(QCalendarWidget.SingleSelection)
        calendar.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        calendar.setDateEditEnabled(True)
        calendar.setFirstDayOfWeek(Qt.Sunday)

        # style tweaks ...
        format_saturday = calendar.weekdayTextFormat(Qt.Saturday)
        format_sunday = calendar.weekdayTextFormat(Qt.Sunday)
        format_saturday.setForeground(QColor(AppColors.calendar_weekend))
        format_sunday.setForeground(QColor(AppColors.calendar_weekend))
        calendar.setWeekdayTextFormat(Qt.Saturday, format_saturday)
        calendar.setWeekdayTextFormat(Qt.Sunday, format_sunday)

        # icons → text arrows
        prev_button = calendar.findChild(QToolButton, "qt_calendar_prevmonth")
        next_button = calendar.findChild(QToolButton, "qt_calendar_nextmonth")
        if prev_button:
            prev_button.setText("<"); prev_button.setIcon(QIcon()); prev_button.setStyleSheet(AppStyles.button_calendar_horizontal())
        if next_button:
            next_button.setText(">"); next_button.setIcon(QIcon()); next_button.setStyleSheet(AppStyles.button_calendar_horizontal())

        year_spinbox = calendar.findChild(QSpinBox, "qt_calendar_yearedit")
        if year_spinbox:
            up_button = year_spinbox.findChild(QToolButton, "qt_spinbox_upbutton")
            down_button = year_spinbox.findChild(QToolButton, "qt_spinbox_downbutton")
            if up_button:
                up_button.setText("▲"); up_button.setIcon(QIcon()); up_button.setStyleSheet(AppStyles.button_calendar_vertical())
            if down_button:
                down_button.setText("▼"); down_button.setIcon(QIcon()); down_button.setStyleSheet(AppStyles.button_calendar_vertical())
            year_spinbox.setAttribute(Qt.WA_MacShowFocusRect, 0)

        calendar.setStyleSheet(AppStyles.calendar_norm())

        if self.task and self.task.due_date:
            # QDate from Python date
            qd = QDateTime(self.task.due_date).date()
            calendar.setSelectedDate(qd)

        button = self.sender()
        pos = button.mapToGlobal(button.rect().bottomLeft())
        calendar.move(pos)

        calendar.clicked.connect(self.updateDueDate)
        calendar.show()

    def updateDueDate(self, date):
        # Store a datetime like the rest of the app (a bare date breaks comparisons)
        self.task.due_date = datetime.combine(date.toPyDate(), datetime.min.time())
        self.due_date_label.setText(date.toString('MM / dd / yyyy'))
        self.clear_due_date_button.setVisible(True)
        if hasattr(self, '_calendar_widget') and self._calendar_widget:
            self._calendar_widget.close()
            self._calendar_widget = None

    def clearDueDate(self):
        self.task.due_date = None
        self.due_date_label.setText("Select due date")
        self.clear_due_date_button.setVisible(False)

    def createCategorySection(self):
        category_layout = QVBoxLayout()
        category_layout.setContentsMargins(0, 0, 5, 10)
        category_layout.setSpacing(6)

        category_label = QLabel("Category")
        category_label.setStyleSheet(f"""
            QLabel {{
                color: {AppColors.text_secondary};
                font-size: 11px;
                font-weight: bold;
            }}
        """)
        category_layout.addWidget(category_label)

        category_combo = QComboBox()
        category_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {AppColors.surface};
                border: 2px solid {AppColors.surface_raised};
                border-radius: 5px;
                padding: 8px 12px;
                color: {AppColors.text_primary};
                font-size: 11px;
            }}
            QComboBox:hover {{
                border: 2px solid {AppColors.accent};
            }}
            QComboBox::drop-down {{
                width: 20px;
                border: none;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {AppColors.text_primary};
                margin-right: 5px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {AppColors.surface};
                border: 2px solid {AppColors.accent};
                selection-background-color: {AppColors.accent};
                color: {AppColors.text_primary};
                padding: 4px;
            }}
        """)
        # Load dynamic categories. Archived is a state (set by completing the task),
        # not a category, so it's only listed for older tasks already in it.
        current_category = self.task.category_name if self.task else None
        categories = [c for c in CategoriesConfigManager.load_categories()
                      if c != TaskCategory.ARCHIVED.value or c == current_category]
        # Keep the task's own category even if it was removed from the list
        if current_category and current_category not in categories:
            categories.append(current_category)
        category_combo.addItems(categories)

        if current_category:
            category_combo.setCurrentText(current_category)
        else:
            category_combo.setCurrentIndex(0)

        category_combo.setView(QListView())
        category_combo.currentTextChanged.connect(self.updateTaskCategory)

        category_layout.addWidget(category_combo)
        return category_layout

    def updateTaskCategory(self, new_category):
        # Update the task object with the new category
        # Try to match with enum first for backward compatibility
        category_found = False
        for category in TaskCategory:
            if category.value == new_category:
                self.task.category = category
                category_found = True
                break

        # If not found in enum, use the string directly (for dynamic categories)
        if not category_found:
            self.task.category = new_category

    def createProjectPhaseSelectionSection(self):
        """Create section for selecting project and phase assignment"""
        section_layout = QHBoxLayout()
        section_layout.setContentsMargins(0, 0, 5, 10)
        section_layout.setSpacing(10)

        # Project selection
        project_container = QVBoxLayout()
        project_container.setSpacing(6)

        project_label = QLabel("Project")
        project_label.setStyleSheet(f"""
            QLabel {{
                color: {AppColors.text_secondary};
                font-size: 11px;
                font-weight: bold;
            }}
        """)
        project_container.addWidget(project_label)

        self.project_combo = QComboBox()
        self.project_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {AppColors.surface};
                border: 2px solid {AppColors.surface_raised};
                border-radius: 5px;
                padding: 8px 12px;
                color: {AppColors.text_primary};
                font-size: 11px;
            }}
            QComboBox:hover {{
                border: 2px solid {AppColors.accent};
            }}
            QComboBox::drop-down {{
                width: 20px;
                border: none;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {AppColors.text_primary};
                margin-right: 5px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {AppColors.surface};
                border: 2px solid {AppColors.accent};
                selection-background-color: {AppColors.accent};
                color: {AppColors.text_primary};
                padding: 4px;
            }}
        """)
        self.project_combo.setView(QListView())
        self.project_combo.currentIndexChanged.connect(self.onProjectChanged)
        project_container.addWidget(self.project_combo)

        # Phase selection
        phase_container = QVBoxLayout()
        phase_container.setSpacing(6)

        phase_label = QLabel("Phase")
        phase_label.setStyleSheet(f"""
            QLabel {{
                color: {AppColors.text_secondary};
                font-size: 11px;
                font-weight: bold;
            }}
        """)
        phase_container.addWidget(phase_label)

        self.phase_combo = QComboBox()
        self.phase_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {AppColors.surface};
                border: 2px solid {AppColors.surface_raised};
                border-radius: 5px;
                padding: 8px 12px;
                color: {AppColors.text_primary};
                font-size: 11px;
            }}
            QComboBox:hover {{
                border: 2px solid {AppColors.accent};
            }}
            QComboBox::drop-down {{
                width: 20px;
                border: none;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {AppColors.text_primary};
                margin-right: 5px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {AppColors.surface};
                border: 2px solid {AppColors.accent};
                selection-background-color: {AppColors.accent};
                color: {AppColors.text_primary};
                padding: 4px;
            }}
        """)
        self.phase_combo.setView(QListView())
        self.phase_combo.currentIndexChanged.connect(self.onPhaseChanged)
        phase_container.addWidget(self.phase_combo)

        section_layout.addLayout(project_container)
        section_layout.addLayout(phase_container)

        # Load and populate projects
        self.loadProjectsAndPhases()

        return section_layout

    def loadProjectsAndPhases(self):
        """Load projects into dropdown and set current selections"""
        # Block signals while populating to prevent unwanted changes to task data
        self.project_combo.blockSignals(True)
        self.phase_combo.blockSignals(True)

        # Get all projects from DataManager
        all_projects = self.data_manager.get_projects()

        # Add "None" option first
        self.project_combo.addItem("(No Project)", None)

        # Add all non-archived projects
        self.project_data = {}
        for project_id, project in all_projects.items():
            if not project.archived:
                self.project_combo.addItem(project.title, project_id)
                self.project_data[project_id] = project

        # Get all phases from DataManager
        self.all_phases = self.data_manager.get_phases()

        # Set current project if task has one
        if self.task.project_id:
            index = self.project_combo.findData(self.task.project_id)
            if index >= 0:
                self.project_combo.setCurrentIndex(index)
        else:
            self.project_combo.setCurrentIndex(0)  # "None"

        # Trigger phase update based on selected project
        self.onProjectChanged(self.project_combo.currentIndex())

        # Unblock signals after initial population
        self.project_combo.blockSignals(False)
        self.phase_combo.blockSignals(False)

    def onProjectChanged(self, index):
        """Handle project selection change - update phase dropdown"""
        # Block phase combo signals while repopulating
        self.phase_combo.blockSignals(True)

        # Clear phase combo
        self.phase_combo.clear()

        # Get selected project ID
        project_id = self.project_combo.itemData(index)

        if project_id is None:
            # No project selected
            self.phase_combo.addItem("(No Phase)", None)
            self.phase_combo.setEnabled(False)
            # Only clear task data if user actively deselected project (signals not blocked)
            if not self.project_combo.signalsBlocked():
                self.task.project_id = None
                self.task.phase_id = None
            self.phase_combo.blockSignals(False)
            return

        # Enable phase combo
        self.phase_combo.setEnabled(True)

        # Add "None" option
        self.phase_combo.addItem("(No Phase)", None)

        # Get project and load its phases
        if project_id in self.project_data:
            project = self.project_data[project_id]
            # Get phases for this project, sorted by order
            project_phases = []
            for phase_id in project.phases:
                if phase_id in self.all_phases:
                    project_phases.append(self.all_phases[phase_id])

            project_phases.sort(key=lambda p: p.order)

            # Add phases to combo
            for phase in project_phases:
                self.phase_combo.addItem(phase.name, phase.id)

        # Update task project_id only if user actively changed it
        if not self.project_combo.signalsBlocked():
            self.task.project_id = project_id

        # Set current phase if task has one
        if self.task.phase_id:
            index = self.phase_combo.findData(self.task.phase_id)
            if index >= 0:
                self.phase_combo.setCurrentIndex(index)
            else:
                # Phase not found in current project, reset to None only if user changed project
                self.phase_combo.setCurrentIndex(0)
                if not self.project_combo.signalsBlocked():
                    self.task.phase_id = None
        else:
            self.phase_combo.setCurrentIndex(0)

        # Unblock phase combo signals
        self.phase_combo.blockSignals(False)

    def onPhaseChanged(self, index):
        """Handle phase selection change"""
        phase_id = self.phase_combo.itemData(index)
        # Only update task if signals are not blocked (user interaction)
        if not self.phase_combo.signalsBlocked():
            self.task.phase_id = phase_id

    def _updateArchiveButton(self):
        if self.task is None:
            self.archive_btn.setVisible(False)
            return
        completed = self.task.status == TaskStatus.COMPLETED
        self.archive_btn.setText("↩ Unarchive" if self.task.archived_by_hand else "🗄 Archive")
        self.archive_btn.setEnabled(not completed)
        self.archive_btn.setToolTip(
            "Completed tasks are archived automatically. Reopen it to bring it back." if completed else
            "Put it back in its group" if self.task.archived_by_hand else
            "Move it to the Archived group without completing it")

    def toggleArchived(self):
        """Archive (or unarchive) the task without changing its status, and save"""
        self.task.set_archived_by_hand(not self.task.archived_by_hand)
        self._updateArchiveButton()
        self._handleSaveClick()

    def _handleSaveClick(self):
        """Handle the save button click - save task and emit appropriate signal"""
        # Pick up a title typed without leaving the field
        self.updateTaskTitle(self.title_edit.text().strip())
        if not self.task.title:
            dialogs.warning(self, "Missing Title", "Please give the task a name before saving.")
            self.title_edit.setFocus()
            return

        # Stop any pending debounced save
        self._save_debounce_timer.stop()

        # Show loading overlay
        self._show_save_overlay()

        # Defer the save so the overlay can paint first. A bound method (not a
        # lambda), so Qt drops the call if the card is closed in the meantime.
        self._pending_save_is_new = self.isNewTask
        QTimer.singleShot(10, self._performPendingSave)

    def _performPendingSave(self):
        self._perform_save(self._pending_save_is_new)

    def _perform_save(self, is_new_task):
        """Actually perform the save operation"""
        try:
            # Keep the card open if the save fails, so nothing typed is lost
            if not self.data_manager.save_task(self.task):
                dialogs.critical(self, "Save Failed",
                                     "The task could not be saved. See app.log for details.")
                return
            self.isNewTask = False

            # Emit the appropriate signal with the task object
            if is_new_task:
                self.saveCompleted.emit(self.task, self.grid_id)
            else:
                self.newTaskUpdate.emit(self.task, self.grid_id)
        finally:
            # Hide loading overlay
            self._hide_save_overlay()

    def _show_save_overlay(self):
        """Show a semi-transparent overlay with loading spinner"""
        # Create overlay widget if it doesn't exist
        if not hasattr(self, '_save_overlay'):
            from PyQt5.QtWidgets import QFrame
            from PyQt5.QtCore import Qt

            self._save_overlay = QFrame(self)
            self._save_overlay.setStyleSheet("""
                QFrame {
                    background-color: rgba(0, 0, 0, 0.5);
                }
            """)

            # Create loading label
            self._save_label = QLabel("Saving...", self._save_overlay)
            self._save_label.setStyleSheet("""
                QLabel {
                    color: white;
                    font-size: 16px;
                    font-weight: bold;
                    background-color: transparent;
                }
            """)
            self._save_label.setAlignment(Qt.AlignCenter)

            # Position label in center
            overlay_layout = QVBoxLayout(self._save_overlay)
            overlay_layout.addWidget(self._save_label)

        # Resize and show overlay
        self._save_overlay.setGeometry(self.rect())
        self._save_overlay.raise_()
        self._save_overlay.show()

        # Force immediate UI update
        QApplication.processEvents()

    def _hide_save_overlay(self):
        """Hide the save overlay"""
        if hasattr(self, '_save_overlay'):
            self._save_overlay.hide()

    def createButtonSection(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 10, 5, 15)
        layout.setSpacing(8)

        # Save button (primary action)
        save_btn = QPushButton("💾 Save")
        save_btn.setToolTip("Save and close")
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {AppColors.success};
                border: 2px solid {AppColors.success};
                border-radius: 6px;
                padding: 10px 20px;
                color: white;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {AppColors.success_light};
                border: 2px solid {AppColors.success_light};
            }}
            QPushButton:pressed {{
                background-color: {AppColors.success_dark};
            }}
        """)
        save_btn.clicked.connect(self._handleSaveClick)
        layout.addWidget(save_btn)

        # Cancel button
        cancel_btn = QPushButton("✖ Cancel")
        cancel_btn.setToolTip("Close without saving changes")
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {AppColors.text_muted};
                border: 2px solid {AppColors.text_muted};
                border-radius: 6px;
                padding: 10px 20px;
                color: white;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {AppColors.text_faint};
                border: 2px solid {AppColors.text_faint};
            }}
            QPushButton:pressed {{
                background-color: {AppColors.border_muted};
            }}
        """)
        cancel_btn.clicked.connect(self.cancelTaskChanges)
        layout.addWidget(cancel_btn)

        # Delete button (warning action)
        delete_btn = QPushButton("🗑 Delete")
        delete_btn.setToolTip("Delete this task (Ctrl+Z brings it back)")
        delete_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {AppColors.danger};
                border: 2px solid {AppColors.danger};
                border-radius: 6px;
                padding: 10px 20px;
                color: white;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {AppColors.danger_dark};
                border: 2px solid {AppColors.danger_dark};
            }}
            QPushButton:pressed {{
                background-color: {AppColors.danger_darker};
            }}
        """)
        delete_btn.clicked.connect(self.deleteTask)
        layout.addWidget(delete_btn)

        # Archive without completing (completed tasks are archived anyway)
        self.archive_btn = QPushButton()
        self.archive_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 2px solid {AppColors.surface_raised};
                border-radius: 6px;
                padding: 10px 14px;
                color: {AppColors.text_primary};
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{ border: 2px solid {AppColors.accent}; }}
            QPushButton:disabled {{ color: {AppColors.text_faint}; }}
        """)
        self.archive_btn.clicked.connect(self.toggleArchived)
        self._updateArchiveButton()
        layout.addWidget(self.archive_btn)

        layout.addStretch()

        # Sections button: add or remove sections on this card (menu right here)
        settings_btn = QPushButton("☰ Sections")
        settings_btn.setToolTip("Add or remove sections on this task's card")
        self.sections_btn = settings_btn
        settings_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 2px solid {AppColors.surface_raised};
                border-radius: 6px;
                padding: 10px 20px;
                color: {AppColors.text_primary};
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {AppColors.surface_raised};
                border: 2px solid {AppColors.accent};
            }}
            QPushButton:pressed {{
                background-color: {AppColors.surface};
            }}
        """)
        settings_btn.clicked.connect(lambda: self.showSectionsMenu(settings_btn))
        layout.addWidget(settings_btn)

        return layout

    def createActivitySection(self):
        # Create a container widget for the activity section
        activity_widget = QWidget()
        activity_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        activity_layout = QVBoxLayout(activity_widget)
        activity_layout.setContentsMargins(0, 0, 5, 15)
        activity_layout.setSpacing(8)

        scroll_content = QWidget()
        scroll_content.setStyleSheet(AppStyles.widget_trans())
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 10, 5, 0)
        scroll_layout.setSpacing(10)

        scroll_area = QScrollArea()
        scroll_area.setStyleSheet(AppStyles.scroll_area())
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setWidget(scroll_content)

        activity_layout.addWidget(scroll_area)

        # Activity section label
        activity_label = QLabel("Activity")
        activity_label.setStyleSheet(f"""
            QLabel {{
                color: {AppColors.text_secondary};
                font-size: 12px;
                font-weight: bold;
                padding-bottom: 4px;
            }}
        """)
        scroll_layout.addWidget(activity_label)

        # Create tab widget with modern styling
        tab_widget = QTabWidget()
        tab_widget.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 2px solid {AppColors.surface_raised};
                border-radius: 6px;
                background-color: {AppColors.surface};
                top: -1px;
            }}
            QTabBar::tab {{
                background-color: {AppColors.surface_raised};
                color: {AppColors.text_muted};
                padding: 10px 24px;
                min-width: 80px;
                border: 2px solid {AppColors.surface_raised};
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 2px;
                font-size: 11px;
                font-weight: bold;
            }}
            QTabBar::tab:selected {{
                background-color: {AppColors.surface};
                color: {AppColors.accent};
                border: 2px solid {AppColors.accent};
                border-bottom: 2px solid {AppColors.surface};
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {AppColors.surface};
                color: {AppColors.text_secondary};
            }}
        """)

        # Comments tab
        comments_tab = QWidget()
        comments_layout = QVBoxLayout(comments_tab)
        comments_layout.setContentsMargins(10, 10, 10, 10)
        comments_layout.setSpacing(8)

        # Add text entry for new comments with modern styling
        comment_input = QTextEdit()
        comment_input.setPlaceholderText("Write a comment...")
        comment_input.setMaximumHeight(90)
        comment_input.setStyleSheet(f"""
            QTextEdit {{
                background-color: {AppColors.surface_raised};
                border: 2px solid {AppColors.accent};
                border-radius: 5px;
                padding: 8px;
                color: {AppColors.text_primary};
                font-size: 11px;
                selection-background-color: {AppColors.accent};
            }}
            QTextEdit:focus {{
                border: 2px solid {AppColors.accent_light};
            }}
        """)

        # Create container for comment input and button
        comment_input_container = QWidget()
        comment_input_layout = QVBoxLayout(comment_input_container)
        comment_input_layout.addWidget(comment_input)

        # Add post button in a horizontal layout to push it right
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.addStretch()
        post_button = QPushButton("💬 Post")
        post_button.setToolTip("Add the comment")
        post_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {AppColors.accent};
                border: 2px solid {AppColors.accent};
                border-radius: 5px;
                padding: 6px 16px;
                color: white;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {AppColors.accent_light};
                border: 2px solid {AppColors.accent_light};
            }}
            QPushButton:pressed {{
                background-color: {AppColors.accent_dark};
            }}
        """)
        button_layout.addWidget(post_button)

        comment_input_layout.addWidget(button_container)
        comments_layout.addWidget(comment_input_container)

        # Add comments list view with modern styling
        self.comments_list = QListWidget()
        self.comments_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.comments_list.setWordWrap(True)
        self.comments_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.comments_list.setStyleSheet(f"""
            QListWidget {{
                background-color: transparent;
                border: none;
                outline: none;
            }}
            QListWidget::item {{
                background-color: {AppColors.surface_raised};
                border: 1px solid {AppColors.accent};
                border-radius: 5px;
                padding: 8px;
                margin: 4px 0px;
            }}
            QListWidget::item:hover {{
                background-color: {AppColors.surface_hover};
            }}
        """)



        comments_layout.addWidget(self.comments_list, 1)

        # Connect signals - pass the input widget
        post_button.clicked.connect(partial(self.add_comment, comment_input))

        # Work Logs tab
        work_logs_tab = QWidget()
        work_logs_layout = QVBoxLayout(work_logs_tab)
        work_logs_layout.setContentsMargins(10, 10, 10, 10)
        work_logs_layout.setSpacing(8)

        # Add new work log entry section
        log_entry = QWidget()
        log_layout = QHBoxLayout(log_entry)
        log_layout.setSpacing(8)

        hours_input = QSpinBox()
        hours_input.setMinimum(0)
        hours_input.setMaximum(24)
        hours_input.setSuffix(" hrs")
        hours_input.setStyleSheet(f"""
            QSpinBox {{
                background-color: {AppColors.surface_raised};
                border: 2px solid {AppColors.accent};
                border-radius: 5px;
                padding: 6px;
                color: {AppColors.text_primary};
                font-size: 11px;
            }}
            QSpinBox:focus {{
                border: 2px solid {AppColors.accent_light};
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                background-color: {AppColors.accent};
                border-radius: 3px;
            }}
            QSpinBox::up-arrow, QSpinBox::down-arrow {{
                width: 8px;
                height: 8px;
            }}
        """)

        log_description = QLineEdit()
        log_description.setPlaceholderText("Describe your work...")
        log_description.setStyleSheet(f"""
            QLineEdit {{
                background-color: {AppColors.surface_raised};
                border: 2px solid {AppColors.accent};
                border-radius: 5px;
                padding: 6px 10px;
                color: {AppColors.text_primary};
                font-size: 11px;
            }}
            QLineEdit:focus {{
                border: 2px solid {AppColors.accent_light};
            }}
        """)

        log_button = QPushButton("⏱ Log")
        log_button.setToolTip("Add the hours to the work log")
        log_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {AppColors.success};
                border: 2px solid {AppColors.success};
                border-radius: 5px;
                padding: 6px 16px;
                color: white;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {AppColors.success_light};
                border: 2px solid {AppColors.success_light};
            }}
            QPushButton:pressed {{
                background-color: {AppColors.success_dark};
            }}
        """)

        log_layout.addWidget(hours_input)
        log_layout.addWidget(log_description, 1)
        log_layout.addWidget(log_button)
        work_logs_layout.addWidget(log_entry)

        # Add work logs list with modern styling
        self.work_logs_list = QListWidget()
        self.work_logs_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.work_logs_list.setWordWrap(True)
        self.work_logs_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.work_logs_list.setStyleSheet(f"""
            QListWidget {{
                background-color: transparent;
                border: none;
                outline: none;
            }}
            QListWidget::item {{
                background-color: {AppColors.surface_raised};
                border: 1px solid {AppColors.success};
                border-radius: 5px;
                padding: 8px;
                margin: 4px 0px;
            }}
            QListWidget::item:hover {{
                background-color: {AppColors.surface_hover};
            }}
        """)

        work_logs_layout.addWidget(self.work_logs_list, 1)

        # Connect to work log method - pass both inputs
        log_button.clicked.connect(partial(self.add_work_log, hours_input, log_description))

        # Add tabs to tab widget
        tab_widget.addTab(comments_tab, " Comments ")
        tab_widget.addTab(work_logs_tab, " Work Logs ")
        scroll_layout.addWidget(tab_widget)

        # Display existing activities
        self.display_activities()
        QApplication.processEvents()

        return activity_widget

    def edit_comment(self, item, comment_label):
        current_text = comment_label.text().split(" - ")[0]
        new_text, ok = dialogs.getText(None, "Edit Comment", "Edit your comment:", QLineEdit.Normal, current_text)

        if ok and new_text.strip():
            timestamp = QDateTime.currentDateTime().toString("MM / dd / yyyy hh:mm")
            comment_label.setText(f"{new_text} - {timestamp} (edited)")
            self.saveActivity(current_text, timestamp, "comment", is_edit=True)


    def delete_comment(self, item):
        comment_label = item.listWidget().itemWidget(item).layout().itemAt(0).widget().text()
        text = comment_label.split(" - ")[0]
        reply = dialogs.question(None, "Delete Comment", "Are you sure you want to delete this comment?", QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            row = item.listWidget().row(item)
            item.listWidget().takeItem(row)
            timestamp = QDateTime.currentDateTime().toString("MM / dd / yyyy hh:mm")
            self.saveActivity(text, timestamp, "comment", is_delete=True)

    def initCollapsableSections(self):
        # Create a vertical layout to return
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setStyleSheet(AppStyles.scroll_area())
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Create content widget for the scroll area
        scroll_content = QWidget()
        scroll_content.setStyleSheet(AppStyles.widget_trans())
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 10, 0, 0)
        scroll_layout.setSpacing(10)

        # Add sections to the scroll content
        details_section = self.createDetailsSection()
        dependencies_section = self.createDependenciesSection()
        attachments_section = self.createAttachmentsSection()
        checklist_section = self.createChecklistSection()

        scroll_layout.addLayout(details_section)
        scroll_layout.addLayout(dependencies_section)
        scroll_layout.addLayout(attachments_section)
        scroll_layout.addLayout(checklist_section)
        scroll_layout.addStretch(1)

        # Set the content widget to the scroll area
        scroll_area.setWidget(scroll_content)

        # Add scroll area to the main layout
        main_layout.addWidget(scroll_area)

        # CRITICAL FIX: Force layout adjustment after a brief delay
        # This mimics what happens during collapse and fixes the layout
        # A bound method (not a lambda), so Qt drops the call if the card closes first
        self._pending_scroll_content = scroll_content
        QTimer.singleShot(10, self._forceScrollLayoutUpdate)

        return main_layout

    def _forceScrollLayoutUpdate(self):
        self.forceLayoutUpdate(self._pending_scroll_content)

    def forceLayoutUpdate(self, widget):
        """Force the widget to update its layout to fit the available space"""
        # This triggers layout recalculation similar to what happens on collapse
        widget.adjustSize()
        widget.updateGeometry()
        # Force a resize of all child CollapsibleSection widgets
        for child in widget.findChildren(CollapsibleSection):
            child.updateGeometry()

    def createDetailsSection(self):
        # Create a layout without a parent widget
        section_layout = QVBoxLayout()
        section_layout.setContentsMargins(0, 0, 15, 0)
        section_layout.setSpacing(5)

        # Details section
        details_section = CollapsibleSection("Details", self)
        details_section.setStyleSheet(AppStyles.border_widget())

        details_section.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)

        # Add your regular details rows
        details_section.add_dates(self.createDatesSection())

        # Add the team list
        details_section.add_team_list()

        # Connect signals to your existing functions
        details_section.team_member_added.connect(self.add_team_member_to_task)
        details_section.team_member_removed.connect(self.remove_team_member_from_task)

        # Load existing team members from the Task object
        if hasattr(self.task, 'collaborators') and self.task.collaborators:
            for member in self.task.collaborators:
                details_section.team_input.setText(member)
                details_section.add_team_member()

        if not self.task.collaborators:
            self.logger.debug("No teams found")
            details_section.toggle_collapsed()
        else:
            self.logger.debug("found teams")

        # Store ref for visibility toggling
        self.details_section = details_section

        # Add section to layout
        section_layout.addWidget(details_section)
        section_layout.addStretch()

        return section_layout

    def createDependenciesSection(self):
        section_layout = QVBoxLayout()
        section_layout.setContentsMargins(0, 0, 15, 0)
        section_layout.setSpacing(5)

        # Dependencies section
        dependencies_section = CollapsibleSection("Dependencies", self)
        dependencies_section.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        dependencies_section.setStyleSheet(AppStyles.border_widget())
        dependencies_section.add_dependencies_list()

        # Update available tasks
        all_tasks = self.load_dependencies()
        dependencies_section.update_available_tasks(self.task.id if self.task is not None else None, all_tasks)

        # Older versions stored dependencies by title; convert any that still match a task
        ids_by_title = {title: task_id for task_id, title in all_tasks.items()}
        self.task.dependencies = {
            dep if dep in all_tasks else ids_by_title.get(dep, dep)
            for dep in self.task.dependencies
        }

        # Connect signals
        dependencies_section.dependency_added.connect(self.add_dependency_to_task)
        dependencies_section.dependency_removed.connect(self.remove_dependency_from_task)

        for dep_id in list(self.task.dependencies):
            dependencies_section.add_dependency(dep_id)

        if not self.task.dependencies:
            dependencies_section.toggle_collapsed()

        # Store ref for visibility toggling
        self.dependencies_section = dependencies_section

        section_layout.addWidget(dependencies_section)
        section_layout.addStretch()

        return section_layout


    def createChecklistSection(self):
        section_layout = QVBoxLayout()
        section_layout.setContentsMargins(0, 0, 15, 0)
        section_layout.setSpacing(5)

        # Create section
        self.checklist_section = CollapsibleSection("Checklist", self)
        self.checklist_section.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.checklist_section.setStyleSheet(AppStyles.border_widget())

        # Add checklist functionality
        self.checklist_section.add_checklist("Task Items")

        # IMPORTANT: Load the existing data BEFORE connecting the signal
        # Load existing BEFORE signals
        for item in self.task.checklist:
            self.checklist_section.checklist_input.setText(item['text'])
            self.checklist_section.add_checklist_item()
            if item.get('checked', False):
                last_idx = len(self.checklist_section.checklist_data) - 1
                if last_idx >= 0:
                    checkbox = self.checklist_section.checklist_data[last_idx].get('checkbox')
                    if checkbox:
                        checkbox.setChecked(True)

        # Connect signals AFTER load
        self.checklist_section.checklist_item_added.connect(self.addChecklistItem)
        self.checklist_section.checkbox_state_changed.connect(self.updateCheckboxState)
        self.checklist_section.checklist_item_removed.connect(self.removeChecklistItem)

        if not self.task.checklist:
            self.checklist_section.toggle_collapsed()

        section_layout.addWidget(self.checklist_section)
        section_layout.addStretch()
        return section_layout

    def createAttachmentsSection(self):
        section_layout = QVBoxLayout()
        section_layout.setContentsMargins(0, 0, 15, 0)
        section_layout.setSpacing(5)

        attachments_section = CollapsibleSection("Attachments", self)
        attachments_section.setStyleSheet(AppStyles.border_widget())
        attachments_section.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # Add attachments list
        if hasattr(self.task, 'attachments') and self.task.attachments:
            attachments_section.add_attachments(self.task.attachments)
        else:
            if self.task is not None:
                self.task.attachments = []
                attachments_section.add_attachments([])

        if not self.task.attachments:
            attachments_section.toggle_collapsed()

        # Connect signals
        attachments_section.attachment_clicked.connect(self.open_attachment)
        attachments_section.add_file_attachment_clicked.connect(self.add_file_attachment_to_task)
        attachments_section.attachment_removed.connect(self.remove_attachment_from_task)

        # Store reference to the section widget
        self.attachments_section = attachments_section

        section_layout.addWidget(attachments_section)
        section_layout.addStretch()

        return section_layout

    def open_attachment(self, path_or_url):
        # Convert to an absolute path if needed
        if not os.path.isabs(path_or_url):
            path_or_url = os.path.abspath(path_or_url)

        url = QUrl.fromLocalFile(path_or_url)
        # print(f"Opening url: {url}")
        QDesktopServices.openUrl(url)

    def add_file_attachment_to_task(self):
        path_or_url, _ = QFileDialog.getOpenFileName(self, "Select Attachment", "", "All Files (*)")
        if path_or_url:
            path_or_url = os.path.abspath(path_or_url)
            attachment = Attachment(path_or_url, user_id="Current User", description="")
            self.task.attachments.append(attachment)
            self.attachments_section.add_attachments(self.task.attachments)  # single refresh

    def remove_attachment_from_task(self, attachment):
        """Remove an attachment from the task."""
        # Handle both object and dictionary attachments for backward compatibility
        if isinstance(attachment, dict):
            # Remove by matching file path
            path_or_url = attachment.get('path_or_url')
            self.task.attachments = [a for a in self.task.attachments
                                    if getattr(a, 'path_or_url', '') != path_or_url]
        else:
            # Remove the attachment object
            if attachment in self.task.attachments:
                self.task.attachments.remove(attachment)

        # Refresh the UI
        self.attachments_section.add_attachments(self.task.attachments)

    def saveActivity(self, text, timestamp, activity_type, is_edit=False, is_delete=False):
        # Find existing activity if editing/deleting
        if is_edit or is_delete:
            for idx, entry in enumerate(self.task.entries):
                if entry.content == text:
                    if is_delete:
                        # Remove the entry
                        self.task.entries.pop(idx)
                        break
                    elif is_edit:
                        # Update the entry
                        entry.edit(text, "Current User")
                        break
        else:
            # Create new TaskEntry
            new_entry = TaskEntry(
                content=text,
                entry_type=activity_type,
                user_id="Current User"
            )
            self.task.entries.append(new_entry)

    def display_activities(self):
        """Display task entries in the appropriate lists, ordered by newest first."""
        # Clear existing items
        self.comments_list.clear()
        self.work_logs_list.clear()

        # Display entries by type
        if hasattr(self.task, 'entries'):
            # Sort entries by timestamp in descending order (newest first)
            sorted_entries = sorted(self.task.entries, key=lambda entry: entry.timestamp, reverse=True)

            for entry in sorted_entries:
                if entry.entry_type == "comment":
                    self.add_entry_to_list(entry, self.comments_list)
                elif entry.entry_type == "work_log":
                    self.add_entry_to_list(entry, self.work_logs_list)

    def add_entry_to_list(self, entry, list_widget):
        """Add a TaskEntry to a list widget with proper formatting"""
        from PyQt5.QtGui import QFontMetrics, QFont
        from PyQt5.QtCore import QRect

        # Create and set up list item first
        item = QListWidgetItem()
        list_widget.addItem(item)

        # Get available width - the list widget viewport gives us the actual usable space
        viewport_width = list_widget.viewport().width()

        # Create entry widget with constrained width
        entry_widget = QWidget()
        entry_widget.setStyleSheet("background-color: transparent;")
        entry_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        entry_widget.setMaximumWidth(viewport_width)

        entry_layout = QVBoxLayout(entry_widget)
        entry_layout.setContentsMargins(12, 10, 12, 10)
        entry_layout.setSpacing(8)

        # Calculate text width: viewport - widget margins - list item padding - borders - buffer
        # Widget margins: 12*2 = 24
        # List item padding (from CSS): 8*2 = 16
        # List item border: 1*2 = 2
        # Buffer for safety: 8
        # Total: 50
        text_width = viewport_width - 50

        # Content label with word wrap
        content_label = QLabel(entry.content)
        content_label.setWordWrap(True)
        content_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        content_label.setMaximumWidth(text_width)
        content_label.setStyleSheet(f"""
            QLabel {{
                color: {AppColors.text_primary};
                font-size: 11px;
                padding: 0px;
            }}
        """)

        # Calculate the required height for wrapped text using QFontMetrics
        font = QFont()
        font.setPointSize(11)
        font_metrics = QFontMetrics(font)
        bounding_rect = font_metrics.boundingRect(
            QRect(0, 0, text_width, 0),
            Qt.TextWordWrap,
            entry.content
        )
        calculated_text_height = bounding_rect.height()

        entry_layout.addWidget(content_label)

        # Action buttons and timestamp
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(10)

        edit_label = QLabel("✏ Edit")
        delete_label = QLabel("🗑 Delete")

        for label in [edit_label, delete_label]:
            label.setStyleSheet(f"""
                QLabel {{
                    color: {AppColors.accent};
                    font-size: 10px;
                    padding: 2px 4px;
                }}
                QLabel:hover {{
                    color: {AppColors.accent_light};
                    text-decoration: underline;
                }}
            """)
            label.setCursor(Qt.PointingHandCursor)
            label.setTextInteractionFlags(Qt.TextBrowserInteraction)

        # Timestamp (and hours, for a work log)
        stamp = entry.timestamp.strftime("%m/%d/%Y %H:%M")
        if entry.entry_type == "work_log":
            time_log = self._time_log_for_entry(entry)
            if time_log is not None:
                stamp = f"{time_log.hours:g} h  ·  {stamp}"
        timestamp_label = QLabel(stamp)
        timestamp_label.setStyleSheet(f"""
            QLabel {{
                color: {AppColors.text_faint};
                font-size: 9px;
                font-style: italic;
            }}
        """)

        actions_layout.addWidget(edit_label)
        actions_layout.addWidget(delete_label)
        actions_layout.addWidget(timestamp_label)
        actions_layout.addStretch()

        entry_layout.addLayout(actions_layout)

        # Set the widget to the item
        list_widget.setItemWidget(item, entry_widget)

        # Calculate total height based on components
        # Text height (from font metrics) + actions row + margins + spacing + buffer
        actions_height = 30  # Height for edit/delete/timestamp row
        margins_spacing = 20 + 8  # top/bottom margins + spacing between rows
        buffer = 15  # Extra buffer to ensure nothing gets cut off

        total_height = calculated_text_height + actions_height + margins_spacing + buffer

        # Ensure minimum height for small comments
        final_height = max(total_height, 75)

        # Set size hint for the list item
        item.setSizeHint(QSize(viewport_width, final_height))

        # Store reference to the entry
        item.setData(Qt.UserRole, entry)

        # Connect action signals
        edit_label.mousePressEvent = lambda event, item=item: self.edit_activity(item)
        delete_label.mousePressEvent = lambda event, item=item: self.delete_activity(item)

    def add_comment(self, comment_input):
        text = comment_input.toPlainText().strip()
        if text:
            ts = QDateTime.currentDateTime().toString("MM / dd / yyyy hh:mm")
            self.saveActivity(text, ts, "comment")
            comment_input.clear()
            self.display_activities()

    def add_work_log(self, hours_input, description_input):
        hours = hours_input.value()
        description = description_input.text().strip()
        if hours > 0 and description:
            ts = QDateTime.currentDateTime().toString("MM / dd / yyyy hh:mm")
            self.saveActivity(description, ts, "work_log")
            time_log = TimeLog(hours=float(hours), user_id="Current User", description=description)
            self.task.time_logs.append(time_log)
            self.task.actual_hours += float(hours)
            hours_input.setValue(0)
            description_input.clear()
            self.display_activities()

    def _time_log_for_entry(self, entry):
        """The TimeLog recorded together with a work log entry (same text, closest time)"""
        candidates = [log for log in self.task.time_logs if log.description == entry.content]
        if not candidates:
            return None
        return min(candidates, key=lambda log: abs((log.timestamp - entry.timestamp).total_seconds()))

    def edit_activity(self, item):
        """Edit a TaskEntry (a work log's hours too)"""
        entry = item.data(Qt.UserRole)
        if not entry:
            return
        if entry.entry_type != "work_log":
            text, ok = dialogs.getMultiLineText(self, "Edit Comment", "Update your comment:", entry.content)
            if ok and text:
                entry.edit(text, "Current User")
                self.display_activities()
            return

        time_log = self._time_log_for_entry(entry)
        result = WorkLogDialog.edit(self, entry.content, time_log.hours if time_log else 0.0)
        if result is None:
            return
        text, hours = result
        if time_log is None:
            # Older work logs may have no hours recorded with them
            time_log = TimeLog(hours=0.0, user_id="Current User", description=entry.content)
            time_log.timestamp = entry.timestamp
            self.task.time_logs.append(time_log)
        self.task.actual_hours = max(0.0, self.task.actual_hours - time_log.hours + hours)
        time_log.hours = hours
        time_log.description = text
        if text != entry.content:
            entry.edit(text, "Current User")
        self.display_activities()

    def delete_activity(self, item):
        """Delete a TaskEntry"""
        self.logger.debug(f"Attempting to delete item: {item}")
        entry = item.data(Qt.UserRole)
        self.logger.debug(f"found entry: {entry}")
        if entry:
            is_work_log = entry.entry_type == "work_log"
            confirm = dialogs.question(
                self, "Confirm Delete",
                f"Are you sure you want to delete this {'work log' if is_work_log else 'comment'}?",
                QMessageBox.Yes | QMessageBox.No
            )

            if confirm == QMessageBox.Yes:
                # A work log's hours go with it
                if is_work_log:
                    time_log = self._time_log_for_entry(entry)
                    if time_log is not None:
                        self.task.time_logs.remove(time_log)
                        self.task.actual_hours = max(0.0, self.task.actual_hours - time_log.hours)

                # Remove from task entries
                if entry in self.task.entries:
                    self.task.entries.remove(entry)

                # Refresh the UI
                self.display_activities()
        else:
            self.logger.debug("failed to delete")

    def add_team_member_to_task(self, member_name):
        """Add team member to the current task"""
        # Add to the Task object's collaborators set
        self.task.collaborators.add(member_name)

    def remove_team_member_from_task(self, member_name):
        """Remove team member from the current task"""
        # Remove from the Task object's collaborators set
        if member_name in self.task.collaborators:
            self.task.collaborators.remove(member_name)

    def load_dependencies(self):
        """Return {task_id: title} for every task that can be a dependency"""
        return {task_id: task.title for task_id, task in self.data_manager.get_tasks().items()}

    def add_dependency_to_task(self, dependency_task_id):
        """Add dependency to current task"""
        self.task.dependencies.add(dependency_task_id)

    def remove_dependency_from_task(self, dependency_task_id):
        """Remove dependency from current task"""
        self.task.dependencies.discard(dependency_task_id)

    def _flushPendingChecklistSave(self):
        """Save a checklist change still waiting on the debounce timer"""
        if self._save_debounce_timer.isActive():
            self._save_debounce_timer.stop()
            self._debounced_save()

    def cancelTaskChanges(self):
        """Close expanded card and restore original task state"""
        # Checklist ticks save on their own, so keep one made just before Cancel
        self._flushPendingChecklistSave()

        # Restore the task to its initial state
        if self.initial_state is not None:
            self.restore_task_state()

        # Hide overlay and close
        self.cancelTask.emit()

    def restore_task_state(self):
        """Restore the task to its original state"""
        restored = Task.from_dict(self.initial_state)
        for name, value in vars(restored).items():
            setattr(self.task, name, value)

    def deleteTask(self):
        confirm = dialogs.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete the task '{self.task.title}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        try:
            # Keep these for messages/signals
            task_id = self.task.id
            task_title = self.task.title

            if self.data_manager.delete_task(task_id):
                # One undoable step, with anything saved while the card was open
                self._recordHistory(f"Deleted \u201c{task_title}\u201d")
                self.taskDeleted.emit(task_id)
                if hasattr(self, 'parent_view') and self.parent_view and hasattr(self.parent_view, 'overlay') and self.parent_view.overlay is not None:
                    self.parent_view.overlay.hide()
                self.close()
            else:
                dialogs.warning(self, "Warning", f"Task '{task_title}' could not be deleted. See app.log for details.")
        except Exception as e:
            self.logger.error(f"Error deleting task: {e}")
            dialogs.critical(self, "Error", f"An error occurred while deleting the task: {str(e)}")


    def add_checklist_item_to_task(self, text):
        """Add a checklist item to the task"""
        if not hasattr(self.task, 'checklist'):
            self.task.checklist = []

        self.task.checklist.append({
            'text': text,
            'checked': False
        })

    def remove_checklist_item_from_task(self, text):
        """Remove a checklist item from the task"""
        if hasattr(self.task, 'checklist'):
            # Remove the item with matching text
            self.task.checklist = [item for item in self.task.checklist if item['text'] != text]

    def update_checklist_item_in_task(self, text, checked):
        """Update the checked state of a checklist item"""
        if hasattr(self.task, 'checklist'):
            for item in self.task.checklist:
                if item['text'] == text:
                    item['checked'] = checked
                    break

    def closeEvent(self, event):
        """Clean up resources when widget closes"""
        self._flushPendingChecklistSave()
        self._recordHistory()
        # Clean up calendar widget if exists
        if self._calendar_widget is not None:
            self._calendar_widget.close()
            self._calendar_widget = None

        super().closeEvent(event)

    def _recordHistory(self, label=None):
        """Record what was saved while the card was open as one undoable step (once)"""
        if self._history_recorded or self.task is None:
            return
        self._history_recorded = True
        from utils.data_history import history
        name = self.task.title or "task"
        history().record(label or (f"Added \u201c{name}\u201d" if self._opened_as_new else f"Edited \u201c{name}\u201d"),
                         self._history_before)

    def closeWindow(self):
        self.logger.debug("Closing expanded card")
        if self.parent_view and hasattr(self.parent_view, 'overlay') and self.parent_view.overlay:
            self.parent_view.overlay.hide()
        self.close()
        self.deleteLater()

    def _debounced_save(self):
        """Save checklist changes on their own, 500 ms after the last one.

        Only the checklist is written, so other edits in the card stay unsaved until
        Save (and Cancel can still undo them). A new task isn't on disk yet, so its
        checklist is simply saved with the task.
        """
        if self.isNewTask:
            return
        checklist = [dict(item) for item in self.task.checklist]
        if update_task_fields(self.task.id, {'checklist': checklist}, self.logger):
            # Cancel shouldn't undo a change that's already saved
            if self.initial_state is not None:
                self.initial_state['checklist'] = checklist

    def _schedule_debounced_save(self):
        """Schedule a debounced save - restarts timer if already running"""
        self._save_debounce_timer.stop()
        self._save_debounce_timer.start(500)  # 500ms delay

    def addChecklistItem(self, text):
        """Add checklist item to the current task"""
        # Check the flag to prevent recursion during loading
        if hasattr(self, '_loading_checklist_items') and self._loading_checklist_items:
            return

        # Add to the Task object's checklist list
        self.task.checklist.append({
            'text': text,
            'checked': False
        })

        # Schedule debounced save (waits 500ms after last change)
        self._schedule_debounced_save()

    def removeChecklistItem(self, text):
        """Remove a checklist item from the task"""
        if hasattr(self.task, 'checklist'):
            # Remove the item with matching text
            self.task.checklist = [item for item in self.task.checklist if item['text'] != text]

            # Schedule debounced save (waits 500ms after last change)
            self._schedule_debounced_save()

    def updateCheckboxState(self, text, checked):
        """Update the task's checklist item state"""
        # Find the item with matching text in the task's checklist
        for i, item in enumerate(self.task.checklist):
            if item['text'] == text:
                # Update the checked state
                self.task.checklist[i]['checked'] = checked

                # Schedule debounced save (waits 500ms after last change)
                self._schedule_debounced_save()
                break

    # ------------------------------------------------------------------
    # Sections: which parts of the card this task shows
    # ------------------------------------------------------------------

    def _sectionWidgets(self):
        return {
            'description': self.description_section_widget,
            'activity': self.activity_section_widget,
            'status_priority': self.status_priority_widget,
            'details': self.details_section,
            'dependencies': self.dependencies_section,
            'attachments': getattr(self, 'attachments_section', None),
            'checklist': getattr(self, 'checklist_section', None),
            'category': self.category_section_widget,
            'project_phase_selection': self.project_phase_section_widget,
        }

    def apply_section_visibility(self):
        """Show the sections this task shows (its own choices, otherwise the defaults)"""
        from utils import task_sections
        for key, widget in self._sectionWidgets().items():
            if widget is not None:
                widget.setVisible(task_sections.is_shown(self.task, key))

    def buildSectionsMenu(self):
        """The ☰ Sections menu: tick a section to show it on this card, untick to remove it"""
        from utils import task_sections
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{ background-color: {AppColors.surface_raised}; color: {AppColors.text_primary};
                     border: 1px solid {AppColors.surface_hover_alt}; padding: 4px; }}
            QMenu::item {{ padding: 6px 22px 6px 26px; border-radius: 3px; }}
            QMenu::item:selected {{ background-color: {AppColors.accent}; }}
            QMenu::item:disabled {{ color: {AppColors.text_faint}; }}
            QMenu::separator {{ height: 1px; background: {AppColors.surface_hover_alt}; margin: 4px 6px; }}""")
        title = menu.addAction("Sections on this card")
        title.setEnabled(False)
        for key, label, _where in task_sections.SECTIONS:
            action = menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(task_sections.is_shown(self.task, key))
            action.toggled.connect(lambda shown, key=key: self.setSectionShown(key, shown))
        menu.addSeparator()
        reset = menu.addAction("Reset to the defaults", self.resetSections)
        reset.setEnabled(task_sections.is_customized(self.task))
        menu.addAction("Make these the defaults", self.makeSectionsDefault)
        menu.addAction("Edit the defaults in Settings…", self.openSectionDefaults)
        return menu

    def showSectionsMenu(self, button):
        self.buildSectionsMenu().exec_(button.mapToGlobal(button.rect().bottomLeft()))

    def setSectionShown(self, key, shown):
        from utils import task_sections
        task_sections.set_shown(self.task, key, shown)
        self.apply_section_visibility()
        self._saveSections()

    def resetSections(self):
        from utils import task_sections
        task_sections.reset(self.task)
        self.apply_section_visibility()
        self._saveSections()

    def makeSectionsDefault(self):
        from utils import task_sections
        task_sections.make_defaults(self.task)
        self.apply_section_visibility()
        self._saveSections()

    def openSectionDefaults(self):
        """Go to Settings > Behaviour, where the defaults are"""
        window = self.window()
        if hasattr(window, "showScreenNow"):
            if self.parent_view is not None and hasattr(self.parent_view, "closeExpandedCard"):
                self.parent_view.closeExpandedCard()
            window.showScreenNow("settings_screen")
            from ui.settings_screen import SECTIONS
            window.settings_screen.showSection(next(i for i, name in enumerate(SECTIONS) if "Behaviour" in name))

    def _saveSections(self):
        """Keep the choice even if the card is closed without Save (a new task saves with Save)"""
        if self.isNewTask or self.task is None:
            return
        update_task_fields(self.task.id, {'visible_sections': dict(self.task.visible_sections)}, self.logger)


class WorkLogDialog(QDialog):
    """Edit a work log's description and hours together"""

    def __init__(self, parent, description, hours):
        super().__init__(parent)
        self.setWindowTitle("Edit Work Log")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Description:"))
        self.description_edit = QTextEdit()
        self.description_edit.setPlainText(description)
        self.description_edit.setStyleSheet(text_area_style())
        layout.addWidget(self.description_edit)

        hours_row = QHBoxLayout()
        hours_row.addWidget(QLabel("Hours:"))
        self.hours_input = QDoubleSpinBox()
        self.hours_input.setRange(0.0, 24.0)
        self.hours_input.setSingleStep(0.25)
        self.hours_input.setDecimals(2)
        self.hours_input.setValue(hours)
        hours_row.addWidget(self.hours_input)
        hours_row.addStretch(1)
        layout.addLayout(hours_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _accept(self):
        if self.description_edit.toPlainText().strip():
            self.accept()

    def values(self):
        return self.description_edit.toPlainText().strip(), self.hours_input.value()

    @classmethod
    def edit(cls, parent, description, hours):
        """(description, hours), or None if cancelled"""
        dialog = cls(parent, description, hours)
        return dialog.values() if dialog.exec_() == QDialog.Accepted else None
