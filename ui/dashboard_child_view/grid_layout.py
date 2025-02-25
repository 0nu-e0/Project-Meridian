
import os, json
from utils.tasks_io import load_tasks_from_json, save_task_to_json
from datetime import datetime, timedelta
from ui.custom_widgets.filter_image import FilterButton
from models.task import Task, TaskStatus, TaskPriority, TaskCategory, TaskEntry, Attachment, DueStatus
from resources.styles import AppStyles, AnimatedButton
from utils.directory_finder import resource_path
from ui.task_files.task_card import TaskCard
from ui.task_files.task_card_expanded import TaskCardExpanded
from ui.task_files.task_card_lite import TaskCardLite
from PyQt5.QtWidgets import (QApplication, QWidget, QGridLayout, QPushButton, QVBoxLayout, QHBoxLayout, QMainWindow,
                             QSpacerItem, QLabel, QSizePolicy, QStackedWidget, QDesktopWidget, QScrollArea, QStyle,
                             QComboBox
                             )
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QEvent
from PyQt5.QtGui import QResizeEvent, QIcon

class GridLayout(QWidget):
    task_instance = pyqtSignal(Task)
    sendTaskInCardClicked = pyqtSignal(object)
    switchToConsoleView = pyqtSignal()
    toggleTaskManagerView = pyqtSignal()
    taskDeleted = pyqtSignal(str)

    json_file_path = resource_path('data/saved_tasks.json')

    def __init__(self, logger, filter=None):
        super().__init__()
        self.logger = logger
        self.filter = filter
        self.taskCards = []
        self.setAcceptDrops(True)
        self.currentlyDraggedCard = None 
        # print("Grid layout found")
        self.load_known_tasks()

        self.initUI()

        if self.filter is not None:
            # print("found filters")
            self.onFilterChanged(self.filter)
        else:
            print("didnt find filters")


    def updateView(self):
        self.rearrangeGridLayout() 

    def showEvent(self, event):
        self.updateView()
        super().showEvent(event)
        self.rearrangeGridLayout()

    def resizeEvent(self, event: QResizeEvent):
        try:
            super().resizeEvent(event)
            newSize: QSize = event.size()
            total_card_space = self.card_width + self.min_spacing
            available_width = newSize.width() - self.min_spacing
            num_cards_fit = int((available_width) // total_card_space)
            new_num_columns = int(max(1, num_cards_fit))
            if new_num_columns != self.num_columns:
                self.num_columns = new_num_columns
                self.rearrangeGridLayout()

        except Exception as e:
            print(f"Error in resizeEvent: {e}")
        
        self.grid_layout.update()

    def load_known_tasks(self):

        self.tasks = load_tasks_from_json()

        return self.tasks

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
        task_header = QLabel("Current Tasks")
        # print("in grid layout")
        task_header.setStyleSheet(AppStyles.label_lgfnt())

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
        self.manage_tasks_layout.addWidget(task_header)
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
        self.screen_width = QMainWindow().geometry().width()
        self.num_columns = int(max(1, self.screen_width // (self.card_width + self.min_spacing)))
        
        self.grid_layout = QGridLayout()
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setAlignment(Qt.AlignTop) 
        
        self.grid_container_widget = QWidget()
        self.grid_container_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.grid_container_widget.setLayout(self.grid_layout)
    
        self.addTaskCard()
        self.central_layout.addWidget(self.grid_container_widget)

    def rearrangeGridLayout(self):
        """Rearrange the grid layout to remove gaps"""
        try:
            print("Starting grid rearrangement")
            print(f"Number of columns: {self.num_columns}")
            
            # Collect all visible widgets
            visible_widgets = []
            self.widgets = []
            
            while self.grid_layout.count():
                item = self.grid_layout.takeAt(0)
                if item.widget():
                    widget = item.widget()
                    self.widgets.append(widget)
                    if widget.isVisible():
                        visible_widgets.append(widget)
            
            print(f"Total widgets: {len(self.widgets)}, Visible widgets: {len(visible_widgets)}")
        
            # Reset counters
            self.current_row = 0
            self.current_column = 0
            
            # First add only visible widgets
            for widget in visible_widgets:
                print(f"Adding visible widget at row {self.current_row}, column {self.current_column}")
                self.grid_layout.addWidget(widget, self.current_row, self.current_column)
                
                # Set row position in card
                if isinstance(widget, TaskCardLite):
                    widget.setRowPosition(self.current_row)
                
                self.current_column += 1
                if self.current_column >= self.num_columns:
                    self.current_column = 0
                    self.current_row += 1
            
            # Then add invisible widgets at the end (off-screen)
            hidden_row = self.current_row + 10  # Position them far below
            hidden_col = 0
            
            for widget in self.widgets:
                if widget not in visible_widgets:
                    print(f"Adding hidden widget at row {hidden_row}, column {hidden_col}")
                    self.grid_layout.addWidget(widget, hidden_row, hidden_col)
                    hidden_col += 1
                    if hidden_col >= self.num_columns:
                        hidden_col = 0
                        hidden_row += 1
            
            self.grid_layout.update()
            
            container_widget = self.grid_layout.parentWidget()
            if container_widget:
                container_widget.adjustSize()
                
            print("Grid rearrangement completed")
            
        except Exception as e:
            print(f"Error in rearrangeGridLayout: {e}")

    def addTaskCard(self):
        print("Adding task")
        for task_name, task in self.tasks.items():
            # Task is already a fully populated Task object - no need to create or populate it again
            
            # Create card with Task object
            card = TaskCardLite(logger=self.logger, task=task)
            # print(f"Adding task card: {task_name}")
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
            self.grid_layout.addWidget(card, self.current_row, self.current_column)
            self.current_column += 1
            if self.current_column >= self.num_columns:
                self.current_column = 0
                self.current_row += 1

    def handleCardHover(self, is_hovering, row):
        # Find the specific card that emitted the signal
        sender_card = self.sender()
        if sender_card:
            sender_card.setExpanded(is_hovering)
        
        # Update grid layout
        self.grid_layout.update()

    def handleCardClicked(self, task):
        self.sendTaskInCardClicked.emit(task)

    def removeTaskCard(self, task_title):
        """Remove a task card from this grid layout"""
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

    def updateGridLayoutAfterRemoval(self):
        # Reset position counters
        self.current_row = 0
        self.current_column = 0

        # Re-add remaining widgets to the grid layout in their new positions
        for card in self.taskCards:
            self.grid_layout.addWidget(card, self.current_row, self.current_column)
            self.current_column += 1
            if self.current_column >= self.num_columns:
                self.current_column = 0
                self.current_row += 1

        # Update the layout to reflect the changes
        self.grid_layout.update()

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
        """Handle filter changes"""
        print(f"Grid layout '{getattr(self, 'name', 'unknown')}' handling active filters: {active_filters}")
        print(f"Total task cards before filtering: {len(self.taskCards)}")
        
        # Count cards that will be visible
        visible_count = 0
        for card in self.taskCards:
            # Default visibility
            show_card = True
            task = card.task
            
            # Check status filters
            if active_filters['status']:
                if task.status.value not in active_filters['status']:
                    show_card = False
                    print(f"Card '{task.title}' hidden by status filter")
                    
            # Check category filters
            if show_card and active_filters['category']:
                if task.category.value not in active_filters['category']:
                    show_card = False
                    print(f"Card '{task.title}' hidden by category filter")
                    
            # Check due date filters
            if show_card and active_filters['due']:
                # Use default calculateDueStatus implementation
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
                    print(f"Card '{task.title}' hidden by due date filter")
            
            # Set card visibility
            card.setVisible(show_card)
            if show_card:
                visible_count += 1
        
        self.rearrangeGridLayout()

    def rearrangeCards(self):
        """Rearrange cards in the grid after one is removed"""
        # Clear the current layout
        for i in reversed(range(self.grid_layout.count())):
            self.grid_layout.itemAt(i).widget().setParent(None)
        
        # Reset row and column counters
        self.current_row = 0
        self.current_column = 0
        
        # Add cards back to the grid
        for card in self.taskCards:
            self.grid_layout.addWidget(card, self.current_row, self.current_column)
            self.current_column += 1
            if self.current_column >= self.num_columns:
                self.current_column = 0
                self.current_row += 1
        
    def calculateDueStatus(self, task):
        """
        Calculate the due status of a task based on its due date.
        
        Args:
            task: The task object with a due_date attribute
            
        Returns:
            str: One of the DueStatus values
        """
        if not task.due_date:
            return DueStatus.NO_DUE_DATE.value
        
        # Calculate days until due
        today = datetime.now().date()
        due_date = task.due_date.date() if isinstance(task.due_date, datetime) else task.due_date
        days_until_due = (due_date - today).days
        
        if days_until_due < 0:
            return DueStatus.OVERDUE.value
        elif days_until_due <= 3:
            return DueStatus.DUE_SOON.value
        elif days_until_due <= 14:
            return DueStatus.UPCOMING.value
        else:
            return DueStatus.FAR_FUTURE.value