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
# File: task_dialog.py
# Description: Simple dialog for creating tasks within a phase
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTextEdit, QPushButton, QComboBox, QFormLayout, QWidget, QMessageBox
)

from models.task import TaskPriority, TaskStatus
from resources.styles import AppStyles


class TaskDialog(QDialog):
    """
    Simple dialog for creating or editing a task within a phase
    """

    taskSaved = pyqtSignal(dict)  # Emits task data when saved

    def __init__(self, project_id=None, phase_id=None, logger=None, parent=None):
        """
        Args:
            project_id: Project ID (required)
            phase_id: Phase ID (required)
            logger: Logger instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.project_id = project_id
        self.phase_id = phase_id
        self.logger = logger
        self._saving = False  # Flag to prevent duplicate saves

        self.initUI()

    def initUI(self):
        """Initialize the dialog UI"""
        self.setWindowTitle("Add Task to Phase")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setStyleSheet("""
            QDialog {
                background-color: #2c3e50;
            }
        """)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title
        title_label = QLabel("Add Task to Phase")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #ecf0f1;
            }
        """)
        layout.addWidget(title_label)

        # Form layout
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        form_layout.setLabelAlignment(Qt.AlignRight)

        # Title input
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Enter task title")
        self.title_input.setStyleSheet(self.getInputStyle())
        form_layout.addRow("Title *:", self.title_input)

        # Description input
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Enter task description (optional)")
        self.description_input.setMaximumHeight(100)
        self.description_input.setStyleSheet(self.getInputStyle())
        form_layout.addRow("Description:", self.description_input)

        # Priority dropdown
        self.priority_combo = QComboBox()
        for priority in TaskPriority:
            self.priority_combo.addItem(priority.name, priority)
        # Set default to MEDIUM
        self.priority_combo.setCurrentText("MEDIUM")
        self.priority_combo.setStyleSheet(self.getInputStyle())
        form_layout.addRow("Priority:", self.priority_combo)

        # Status dropdown
        self.status_combo = QComboBox()
        for status in TaskStatus:
            self.status_combo.addItem(status.value, status)
        # Set default to INCOMPLETE
        self.status_combo.setCurrentIndex(0)
        self.status_combo.setStyleSheet(self.getInputStyle())
        form_layout.addRow("Status:", self.status_combo)

        form_widget = QWidget()
        form_widget.setLayout(form_layout)
        layout.addWidget(form_widget)

        # Buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        buttons_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedSize(100, 35)
        cancel_btn.setStyleSheet(self.getSecondaryButtonStyle())
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setAutoDefault(False)  # Prevent this from being default
        buttons_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Add Task")
        save_btn.setFixedSize(100, 35)
        save_btn.setStyleSheet(AppStyles.save_button())
        save_btn.clicked.connect(self.onSave)
        save_btn.setDefault(True)  # Make this the default button for Enter key
        buttons_layout.addWidget(save_btn)

        layout.addLayout(buttons_layout)

    def onSave(self):
        """Validate and save task data"""
        # Prevent duplicate saves
        if self._saving:
            return

        self._saving = True

        try:
            # Validate title
            title = self.title_input.text().strip()
            if not title:
                QMessageBox.warning(self, "Validation Error", "Task title is required.")
                self._saving = False  # Reset flag on validation failure
                return

            # Get form data
            task_data = {
                'title': title,
                'description': self.description_input.toPlainText().strip(),
                'priority': self.priority_combo.currentData(),
                'status': self.status_combo.currentData(),
                'project_id': self.project_id,
                'phase_id': self.phase_id
            }

            # Emit signal with task data
            self.taskSaved.emit(task_data)

            # Close dialog
            self.accept()
        except Exception as e:
            self._saving = False  # Reset flag on error
            raise e

    def getInputStyle(self):
        """Get stylesheet for input widgets"""
        return """
            QLineEdit, QTextEdit, QComboBox {
                padding: 8px;
                border: 2px solid #3498db;
                border-radius: 5px;
                background-color: #34495e;
                color: #ecf0f1;
                font-size: 12px;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
                border: 2px solid #5dade2;
            }
            QLineEdit::placeholder, QTextEdit::placeholder {
                color: #7f8c8d;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid #ecf0f1;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #2c3e50;
                border: 2px solid #3498db;
                selection-background-color: #3498db;
                color: #ecf0f1;
                padding: 4px;
            }
        """

    def getSecondaryButtonStyle(self):
        """Get stylesheet for secondary button"""
        return """
            QPushButton {
                background-color: #34495e;
                color: #ecf0f1;
                border: 2px solid #7f8c8d;
                border-radius: 5px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
            QPushButton:pressed {
                background-color: #95a5a6;
            }
        """
