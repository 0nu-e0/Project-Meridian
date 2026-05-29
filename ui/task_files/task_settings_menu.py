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
# File: task_settings_menu.py
# Description: Settings view for toggling visible sections on the task card.
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QCheckBox, QScrollArea, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QGuiApplication


class TaskSettingsMenu(QWidget):
    """Settings panel that lives as a page inside the task card's QStackedWidget.

    Signals:
        back_requested  -- user clicked the Back button; caller switches to page 0.
        settings_changed(dict) -- emitted immediately on every checkbox toggle;
                                   dict maps section keys → bool (visible).
    """

    back_requested = pyqtSignal()
    settings_changed = pyqtSignal(dict)

    # (key, display_name, group_header)
    SECTIONS = [
        ('description',            'Description',                    'Left Panel'),
        ('activity',               'Activity  (Comments & Work Logs)', 'Left Panel'),
        ('status_priority',        'Status & Priority',              'Right Panel'),
        ('details',                'Details  (Dates & Team)',        'Right Panel'),
        ('dependencies',           'Dependencies',                   'Right Panel'),
        ('attachments',            'Attachments',                    'Right Panel'),
        ('checklist',              'Checklist',                      'Right Panel'),
        ('category',               'Category',                       'Right Panel'),
        ('project_phase_selection','Project & Phase Assignment',     'Right Panel'),
    ]

    def __init__(self, task, parent=None):
        super().__init__(parent)
        self.task = task
        self._checkboxes: dict = {}
        self._init_ui()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def refresh(self):
        """Sync checkbox states from the task's current visible_sections dict.
        Call this every time the settings page is shown so the UI is up-to-date.
        """
        vs = getattr(self.task, 'visible_sections', {})
        for key, cb in self._checkboxes.items():
            cb.blockSignals(True)
            cb.setChecked(vs.get(key, True))
            cb.blockSignals(False)

    # ------------------------------------------------------------------
    # Build UI
    # ------------------------------------------------------------------

    def _init_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)
        outer.setSpacing(0)

        # ── Header ───────────────────────────────────────────────────
        header_widget = QWidget()
        header_widget.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border-bottom: 1px solid #34495e;
            }
        """)
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 14)
        header_layout.setSpacing(12)

        back_btn = QPushButton("← Back")
        back_btn.setFixedWidth(90)
        back_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 2px solid #34495e;
                border-radius: 6px;
                padding: 8px 16px;
                color: #ecf0f1;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #34495e;
                border-color: #3498db;
            }
            QPushButton:pressed {
                background-color: #2c3e50;
            }
        """)
        back_btn.clicked.connect(self.back_requested.emit)

        title_label = QLabel("⚙  Card Settings")
        title_label.setStyleSheet("""
            QLabel {
                color: #ecf0f1;
                font-size: 16px;
                font-weight: bold;
                background-color: transparent;
                border: none;
            }
        """)

        header_layout.addWidget(back_btn)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        outer.addWidget(header_widget)

        # ── Subtitle ─────────────────────────────────────────────────
        subtitle = QLabel("Choose which sections are visible on this task card. "
                          "Changes are applied immediately and saved when you save the task.")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("""
            QLabel {
                color: #7f8c8d;
                font-size: 11px;
                padding: 12px 0px 12px 0px;
                background-color: transparent;
                border: none;
            }
        """)
        outer.addWidget(subtitle)

        # ── Scrollable toggle list ────────────────────────────────────
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #1a252f;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #34495e;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #3498db;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: transparent;")
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setContentsMargins(0, 0, 10, 0)
        content_layout.setSpacing(4)

        vs = getattr(self.task, 'visible_sections', {})
        current_group = None

        for key, label_text, group in self.SECTIONS:
            if group != current_group:
                current_group = group
                grp_label = QLabel(group.upper())
                grp_label.setStyleSheet("""
                    QLabel {
                        color: #7f8c8d;
                        font-size: 10px;
                        font-weight: bold;
                        letter-spacing: 1px;
                        padding: 12px 0px 4px 4px;
                        background-color: transparent;
                        border: none;
                    }
                """)
                content_layout.addWidget(grp_label)

            row = self._create_row(key, label_text, vs.get(key, True))
            content_layout.addWidget(row)

        content_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        outer.addWidget(scroll_area, 1)

    def _create_row(self, key: str, label_text: str, is_checked: bool) -> QFrame:
        row = QFrame()
        row.setStyleSheet("""
            QFrame {
                background-color: #2c3e50;
                border: 1px solid #34495e;
                border-radius: 6px;
            }
            QFrame:hover {
                border-color: #3498db;
                background-color: #2e4057;
            }
        """)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(14, 10, 14, 10)
        row_layout.setSpacing(12)

        label = QLabel(label_text)
        label.setStyleSheet("""
            QLabel {
                color: #ecf0f1;
                font-size: 12px;
                background-color: transparent;
                border: none;
            }
        """)

        checkbox = QCheckBox()
        checkbox.setChecked(is_checked)
        checkbox.setStyleSheet("""
            QCheckBox {
                background-color: transparent;
            }
            QCheckBox::indicator {
                width: 22px;
                height: 22px;
                border-radius: 5px;
                border: 2px solid #34495e;
                background-color: #1a252f;
            }
            QCheckBox::indicator:checked {
                background-color: #27ae60;
                border-color: #27ae60;
            }
            QCheckBox::indicator:checked:hover {
                background-color: #2ecc71;
                border-color: #2ecc71;
            }
            QCheckBox::indicator:unchecked:hover {
                border-color: #3498db;
            }
        """)
        checkbox.stateChanged.connect(lambda *_args, k=key: self._on_toggle(k))

        row_layout.addWidget(label, 1)
        row_layout.addWidget(checkbox)

        self._checkboxes[key] = checkbox
        return row

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_toggle(self, _key: str):
        new_visible = {k: cb.isChecked() for k, cb in self._checkboxes.items()}
        self.task.visible_sections = new_visible
        self.settings_changed.emit(new_visible)

    # ------------------------------------------------------------------
    # Legacy compatibility (was used by old settingsMenu() caller)
    # ------------------------------------------------------------------

    @classmethod
    def calculate_optimal_card_size(cls, parent_window=None):
        if parent_window:
            w, h = parent_window.width(), parent_window.height()
        else:
            screen = QGuiApplication.primaryScreen().availableGeometry()
            w, h = screen.width(), screen.height()
        return max(600, int(w * 0.75)), max(400, int(h * 0.85))
