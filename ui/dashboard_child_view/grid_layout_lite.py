
from models.task import Task
from resources.styles import AppStyles, AnimatedButton
from ui.task_files.task_card import TaskCard
from ui.task_files.task_card_lite import TaskCardLite
from PyQt5.QtWidgets import (QWidget, QGridLayout, QPushButton, QVBoxLayout, QHBoxLayout, QMainWindow,
                             QSpacerItem, QLabel, QSizePolicy, QStackedWidget, QDesktopWidget, QScrollArea)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QResizeEvent

class GridLayout(QWidget):
    task_instance = pyqtSignal(Task)
    sendTaskInCardClicked = pyqtSignal(Task)
    switchToConsoleView = pyqtSignal()
    toggleTaskManagerView = pyqtSignal()

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
        print("loading tasks")
        try:
            if not os.path.exists(self.json_file_path):
                self.logger.error(f"JSON file does not exist: {self.json_file_path}")
                self.stored_tasks_dict = {}
                return

            with open(self.json_file_path, 'r') as file:
                content = file.read()
                if content:
                    self.stored_tasks_dict = json.loads(content)
                    #self.logger.info(f"Loaded devices: {self.stored_devices_dict}")
                    # print("Loaded:", self.stored_tasks_dict)
                else:
                    self.logger.warning("JSON file is empty.")
                    self.stored_tasks_dict = {}

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to decode JSON: {e}")
            self.stored_tasks_dict = {}
        except Exception as e:
            self.logger.error(f"Error loading known devices: {e}")
            self.stored_tasks_dict = {}
            return self.stored_tasks_dict


    def initUI(self):
        #self.setStyleSheet("border: 1px solid green;")
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
        task_header = QLabel("")
        #task_header.setStyleSheet(AppStyles.label_lgfnt())

        self.manage_tasks_label = QLabel("Add New Task")
        #self.manage_tasks_label.setStyleSheet(AppStyles.label_lgfnt())

        self.addTaskButton = AnimatedButton("+", blur=2, x=10, y=10, offsetX=1, offsetY=1) 
        #self.addTaskButton.setStyleSheet(AppStyles.button_normal())

        self.manage_tasks_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        self.manage_tasks_layout.addWidget(task_header)
        self.manage_tasks_layout.addStretch(1)
        self.manage_tasks_layout.addWidget(self.manage_tasks_label)
        self.manage_tasks_layout.addWidget(self.addTaskButton)

        self.addTaskButton.clicked.connect(self.emitNavigateSignal)

        self.central_layout.addWidget(self.manage_tasks_widget)

    def initCardGridLayout(self):
        print("reached grid layout")
        self.current_row = 0
        self.current_column = 0
        
        self.card_width = 500
        card_height = 400
        self.min_spacing = 50 

        # Determine screen width and calculate the number of columns
        self.screen_width = QMainWindow().geometry().width()
        self.num_columns = int(max(1, self.screen_width // self.card_width))  # Ensure at least one column, return the highest value
        #print("number of column set in initCardGridLayout: ", self.num_columns)

        self.grid_layout = QGridLayout()
        self.grid_layout.setContentsMargins(0, 50, 0, 0)
        self.grid_layout.setSpacing(40) 

        self.grid_container_widget = QWidget()
        self.grid_container_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.grid_container_widget.setLayout(self.grid_layout)

        scroll_area = QScrollArea()    
        scroll_area.setFrameShape(QScrollArea.NoFrame)  
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.grid_container_widget)

        #scroll_area.setStyleSheet(AppStyles.scroll_area())

        self.addTaskCard()

        self.central_layout.addWidget(scroll_area)

    def rearrangeGridLayout(self):
        try:
            self.widgets = []
            while self.grid_layout.count():
                item = self.grid_layout.takeAt(0)
                if item.widget():
                    self.widgets.append(item.widget())

            # Clear grid layout counters
            self.current_row = 0
            self.current_column = 0

            # Re-add the widgets to the grid layout
            for widget in self.widgets:
                self.grid_layout.addWidget(widget, self.current_row, self.current_column)
                #print("rearrangeGris row: ", self.current_row)
                #print("rearrangeGris column: ", self.current_column)
                self.current_column += 1
                if self.current_column >= self.num_columns:
                    #print("rearrangeGris row 2: ", self.current_row)
                    #print("rearrangeGris column 2: ", self.current_column)
                    self.current_column = 0
                    self.current_row += 1

            # Update the layout
            self.grid_layout.update()
            container_widget = self.grid_layout.parentWidget()
            if container_widget:
                container_widget.adjustSize()

        except Exception as e:
            print(f"Error in rearrangeGridLayout: {e}")

    def addTaskCard(self):
        print("Adding task")
        for task_name in self.stored_tasks_dict.items():
            # Create card for each task
            card = TaskCardLite(logger=self.logger, task=task_name)
            
            # The current duplicate check will skip ALL cards after finding one duplicate
            # Let's modify this:
            skip_this_card = False
            for existingTaskCard in self.taskCards:
                if existingTaskCard.task == task_name:
                    skip_this_card = True
                    break
                    
            if skip_this_card:
                continue
                
            # If no duplicate found, add the task
            print(f"Adding card for task: {task_name}")  # Add this
            self.taskCards.append(card)
            self.grid_layout.addWidget(card, self.current_row, self.current_column)
            self.current_column += 1  # Add this
            if self.current_column >= self.num_columns:  # Add this
                self.current_column = 0  # Add this
                self.current_row += 1  # Add this


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

    def handleCardClick(self, task):
        #print("handling card click: ", task)
        # self.switchToConsoleView.emit()
        self.sendTaskInCardClicked.emit(task)

    def emitNavigateSignal(self):
        self.toggleTaskManagerView.emit()  