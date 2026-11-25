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
from PyQt5.QtGui import QColor, QCursor, QFontMetrics
from PyQt5.QtWidgets import (QApplication, QGraphicsDropShadowEffect, QHBoxLayout, QLabel,
                             QScrollArea, QSizePolicy, QVBoxLayout, QWidget)

# Local application imports
from models.task import Task
from resources.styles import AppColors
from ui.custom_widgets.rich_text import DescriptionView
from utils.constants import (ANIMATION_COLLAPSE_DURATION_MS, ANIMATION_DURATION_MS,
                             CARD_HEIGHT_ASPECT_RATIO, CARD_MIN_HEIGHT_FOR_CONTENT,
                             CARD_MIN_READABLE_WIDTH, CARD_PADDING, CARD_TARGET_WIDTH,
                             LAYOUT_NO_SPACING)

# Tallest the hover preview of a description gets before it scrolls
DESCRIPTION_PREVIEW_MAX_HEIGHT = 180


def elide_lines(text, font, width, max_lines):
    """Wrap text to width and cut it to max_lines, ending with an ellipsis if it was cut"""
    metrics = QFontMetrics(font)
    words = text.split()
    lines, current = [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if metrics.horizontalAdvance(candidate) <= width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    if len(lines) <= max_lines:
        return "\n".join(lines)
    kept = lines[:max_lines]
    kept[-1] = metrics.elidedText(" ".join(lines[max_lines - 1:]), Qt.ElideRight, width)
    return "\n".join(kept)


def badge(text, color):
    label = QLabel(text)
    font = label.font()
    font.setPixelSize(11)
    font.setBold(True)
    label.setFont(font)
    label.setAlignment(Qt.AlignCenter)
    label.setStyleSheet(f"""
        QLabel {{ background-color: {color}; color: white;
                 border-radius: 4px; padding: 2px 8px; }}
    """)
    # Reserve the whole word, so a narrow card never squeezes it into "Mediu"
    label.setMinimumWidth(QFontMetrics(font).horizontalAdvance(text) + 2 * 8 + 4)
    label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    return label


class TaskCardLite(QWidget):
    card_count = 0
    cardClicked = pyqtSignal(object, str)
    cardHovered = pyqtSignal(bool, int)
    archiveToggled = pyqtSignal(object)  # task: archive or unarchive it by hand
    filterPass = pyqtSignal(str)

    @staticmethod
    def calculate_grid_layout(available_width: int, spacing: int) -> Tuple[int, int, int]:
        """Return (columns, card_width, card_height) so a row of cards exactly fills available_width."""
        available_width = max(CARD_MIN_READABLE_WIDTH, available_width)

        # Pick the column count whose card width lands closest to the target width
        columns = max(1, round((available_width + spacing) / (CARD_TARGET_WIDTH + spacing)))
        card_width = (available_width - spacing * (columns - 1)) // columns

        # Drop columns until cards are readable
        while columns > 1 and card_width < CARD_MIN_READABLE_WIDTH:
            columns -= 1
            card_width = (available_width - spacing * (columns - 1)) // columns

        card_height = min(
            int(card_width / CARD_HEIGHT_ASPECT_RATIO),
            CARD_MIN_HEIGHT_FOR_CONTENT
        )
        return columns, card_width, card_height

    def __init__(self, logger: Logger, task: Task, grid_id: Optional[str] = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        TaskCardLite.card_count += 1
        self.logger = logger
        self.task = task  # This is now a Task object that contains all the info
        self.grid_id = grid_id

        # Start at the target size; the owning grid calls setCardWidth once it knows its width
        self.card_width = CARD_TARGET_WIDTH
        self.card_height = min(int(self.card_width / CARD_HEIGHT_ASPECT_RATIO), CARD_MIN_HEIGHT_FOR_CONTENT)
        self.title_label = None
        self.desc_view = None
        self.compact_widget = None
        self.detail_widget = None

        # Expansion properties
        self.expanded = False
        self.row_position = 0
        self.compact_height = self.card_height
        self.expanded_height = int(self.card_height * 2.0)  # 2x expansion for more detail

        # Animation for smooth expansion
        self.animation = None
        self.detail_container = None

        # Timer for periodic collapse checks
        self.collapse_check_timer = QTimer(self)
        self.collapse_check_timer.timeout.connect(self._periodicCollapseCheck)
        self.collapse_check_timer.setInterval(50)  # Check every 50ms when expanded

        # Enable mouse tracking to detect when mouse leaves
        self.setMouseTracking(True)

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

    def setCardWidth(self, width: int) -> None:
        """Resize the card to the width the grid assigned it"""
        if width == self.card_width:
            return
        self.card_width = width
        self.setFixedWidth(width)
        self._fitToWidth()
        self.updateGeometry()

    # Text area inside the card: card width minus the container and label padding
    def _textWidth(self):
        return max(80, self.card_width - 2 * CARD_PADDING - 24)

    def _fitToWidth(self):
        """Re-wrap the title and size the card (compact and hover) to its content"""
        if self.title_label is None:
            return
        title = elide_lines(self.task.title, self.title_label.font(), self._textWidth(), 2)
        self.title_label.setText(title)
        # Exact height for the lines shown; a wrapped label's own estimate runs tall
        line_count = len(title.splitlines()) or 1
        self.title_label.setFixedHeight(QFontMetrics(self.title_label.font()).lineSpacing() * line_count + 2)

        if self.desc_view is not None:
            document = self.desc_view.document()
            document.setTextWidth(self._textWidth())
            # Short descriptions show in full; long ones scroll (mouse wheel)
            self.desc_view.setFixedHeight(int(min(document.size().height() + 20, DESCRIPTION_PREVIEW_MAX_HEIGHT)))

        # The compact part never changes size; while the card shrinks back after a
        # hover, only the detail area below it gives up room
        self.compact_widget.setFixedHeight(QWidget.sizeHint(self.compact_widget).height())
        self.compact_height = self.compact_widget.height()
        self.expanded_height = self.compact_height + self.detail_widget.sizeHint().height()
        if not self.expanded:
            self.setMinimumHeight(self.compact_height)
            self.setMaximumHeight(self.compact_height)

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
        # Stop any pending collapse checks
        self.collapse_check_timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        """Collapse card smoothly when mouse leaves"""
        if self.expanded:
            # Start periodic checks immediately
            self.collapse_check_timer.start()
            # Also schedule immediate check
            QTimer.singleShot(50, self._checkCollapseCard)
        super().leaveEvent(event)

    def _checkCollapseCard(self) -> None:
        """Check if mouse has truly left the card before collapsing"""
        if not self.expanded:
            self.collapse_check_timer.stop()
            return

        # Get the widget under the cursor
        cursor_pos = QCursor.pos()
        widget_under_cursor = QApplication.widgetAt(cursor_pos)

        # Check if the cursor is outside the application window
        app_widget = QApplication.activeWindow()
        if app_widget:
            global_rect = app_widget.geometry()
            if not global_rect.contains(cursor_pos):
                # Mouse is outside the application window, collapse immediately
                self.collapse_check_timer.stop()
                self.collapseCard()
                return

        # Check if mouse is still over this card or its children
        if widget_under_cursor is self or (widget_under_cursor and self.isAncestorOf(widget_under_cursor)):
            # Mouse is back over the card, stop checking
            self.collapse_check_timer.stop()
            return

        # Mouse has left the card
        self.collapse_check_timer.stop()
        self.collapseCard()

    def _periodicCollapseCheck(self) -> None:
        """Periodic check to ensure card collapses when mouse is not over it"""
        if not self.expanded:
            self.collapse_check_timer.stop()
            return

        # Get current cursor position
        cursor_pos = QCursor.pos()

        # Check if cursor is outside application window
        app_widget = QApplication.activeWindow()
        if app_widget:
            global_rect = app_widget.geometry()
            if not global_rect.contains(cursor_pos):
                self.collapse_check_timer.stop()
                self.collapseCard()
                return

        # Get widget under cursor
        widget_under_cursor = QApplication.widgetAt(cursor_pos)

        # Check if mouse is over this card or any of its children
        if widget_under_cursor is self or (widget_under_cursor and self.isAncestorOf(widget_under_cursor)):
            # Still hovering, keep checking
            return

        # Check if card geometry contains the cursor (in case widgetAt fails)
        card_global_rect = self.geometry()
        card_global_rect.moveTopLeft(self.mapToGlobal(card_global_rect.topLeft()))
        if card_global_rect.contains(cursor_pos):
            # Still hovering, keep checking
            return

        # Mouse is definitely not over the card, collapse it
        self.collapse_check_timer.stop()
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

        # Stop the periodic collapse check timer
        self.collapse_check_timer.stop()

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

    def eventFilter(self, watched, event):
        if (self.desc_view is not None and watched is self.desc_view.viewport()
                and event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton
                and not self.desc_view.anchorAt(event.pos())):
            self.cardClicked.emit(self.task, self.grid_id)
            return True
        return super().eventFilter(watched, event)

    def contextMenuEvent(self, event):
        """Right-click: open, or archive/unarchive without completing"""
        from PyQt5.QtWidgets import QMenu
        from models.task import TaskStatus
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{ background-color: {AppColors.surface_raised}; color: {AppColors.text_primary};
                     border: 1px solid {AppColors.surface_hover_alt}; padding: 4px; }}
            QMenu::item {{ padding: 6px 22px 6px 10px; border-radius: 3px; }}
            QMenu::item:selected {{ background-color: {AppColors.accent}; }}
            QMenu::item:disabled {{ color: {AppColors.text_faint}; }}""")
        menu.addAction("Open", lambda: self.cardClicked.emit(self.task, self.grid_id))
        if self.task.status == TaskStatus.COMPLETED:
            menu.addAction("Archived (completed)").setEnabled(False)
        else:
            menu.addAction("Unarchive" if self.task.archived_by_hand else "Archive",
                           lambda: self.archiveToggled.emit(self.task))
        menu.exec_(event.globalPos())

    def setRowPosition(self, row):
        self.row_position = row

    def initUI(self):
        """Initialize UI with both compact and expandable detail sections"""
        self.initCentralWidget()

        # Generate compact view
        self.generateCompactUI()

        # Create detail container (initially hidden)
        self.detail_container = QWidget()
        self.detail_container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Ignored)
        detail_layout = QVBoxLayout(self.detail_container)
        detail_layout.setContentsMargins(LAYOUT_NO_SPACING, LAYOUT_NO_SPACING, LAYOUT_NO_SPACING, LAYOUT_NO_SPACING)
        detail_layout.setSpacing(LAYOUT_NO_SPACING)

        # Generate detail content
        self.generateDetailContent(detail_layout)

        # Add detail container to main layout (collapsed initially)
        self.detail_container.setMaximumHeight(0)
        self.main_layout.addWidget(self.detail_container)

        self._fitToWidth()

    def initCentralWidget(self):
        self.central_widget = QWidget()
        self.central_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(LAYOUT_NO_SPACING, LAYOUT_NO_SPACING, LAYOUT_NO_SPACING, LAYOUT_NO_SPACING)
        self.main_layout.setSpacing(LAYOUT_NO_SPACING)
        self.setLayout(self.main_layout)


    def generateCompactUI(self):
        """Compact view, always visible: title, then status, priority, category, and due date"""
        self.compact_widget = QWidget()
        self.compact_widget.setObjectName("card_container")
        layout = QVBoxLayout(self.compact_widget)
        layout.setContentsMargins(CARD_PADDING + 4, CARD_PADDING + 2, CARD_PADDING + 4, CARD_PADDING + 2)
        layout.setSpacing(8)

        # Title: a readable fixed size, at most two lines, full title on hover
        self.title_label = QLabel()
        self.title_label.setWordWrap(True)
        self.title_label.setToolTip(self.task.title)
        self.title_label.setStyleSheet(f"""
            QLabel {{ color: {AppColors.text_primary}; font-size: 14px; font-weight: bold;
                     background: transparent; padding: 0px; }}
        """)
        title_font = self.title_label.font()
        title_font.setPixelSize(14)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        layout.addWidget(self.title_label)

        # Status and priority as badges; category and due date as quieter text
        meta = QHBoxLayout()
        meta.setSpacing(6)
        meta.addWidget(badge(self.task.status.value, AppColors.get_status_color(self.task.status)))
        meta.addWidget(badge(self.task.priority.name.title(), AppColors.get_priority_color(self.task.priority)))
        meta.addStretch(1)
        if self.task.due_date is not None:
            due = QLabel(f"Due {self.task.due_date.strftime('%b %d').replace(' 0', ' ')}")
            due.setStyleSheet(f"color: {AppColors.get_due_date_color(self.task.due_date)}; font-size: 11px; "
                              f"font-weight: bold; background: transparent;")
            meta.addWidget(due)
        layout.addLayout(meta)

        category = QLabel(self.task.category_name)
        category.setStyleSheet(f"color: {AppColors.text_muted}; font-size: 11px; background: transparent;")
        layout.addWidget(category)

        self.main_layout.addWidget(self.compact_widget)

    def generateDetailContent(self, detail_layout):
        """Shown while hovering: the formatted description (scrollable), hours, and people"""
        self.detail_widget = QWidget()
        self.detail_widget.setObjectName("card_container")
        layout = QVBoxLayout(self.detail_widget)
        layout.setContentsMargins(CARD_PADDING + 4, 0, CARD_PADDING + 4, CARD_PADDING + 2)
        layout.setSpacing(6)

        if self.task.description:
            self.desc_view = DescriptionView(self.task)
            self.desc_view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.desc_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            # Clicking the description opens the task like the rest of the card;
            # the wheel still scrolls it
            self.desc_view.setTextInteractionFlags(Qt.LinksAccessibleByMouse)
            self.desc_view.viewport().installEventFilter(self)
            layout.addWidget(self.desc_view)

        facts = []
        if self.task.estimated_hours:
            facts.append(f"Est. {self.task.estimated_hours:g}h")
        if self.task.actual_hours:
            facts.append(f"Logged {self.task.actual_hours:g}h")
        if self.task.assignee:
            facts.append(f"Assignee: {self.task.assignee}")
        if self.task.start_date is not None:
            facts.append(f"Started {self.task.start_date.strftime('%b %d').replace(' 0', ' ')}")
        if facts:
            info = QLabel("   ·   ".join(facts))
            info.setWordWrap(True)
            info.setStyleSheet(f"color: {AppColors.text_secondary}; font-size: 11px; background: transparent;")
            layout.addWidget(info)

        hint = QLabel("Click to open")
        hint.setStyleSheet(f"color: {AppColors.text_faint}; font-size: 10px; font-style: italic; background: transparent;")
        layout.addWidget(hint)

        detail_layout.addWidget(self.detail_widget)

