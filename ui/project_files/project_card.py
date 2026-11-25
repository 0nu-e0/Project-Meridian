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
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# -----------------------------------------------------------------------------
# File: project_card.py
# Description: Widget for displaying project information in a card format
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

from PyQt5.QtCore import QPoint, Qt, pyqtSignal
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout

from models.project import Project
from resources.styles import AppColors
from ui.project_files.project_look import (CARD_BACKGROUND, CARD_BORDER, badge, due_text, priority_badge,
                                           progress_bar, status_badge)
from utils.projects_io import load_phases_from_json

MIN_CARD_WIDTH = 290


class ProjectCard(QFrame):
    """A project on the Projects screen: name, status, priority, phase, progress, and due date.
    Click to open it; right-click for more."""

    clicked = pyqtSignal(str)  # project id
    menuRequested = pyqtSignal(str, QPoint)  # project id, global position

    def __init__(self, project: Project, logger, phases=None):
        super().__init__()
        self.project = project
        self.logger = logger
        self._phases = phases  # all phases, if the caller has them already
        self.setObjectName("projectCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumWidth(MIN_CARD_WIDTH)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setToolTip(project.title)
        self.initUI()

    def initUI(self):
        project = self.project
        self.setStyleSheet(f"""
            QFrame#projectCard {{ background-color: {CARD_BACKGROUND}; border: 1px solid {CARD_BORDER};
                                  border-left: 4px solid {project.color}; border-radius: 8px; }}
            QFrame#projectCard:hover {{ border-color: {AppColors.accent}; border-left: 4px solid {project.color}; }}
            QLabel {{ background: transparent; border: none; }}""")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        self.title_label = QLabel(project.title)
        self.title_label.setStyleSheet(f"color: {AppColors.text_primary if not project.archived else AppColors.text_muted}; "
                                       f"font-size: 15px; font-weight: bold;")
        self.title_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        layout.addWidget(self.title_label)

        badges = QHBoxLayout()
        badges.setSpacing(6)
        badges.addWidget(status_badge(project.status))
        badges.addWidget(priority_badge(project.priority))
        if project.archived:
            badges.addWidget(badge("Archived", AppColors.text_faint))
        badges.addStretch(1)
        layout.addLayout(badges)

        self.description_label = QLabel(project.description.splitlines()[0] if project.description else "No description")
        self.description_label.setStyleSheet(f"color: {AppColors.text_muted if project.description else AppColors.text_faint}; "
                                             f"font-size: 12px;")
        self.description_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        layout.addWidget(self.description_label)
        self._fullTexts = {self.title_label: project.title, self.description_label: self.description_label.text()}

        phase_label = QLabel(self.getPhaseInfo())
        phase_label.setStyleSheet(f"color: {AppColors.text_secondary}; font-size: 12px;")
        layout.addWidget(phase_label)

        progress = project.get_progress_percentage()
        progress_row = QHBoxLayout()
        progress_row.setSpacing(8)
        progress_row.addWidget(progress_bar(project.color, progress), 1)
        percent = QLabel(f"{progress:.0f}%")
        percent.setStyleSheet(f"color: {AppColors.text_secondary}; font-size: 11px; font-weight: bold;")
        progress_row.addWidget(percent)
        layout.addLayout(progress_row)

        footer = QHBoxLayout()
        footer.setSpacing(8)
        total, done = project.get_total_tasks(), project.get_completed_tasks()
        counts = f"{done} of {total} task{'s' if total != 1 else ''} done" if total else "No tasks yet"
        if project.mindmap_id:
            counts += "  ·  Mind map"
        tasks_label = QLabel(counts)
        tasks_label.setStyleSheet(f"color: {AppColors.text_muted}; font-size: 11px;")
        footer.addWidget(tasks_label)
        footer.addStretch(1)
        text, color = due_text(project)
        if text:
            due = QLabel(text)
            due.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: bold;")
            footer.addWidget(due)
        layout.addLayout(footer)

    def getPhaseInfo(self):
        """e.g. "Phase 2 of 4 · Build", or how many phases there are"""
        count = len(self.project.phases)
        if not count:
            return "No phases yet"
        if self.project.current_phase_id:
            phases = self._phases if self._phases is not None else load_phases_from_json(self.logger)
            current = phases.get(self.project.current_phase_id)
            if current:
                return f"Phase {current.order + 1} of {count}  ·  {current.name}"
        return f"{count} phase{'s' if count != 1 else ''}"

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Long names and descriptions end in "…" rather than widening the card
        width = max(self.width() - 40, 40)
        for label, text in self._fullTexts.items():
            label.setText(label.fontMetrics().elidedText(text, Qt.ElideRight, width))

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.rect().contains(event.pos()):
            self.clicked.emit(self.project.id)
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event):
        self.menuRequested.emit(self.project.id, event.globalPos())
