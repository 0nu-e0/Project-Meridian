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
# File: form_dialog.py
# Description: A dialog with a few fields (a project's, a phase's, a task's), in
#              the same card style as the app's other dialogs. Problems are shown
#              inside it, next to the field, rather than in another pop-up.
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

from PyQt5.QtCore import QDate, Qt, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (QButtonGroup, QCheckBox, QColorDialog, QComboBox, QDateEdit, QFormLayout, QHBoxLayout,
                             QLabel, QPushButton, QTextEdit, QWidget)

from resources.styles import AppColors
from ui.custom_widgets.dialogs import PRIMARY, StyledDialog
from ui.custom_widgets.panel_styles import FORM_INPUT_STYLE, LINK_BUTTON_STYLE


class FormDialog(StyledDialog):
    """Fields in a form, Cancel, and a save button that checks the form (see validate) first"""

    def __init__(self, parent, title, message="", icon="✎", save_label="Save"):
        super().__init__(parent, title, message, icon=icon, cancel_value=False)
        self.formWidget = QWidget()
        self.formWidget.setObjectName("formWidget")
        self.formWidget.setStyleSheet(FORM_INPUT_STYLE)
        self.form = QFormLayout(self.formWidget)
        self.form.setContentsMargins(0, 4, 0, 0)
        self.form.setHorizontalSpacing(14)
        self.form.setVerticalSpacing(10)
        self.form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.content.addWidget(self.formWidget)

        self.errorLabel = QLabel()
        self.errorLabel.setWordWrap(True)
        self.errorLabel.setStyleSheet(f"color: {AppColors.danger}; font-size: 12px; background: transparent;")
        self.errorLabel.hide()
        self.content.addWidget(self.errorLabel)

        self.addButton("Cancel", False)
        self.saveButton = self.addActionButton(save_label, self._save, PRIMARY, default=True)
        self.setMinimumWidth(520)

    def addRow(self, label, field):
        self.form.addRow(label, field)
        return field

    def textArea(self, placeholder, height=80):
        area = QTextEdit()
        area.setAcceptRichText(False)
        area.setTabChangesFocus(True)
        area.setPlaceholderText(placeholder)
        area.setFixedHeight(height)
        return area

    @staticmethod
    def combo(items, current=None):
        """items: (text, value) pairs"""
        box = QComboBox()
        for text, value in items:
            box.addItem(text, value)
        if current is not None:
            index = box.findData(current)
            if index >= 0:
                box.setCurrentIndex(index)
        return box

    def showError(self, text, field=None):
        self.errorLabel.setText(text)
        self.errorLabel.show()
        if field is not None:
            field.setProperty("invalid", True)
            field.style().unpolish(field)
            field.style().polish(field)
            field.setFocus()
            # Typing again clears the warning
            if hasattr(field, "textChanged") and not field.property("watched"):
                field.setProperty("watched", True)
                field.textChanged.connect(lambda *_: self._clearError(field))

    def _clearError(self, field):
        self.errorLabel.hide()
        field.setProperty("invalid", False)
        field.style().unpolish(field)
        field.style().polish(field)

    def validate(self):
        """Override: check the fields, call showError and return False to keep the dialog open"""
        return True

    def _save(self):
        if self.validate():
            self.value = True
            self.accept()


class OptionalDate(QWidget):
    """A date that can be left unset: a tick box, then the date"""

    def __init__(self, label, date=None, default=None, parent=None):
        super().__init__(parent)
        self.setObjectName("optionalDate")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.check = QCheckBox(label)
        self.edit = QDateEdit()
        self.edit.setCalendarPopup(True)
        self.edit.setDisplayFormat("MMM d, yyyy")
        self.edit.setDate(QDate(date.year, date.month, date.day) if date else (default or QDate.currentDate()))
        self.check.setChecked(date is not None)
        self.edit.setEnabled(date is not None)
        self.check.toggled.connect(self.edit.setEnabled)
        layout.addWidget(self.check)
        layout.addWidget(self.edit, 1)

    def value(self):
        """The date as a datetime, or None when unticked"""
        if not self.check.isChecked():
            return None
        from datetime import datetime
        date = self.edit.date()
        return datetime(date.year(), date.month(), date.day())

    def setValue(self, date):
        self.check.setChecked(date is not None)
        if date is not None:
            self.edit.setDate(QDate(date.year, date.month, date.day))


class ColorChoice(QWidget):
    """A row of colour dots to pick from, and Custom… for any other colour"""
    colorChanged = pyqtSignal(str)

    def __init__(self, swatches, color, parent=None):
        super().__init__(parent)
        self.setObjectName("colorChoice")
        self.swatches = list(swatches)
        self._color = color
        self.layout_ = QHBoxLayout(self)
        self.layout_.setContentsMargins(0, 0, 0, 0)
        self.layout_.setSpacing(6)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.custom = QPushButton("Custom…")
        self.custom.setCursor(Qt.PointingHandCursor)
        self.custom.setStyleSheet(LINK_BUTTON_STYLE)
        self.custom.clicked.connect(self._pickCustom)
        self._build()

    def _build(self):
        for button in self.group.buttons():
            self.group.removeButton(button)
            button.deleteLater()
        while self.layout_.count():
            self.layout_.takeAt(0)
        colors = self.swatches + ([self._color] if self._color.lower() not in
                                   [c.lower() for c in self.swatches] else [])
        for color in colors:
            dot = QPushButton()
            dot.setCheckable(True)
            dot.setFixedSize(24, 24)
            dot.setCursor(Qt.PointingHandCursor)
            dot.setToolTip(color)
            dot.setProperty("color", color)
            dot.setStyleSheet(f"""
                QPushButton {{ background-color: {color}; border: 2px solid transparent; border-radius: 12px; }}
                QPushButton:hover {{ border-color: {AppColors.text_muted}; }}
                QPushButton:checked {{ border: 2px solid white; }}""")
            dot.setChecked(color.lower() == self._color.lower())
            dot.clicked.connect(lambda _=False, c=color: self.setColor(c))
            self.group.addButton(dot)
            self.layout_.addWidget(dot)
        self.layout_.addWidget(self.custom)
        self.layout_.addStretch(1)

    def color(self):
        return self._color

    def setColor(self, color):
        changed = color.lower() != self._color.lower()
        self._color = color
        if color.lower() not in [b.property("color").lower() for b in self.group.buttons()]:
            self._build()
        for button in self.group.buttons():
            button.setChecked(button.property("color").lower() == color.lower())
        if changed:
            self.colorChanged.emit(color)

    def _pickCustom(self):
        color = QColorDialog.getColor(QColor(self._color), self, "Pick a colour")
        if color.isValid():
            self.setColor(color.name())
