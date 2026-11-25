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
# File: draggable_task_item.py
# Description: Draggable task item widget for drag-and-drop between phases
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

from PyQt5.QtCore import QMimeData, Qt, pyqtSignal
from PyQt5.QtGui import QDrag
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy

from models.task import Task, TaskStatus
from resources.styles import AppColors
from ui.project_files.project_look import ROW_BACKGROUND, TASK_STATUS_ICONS, priority_badge, short_date

TASK_MIME = "application/x-task-id"


class DraggableTaskItem(QFrame):
    """A task in a phase: click to open it, drag it onto another phase to move it there"""

    clicked = pyqtSignal(object)  # the task

    def __init__(self, task: Task, parent=None):
        super().__init__(parent)
        self.task = task
        self.drag_start_position = None
        self.setAcceptDrops(False)  # the phase takes drops
        self.setObjectName("taskRow")
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setToolTip(f"{task.title}\n{task.status.value}  ·  click to open, drag to move")
        self.initUI()

    def initUI(self):
        task = self.task
        finished = task.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED)
        self.setStyleSheet(f"""
            QFrame#taskRow {{ background-color: {ROW_BACKGROUND}; border: 1px solid transparent; border-radius: 6px; }}
            QFrame#taskRow:hover {{ border-color: {AppColors.accent}; }}
            QLabel {{ background: transparent; border: none; }}""")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 7, 10, 7)
        layout.setSpacing(8)

        status = QLabel(TASK_STATUS_ICONS.get(task.status, "○"))
        status.setToolTip(task.status.value)
        status.setFixedWidth(16)
        status.setAlignment(Qt.AlignCenter)
        status.setStyleSheet(f"color: {AppColors.get_status_color(task.status)}; font-size: 14px;")
        layout.addWidget(status)

        self.title_label = QLabel(task.title)
        self.title_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.title_label.setMinimumWidth(60)
        font = self.title_label.font()
        font.setStrikeOut(task.status == TaskStatus.COMPLETED)
        self.title_label.setFont(font)
        self.title_label.setStyleSheet(f"color: {AppColors.text_muted if finished else AppColors.text_primary}; "
                                       f"font-size: 13px;")
        layout.addWidget(self.title_label, 1)

        if task.due_date is not None and not finished:
            due = QLabel(short_date(task.due_date))
            due.setToolTip(f"Due {short_date(task.due_date, with_year=True)}")
            due.setStyleSheet(f"color: {AppColors.get_due_date_color(task.due_date)}; font-size: 11px; "
                              f"font-weight: bold;")
            layout.addWidget(due)
        if not finished:
            layout.addWidget(priority_badge(task.priority))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.title_label.setText(self.title_label.fontMetrics().elidedText(
            self.task.title, Qt.ElideRight, max(self.title_label.width(), 40)))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.pos()

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton) or self.drag_start_position is None:
            return
        if (event.pos() - self.drag_start_position).manhattanLength() < 10:
            return
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(self.task.id)
        mime_data.setData(TASK_MIME, self.task.id.encode())
        drag.setMimeData(mime_data)
        drag.setPixmap(self.grab())
        self.drag_start_position = None
        self.setCursor(Qt.ClosedHandCursor)
        drag.exec_(Qt.MoveAction)
        from PyQt5 import sip
        if not sip.isdeleted(self):
            self.setCursor(Qt.PointingHandCursor)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.drag_start_position is not None:
            if (event.pos() - self.drag_start_position).manhattanLength() < 10:
                self.clicked.emit(self.task)
        self.drag_start_position = None
