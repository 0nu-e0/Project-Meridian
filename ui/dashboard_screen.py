import os, json
from resources.styles import AppStyles, AnimatedButton
from models.task import Task
from ui.task_files.task_card import TaskCard
from .dashboard_child_view.grid_layout import GridLayout

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame,
                             QSpacerItem, QLabel, QSizePolicy, QStackedWidget, )
from PyQt5.QtCore import pyqtSignal, QPropertyAnimation, QEasingCurve, QRect, QTimer, pyqtSlot, QSize
from PyQt5.QtGui import QResizeEvent

class DashboardScreen(QWidget):
    sendTaskInCardClicked = pyqtSignal(Task)
    json_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'saved_tasks.json')

    def __init__(self, logger):
        super().__init__()

        self.logger = logger

        self.consoles = {}
        self.taskCards = []

        self.initUI()

    def initUI(self):
        #self.setStyleSheet(AppStyles.background_color()) 
        self.initCentralWidget()
        self.initBannerSpacer()
        self.addSeparator()
        self.initTasksLayout()
        self.addSeparator()

    def initCentralWidget(self):
        self.central_widget = QWidget()
        self.central_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.setLayout(self.main_layout)    
        
    def initBannerSpacer(self):
        self.banner_widget = QWidget()
        #self.banner_widget.setStyleSheet("border: 1px solid purple;")
        self.banner_layout = QVBoxLayout(self.banner_widget)
        banner_height = int(self.height()*0.15) 
        self.banner_spacer = QSpacerItem(1, banner_height, QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.banner_layout.addSpacerItem(self.banner_spacer)
        self.main_layout.addWidget(self.banner_widget)

    def addSeparator(self):
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFixedHeight(2)
        #separator.setStyleSheet(AppStyles.divider())
        self.main_layout.addWidget(separator)
        # Add some spacing around the separator
        self.main_layout.addSpacing(20)

    def initTasksLayout(self):
        task_layout_widget = QWidget()
        task_layout_container = QHBoxLayout(task_layout_widget)
        grid_layout = GridLayout(logger=self.logger)
        
        task_layout_container.addWidget(grid_layout)

        self.main_layout.addWidget(task_layout_widget)





    def initProjectsLayout(self):
        self.setStyleSheet()

    def initGanttLayout(self):
        self.setStyleSheet()
