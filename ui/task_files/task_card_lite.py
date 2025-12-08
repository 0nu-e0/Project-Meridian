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

# Standard library imports
from logging import Logger
from typing import Optional, Tuple

# Third-party imports
from PyQt5.QtCore import QEasingCurve, QEvent, QPropertyAnimation, QSize, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QCursor, QFontMetrics, QGuiApplication
from PyQt5.QtWidgets import (QApplication, QGraphicsDropShadowEffect, QGridLayout, QLabel,
                             QScrollArea, QSizePolicy, QStyle, QVBoxLayout, QWidget)

# Local application imports
from models.task import Task
from resources.styles import AppColors, AppStyles
from utils.constants import (ANIMATION_COLLAPSE_DURATION_MS, ANIMATION_DURATION_MS,
                             ANIMATION_UPDATE_INTERVAL_MS, CARD_DETAIL_SPACING,
                             CARD_HEIGHT_ASPECT_RATIO, CARD_MARGIN_MULTIPLIER,
                             CARD_MIN_CARDS_PER_ROW, CARD_MIN_HEIGHT_FOR_CONTENT,
                             CARD_MIN_READABLE_WIDTH, CARD_PADDING,
                             CARD_TARGET_CARDS_PER_ROW_DIVISOR, LAYOUT_NO_SPACING)

