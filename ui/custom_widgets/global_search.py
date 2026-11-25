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
# File: global_search.py
# Description: The search box in the banner and the results list under it.
#              Searches tasks, projects, notes, and mind maps as you type;
#              arrow keys and Enter (or a click) open a result.
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

from PyQt5.QtCore import QEvent, QPoint, Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import (QApplication, QFrame, QLabel, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout,
                             QWidget)

from resources.styles import AppColors
from utils.search import KIND_LABELS, search_everything

KIND_ICONS = {"task": "☑", "project": "📁", "note": "📝", "mindmap": "🧠"}
HEADER_ROLE = Qt.UserRole + 1
PANEL_WIDTH = 520
PANEL_MAX_HEIGHT = 460
TYPING_PAUSE_MS = 150


class SearchBox(QLineEdit):
    """The search field in the banner"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Search tasks, projects, notes, mind maps…   Ctrl+K")
        self.setClearButtonEnabled(True)
        self.setMinimumWidth(320)
        self.setMaximumWidth(460)
        self.setFixedHeight(36)
        self.setStyleSheet(f"""
            QLineEdit {{ background-color: rgba(255, 255, 255, 30); color: white;
                         border: 1px solid rgba(255, 255, 255, 60); border-radius: 18px;
                         padding: 0 14px; font-size: 13px; }}
            QLineEdit:focus {{ background-color: {AppColors.surface}; border-color: {AppColors.accent}; }}""")


class SearchResults(QFrame):
    """The list of results under the search box (a panel inside the window, so typing
    keeps going to the search box)"""

    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("searchResults")
        self.setStyleSheet(f"""
            QFrame#searchResults {{ background-color: {AppColors.surface}; border: 1px solid {AppColors.surface_hover_alt};
                                    border-radius: 10px; }}
            QListWidget {{ background: transparent; border: none; outline: none; }}
            QListWidget::item {{ border-radius: 6px; }}
            QListWidget::item:selected {{ background-color: rgba(52, 152, 219, 70); border-left: 3px solid {AppColors.accent}; }}
            QListWidget::item:hover:!selected {{ background-color: {AppColors.surface_raised}; }}
            QLabel {{ background: transparent; }}""")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        self.list = QListWidget()
        self.list.setFocusPolicy(Qt.NoFocus)  # typing stays in the search box
        self.list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        layout.addWidget(self.list)
        self.hide()

    def show_results(self, query, results):
        self.list.clear()
        if not results:
            item = QListWidgetItem(f"No matches for “{query}”")
            item.setFlags(Qt.NoItemFlags)
            item.setData(HEADER_ROLE, True)
            self.list.addItem(item)
        kind = None
        for result in results:
            if result.kind != kind:
                kind = result.kind
                header = QListWidgetItem(KIND_LABELS[kind].upper())
                header.setFlags(Qt.NoItemFlags)
                header.setData(HEADER_ROLE, True)
                font = header.font()
                font.setPixelSize(11)
                font.setBold(True)
                header.setFont(font)
                header.setForeground(Qt.gray)
                self.list.addItem(header)
            self._row(result)
        self._select(self._next_selectable(-1, 1))
        rows = sum(self.list.sizeHintForRow(i) + 2 for i in range(self.list.count()))
        self.setFixedHeight(min(PANEL_MAX_HEIGHT, rows + 16))

    def _row(self, result):
        item = QListWidgetItem()
        item.setData(Qt.UserRole, result)
        card = QWidget()
        card.setAttribute(Qt.WA_TransparentForMouseEvents)
        card.setStyleSheet("background: transparent;")  # let the row's hover and selection show
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(1)
        title = QLabel(f"{KIND_ICONS.get(result.kind, '')}  {result.title}")
        title.setStyleSheet(f"color: {AppColors.text_primary}; font-size: 13px; font-weight: bold;")
        detail = QLabel(result.detail)
        detail.setStyleSheet(f"color: {AppColors.text_muted}; font-size: 11px;")
        layout.addWidget(title)
        layout.addWidget(detail)
        card.setFixedWidth(PANEL_WIDTH - 40)
        for label in (title, detail):  # long text ends in … rather than widening the panel
            label.setText(label.fontMetrics().elidedText(label.text(), Qt.ElideRight, PANEL_WIDTH - 60))
        item.setSizeHint(card.sizeHint())
        self.list.addItem(item)
        self.list.setItemWidget(item, card)
        return item

    def _selectable(self, row):
        item = self.list.item(row)
        return item is not None and not item.data(HEADER_ROLE)

    def _next_selectable(self, row, step):
        row += step
        while 0 <= row < self.list.count():
            if self._selectable(row):
                return row
            row += step
        return None

    def _select(self, row):
        if row is not None:
            self.list.setCurrentRow(row)
            self.list.scrollToItem(self.list.item(row))

    def move_selection(self, step):
        row = self._next_selectable(self.list.currentRow(), step)
        self._select(row)

    def current_result(self):
        item = self.list.currentItem()
        return item.data(Qt.UserRole) if item is not None and not item.data(HEADER_ROLE) else None


class GlobalSearch(QWidget):
    """Search box plus results. Emits resultChosen(Result) when one is opened."""
    resultChosen = pyqtSignal(object)

    def __init__(self, window, logger, parent=None):
        super().__init__(parent)
        self.window_ = window
        self.logger = logger
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.box = SearchBox()
        layout.addWidget(self.box)
        self.results = SearchResults(window)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(TYPING_PAUSE_MS)
        self._timer.timeout.connect(self.run_search)
        self.box.textChanged.connect(lambda _: self._timer.start())
        self.box.installEventFilter(self)
        self.results.list.itemClicked.connect(self._clicked)
        QApplication.instance().focusChanged.connect(self._focus_changed)

    def focus(self):
        self.box.setFocus(Qt.ShortcutFocusReason)
        self.box.selectAll()
        if self.box.text().strip():
            self.run_search()

    def run_search(self):
        query = self.box.text().strip()
        if not query:
            self.results.hide()
            return
        self.results.show_results(query, search_everything(query, self.logger))
        self._place_results()
        self.results.show()
        self.results.raise_()

    def _place_results(self):
        bottom_right = self.box.mapTo(self.window_, QPoint(self.box.width(), self.box.height() + 6))
        width = min(PANEL_WIDTH, self.window_.width() - 20)
        self.results.setFixedWidth(width)
        self.results.move(max(10, bottom_right.x() - width), bottom_right.y())

    def open_current(self):
        result = self.results.current_result()
        if result is not None:
            self.results.hide()
            self.box.clearFocus()
            self.resultChosen.emit(result)

    def _clicked(self, item):
        if not item.data(HEADER_ROLE):
            self.results.list.setCurrentItem(item)
            self.open_current()

    def close_results(self):
        self.results.hide()

    def eventFilter(self, watched, event):
        if watched is self.box and event.type() == QEvent.KeyPress:
            key = event.key()
            if key in (Qt.Key_Down, Qt.Key_Up) and self.results.isVisible():
                self.results.move_selection(1 if key == Qt.Key_Down else -1)
                return True
            if key in (Qt.Key_Return, Qt.Key_Enter):
                if self._timer.isActive():  # Enter straight after typing: search first
                    self._timer.stop()
                    self.run_search()
                self.open_current()
                return True
            if key == Qt.Key_Escape:
                if self.results.isVisible():
                    self.results.hide()
                else:
                    self.box.clear()
                    self.box.clearFocus()
                return True
        return super().eventFilter(watched, event)

    def _focus_changed(self, old, new):
        # Clicking anywhere else closes the results
        if new is not self.box and self.results.isVisible() and not self.results.isAncestorOf(new or self):
            self.results.hide()
