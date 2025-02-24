import sys, json, os
from pathlib import Path
from resources.styles import AppStyles, AnimatedButton
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSpacerItem, 
                             QSizePolicy, QGridLayout, QPushButton, QComboBox, QLineEdit,
                             )
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QColor, QPainter, QBrush, QPen, QMovie
from PyQt5.QtSvg import QSvgWidget

class TaskCardEntry(QWidget):

    def __init__(self, logger, task, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.logger = logger
        self.task = task
        self.card_width = 500
        self.card_height = 400
        self.setFixedSize(self.card_width, self.card_height)

        self.projects = self.getProjects()
        self.task_types = self.getTaskTypes()
        self.status_types = self.getStatusTypes()
        self.priority_types = self.getPriorityTypes()

        self.initUI()

    def get_application_root(self):
        if getattr(sys, 'frozen', False):
            return Path(sys.executable).resolve().parent
        else:
            main_module = sys.modules['__main__']
            return Path(main_module.__file__).resolve().parent

    def get_data_directory(self):
        app_dir = self.get_application_root()
        data_directory = app_dir / 'data'
        data_directory.mkdir(exists_ok=True)
        return data_directory

    def loadJSONs(self, json_type):
        json_file_path = self.get_data_directory() / json_type

        try:
            if not os.path.exists(json_file_path):
                self.logger.error(f"JSON file does not exist: {json_file_path}")
                app_dir = self.get_application_root() 
                new_dir = app_dir / 'data' / json_file_path
                new_dir.mkdir(exists_ok=True)
                return

            with open(json_file_path, 'r') as file:
                contents = json.load(file)
                if contents:
                    return contents
                else:
                    self.logger.warning("JSON file is empty")

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to decode JSON: {e}")
        except Exception as e:
            self.logger.error(f"Error loading file: {json_file_path}")

    def initUI(self):
        
        self.initCentralWidget()
        self.initProjectSelection()
        self.initTaskTypeSelection()
        self.initTaskName()
        self.initTaskDescription()
        self.initTaskStatusSelection()
        self.initTaskPriority()

    def initCentralWidget(self):

        central_widget = QWidget()
        central_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.central_layout = QVBoxLayout(central_widget)
        self.central_layout.setContentsMargins(0, 0, 0, 0)
        self.central_layout.setSpacing(0)
        self.setLayout(self.central_layout)

    def initProjectSelection(self):
        
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)

        project_header = QLabel("Projects")

        project_selection_combo = QComboBox()
        project_selection_combo.addItems(self.projects)

        main_layout.addWidget(project_header)
        main_layout.addWidget(project_selection_combo)

        self.central_layout.addWidget(main_widget)
        
    def getProjects(self):
        projects = self.loadJSONs("storedProjects.json")
        return projects
    
    def initTaskTypeSelection(self):

        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)

        task_type_header = QLabel("Tasks Issue")

        task_type_combo = QComboBox()
        task_type_combo.addItems(self.task_types)

        main_layout.addWidget(task_type_header)
        main_layout.addWidget(task_type_combo)

        self.central_layout.addWidget(main_widget)

    def getTaskTypes(self):
        task_types = self.loadJSONs("storedTaskTypes.json")
        return task_types
    
    def initTaskName(self):

        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)

        task_summary_header = QLabel("Summary")

        task_summary_edit = QLineEdit()
        task_summary_edit.setPlaceholderText("Enter Task")

        main_layout.addWidget(task_summary_header)
        main_layout.addWidget(task_summary_edit)

        self.central_layout.addWidget(main_widget)

    def initTaskDescription(self):

        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)

        task_description_header = QLabel("Description")

        task_description_edit = QLineEdit()
        task_description_edit.setPlaceholderText("Describe the Task")

        main_layout.addWidget(task_description_header)
        main_layout.addWidget(task_description_edit)

        self.central_layout.addWidget(main_widget)

    def initTaskStatusSelection(self):

        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)

        task_status_header = QLabel("Status")

        task_status_combo = QComboBox()
        task_status_combo.addItems(self.status_types)

        main_layout.addWidget(task_status_header)
        main_layout.addWidget(task_status_combo)

        self.central_layout.addWdget(main_widget)

    def getStatusTypes(self):
        status_types = self.loadJSONs("storedStatusTypes.json")
        return status_types

    def initTaskPriority(self):

        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)

        task_priority_header = QLabel("Priority")

        task_priority_combo = QComboBox()
        task_priority_combo.addItems(self.priority_types)

        main_layout.addWidget(task_priority_header)
        main_layout.addWidget(task_priority_combo)

        self.central_layout.addWdget(main_widget)

    def getPriorityTypes(self):
        priority_types = self.loadJSONs("storedPriorityTypes.json")
        return priority_types