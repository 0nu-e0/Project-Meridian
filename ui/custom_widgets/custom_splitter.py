from PyQt5.QtWidgets import QSplitterHandle, QFrame, QSplitter
from PyQt5.QtCore import QSize, Qt

class CustomSplitterHandle(QSplitterHandle): 
    def __init__(self, orientation, parent=None): 
        super().__init__(orientation, parent) 
        self.frame = QFrame(self) 
        self.frame.setFrameStyle(QFrame.Panel | QFrame.Sunken) 
        self.frame.setGeometry(self.rect()) 

    def sizeHint(self): 
        return QSize(2, 2) if self.orientation() == Qt.Horizontal else QSize(2, 2) 

    def resizeEvent(self, event): 
        super().resizeEvent(event) 
        self.frame.setGeometry(self.rect()) 

class CustomSplitter(QSplitter): 
    def createHandle(self): 
        return CustomSplitterHandle(self.orientation(), self)