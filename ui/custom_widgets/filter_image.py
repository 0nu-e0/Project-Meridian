# -----------------------------------------------------------------------------
# Project Maridian
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
# File: filter_image.py
# Description: Custom filter button to display the available filters for the 
#              grid layouts.
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

from datetime import datetime
from ui.task_files.task_card_lite import TaskCardLite
from models.task import TaskCategory, TaskStatus, DueStatus
from PyQt5.QtWidgets import QPushButton, QMenu
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, pyqtSignal, QPoint

class FilterButton(QPushButton):
    filtersChanged = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setText("Filter")
        self.setIcon(QIcon.fromTheme("view-filter"))  # Use system icon if available
        
        # Store active filters
        self.active_filters = {
            'status': [],
            'category': [],
            'due': []
        }
        
    def mousePressEvent(self, event):
        # Show filter menu when clicked
        self.showFilterMenu()
        super().mousePressEvent(event)
        
    def showFilterMenu(self):
        # Create popup menu
        menu = QMenu(self)
        
        # Create filter sections
        self.addStatusFilters(menu)
        menu.addSeparator()
        self.addCategoryFilters(menu)
        menu.addSeparator()
        self.addDueFilters(menu)
        menu.addSeparator()
        
        # Add Clear All action
        clear_action = menu.addAction("Clear All Filters")
        clear_action.triggered.connect(self.clearAllFilters)
        
        # Show the menu at button position
        menu.exec_(self.mapToGlobal(QPoint(0, self.height())))
        
    def addStatusFilters(self, menu):
        status_menu = menu.addMenu("Status")
        for status in TaskStatus:
            action = status_menu.addAction(status.value)
            action.setCheckable(True)
            action.setChecked(status.value in self.active_filters['status'])
            action.triggered.connect(lambda checked, s=status.value: self.toggleFilter('status', s, checked))
            
    def addCategoryFilters(self, menu):
        category_menu = menu.addMenu("Category")
        for category in TaskCategory:
            action = category_menu.addAction(category.value)
            action.setCheckable(True)
            action.setChecked(category.value in self.active_filters['category'])
            action.triggered.connect(lambda checked, c=category.value: self.toggleFilter('category', c, checked))
            
    def addDueFilters(self, menu):
        due_menu = menu.addMenu("Due Date")
        for due in DueStatus:
            action = due_menu.addAction(due.value)
            action.setCheckable(True)
            action.setChecked(due.value in self.active_filters['due'])
            action.triggered.connect(lambda checked, d=due.value: self.toggleFilter('due', d, checked))
            
    def toggleFilter(self, filter_type, value, checked):
        if checked and value not in self.active_filters[filter_type]:
            self.active_filters[filter_type].append(value)
        elif not checked and value in self.active_filters[filter_type]:
            self.active_filters[filter_type].remove(value)
            
        # Emit signal with updated filters
        self.filtersChanged.emit(self.active_filters)
        
        # Update button appearance
        self.updateButtonState()
        
    def clearAllFilters(self):
        for key in self.active_filters:
            self.active_filters[key] = []
            
        # Emit signal with cleared filters
        self.filtersChanged.emit(self.active_filters)
        
        # Update button appearance
        self.updateButtonState()
        
    def updateButtonState(self):
        # Change button appearance based on whether filters are active
        has_filters = any(len(filters) > 0 for filters in self.active_filters.values())
        
        if has_filters:
            self.setStyleSheet("QPushButton { font-weight: bold; background-color: #3498db; color: white; }")
            
            # Update text to show how many filters are applied
            count = sum(len(filters) for filters in self.active_filters.values())
            self.setText(f"Filter ({count})")
        else:
            self.setStyleSheet("")
            self.setText("Filter")

    def applyFilters(self, active_filters):
        """Apply filters to the task cards"""
        for card in self.parent().findChildren(TaskCardLite):  # Get all task cards
            # Default visibility
            show_card = True
            task = card.task  # Get the Task object from the card
            
            # Check status filters
            if active_filters['status']:
                if task.status.value not in active_filters['status']:
                    show_card = False
                    
            # Check category filters
            if show_card and active_filters['category']:
                if task.category.value not in active_filters['category']:
                    show_card = False
                    
            # Check due date filters
            if show_card and active_filters['due']:
                due_status = self.calculateDueStatus(task)
                if due_status not in active_filters['due']:
                    show_card = False
            
            # Set card visibility
            card.setVisible(show_card)

    def calculateDueStatus(self, task):
        """Calculate the due status of a task"""
        if not task.due_date:
            return DueStatus.NO_DUE_DATE.value
            
        days_until_due = (task.due_date - datetime.now()).days
        
        if days_until_due < 0:
            return DueStatus.OVERDUE.value
        elif days_until_due <= 2:
            return DueStatus.DUE_SOON.value
        elif days_until_due <= 7:
            return DueStatus.UPCOMING.value
        else:
            return DueStatus.FAR_FUTURE.value