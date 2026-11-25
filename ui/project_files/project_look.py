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
# File: project_look.py
# Description: How projects are drawn everywhere: status colours, badges, dates,
#              the slim progress bar, and the colours a project can have.
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QProgressBar

from models.project import ProjectStatus
from models.task import TaskStatus
from resources.styles import AppColors

STATUS_COLORS = {
    ProjectStatus.PLANNING: "#9b59b6",
    ProjectStatus.ACTIVE: "#3498db",
    ProjectStatus.ON_HOLD: "#f39c12",
    ProjectStatus.COMPLETED: "#27ae60",
    ProjectStatus.CANCELLED: "#7f8c8d",
}

# The colours offered for a project (any other can still be picked with Custom…)
PROJECT_SWATCHES = ["#3498db", "#1abc9c", "#2ecc71", "#f1c40f", "#e67e22", "#e74c3c", "#9b59b6", "#95a5a6"]

TASK_STATUS_ICONS = {
    TaskStatus.NOT_STARTED: "○",
    TaskStatus.IN_PROGRESS: "◐",
    TaskStatus.IN_REVIEW: "◑",
    TaskStatus.COMPLETED: "●",
    TaskStatus.BLOCKED: "✖",
    TaskStatus.ON_HOLD: "⊝",
    TaskStatus.CANCELLED: "⊗",
}

# Cards and boxes: the same dark surface as the Dashboard's task cards
CARD_BACKGROUND = AppColors.accent_background_color
CARD_BORDER = "#262b35"
ROW_BACKGROUND = AppColors.accent_background_color_dark


def status_color(status):
    return STATUS_COLORS.get(status, AppColors.text_muted)


def badge(text, color):
    """A small coloured label, the same as on the Dashboard's task cards"""
    from ui.task_files.task_card_lite import badge as task_badge
    return task_badge(text, color)


def status_badge(status):
    return badge(status.value, status_color(status))


def priority_badge(priority):
    return badge(priority.name.title(), AppColors.get_priority_color(priority))


def short_date(when, with_year=False):
    if when is None:
        return ""
    text = when.strftime("%b %d").replace(" 0", " ")
    return f"{text}, {when.year}" if with_year else text


def due_text(project):
    """("Due Dec 15", colour) for a project still under way; ("", None) otherwise"""
    if project.target_completion is None:
        return "", None
    if project.status in (ProjectStatus.COMPLETED, ProjectStatus.CANCELLED):
        return f"Due {short_date(project.target_completion)}", AppColors.text_muted
    return f"Due {short_date(project.target_completion)}", AppColors.get_due_date_color(project.target_completion)


def progress_bar(color, percent, height=6):
    """A thin bar with no text; say the number next to it"""
    bar = QProgressBar()
    bar.setTextVisible(False)
    bar.setRange(0, 100)
    bar.setValue(int(round(percent)))
    bar.setFixedHeight(height)
    radius = height // 2
    bar.setStyleSheet(f"""
        QProgressBar {{ background-color: {AppColors.surface_raised}; border: none; border-radius: {radius}px; }}
        QProgressBar::chunk {{ background-color: {color}; border-radius: {radius}px; }}""")
    bar.setAttribute(Qt.WA_TransparentForMouseEvents)
    return bar
