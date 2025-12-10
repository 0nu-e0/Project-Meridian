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

from PyQt5.QtCore import Qt, pyqtSignal, QMimeData
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel
from PyQt5.QtGui import QDrag

from models.task import Task, TaskStatus


class DraggableTaskItem(QFrame):
    """
    Draggable task item widget that can be dragged between phases
    """

    clicked = pyqtSignal(object)  # Emits task when clicked

    def __init__(self, task: Task, parent=None):
        super().__init__(parent)
        self.task = task
        self.setAcceptDrops(False)  # This widget doesn't accept drops, the phase widget does
        self.initUI()

    def initUI(self):
        """Initialize the widget UI"""
        self.setStyleSheet("""
            QFrame {
                background-color: #34495e;
                border: 2px solid #3498db;
                border-radius: 5px;
                padding: 8px;
            }
            QFrame:hover {
                border: 2px solid #5dade2;
                background-color: #3498db;
            }
        """)
        self.setCursor(Qt.OpenHandCursor)
        self.setMinimumHeight(50)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)

        # Drag handle
        drag_label = QLabel("⋮⋮")
        drag_label.setStyleSheet("color: #bdc3c7; font-size: 14px;")
        drag_label.setAlignment(Qt.AlignTop)
        layout.addWidget(drag_label)

        # Status icon
        status_icon = self.getStatusIcon(self.task.status)
        status_label = QLabel(status_icon)
        status_label.setStyleSheet("font-size: 14px;")
        status_label.setAlignment(Qt.AlignTop)
        layout.addWidget(status_label)

        # Task title
        title_label = QLabel(self.task.title)
        title_label.setStyleSheet("font-size: 13px; color: #ecf0f1; line-height: 1.4;")
        title_label.setWordWrap(True)
        title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(title_label, stretch=1)

        # Priority badge
        priority_badge = QLabel(self.task.priority.name)
        priority_color = self.getPriorityColor(self.task.priority.name)
        priority_badge.setStyleSheet(f"""
            QLabel {{
                background-color: {priority_color};
                color: white;
                font-size: 10px;
                font-weight: bold;
                padding: 3px 8px;
                border-radius: 3px;
            }}
        """)
        priority_badge.setAlignment(Qt.AlignTop)
        layout.addWidget(priority_badge)

    def getStatusIcon(self, status):
        """Get icon for task status"""
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

    def getPriorityColor(self, priority_name):
        """Get color for priority badge"""
        priority_colors = {
            "HIGH": "#e74c3c",
            "MEDIUM": "#f39c12",
            "LOW": "#3498db",
            "CRITICAL": "#c0392b"
        }
        return priority_colors.get(priority_name, "#7f8c8d")

    def mousePressEvent(self, event):
        """Handle mouse press - start drag or emit clicked"""
        if event.button() == Qt.LeftButton:
            # Store the press position
            self.drag_start_position = event.pos()

    def mouseMoveEvent(self, event):
        """Handle mouse move - initiate drag if moved enough"""
        if not (event.buttons() & Qt.LeftButton):
            return

        # Check if moved enough to start drag
        if (event.pos() - self.drag_start_position).manhattanLength() < 10:
            return

        # Start drag operation
        drag = QDrag(self)
        mime_data = QMimeData()

        # Store task ID in mime data
        mime_data.setText(self.task.id)
        mime_data.setData("application/x-task-id", self.task.id.encode())

        drag.setMimeData(mime_data)

        # Change cursor during drag
        self.setCursor(Qt.ClosedHandCursor)

        # Execute drag
        drag.exec_(Qt.MoveAction)

        # Reset cursor
        self.setCursor(Qt.OpenHandCursor)

    def mouseReleaseEvent(self, event):
        """Handle mouse release - emit clicked if not dragging"""
        if event.button() == Qt.LeftButton:
            # If we didn't move much, it's a click
            if hasattr(self, 'drag_start_position'):
                if (event.pos() - self.drag_start_position).manhattanLength() < 10:
                    self.clicked.emit(self.task)
