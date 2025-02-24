
import os, json
from utils.tasks_io import load_tasks_from_json, save_task_to_json
from datetime import datetime, timedelta
from ui.custom_widgets.filter_image import FilterButton
from models.task import Task, TaskStatus, TaskPriority, TaskCategory, TaskEntry, Attachment, DueStatus
from resources.styles import AppStyles, AnimatedButton
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
    sendTaskInCardClicked = pyqtSignal(Task)
    switchToConsoleView = pyqtSignal()
    toggleTaskManagerView = pyqtSignal()

    json_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'saved_tasks.json')

    def __init__(self, logger):
        super().__init__()
        self.logger = logger
        self.taskCards = []
        self.setAcceptDrops(True)
        self.currentlyDraggedCard = None  # This will hold the reference to the dragged card
        print("Grid layout found")
        self.load_known_tasks()
        self.initUI()

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
        
        # Logging/debugging
        if self.tasks:
            print(f"Loaded {len(self.tasks)} tasks")
        else:
            print("No tasks loaded or error occurred")
        
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
        

        filter_combo = QComboBox()
        filter_combo.setStyleSheet(AppStyles.combo_box_norm())
        filter_combo.addItems([status.value for status in TaskStatus])
        filter_combo.addItems([category.value for category in TaskCategory])
        filter_combo.addItems([due.value for due in DueStatus])


        filter_button.filtersChanged.connect(self.onFilterChanged)


        self.manage_tasks_label = QLabel("Add New Task")
        self.manage_tasks_label.setStyleSheet(AppStyles.label_lgfnt())

        self.addTaskButton = AnimatedButton("+", blur=2, x=10, y=10, offsetX=1, offsetY=1) 
        self.addTaskButton.setStyleSheet(AppStyles.button_normal())

        self.manage_tasks_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        self.manage_tasks_layout.addWidget(task_header)
        self.manage_tasks_layout.addWidget(filter_button)
        self.manage_tasks_layout.addStretch(1)
        self.manage_tasks_layout.addWidget(self.manage_tasks_label)
        self.manage_tasks_layout.addWidget(self.addTaskButton)

        self.addTaskButton.clicked.connect(self.addNewTask)

        self.central_layout.addWidget(self.manage_tasks_widget)

    def initCardGridLayout(self):
        # print("reached grid layout")
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
        #self.grid_layout.setSpacing(40)
       # self.grid_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)  
        self.grid_layout.setAlignment(Qt.AlignTop) 
        
        self.grid_container_widget = QWidget()
        self.grid_container_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.grid_container_widget.setLayout(self.grid_layout)
        
        scroll_area = QScrollArea()
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.grid_container_widget)
        scroll_area.setStyleSheet(AppStyles.scroll_area())
    
        self.addTaskCard()
        self.central_layout.addWidget(scroll_area)

    def rearrangeGridLayout(self):
        try:
            self.widgets = []
            while self.grid_layout.count():
                item = self.grid_layout.takeAt(0)
                if item.widget():
                    self.widgets.append(item.widget())

            self.current_row = 0
            self.current_column = 0

            for widget in self.widgets:
                self.grid_layout.addWidget(widget, self.current_row, self.current_column)
                # Set row position in card
                if isinstance(widget, TaskCardLite):
                    widget.setRowPosition(self.current_row)
                
                self.current_column += 1
                if self.current_column >= self.num_columns:
                    self.current_column = 0
                    self.current_row += 1

            self.grid_layout.update()
            container_widget = self.grid_layout.parentWidget()
            if container_widget:
                container_widget.adjustSize()

        except Exception as e:
            print(f"Error in rearrangeGridLayout: {e}")

    def addTaskCard(self):
        print("Adding task")
        for task_name, task in self.tasks.items():
            # Task is already a fully populated Task object - no need to create or populate it again
            
            # Create card with Task object
            card = TaskCardLite(logger=self.logger, task=task)
            card.setStyleSheet(AppStyles.task_card())
            card.cardHovered.connect(self.handleCardHover)
            card.cardClicked.connect(self.handleCardClicked)
            
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
        # Create overlay shadow effect
        self.overlay = QWidget(self)
        self.overlay.setStyleSheet("""
            QWidget {
                background-color: rgba(0, 0, 0, 0.5);
            }
        """)
        self.overlay.setGeometry(self.rect())
        
        # Create expanded card
        self.expanded_card = TaskCardExpanded(logger=self.logger, task=task, parent_view=self)
        self.expanded_card.setStyleSheet(AppStyles.expanded_task_card())
        #self.expanded_card.setAttribute(Qt.WA_TranslucentBackground, True)

        self.expanded_card.taskDeleted.connect(self.removeTaskCard)
        # Get screen and window geometries
        screen_geometry = QApplication.desktop().screenGeometry()
        window = self.window()  # Get the main window
        window_geometry = window.geometry()
        
        # Calculate card dimensions
        card_width, card_height = self.expanded_card.calculate_optimal_card_size()
        
        # Calculate center position relative to the window
        center_x = window_geometry.x() + (window_geometry.width() - card_width) // 2
        center_y = window_geometry.y() + (window_geometry.height() - card_height) // 2
        
        # Set position and show expanded card
        self.expanded_card.setGeometry(center_x, center_y, card_width, card_height)
        self.expanded_card.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        
        # Show overlay and card
        self.overlay.show()
        self.expanded_card.show()
        
        # Install event filter to handle clicks outside
        self.overlay.installEventFilter(self)
        
    def eventFilter(self, obj, event):
        if obj == self.overlay and event.type() == QEvent.MouseButtonPress:
            # Check if click is outside the expanded card
            if not self.expanded_card.geometry().contains(event.globalPos()):
                self.closeExpandedCard()
                return True
        return super().eventFilter(obj, event)

    def closeExpandedCard(self):
        if hasattr(self, 'expanded_card'):
            self.expanded_card.close()
            self.expanded_card.deleteLater()
        if hasattr(self, 'overlay'):
            self.overlay.close()
            self.overlay.deleteLater()
        
            
    def removeTaskCard(self, task_name):
        # Find the card with the matching serial number
        for card in self.taskCards:
            if card.task.task_name == task_name:
                # Remove the card widget from the grid layout
                self.grid_layout.removeWidget(card)
                card.deleteLater()  # Ensure the widget is properly disposed of
                # Remove the card from the tracking list
                self.taskCards.remove(card)
                  # Exit the loop once the card is found and removed
        self.updateGridLayoutAfterRemoval()

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

    # def handleCardClick(self, task):
    #     #print("handling card click: ", task)
    #     # self.switchToConsoleView.emit()
    #     self.sendTaskInCardClicked.emit(task)
    #     self.expanded_card.taskDeleted.connect(self.removeTaskCard)

    def addNewTask(self):
        # Create overlay shadow effect
        self.overlay = QWidget(self)
        self.overlay.setStyleSheet("""
            QWidget {
                background-color: rgba(0, 0, 0, 0.5);
            }
        """)
        self.overlay.setGeometry(self.rect())
        
        # Create expanded card
        self.expanded_card = TaskCardExpanded(logger=self.logger, task=None, parent_view=self)
        self.expanded_card.setStyleSheet(AppStyles.expanded_task_card())
        #self.expanded_card.setAttribute(Qt.WA_TranslucentBackground, True)

        self.expanded_card.taskDeleted.connect(self.removeTaskCard)
        # Get screen and window geometries
        screen_geometry = QApplication.desktop().screenGeometry()
        window = self.window()  # Get the main window
        window_geometry = window.geometry()
        
        # Calculate card dimensions
        card_width, card_height = self.expanded_card.calculate_optimal_card_size()
        
        # Calculate center position relative to the window
        center_x = window_geometry.x() + (window_geometry.width() - card_width) // 2
        center_y = window_geometry.y() + (window_geometry.height() - card_height) // 2
        
        # Set position and show expanded card
        self.expanded_card.setGeometry(center_x, center_y, card_width, card_height)
        self.expanded_card.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        
        # Show overlay and card
        self.overlay.show()
        self.expanded_card.show()
        
        # Install event filter to handle clicks outside
        self.overlay.installEventFilter(self)
        
    def onFilterChanged(self, active_filters):
        """Handle filter changes"""
        for card in self.taskCards:  # Use your list of task cards
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
                due_status = self.calculateDueStatus(task)
                if due_status not in active_filters['due']:
                    show_card = False
            
            # Set card visibility
            card.setVisible(show_card)
    
    def removeTaskCard(self, task_title):
        """Remove a task card from the grid layout"""
        # Find the card with matching task title
        for i, card in enumerate(self.taskCards):
            if card.task.title == task_title:
                # Remove from the layout
                self.grid_layout.removeWidget(card)
                
                # Remove from our list
                self.taskCards.pop(i)
                
                # Delete the widget
                card.deleteLater()
                
                # Rearrange remaining cards if needed
                self.rearrangeCards()
                
                # Break after finding the card
                break

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
        
    