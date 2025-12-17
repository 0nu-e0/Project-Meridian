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
# File: project_dialog.py
# Description: Dialog for creating and editing projects
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

from PyQt5.QtCore import Qt, pyqtSignal, QDate
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTextEdit, QComboBox, QDateEdit, QPushButton, QColorDialog,
    QFormLayout, QWidget, QMessageBox
)
from PyQt5.QtGui import QColor

from models.project import ProjectStatus
from models.task import TaskPriority
from resources.styles import AppStyles


class ProjectDialog(QDialog):
    """
    Dialog for creating or editing a project
    """

    projectSaved = pyqtSignal(dict)  # Emits project data when saved

    def __init__(self, mode="create", project=None, logger=None, parent=None):
        """
        Args:
            mode: "create" or "edit"
            project: Project object (required if mode is "edit")
            logger: Logger instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.mode = mode
        self.project = project
        self.logger = logger
        self.selected_color = "#3498db"  # Default color
        self.project_data = None  # Store project data when saved

        # Pre-fill with project data if editing
        if mode == "edit" and project:
            self.selected_color = project.color

        self.initUI()

        # Pre-fill fields if editing
        if mode == "edit" and project:
            self.fillFields()

    def initUI(self):
        """Initialize the dialog UI"""
        self.setWindowTitle("New Project" if self.mode == "create" else "Edit Project")
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
        title_label = QLabel("New Project" if self.mode == "create" else "Edit Project")
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
        self.title_input.setPlaceholderText("Enter project title")
        self.title_input.setStyleSheet(self.getInputStyle())
        form_layout.addRow("Title *:", self.title_input)

        # Description input
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Enter project description (optional)")
        self.description_input.setMaximumHeight(100)
        self.description_input.setStyleSheet(self.getInputStyle())
        form_layout.addRow("Description:", self.description_input)

        # Status dropdown
        self.status_combo = QComboBox()
        for status in ProjectStatus:
            self.status_combo.addItem(status.value, status)
        self.status_combo.setStyleSheet(self.getInputStyle())
        form_layout.addRow("Status:", self.status_combo)

        # Priority dropdown
        self.priority_combo = QComboBox()
        for priority in TaskPriority:
            self.priority_combo.addItem(priority.name, priority)
        # Set default to MEDIUM
        self.priority_combo.setCurrentText("MEDIUM")
        self.priority_combo.setStyleSheet(self.getInputStyle())
        form_layout.addRow("Priority:", self.priority_combo)

        # Start date picker
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDate(QDate.currentDate())
        self.start_date_edit.setSpecialValueText("Not set")
        self.start_date_edit.setStyleSheet(self.getInputStyle())
        form_layout.addRow("Start Date:", self.start_date_edit)

        # Target completion date picker
        self.target_date_edit = QDateEdit()
        self.target_date_edit.setCalendarPopup(True)
        self.target_date_edit.setDate(QDate.currentDate().addMonths(1))
        self.target_date_edit.setSpecialValueText("Not set")
        self.target_date_edit.setStyleSheet(self.getInputStyle())
        form_layout.addRow("Target Date:", self.target_date_edit)

        # Color picker
        color_layout = QHBoxLayout()
        self.color_button = QPushButton()
        self.color_button.setFixedSize(100, 30)
        self.updateColorButton()
        self.color_button.clicked.connect(self.onColorPicker)
        color_layout.addWidget(self.color_button)
        color_layout.addStretch()

        form_widget = QWidget()
        form_widget.setLayout(form_layout)
        layout.addWidget(form_widget)

        # Add color picker row
        color_label = QLabel("Color:")
        color_label.setStyleSheet("font-size: 12px; color: #ecf0f1;")
        form_layout.addRow(color_label, color_layout)

        # Buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        buttons_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedSize(100, 35)
        cancel_btn.setStyleSheet(self.getSecondaryButtonStyle())
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setFixedSize(100, 35)
        save_btn.setStyleSheet(AppStyles.save_button())
        save_btn.clicked.connect(self.onSave)
        buttons_layout.addWidget(save_btn)

        layout.addLayout(buttons_layout)

    def fillFields(self):
        """Fill form fields with project data (for edit mode)"""
        if not self.project:
            return

        self.title_input.setText(self.project.title)
        self.description_input.setPlainText(self.project.description)

        # Set status
        index = self.status_combo.findData(self.project.status)
        if index >= 0:
            self.status_combo.setCurrentIndex(index)

        # Set priority
        index = self.priority_combo.findData(self.project.priority)
        if index >= 0:
            self.priority_combo.setCurrentIndex(index)

        # Set dates
        if self.project.start_date:
            self.start_date_edit.setDate(QDate(
                self.project.start_date.year,
                self.project.start_date.month,
                self.project.start_date.day
            ))

        if self.project.target_completion:
            self.target_date_edit.setDate(QDate(
                self.project.target_completion.year,
                self.project.target_completion.month,
                self.project.target_completion.day
            ))

        # Color is already set in __init__

    def onColorPicker(self):
        """Open color picker dialog"""
        color = QColorDialog.getColor(QColor(self.selected_color), self, "Select Project Color")

        if color.isValid():
            self.selected_color = color.name()
            self.updateColorButton()

    def updateColorButton(self):
        """Update the color button appearance"""
        self.color_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.selected_color};
                border: 2px solid #bdc3c7;
                border-radius: 5px;
            }}
            QPushButton:hover {{
                border: 2px solid #95a5a6;
            }}
        """)
        self.color_button.setText("")

    def onSave(self):
        """Validate and save project data"""
        # Validate title
        title = self.title_input.text().strip()
        if not title:
            QMessageBox.warning(self, "Validation Error", "Project title is required.")
            return

        # Get form data
        from datetime import datetime

        project_data = {
            'title': title,
            'description': self.description_input.toPlainText().strip(),
            'status': self.status_combo.currentData(),
            'priority': self.priority_combo.currentData(),
            'color': self.selected_color,
            'start_date': None,
            'target_completion': None
        }

        # Convert QDate to datetime
        start_qdate = self.start_date_edit.date()
        if start_qdate != self.start_date_edit.minimumDate():
            project_data['start_date'] = datetime(
                start_qdate.year(),
                start_qdate.month(),
                start_qdate.day()
            )

        target_qdate = self.target_date_edit.date()
        if target_qdate != self.target_date_edit.minimumDate():
            project_data['target_completion'] = datetime(
                target_qdate.year(),
                target_qdate.month(),
                target_qdate.day()
            )

        # If editing, include project_id
        if self.mode == "edit" and self.project:
            project_data['project_id'] = self.project.id

        # Store project data for getProjectData() method
        self.project_data = project_data

        # Emit signal with project data
        self.projectSaved.emit(project_data)

        # Close dialog
        self.accept()

    def getProjectData(self):
        """Return the saved project data"""
        return self.project_data

    def getInputStyle(self):
        """Get stylesheet for input widgets"""
        return """
            QLineEdit, QTextEdit, QComboBox, QDateEdit {
                padding: 8px;
                border: 2px solid #3498db;
                border-radius: 5px;
                background-color: #34495e;
                color: #ecf0f1;
                font-size: 12px;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QDateEdit:focus {
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