class TaskCardLite(QWidget):
    card_count = 0
    cardClicked = pyqtSignal(object, str)
    cardHovered = pyqtSignal(bool, int) 
    filterPass = pyqtSignal(str)

    @classmethod
    def calculate_optimal_card_size(cls) -> Tuple[int, int]:
        # Get screen dimensions using QGuiApplication instead of deprecated QDesktopWidget
        screen = QGuiApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()

        # Calculate width
        target_cards_per_row = max(
            CARD_MIN_CARDS_PER_ROW,
            screen_width // CARD_TARGET_CARDS_PER_ROW_DIVISOR
        )
        available_width = screen_width - (CARD_MARGIN_MULTIPLIER * (target_cards_per_row + 1))
        card_width = max(CARD_MIN_READABLE_WIDTH, available_width // target_cards_per_row)

        # Calculate height
        card_height = min(
            int(card_width / CARD_HEIGHT_ASPECT_RATIO),
            CARD_MIN_HEIGHT_FOR_CONTENT
        )

        return card_width, card_height

    def __init__(self, logger: Logger, task: Task, grid_id: Optional[str] = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        TaskCardLite.card_count += 1
        self.logger = logger
        self.task = task  # This is now a Task object that contains all the info
        self.grid_id = grid_id

        # Calculate size first
        self.card_width, self.card_height = self.calculate_optimal_card_size()

        # Expansion properties
        self.expanded = False
        self.row_position = 0
        self.compact_height = self.card_height
        self.expanded_height = int(self.card_height * 2.0)  # 2x expansion for more detail

        # Animation for smooth expansion
        self.animation = None
        self.detail_container = None

        # Add shadow effect
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setColor(QColor(AppColors.accent_background_color_dark))
        self.shadow.setBlurRadius(15)
        self.shadow.setXOffset(2)
        self.shadow.setYOffset(2)
        self.setGraphicsEffect(self.shadow)

        # Set initial size
        self.setMinimumHeight(self.compact_height)
        self.setMaximumHeight(self.compact_height)
        self.setFixedWidth(self.card_width)

        # Set size policy to allow vertical expansion
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self.initUI()

    def sizeHint(self) -> QSize:
        """Provide size hint based on current expansion state"""
        current_height = self.expanded_height if self.expanded else self.compact_height
        return QSize(self.card_width, current_height)

    def minimumSizeHint(self) -> QSize:
        """Minimum size hint"""
        return QSize(self.card_width, self.compact_height)

    def enterEvent(self, event: QEvent) -> None:
        """Expand card smoothly when mouse enters"""
        if not self.expanded:
            self.expandCard()
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        """Collapse card smoothly when mouse leaves"""
        if self.expanded:
            QTimer.singleShot(100, self._checkCollapseCard)
        super().leaveEvent(event)

    def _checkCollapseCard(self) -> None:
        """Check if mouse has truly left the card before collapsing"""
        widget_under_cursor = QApplication.widgetAt(QCursor.pos())
        if widget_under_cursor is self or self.isAncestorOf(widget_under_cursor):
            return  # Mouse still over card, don't collapse
        self.collapseCard()
    
    def expandCard(self) -> None:
        """Expand card to show detailed information with smooth animation"""
        if self.expanded or self.animation and self.animation.state() == QPropertyAnimation.Running:
            return

        self.expanded = True
        self.shadow.setBlurRadius(25)
        self.cardHovered.emit(True, self.row_position)

        # Show detail container
        if self.detail_container:
            self.detail_container.setMaximumHeight(16777215)  # Remove height restriction

        # Update max height immediately to allow expansion
        self.setMaximumHeight(self.expanded_height)

        # Animate card height expansion
        self.animation = QPropertyAnimation(self, b"minimumHeight")
        self.animation.setDuration(ANIMATION_DURATION_MS)
        self.animation.setStartValue(self.compact_height)
        self.animation.setEndValue(self.expanded_height)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)

        # Update layout during animation, not just at the end
        self.animation.valueChanged.connect(self._onHeightChanged)
        self.animation.finished.connect(self._onExpandFinished)
        self.animation.start()

    def _onHeightChanged(self) -> None:
        """Called during animation to update layout in real-time"""
        self.updateGeometry()
        parent = self.parent()
        if parent and hasattr(parent, 'layout') and parent.layout():
            parent.layout().invalidate()

    def _onExpandFinished(self) -> None:
        """Called when expansion animation completes"""
        self.animation.valueChanged.disconnect(self._onHeightChanged)
        self._notifyParentLayoutUpdate()

    def _notifyParentLayoutUpdate(self) -> None:
        """Notify parent widgets to update their geometry after expansion"""
        # Update this widget's geometry first
        self.updateGeometry()

        # Force immediate size policy recalculation
        size_policy = self.sizePolicy()
        size_policy.setHeightForWidth(False)
        self.setSizePolicy(size_policy)

        # Traverse up the widget hierarchy and force layout updates
        parent = self.parent()
        while parent:
            # Update parent geometry
            parent.updateGeometry()

            # If parent has a layout, force it to recalculate
            if hasattr(parent, 'layout') and parent.layout():
                layout = parent.layout()
                layout.invalidate()
                layout.activate()
                layout.update()

            # For QScrollArea widgets, ensure viewport is updated
            from PyQt5.QtWidgets import QScrollArea
            if isinstance(parent, QScrollArea):
                if parent.widget():
                    parent.widget().adjustSize()
                parent.updateGeometry()

            parent = parent.parent()

        # Force an immediate repaint to avoid visual lag
        QApplication.processEvents()

    def collapseCard(self) -> None:
        """Collapse card back to compact view with smooth animation"""
        if not self.expanded or self.animation and self.animation.state() == QPropertyAnimation.Running:
            return

        self.expanded = False
        self.shadow.setBlurRadius(15)
        self.cardHovered.emit(False, self.row_position)

        # Animate card height collapse
        self.animation = QPropertyAnimation(self, b"minimumHeight")
        self.animation.setDuration(ANIMATION_COLLAPSE_DURATION_MS)
        self.animation.setStartValue(self.expanded_height)
        self.animation.setEndValue(self.compact_height)
        self.animation.setEasingCurve(QEasingCurve.InCubic)

        # Update layout during animation
        self.animation.valueChanged.connect(self._onHeightChanged)
        self.animation.finished.connect(self._onCollapseFinished)
        self.animation.start()

    def _onCollapseFinished(self) -> None:
        """Hide detail container after collapse animation completes"""
        # Disconnect the value changed signal
        self.animation.valueChanged.disconnect(self._onHeightChanged)

        if self.detail_container and not self.expanded:
            self.detail_container.setMaximumHeight(0)

        # Reset to fixed height after collapse
        self.setMinimumHeight(self.compact_height)
        self.setMaximumHeight(self.compact_height)

        # Notify parent to update layout
        self._notifyParentLayoutUpdate()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # self.cardClicked.emit(self.grid_layout, self.task)
            self.logger.debug(f"card clicked with task in mousePressEvent: {self.task}")
            self.logger.debug(f"card clicked with grid_id in mousePressEvent: {self.grid_id}")
            self.cardClicked.emit(self.task, self.grid_id)
        super().mousePressEvent(event)
        
    def setRowPosition(self, row):
        self.row_position = row

    def initUI(self):
        """Initialize UI with both compact and expandable detail sections"""
        self.initCentralWidget()

        # Generate compact view
        self.generateCompactUI()

        # Create detail container (initially hidden)
        self.detail_container = QWidget()
        detail_layout = QVBoxLayout(self.detail_container)
        detail_layout.setContentsMargins(LAYOUT_NO_SPACING, LAYOUT_NO_SPACING, LAYOUT_NO_SPACING, LAYOUT_NO_SPACING)
        detail_layout.setSpacing(LAYOUT_NO_SPACING)

        # Generate detail content
        self.generateDetailContent(detail_layout)

        # Add detail container to main layout (collapsed initially)
        self.detail_container.setMaximumHeight(0)
        self.main_layout.addWidget(self.detail_container)

    def initCentralWidget(self):
        self.central_widget = QWidget()
        self.central_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(LAYOUT_NO_SPACING, LAYOUT_NO_SPACING, LAYOUT_NO_SPACING, LAYOUT_NO_SPACING)
        self.main_layout.setSpacing(LAYOUT_NO_SPACING)
        self.setLayout(self.main_layout)


    def generateCompactUI(self):
        """Generate compact card view - always visible"""
        card_layout_widget = QWidget()
        card_layout_widget.setObjectName("card_container")
        card_layout = QGridLayout(card_layout_widget)
        card_layout.setContentsMargins(CARD_PADDING, CARD_PADDING, CARD_PADDING, CARD_PADDING)
        card_layout.setSpacing(CARD_DETAIL_SPACING)

        # Set column stretch factors to make columns equal width
        card_layout.setColumnStretch(0, 1)
        card_layout.setColumnStretch(1, 1)

        # Title from Task
        title_label = QLabel()
        title_label.setStyleSheet(AppStyles.card_label_single())

        max_title_width = self.card_width
        self.set_smart_title_height(title_label, self.task.title, max_title_width, max_lines=3)

        card_layout.addWidget(title_label, 0, 0, 1, 2)

        # Status (using TaskStatus enum)
        status_label = QLabel()
        status_icon = self.style().standardIcon(QStyle.SP_DialogApplyButton)
        status_label.setPixmap(status_icon.pixmap(16, 16))
        status_label.setText(f"  {self.task.status.value}")
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
        priority_label.setText(f"  {self.task.priority.name}")
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
        category_label.setText(f"  {self.task.category.value}")
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
        complete_label.setText(f"  {self.task.percentage_complete}%")
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

    def generateDetailContent(self, detail_layout):
        """Generate detailed information shown when card expands"""
        detail_widget = QWidget()
        detail_widget.setObjectName("card_container")
        detail_grid = QGridLayout(detail_widget)
        detail_grid.setContentsMargins(CARD_PADDING, CARD_DETAIL_SPACING, CARD_PADDING, CARD_PADDING)
        detail_grid.setSpacing(CARD_DETAIL_SPACING)

        detail_grid.setColumnStretch(0, 1)
        detail_grid.setColumnStretch(1, 1)

        row = 0

        # Description (if exists)
        if self.task.description:
            desc_label = QLabel(self.task.description)
            desc_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("""
                QLabel {
                    color: white;
                    font-size: 12px;
                    background-color: #34495E;
                    padding: 6px;
                    border-radius: 4px;
                }
            """)
            desc_label.setMaximumWidth(self.card_width - 16)
            detail_grid.addWidget(desc_label, row, 0, 1, 2)
            row += 1

        # Progress info
        progress_info = [f"{self.task.percentage_complete}%"]
        if hasattr(self.task, 'estimated_hours') and self.task.estimated_hours:
            progress_info.append(f"Est: {self.task.estimated_hours}h")
        if hasattr(self.task, 'actual_hours') and self.task.actual_hours:
            progress_info.append(f"Actual: {self.task.actual_hours}h")

        progress_label = QLabel(" | ".join(progress_info))
        progress_label.setStyleSheet(f"""
            QLabel {{
                color: white;
                font-size: 11px;
                background-color: {AppColors.get_progress_color(self.task.percentage_complete)};
                padding: 4px;
                border-radius: 4px;
            }}
        """)
        detail_grid.addWidget(progress_label, row, 0, 1, 2)
        row += 1

        # Dates
        if self.task.start_date is not None:
            started_label = QLabel(f"Started: {self.task.start_date.strftime('%m/%d/%y')}")
            started_label.setStyleSheet("""
                QLabel {
                    color: white;
                    font-size: 11px;
                    background-color: #2980B9;
                    padding: 4px;
                    border-radius: 4px;
                }
            """)
            detail_grid.addWidget(started_label, row, 0)

        if self.task.due_date is not None:
            due_label = QLabel(f"Due: {self.task.due_date.strftime('%m/%d/%y')}")
            due_label.setStyleSheet(f"""
                QLabel {{
                    color: white;
                    font-size: 11px;
                    background-color: {AppColors.get_due_date_color(self.task.due_date)};
                    padding: 4px;
                    border-radius: 4px;
                }}
            """)
            detail_grid.addWidget(due_label, row, 1)

        if self.task.start_date or self.task.due_date:
            row += 1

        # Team info
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
                    font-size: 11px;
                    background-color: #8E44AD;
                    padding: 4px;
                    border-radius: 4px;
                }
            """)
            detail_grid.addWidget(team_label, row, 0, 1, 2)

        detail_layout.addWidget(detail_widget)


    @staticmethod
    def set_smart_title_height(label: QLabel, text: str, max_width: int, max_lines: int = 3):
        """
        Adjust QLabel font size and wrapping so that text fits within `max_width`
        and no more than `max_lines`.
        """
        max_font_size = 16    # highest size you'd like
        min_font_size = 8     # smallest acceptable
        font_size = max_font_size

        # Prepare font & wrap mode
        font = label.font()
        label.setWordWrap(True)

        while font_size >= min_font_size:
            font.setPointSize(font_size)
            fm = QFontMetrics(font)

            # Measure the bounding rectangle with wrapping
            bounding = fm.boundingRect(0, 0, max_width, 1000, Qt.TextWordWrap, text)

            line_height = fm.lineSpacing()
            lines_used = bounding.height() / line_height

            if lines_used <= max_lines:
                # It fits
                break

            font_size -= 1

        # Set final font & text
        font.setPointSize(font_size)
        label.setFont(font)
        label.setText(text)

        # Optional: change styles
        if lines_used > 1:
            label.setStyleSheet(AppStyles.card_label_double())
        else:
            label.setStyleSheet(AppStyles.card_label_single())
            

        # Calculate actual line height including font ascent/descent and some extra padding
        # line_height = font_metrics.lineSpacing()
        # padding = 18  # minimal vertical padding to prevent clipping
        # label.setFixedHeight(line_height * line_count + padding)
