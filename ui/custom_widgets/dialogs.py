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
# File: dialogs.py
# Description: The app's own dialogs (save changes?, confirm, name something),
#              styled to match the app instead of the plain Windows message box.
#              Call them through this module (dialogs.ask_to_save(...)) so tests
#              can answer them.
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

from PyQt5.QtCore import QPoint, Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (QDialog, QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QLineEdit,
                             QMessageBox, QPushButton, QVBoxLayout)

from resources.styles import AppColors

# Button looks
PRIMARY, SECONDARY, GHOST, DANGER = "primary", "secondary", "ghost", "danger"


def _button_style(kind):
    if kind == PRIMARY:
        return f"""
            QPushButton {{ background-color: {AppColors.accent}; color: white; border: none; border-radius: 6px;
                           padding: 8px 18px; font-size: 13px; font-weight: bold; }}
            QPushButton:hover {{ background-color: {AppColors.accent_dark}; }}"""
    if kind == DANGER:
        return f"""
            QPushButton {{ background-color: {AppColors.danger}; color: white; border: none; border-radius: 6px;
                           padding: 8px 18px; font-size: 13px; font-weight: bold; }}
            QPushButton:hover {{ background-color: {AppColors.danger_dark}; }}"""
    if kind == GHOST:
        return f"""
            QPushButton {{ background: transparent; color: {AppColors.text_secondary}; border: none;
                           padding: 8px 10px; font-size: 13px; }}
            QPushButton:hover {{ color: {AppColors.text_primary}; text-decoration: underline; }}"""
    return f"""
        QPushButton {{ background-color: {AppColors.surface_raised}; color: {AppColors.text_primary};
                       border: 1px solid {AppColors.surface_hover_alt}; border-radius: 6px;
                       padding: 8px 18px; font-size: 13px; }}
        QPushButton:hover {{ border-color: {AppColors.accent}; }}"""


