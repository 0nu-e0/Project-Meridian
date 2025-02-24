import sys
from pathlib import Path
from resources.styles import AppStyles, AnimatedButton
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSpacerItem, 
                             QSizePolicy, QGridLayout, QPushButton,
                             )
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QColor, QPainter, QBrush, QPen, QMovie
from PyQt5.QtSvg import QSvgWidget

class TaskCard(QWidget):
    card_count = 0
    cardClicked = pyqtSignal(object)
    removeTaskCardSignal = pyqtSignal(str)

    def __init__(self, logger, task, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        TaskCard.card_count += 1
        self.logger = logger
        self.task = task
        self.card_width = 500
        self.card_height = 400
        self.setFixedSize(self.card_width, self.card_height)

        self.initUI(task)

    def enterEvent(self, event):
        super().enterEvent(event)

    def leaveEvent(self, event):
        super().leaveEvent(event)

    def mouseEnterEvent(self, event):
        self.cardClicked.emit(self.task)
        super().mousePressEvent(event)

    def task_routine(self, task_name, description, creation_date, due_date, status, assigned, catagory, priority, ):
        self.task_name = task_name

    def subtask_routine(self, parent, subtask_name, description, creation_date, due_date, status, assigned, catagory, priority):
        self.subtask_name = subtask_name

    def initUI(self, task):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        #self.setStyleSheet()

        self.generateUI(task)

    def generateUI(self, task):
        card_layout_widget = QWidget()
        card_layout = QVBoxLayout(card_layout_widget)

        task_name_widget = QWidget()
        task_name_layout = QHBoxLayout(task_name_widget)

        task_name_label = QLabel("")
        task_name_layout.addWidget(task_name_label)

        task_description_widget = QWidget()
        task_description_layout = QHBoxLayout(task_description_widget)

        task_description_label = QLabel("")
        task_description_layout(task_description_label)

        



        
