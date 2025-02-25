# -----------------------------------------------------------------------------
# Project Manager
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
# File: custom_splitter.py
# Description: Custom widget to split sections in the UI. 
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

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