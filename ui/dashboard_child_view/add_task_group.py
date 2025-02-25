import time
from datetime import datetime
from utils.dashboard_config import DashboardConfigManager
from models.task import TaskCategory, TaskPriority, TaskStatus, DueStatus
from PyQt5.QtWidgets import (QApplication, QDesktopWidget, QWidget, QSizePolicy, QHBoxLayout, QVBoxLayout,
                             QPushButton, QDialog, QLabel, QLineEdit, QSpinBox, QTabWidget, QCheckBox, 
                             QMessageBox
                            )
from PyQt5.QtCore import Qt, pyqtSignal

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
        screen = QDesktopWidget().screenGeometry()
        width = min(600, screen.width() * 0.5)
        height = min(700, screen.height() * 0.7)
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
        category_layout = QVBoxLayout(category_widget)
        self.category_checkboxes = {}
        for category in TaskCategory:
            checkbox = QCheckBox(category.value)
            self.category_checkboxes[category.value] = checkbox
            category_layout.addWidget(checkbox)
        category_layout.addStretch()
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

    def addGroupSave(self):
        """Collect data from the dialog and save the new grid"""
        # Get name and trim whitespace
        name = self.name_input.text().strip()
        
        # Check if name is empty
        if not name:
            QMessageBox.warning(self, "Missing Information", 
                            "Please enter a name for the grid layout.", 
                            QMessageBox.Ok)
            self.name_input.setFocus()
            return
        
        # Check if any filters are selected
        status_filters = [status for status, checkbox in self.status_checkboxes.items() 
                        if checkbox.isChecked()]
        category_filters = [category for category, checkbox in self.category_checkboxes.items() 
                        if checkbox.isChecked()]
        due_filters = [due for due, checkbox in self.due_checkboxes.items() 
                    if checkbox.isChecked()]
        
        # At least one filter must be selected
        if not status_filters and not category_filters and not due_filters:
            QMessageBox.warning(self, "Missing Information", 
                            "Please select at least one filter in any category.", 
                            QMessageBox.Ok)
            return
    
        # Get the grid ID - pass None for columns to use default
        grid_id = DashboardConfigManager.add_grid_layout(name, None)
        
        # Update the grid with the selected filters
        grid_layouts = DashboardConfigManager.get_all_grid_layouts()
        
        for grid in grid_layouts:
            if grid.id == grid_id:
                # Update the filters
                grid.filter.status = status_filters
                grid.filter.category = category_filters
                grid.filter.due = due_filters
                break
        
        # Save the updated grid layouts
        DashboardConfigManager.save_grid_layouts(grid_layouts)
        
        self.addGroupSaveSignel.emit()
        
        # Close the dialog
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

