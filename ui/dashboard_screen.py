
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame,
                             QSpacerItem, QLabel, QSizePolicy, QStackedWidget, )
from PyQt5.QtCore import pyqtSignal, QPropertyAnimation, QEasingCurve, QRect, QTimer, pyqtSlot

class DashboardScreen(QWidget):
    def __init__(self):
        super().__init__()

        self.consoles = {}

    def initUI(self):
        self.setStyleSheet()

        