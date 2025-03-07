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
# File: grid_layout.py
# Description: Used to display task cards and apply filters for view the cards.
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

import os, json
from utils.tasks_io import load_tasks_from_json, save_task_to_json
from datetime import datetime, timedelta
from ui.custom_widgets.filter_image import FilterButton
from models.task import Task, TaskStatus, TaskPriority, TaskCategory, TaskEntry, Attachment, DueStatus
from resources.styles import AppStyles, AnimatedButton
from utils.directory_finder import resource_path
from ui.task_files.task_card_expanded import TaskCardExpanded
from ui.task_files.task_card_lite import TaskCardLite
from PyQt5.QtWidgets import (QApplication, QWidget, QGridLayout, QPushButton, QVBoxLayout, QHBoxLayout, QMainWindow,
                             QSpacerItem, QLabel, QSizePolicy, QStackedWidget, QDesktopWidget, QScrollArea, QStyle,
                             QComboBox
                             )
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QEvent, QTimer
from PyQt5.QtGui import QResizeEvent, QIcon

class GridLayout(QWidget):
    task_instance = pyqtSignal(Task)
    sendTaskInCardClicked = pyqtSignal(object)
    switchToConsoleView = pyqtSignal()
    toggleTaskManagerView = pyqtSignal()
    taskDeleted = pyqtSignal(str)


    def __init__(self, logger, width, filter=None):
        super().__init__()
        self.logger = logger
        self.filter = filter
        self.grid_width = width
        self.grid_title = ""
        self.taskCards = []
        self.visibleCards = [] 
        self.num_columns = 1
        self.setAcceptDrops(True)
        self.currentlyDraggedCard = None
        self.load_known_tasks()
        self.initComplete = False
        self.initUI()
        
        # Set initial card visibility based on filters
        # If no filter provided, show all cards by default
        if self.filter is not None:
            # print("filter is not none")
            self.onFilterChanged(self.filter)
        else:
            # Make all cards visible by default if no filter
            # print("filter is none")
            self.visibleCards = self.taskCards.copy()
        
        # Force a rearrangement of the layout with the visible cards
        self.rearrangeGridLayout

    def load_known_tasks(self):
        self.tasks = load_tasks_from_json(self.logger)

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)

        # self.updateGeometry()
        self.rearrangeGridLayout()

    def initUI(self):
        self.initCentralWidget()
        self.initManageTasksNav()
        self.initCardGridLayout()

    def initCentralWidget(self):
        self.central_widget = QWidget()
        self.central_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.central_layout = QVBoxLayout(self.central_widget)
        self.central_layout.setContentsMargins(0, 0, 0, 0)
        self.central_layout.setSpacing(0)
        self.setLayout(self.central_layout)

    def initManageTasksNav(self):    
        self.manage_tasks_widget = QWidget()
        self.manage_tasks_layout = QHBoxLayout(self.manage_tasks_widget)  
        self.manage_tasks_layout.setContentsMargins(0, 5, 15, 5)
        # task_header = QLabel("Current Tasks")
        # # print("in grid layout")
        # task_header.setStyleSheet(AppStyles.label_lgfnt())

        filter_button = FilterButton()

        if hasattr(self, 'filter') and self.filter:
            # Copy the filters to the button's active_filters
            filter_button.active_filters = {
                'status': list(self.filter.get('status', [])),
                'category': list(self.filter.get('category', [])),
                'due': list(self.filter.get('due', []))
            }
            # Update the button's appearance
            filter_button.updateButtonState()

        filter_combo = QComboBox()
        filter_combo.setStyleSheet(AppStyles.combo_box_norm())
        filter_combo.addItems([status.value for status in TaskStatus])
        filter_combo.addItems([category.value for category in TaskCategory])
        filter_combo.addItems([due.value for due in DueStatus])

        filter_button.filtersChanged.connect(self.onFilterChanged)

        self.manage_tasks_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        # self.manage_tasks_layout.addWidget(task_header)
        self.manage_tasks_layout.addWidget(filter_button)
        self.manage_tasks_layout.addStretch(1)

        self.central_layout.addWidget(self.manage_tasks_widget)

    def initCardGridLayout(self):
        
        self.current_row = 0
        self.current_column = 0
        self.min_spacing = 20

        # Get card dimensions from TaskCardLite
        self.card_width, _ = TaskCardLite.calculate_optimal_card_size()
        
        # Calculate columns with actual card width
        parent = self
        while parent.parent():
            parent = parent.parent()
        
        # Now parent should be the top-level window
        # print("self.screen_width")
        self.min_spacing = 20
        self.num_columns = int(max(1, self.grid_width / (self.card_width + self.min_spacing)))
        # print(f"size calc: {self.screen_width} // {self.card_width + self.min_spacing}")
        # print(f"Num of columns {self.grid_title}: {self.num_columns}")
        self.grid_layout = QGridLayout()
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setAlignment(Qt.AlignTop)  # Set top alignment for entire grid
        
        # Set default alignment for all cells
        self.grid_layout.setVerticalSpacing(self.min_spacing)  # Add some vertical spacing
        
        self.grid_container_widget = QWidget()
        self.grid_container_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.grid_container_widget.setLayout(self.grid_layout)

        self.addTaskCard()
        self.central_layout.addWidget(self.grid_container_widget)

    def rearrangeGridLayout(self):
        """Rearrange the grid layout using the visibleCards list"""
        # print(f"rearrangement called")
        
        try:
            # Clear the current layout
            while self.grid_layout.count():
                item = self.grid_layout.takeAt(0)
                # Don't need to save widgets as we already have them in taskCards
                
            # Calculate layout parameters
            self.min_spacing = 20
            task_card_lite = TaskCardLite
            task_card_lite.screen_width = self.grid_width
            self.card_width, self.card_height = TaskCardLite.calculate_optimal_card_size()
            total_card_space = self.card_width + self.min_spacing
            print(self.grid_width)
            print(total_card_space)
            
            # Calculate optimal number of columns
            num_cards_fit = int(self.grid_width / total_card_space)
            print(num_cards_fit)
            new_num_columns = max(1, num_cards_fit)
            print(f"num_col: {new_num_columns}")
            self.num_columns = new_num_columns
            
            # Reset position counters
            self.current_row = 0
            self.current_column = 0
            
            # print(f"Total cards: {len(self.taskCards)}, Visible cards: {len(self.visibleCards)}")
            
            # Add only visible cards to the layout
            for card in self.visibleCards:
                # print(f"Setting visible card at: {self.current_row}, {self.current_column}")
                self.grid_layout.addWidget(
                    card,
                    self.current_row,
                    self.current_column,
                    alignment=Qt.AlignTop
                )
                
                # Set row position in card
                card.setRowPosition(self.current_row)
                
                # Move to next position
                self.current_column += 1
                if self.current_column >= self.num_columns:
                    self.current_column = 0
                    self.current_row += 1
            
            # Mark as initialized
            self.initComplete = True
            
            # Update the layout
            # self.grid_layout.update()
            
        except Exception as e:
            print(f"Error in rearrangeGridLayout: {e}")
            import traceback
            traceback.print_exc()

    def addTaskCard(self):
        self.setProperty("source", "add card")
        for task_name, task in self.tasks.items():
            # Create card with Task object
            card = TaskCardLite(logger=self.logger, task=task)
            card.setStyleSheet(AppStyles.task_card())
            card.cardHovered.connect(self.handleCardHover)
            card.cardClicked.connect(lambda _, t=task: self.sendTaskInCardClicked.emit(t))
            
            # Check for duplicates
            skip_this_card = False
            for existingTaskCard in self.taskCards:
                if existingTaskCard.task.title == task.title:
                    skip_this_card = True
                    break
                    
            if skip_this_card:
                continue

            self.taskCards.append(card)
            # Add with explicit top alignment
            self.grid_layout.addWidget(card, self.current_row, self.current_column, 
                                    alignment=Qt.AlignTop)
            self.current_column += 1
            if self.current_column >= self.num_columns:
                self.current_column = 0
                self.current_row += 1
        
        self.rearrangeGridLayout()
    

    def handleCardHover(self, is_hovering, row):
        self.setProperty("source", "hover")
        sender_card = self.sender()

        if sender_card and self.grid_title == sender_card.task.category.value:
            sender_card.setExpanded(is_hovering)

            # Avoid full layout recalculation—only update the specific card
            if is_hovering:
                sender_card.updateGeometry()

    def handleCardClicked(self, task):
        self.sendTaskInCardClicked.emit(task)

    def removeTaskCard(self, task_title):
        """Remove a task card from this grid layout"""
        self.setProperty("source", "remove task card")
        for i, card in enumerate(self.taskCards):
            try:
                if hasattr(card, 'task') and hasattr(card.task, 'title') and card.task.title == task_title:
                    # Remove from the layout
                    self.grid_layout.removeWidget(card)
                    
                    # Remove from our list
                    self.taskCards.pop(i)
                    
                    # Delete the widget
                    card.deleteLater()
                    
                    # Rearrange remaining cards
                    self.rearrangeGridLayout()
                    
                    break  # Break after finding the card
            except Exception as e:
                print(f"Error removing task card: {e}")

    @staticmethod
    def clearGridLayout(layout):
        try:
            # Remove all widgets from the given grid layout
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
        except Exception as e:
            print(f"Error in clearGridLayout: {e}")

    def onFilterChanged(self, active_filters):
        """Handle filter changes and update the visible cards list"""
        # Clear the visible cards list
        self.visibleCards = []
        
        for card in self.taskCards:
            # Default visibility
            show_card = True
            task = card.task
            
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
                # Calculate due status (your existing code)
                if not task.due_date:
                    due_status = DueStatus.NO_DUE_DATE.value
                else:
                    today = datetime.now().date()
                    due_date = task.due_date.date() if isinstance(task.due_date, datetime) else task.due_date
                    days_until_due = (due_date - today).days
                    if days_until_due < 0:
                        due_status = DueStatus.OVERDUE.value
                    elif days_until_due <= 3:
                        due_status = DueStatus.DUE_SOON.value
                    elif days_until_due <= 14:
                        due_status = DueStatus.UPCOMING.value
                    else:
                        due_status = DueStatus.FAR_FUTURE.value
                        
                if due_status not in active_filters['due']:
                    show_card = False
                    
            # Set card visibility and update visibleCards list
            card.setVisible(show_card)
            if show_card:
                self.visibleCards.append(card)
                
        # Rearrange the layout with the updated visibleCards
        self.rearrangeGridLayout()
        
