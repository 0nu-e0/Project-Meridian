# -----------------------------------------------------------------------------
# Project Meridian
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
# File: toast.py
# Description: A small notice at the bottom of the window ("Deleted 'X'  Undo")
#              that goes away on its own after a few seconds.
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QPushButton

from resources.styles import AppColors

SHOW_FOR_MS = 6000
BOTTOM_GAP = 28


class Toast(QFrame):
    """A notice with an optional button, shown at the bottom centre of its window"""

    def __init__(self, window):
        super().__init__(window)
        self.window_ = window
        self._action = None
        self.setObjectName("toast")
        self.setStyleSheet(f"""
            QFrame#toast {{ background-color: {AppColors.surface_raised}; border: 1px solid {AppColors.surface_hover_alt};
                            border-radius: 10px; }}
            QLabel {{ background: transparent; color: {AppColors.text_primary}; font-size: 13px; }}
            QPushButton#toastAction {{ background: transparent; color: {AppColors.accent}; border: none;
                                       font-size: 13px; font-weight: bold; padding: 4px 8px; }}
            QPushButton#toastAction:hover {{ text-decoration: underline; }}
            QPushButton#toastClose {{ background: transparent; color: {AppColors.text_muted}; border: none;
                                      font-size: 14px; padding: 2px 6px; }}
            QPushButton#toastClose:hover {{ color: {AppColors.text_primary}; }}""")
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 120))
        self.setGraphicsEffect(shadow)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 8, 8)
        layout.setSpacing(10)
        self.label = QLabel()
        layout.addWidget(self.label)
        self.button = QPushButton()
        self.button.setObjectName("toastAction")
        self.button.setCursor(Qt.PointingHandCursor)
        self.button.clicked.connect(self._run_action)
        layout.addWidget(self.button)
        close = QPushButton("✕")
        close.setObjectName("toastClose")
        close.setCursor(Qt.PointingHandCursor)
        close.setToolTip("Dismiss")
        close.clicked.connect(self.hide)
        layout.addWidget(close)

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide)
        self.hide()

    def show_message(self, text, action_text=None, action=None):
        self.label.setText(text)
        self._action = action
        self.button.setText(action_text or "")
        self.button.setVisible(bool(action_text and action))
        self.adjustSize()
        self.reposition()
        self.show()
        self.raise_()
        self.timer.start(SHOW_FOR_MS)

    def reposition(self):
        window = self.window_
        self.move((window.width() - self.width()) // 2, window.height() - self.height() - BOTTOM_GAP)

    def _run_action(self):
        action, self._action = self._action, None
        self.hide()
        if action is not None:
            action()