class StyledDialog(QDialog):
    """A card-style dialog: an icon, a title, a message, optional extra content, and buttons.
    The value of the button pressed is in .value (Esc or closing gives cancel_value)."""

    def __init__(self, parent, title, message="", icon="?", icon_color=None, cancel_value=None):
        super().__init__(parent.window() if parent is not None else None)
        self.value = cancel_value
        self.cancel_value = cancel_value
        self._drag_offset = None
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)
        self.setWindowTitle(title)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)  # room for the shadow
        self.card = QFrame()
        self.card.setObjectName("dialogCard")
        self.card.setStyleSheet(f"""
            QFrame#dialogCard {{ background-color: {AppColors.surface}; border: 1px solid {AppColors.surface_hover_alt};
                                 border-radius: 12px; }}
            QLabel {{ background: transparent; border: none; }}
        """)
        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(32)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 140))
        self.card.setGraphicsEffect(shadow)
        outer.addWidget(self.card)

        layout = QVBoxLayout(self.card)
        layout.setContentsMargins(24, 22, 24, 18)
        layout.setSpacing(12)

        header = QHBoxLayout()
        header.setSpacing(14)
        badge = QLabel(icon)
        badge.setFixedSize(40, 40)
        badge.setAlignment(Qt.AlignCenter)
        color = QColor(icon_color or AppColors.accent)
        badge.setStyleSheet(f"background-color: rgba({color.red()}, {color.green()}, {color.blue()}, 45); "
                            f"color: {color.name()}; border-radius: 20px; font-size: 18px; font-weight: bold;")
        header.addWidget(badge, 0, Qt.AlignTop)

        text = QVBoxLayout()
        text.setSpacing(6)
        self.title_label = QLabel(title)
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet(f"color: {AppColors.text_primary}; font-size: 16px; font-weight: bold;")
        text.addWidget(self.title_label)
        self.message_label = QLabel(message)
        self.message_label.setWordWrap(True)
        self.message_label.setStyleSheet(f"color: {AppColors.text_secondary}; font-size: 13px;")
        self.message_label.setVisible(bool(message))
        text.addWidget(self.message_label)
        header.addLayout(text, 1)
        layout.addLayout(header)

        self.content = QVBoxLayout()  # optional extra widgets (e.g. a text field)
        layout.addLayout(self.content)

        self.buttons = QHBoxLayout()
        self.buttons.setSpacing(8)
        layout.addSpacing(6)
        layout.addLayout(self.buttons)

        self.setMinimumWidth(460)

    def addButton(self, label, value, kind=SECONDARY, default=False, left=False):
        button = QPushButton(label)
        button.setCursor(Qt.PointingHandCursor)
        button.setStyleSheet(_button_style(kind))
        button.setAutoDefault(default)
        button.setDefault(default)
        button.clicked.connect(lambda: self._finish(value))
        if left:
            self.buttons.insertWidget(0, button)
        else:
            if self.buttons.count() == 0 or not any(
                    self.buttons.itemAt(i).spacerItem() for i in range(self.buttons.count())):
                self.buttons.addStretch(1)
            self.buttons.addWidget(button)
        if default:
            button.setFocus()
        return button

    def addActionButton(self, label, handler, kind=PRIMARY, default=False):
        """A button that runs handler instead of closing (e.g. to check a form first, then call accept)"""
        button = QPushButton(label)
        button.setCursor(Qt.PointingHandCursor)
        button.setStyleSheet(_button_style(kind))
        button.setAutoDefault(default)
        button.setDefault(default)
        button.clicked.connect(handler)
        if self.buttons.count() == 0 or not any(
                self.buttons.itemAt(i).spacerItem() for i in range(self.buttons.count())):
            self.buttons.addStretch(1)
        self.buttons.addWidget(button)
        return button

    def _finish(self, value):
        self.value = value
        self.accept()

    def reject(self):
        self.value = self.cancel_value
        super().reject()

    def showEvent(self, event):
        super().showEvent(event)
        parent = self.parentWidget()
        if parent is not None:  # centre over the app window
            self.adjustSize()
            center = parent.mapToGlobal(parent.rect().center())
            self.move(center - QPoint(self.width() // 2, self.height() // 2))

    # Frameless: drag it by its body
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_offset = event.globalPos() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self._drag_offset)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_offset = None
        super().mouseReleaseEvent(event)

    def ask(self):
        self.exec_()
        return self.value


# ---------------------------------------------------------------- the dialogs

def ask_to_save(parent, kind, name=None):
    """Save changes before going on? Returns QMessageBox.Save, Discard, or Cancel."""
    title = f"Save changes to “{name}”?" if name else f"Save changes to this {kind}?"
    dialog = StyledDialog(parent, title, "If you don't save, your changes will be lost.",
                          icon="!", icon_color=AppColors.warning, cancel_value=QMessageBox.Cancel)
    dialog.addButton("Don't Save", QMessageBox.Discard, GHOST, left=True)
    dialog.addButton("Cancel", QMessageBox.Cancel)
    dialog.addButton("Save", QMessageBox.Save, PRIMARY, default=True)
    return dialog.ask()


def confirm(parent, title, message, confirm_label="Delete", danger=True):
    """Ask before doing something; returns True to go ahead"""
    dialog = StyledDialog(parent, title, message, icon="!" if danger else "?",
                          icon_color=AppColors.danger if danger else AppColors.accent, cancel_value=False)
    dialog.addButton("Cancel", False)
    dialog.addButton(confirm_label, True, DANGER if danger else PRIMARY, default=not danger)
    return dialog.ask()


def ask_text(parent, title, label, text="", ok_label="Save"):
    """Ask for a name or other short text; returns (text, ok)"""
    dialog = StyledDialog(parent, title, label, icon="✎", cancel_value=False)
    field = QLineEdit(text)
    field.setStyleSheet(f"""
        QLineEdit {{ background-color: {AppColors.surface_raised}; color: {AppColors.text_primary};
                     border: 1px solid {AppColors.surface_hover_alt}; border-radius: 6px; padding: 8px 10px;
                     font-size: 13px; }}
        QLineEdit:focus {{ border-color: {AppColors.accent}; }}""")
    field.selectAll()
    dialog.content.addWidget(field)
    dialog.addButton("Cancel", False)
    ok = dialog.addButton(ok_label, True, PRIMARY, default=True)
    ok.setEnabled(bool(text.strip()))
    field.textChanged.connect(lambda value: ok.setEnabled(bool(value.strip())))
    field.returnPressed.connect(lambda: ok.isEnabled() and ok.click())
    field.setFocus()
    accepted = dialog.ask()
    return field.text().strip(), bool(accepted)


# ---------------------------------------------------------------- drop-ins for the Qt boxes
# Same arguments and return values as QMessageBox.question/information/warning/critical
# and QInputDialog.getText/getMultiLineText/getInt, so calls can switch over unchanged.

_BUTTON_LABELS = [  # in the order they appear, left to right
    (QMessageBox.Discard, "Don't Save"), (QMessageBox.No, "No"), (QMessageBox.Cancel, "Cancel"),
    (QMessageBox.Ok, "OK"), (QMessageBox.Yes, "Yes"), (QMessageBox.Save, "Save"),
]
_DANGER_WORDS = ("delete", "remove", "clear", "reset", "discard")


def _is_danger(title):
    return any(word in (title or "").lower() for word in _DANGER_WORDS)


def question(parent, title, text, buttons=QMessageBox.Yes | QMessageBox.No, defaultButton=QMessageBox.NoButton):
    """QMessageBox.question in the app's style. Returns the QMessageBox button pressed."""
    danger = _is_danger(title)
    cancel = QMessageBox.Cancel if buttons & QMessageBox.Cancel else (
        QMessageBox.No if buttons & QMessageBox.No else QMessageBox.Ok)
    dialog = StyledDialog(parent, title, text, icon="!" if danger else "?",
                          icon_color=AppColors.danger if danger else AppColors.accent, cancel_value=cancel)
    first_word = (title or "").split(" ")[0]
    for button, label in _BUTTON_LABELS:
        if not buttons & button:
            continue
        if button == QMessageBox.Discard:
            dialog.addButton(label, button, GHOST, left=True)
        elif button in (QMessageBox.Yes, QMessageBox.Save, QMessageBox.Ok):
            if danger and button == QMessageBox.Yes and first_word.lower() in _DANGER_WORDS:
                label = first_word.title()  # "Delete" reads better than "Yes"
            dialog.addButton(label, button, DANGER if danger else PRIMARY,
                             default=defaultButton in (button, QMessageBox.NoButton) and not danger)
        else:
            dialog.addButton(label, button, SECONDARY, default=defaultButton == button)
    return dialog.ask()


def _notice(parent, title, text, icon, color):
    dialog = StyledDialog(parent, title, text, icon=icon, icon_color=color, cancel_value=QMessageBox.Ok)
    dialog.message_label.setTextInteractionFlags(Qt.TextSelectableByMouse)  # paths can be copied
    dialog.addButton("OK", QMessageBox.Ok, PRIMARY, default=True)
    return dialog.ask()


def information(parent, title, text, *args, **kwargs):
    return _notice(parent, title, text, "i", AppColors.accent)


def warning(parent, title, text, *args, **kwargs):
    return _notice(parent, title, text, "!", AppColors.warning)


def critical(parent, title, text, *args, **kwargs):
    return _notice(parent, title, text, "✕", AppColors.danger)


def getText(parent, title, label, echo=None, text="", *args, **kwargs):
    """QInputDialog.getText in the app's style: returns (text, ok)"""
    return ask_text(parent, title, label, text or "", ok_label="OK")


def getMultiLineText(parent, title, label, text="", *args, **kwargs):
    """QInputDialog.getMultiLineText in the app's style: returns (text, ok)"""
    from PyQt5.QtWidgets import QPlainTextEdit
    dialog = StyledDialog(parent, title, label, icon="✎", cancel_value=False)
    field = QPlainTextEdit(text)
    field.setMinimumHeight(140)
    field.setStyleSheet(f"""
        QPlainTextEdit {{ background-color: {AppColors.surface_raised}; color: {AppColors.text_primary};
                          border: 1px solid {AppColors.surface_hover_alt}; border-radius: 6px; padding: 6px;
                          font-size: 13px; }}
        QPlainTextEdit:focus {{ border-color: {AppColors.accent}; }}""")
    dialog.content.addWidget(field)
    dialog.addButton("Cancel", False)
    dialog.addButton("OK", True, PRIMARY)
    field.setFocus()
    accepted = dialog.ask()
    return field.toPlainText(), bool(accepted)


def getInt(parent, title, label, value=0, minValue=-2147483647, maxValue=2147483647, step=1, *args, **kwargs):
    """QInputDialog.getInt in the app's style: returns (number, ok)"""
    from PyQt5.QtWidgets import QSpinBox
    dialog = StyledDialog(parent, title, label, icon="#", cancel_value=False)
    field = QSpinBox()
    field.setRange(minValue, maxValue)
    field.setSingleStep(step)
    field.setValue(value)
    field.setStyleSheet(f"""
        QSpinBox {{ background-color: {AppColors.surface_raised}; color: {AppColors.text_primary};
                    border: 1px solid {AppColors.surface_hover_alt}; border-radius: 6px; padding: 6px 8px;
                    font-size: 13px; }}
        QSpinBox:focus {{ border-color: {AppColors.accent}; }}""")
    dialog.content.addWidget(field)
    dialog.addButton("Cancel", False)
    dialog.addButton("OK", True, PRIMARY, default=True)
    field.setFocus()
    field.selectAll()
    accepted = dialog.ask()
    return field.value(), bool(accepted)
