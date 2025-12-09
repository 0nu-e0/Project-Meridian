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
# File: phase_dialog.py
# Description: Dialog for creating and editing project phases
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTextEdit, QPushButton, QFormLayout, QWidget, QMessageBox
)

from models.phase import Phase
from resources.styles import AppStyles


class PhaseDialog(QDialog):
    """
    Dialog for creating or editing a phase
    """

    phaseSaved = pyqtSignal(dict)  # Emits phase data when saved

    def __init__(self, mode="create", project_id=None, phase=None, logger=None, parent=None):
        """
        Args:
            mode: "create" or "edit"
            project_id: Project ID (required for create mode)
            phase: Phase object (required if mode is "edit")
            logger: Logger instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.mode = mode
        self.project_id = project_id
        self.phase = phase
        self.logger = logger

        self.initUI()

        # Pre-fill fields if editing
        if mode == "edit" and phase:
            self.fillFields()

    def initUI(self):
        """Initialize the dialog UI"""
        self.setWindowTitle("New Phase" if self.mode == "create" else "Edit Phase")
        self.setModal(True)
        self.setMinimumWidth(450)
        self.setStyleSheet("""
            QDialog {
                background-color: white;
            }
        """)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title
        title_label = QLabel("New Phase" if self.mode == "create" else "Edit Phase")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #2c3e50;
            }
        """)
        layout.addWidget(title_label)

        # Form layout
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        form_layout.setLabelAlignment(Qt.AlignRight)

        # Name input
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter phase name")
        self.name_input.setStyleSheet(self.getInputStyle())
        form_layout.addRow("Name *:", self.name_input)

        # Description input
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Enter phase description (optional)")
        self.description_input.setMaximumHeight(100)
        self.description_input.setStyleSheet(self.getInputStyle())
        form_layout.addRow("Description:", self.description_input)

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
        buttons_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setFixedSize(100, 35)
        save_btn.setStyleSheet(AppStyles.save_button())
        save_btn.clicked.connect(self.onSave)
        buttons_layout.addWidget(save_btn)

        layout.addLayout(buttons_layout)

    def fillFields(self):
        """Fill form fields with phase data (for edit mode)"""
        if not self.phase:
            return

        self.name_input.setText(self.phase.name)
        self.description_input.setPlainText(self.phase.description)

    def onSave(self):
        """Validate and save phase data"""
        # Validate name
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Phase name is required.")
            return

        # Get form data
        phase_data = {
            'name': name,
            'description': self.description_input.toPlainText().strip()
        }

        # If editing, include phase_id
        if self.mode == "edit" and self.phase:
            phase_data['phase_id'] = self.phase.id

        # Emit signal with phase data
        self.phaseSaved.emit(phase_data)

        # Close dialog
        self.accept()

    def getInputStyle(self):
        """Get stylesheet for input widgets"""
        return """
            QLineEdit, QTextEdit {
                padding: 8px;
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                background-color: white;
                font-size: 12px;
            }
            QLineEdit:focus, QTextEdit:focus {
                border: 2px solid #3498db;
            }
        """

    def getSecondaryButtonStyle(self):
        """Get stylesheet for secondary button"""
        return """
            QPushButton {
                background-color: #ecf0f1;
                color: #2c3e50;
                border: none;
                border-radius: 5px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #bdc3c7;
            }
            QPushButton:pressed {
                background-color: #95a5a6;
            }
        """
