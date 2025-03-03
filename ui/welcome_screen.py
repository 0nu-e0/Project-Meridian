# -----------------------------------------------------------------------------
# Project Maridian
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
# File: welcome_screen.py
# Description: First screen loaded in the app. Placeholder.
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

from resources.styles import AppStyles
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QSpacerItem, QSizePolicy
from PyQt5.QtCore import Qt

class WelcomeScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.central_widget = QWidget()
        self.central_widget.setStyleSheet(AppStyles.background_color()) 

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter) 

        label = QLabel("Welcome to some App")
        self.setStyleSheet(AppStyles.background_color()) 
        label.setStyleSheet(AppStyles.label_normal())

        layout.addStretch()
        layout.addWidget(label)
        layout.addStretch()

        self.central_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.central_widget.setLayout(layout)
        self.setLayout(layout)



