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
# File: add_task_group.py
# Description: Dialog box used to create a new grid layout filter section.
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

import time
from datetime import datetime
from utils.dashboard_config import DashboardConfigManager
from utils.categories_config import CategoriesConfigManager
from models.task import TaskCategory, TaskPriority, TaskStatus, DueStatus
from PyQt5.QtWidgets import (QApplication, QWidget, QSizePolicy, QHBoxLayout, QVBoxLayout,
                             QPushButton, QDialog, QLabel, QLineEdit, QSpinBox, QTabWidget, QCheckBox,
                             QMessageBox, QInputDialog, QScrollArea
                            )
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QGuiApplication

class AddGridDialog(QDialog):
    addGroupCancel = pyqtSignal()
    addGroupSaveSignel = pyqtSignal()

    def __init__(self, logger, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Task Group")

        self.logger = logger
        
        # Get optimal size based on screen dimensions
        width, height = self.calculate_optimal_size()
        self.resize(width, height)
        
        # Initialize UI components
        self.initUI()
        
    def calculate_optimal_size(self):
        # Use QGuiApplication.primaryScreen() instead of deprecated QDesktopWidget
        screen = QGuiApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        width = min(600, screen_geometry.width() * 0.5)
        height = min(700, screen_geometry.height() * 0.7)
        return width, height
        
    def initUI(self):
        layout = QVBoxLayout(self)
        
        # Grid name input
        name_layout = QHBoxLayout()
        name_label = QLabel("Group Name:")
        self.name_input = QLineEdit()
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)
        
        # Create tabbed filter interface
        filter_tabs = QTabWidget()
        
        # Status tab
        status_widget = QWidget()
        status_layout = QVBoxLayout(status_widget)
        self.status_checkboxes = {}
        for status in TaskStatus:
            checkbox = QCheckBox(status.value)
            self.status_checkboxes[status.value] = checkbox
            status_layout.addWidget(checkbox)
        status_layout.addStretch()
        filter_tabs.addTab(status_widget, "Status")
        
        # Category tab
        category_widget = QWidget()
        category_main_layout = QVBoxLayout(category_widget)

        # Add "Create New Category" button at the top
        new_category_btn = QPushButton("+ Create New Category")
        new_category_btn.clicked.connect(self.onCreateNewCategory)
        category_main_layout.addWidget(new_category_btn)

        # Scrollable area for categories
        category_scroll = QScrollArea()
        category_scroll.setWidgetResizable(True)
        category_scroll.setFrameShape(QScrollArea.NoFrame)

        category_scroll_widget = QWidget()
        category_layout = QVBoxLayout(category_scroll_widget)

        # Load dynamic categories
        self.category_checkboxes = {}
        self.loadCategories(category_layout)

        category_layout.addStretch()
        category_scroll.setWidget(category_scroll_widget)
        category_main_layout.addWidget(category_scroll)

        filter_tabs.addTab(category_widget, "Category")
        
        # Due Date tab
        due_widget = QWidget()
        due_layout = QVBoxLayout(due_widget)
        self.due_checkboxes = {}
        for due in DueStatus:
            checkbox = QCheckBox(due.value)
            self.due_checkboxes[due.value] = checkbox
            due_layout.addWidget(checkbox)
        due_layout.addStretch()
        filter_tabs.addTab(due_widget, "Due Date")
        
        layout.addWidget(filter_tabs)
        
        # Button layout
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.addGroupCancel.emit)
        
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.addGroupSave)
        self.save_button.setDefault(True)
        
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.save_button)
        layout.addLayout(button_layout)

    def loadCategories(self, layout):
        """Load categories from config and create checkboxes"""
        # Load dynamic categories from config
        categories = CategoriesConfigManager.load_categories()

        # Clear existing checkboxes
        self.category_checkboxes.clear()

        # Create checkbox for each category
        for category in categories:
            checkbox = QCheckBox(category)
            self.category_checkboxes[category] = checkbox
            layout.addWidget(checkbox)

    def onCreateNewCategory(self):
        """Handle creating a new category"""
        # Show input dialog
        category_name, ok = QInputDialog.getText(
            self,
            "Create New Category",
            "Enter category name:",
            QLineEdit.Normal,
            ""
        )

        if ok and category_name:
            category_name = category_name.strip()

            # Validate category name
            if not category_name:
                QMessageBox.warning(
                    self,
                    "Invalid Name",
                    "Category name cannot be empty.",
                    QMessageBox.Ok
                )
                return

            # Check if category already exists
            if CategoriesConfigManager.category_exists(category_name):
                QMessageBox.warning(
                    self,
                    "Category Exists",
                    f"Category '{category_name}' already exists.",
                    QMessageBox.Ok
                )
                return

            # Add the new category
            if CategoriesConfigManager.add_category(category_name):
                QMessageBox.information(
                    self,
                    "Success",
                    f"Category '{category_name}' has been created successfully!",
                    QMessageBox.Ok
                )

                # Reload the category checkboxes
                self.refreshCategoryList()
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    "Failed to create category. Please try again.",
                    QMessageBox.Ok
                )

    def refreshCategoryList(self):
        """Refresh the category checkboxes after adding a new category"""
        # Find the category scroll widget
        category_tab = self.findChild(QTabWidget).widget(1)  # Category is the second tab
        category_scroll = category_tab.findChild(QScrollArea)
        category_scroll_widget = category_scroll.widget()
        category_layout = category_scroll_widget.layout()

        # Clear the layout (except the stretch)
        while category_layout.count() > 1:
            item = category_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Reload categories
        self.loadCategories(category_layout)

    def addGroupSave(self):
        """Collect data from the dialog and save the new grid"""
        name = self.name_input.text().strip()

        if not name:
            QMessageBox.warning(
                self, "Missing Information",
                "Please enter a name for the grid layout.",
                QMessageBox.Ok
            )
            self.name_input.setFocus()
            return

        status_filters = [status for status, cb in self.status_checkboxes.items() if cb.isChecked()]
        category_filters = [category for category, cb in self.category_checkboxes.items() if cb.isChecked()]
        due_filters = [due for due, cb in self.due_checkboxes.items() if cb.isChecked()]

        if not status_filters and not category_filters and not due_filters:
            QMessageBox.warning(
                self, "Missing Information",
                "Please select at least one filter in any category.",
                QMessageBox.Ok
            )
            return

        grid_id = DashboardConfigManager.add_grid_layout(name, None)
        grid_layouts = DashboardConfigManager.get_all_grid_layouts()

        for grid in grid_layouts:
            # dict case
            if isinstance(grid, dict) and grid.get("id") == grid_id:
                grid.setdefault("filter", {})
                grid["filter"]["status"] = status_filters
                grid["filter"]["category"] = category_filters
                grid["filter"]["due"] = due_filters
                # ensure minimize exists as top-level bool
                grid.setdefault("minimize", False)
                break

            # object case
            if hasattr(grid, "id") and grid.id == grid_id:
                if not hasattr(grid, "filter") or grid.filter is None:
                    f = type("", (), {})()
                    f.status, f.category, f.due = [], [], []
                    grid.filter = f
                grid.filter.status = status_filters
                grid.filter.category = category_filters
                grid.filter.due = due_filters
                if not hasattr(grid, "minimize"):
                    grid.minimize = False
                break

        DashboardConfigManager.save_grid_layouts(grid_layouts)
        self.addGroupSaveSignel.emit()
        self.done(QDialog.Accepted)

        
    def get_grid_config(self):
        """Return the grid configuration dictionary."""
        # Generate a unique ID
        grid_id = f"grid_{int(time.time())}"
        
        # Collect selected filters
        status_filters = [status for status, checkbox in self.status_checkboxes.items() 
                          if checkbox.isChecked()]
        category_filters = [category for category, checkbox in self.category_checkboxes.items() 
                            if checkbox.isChecked()]
        due_filters = [due for due, checkbox in self.due_checkboxes.items() 
                       if checkbox.isChecked()]
        
        # Build configuration dictionary
        config = {
            'id': grid_id,
            'name': self.name_input.text(),
            'position': 0,  # Will be set correctly when added to the list
            'columns': self.columns_spinner.value(),
            'filter': {
                'status': status_filters,
                'category': category_filters,
                'due': due_filters
            }
        }
        
        return config

