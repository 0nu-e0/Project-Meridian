from resources.styles import AppStyles
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QSpacerItem, QSizePolicy
from PyQt5.QtCore import Qt

class WelcomeScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.central_widget = QWidget()
        #self.central_widget.setStyleSheet("background-color: #f5f5f5;")

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter) 

        label = QLabel("Welcome to the App")
        self.setStyleSheet(AppStyles.background_color()) 
        label.setStyleSheet(AppStyles.label_normal())

        layout.addStretch()
        layout.addWidget(label)
        layout.addStretch()

        self.central_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.central_widget.setLayout(layout)
        self.setLayout(layout)



