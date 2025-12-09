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

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QFrame
)
from PyQt5.QtGui import QFont, QColor

from models.project import Project, ProjectStatus
from utils.projects_io import load_phases_from_json


class ProjectCard(QWidget):
    """
    Card widget for displaying project information
    Shows title, status, current phase, progress, and task counts
    """

    clicked = pyqtSignal(str)  # Emits project_id when clicked

    def __init__(self, project: Project, logger):
        super().__init__()
        self.project = project
        self.logger = logger
        self.setFixedSize(320, 220)
        self.setCursor(Qt.PointingHandCursor)

        self.initUI()

    def initUI(self):
        """Initialize the card UI"""
        # Main container with border
        self.setStyleSheet(f"""
            ProjectCard {{
                background-color: white;
                border: 2px solid {self.project.color};
                border-radius: 10px;
            }}
            ProjectCard:hover {{
                border: 3px solid {self.project.color};
                background-color: #f8f9fa;
            }}
        """)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Header row: Title and Status badge
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        # Title with folder icon
        title_label = QLabel(f"📁 {self.project.title}")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #2c3e50;
            }
        """)
        title_label.setWordWrap(True)
        title_label.setMaximumWidth(220)
        header_layout.addWidget(title_label, stretch=1)

        # Status badge
        status_badge = self.createStatusBadge()
        header_layout.addWidget(status_badge)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Priority indicator
        priority_label = QLabel(f"Priority: {self.project.priority.name}")
        priority_color = self.getPriorityColor()
        priority_label.setStyleSheet(f"""
            QLabel {{
                font-size: 11px;
                color: {priority_color};
                font-weight: bold;
            }}
        """)
        layout.addWidget(priority_label)

        # Current phase info
        phase_info = self.getPhaseInfo()
        phase_label = QLabel(phase_info)
        phase_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #7f8c8d;
            }
        """)
        layout.addWidget(phase_label)

        # Progress bar
        progress_bar = QProgressBar()
        progress_bar.setTextVisible(True)
        progress = int(self.project.get_progress_percentage())
        progress_bar.setValue(progress)
        progress_bar.setFormat(f"{progress}%")
        progress_bar.setFixedHeight(20)
        progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                text-align: center;
                font-size: 11px;
                font-weight: bold;
                background-color: #ecf0f1;
            }}
            QProgressBar::chunk {{
                background-color: {self.project.color};
                border-radius: 4px;
            }}
        """)
        layout.addWidget(progress_bar)

        # Task count
        total_tasks = self.project.get_total_tasks()
        completed_tasks = self.project.get_completed_tasks()
        task_label = QLabel(f"📋 {completed_tasks}/{total_tasks} tasks")
        task_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #34495e;
            }
        """)
        layout.addWidget(task_label)

        # Dates row
        dates_layout = QHBoxLayout()
        dates_layout.setSpacing(10)

        # Start date
        if self.project.start_date:
            start_label = QLabel(f"Started: {self.project.start_date.strftime('%m/%d/%Y')}")
            start_label.setStyleSheet("""
                QLabel {
                    font-size: 10px;
                    color: #95a5a6;
                }
            """)
            dates_layout.addWidget(start_label)

        # Due date
        if self.project.target_completion:
            due_label = QLabel(f"Due: {self.project.target_completion.strftime('%m/%d/%Y')}")
            due_label.setStyleSheet("""
                QLabel {
                    font-size: 10px;
                    color: #95a5a6;
                }
            """)
            dates_layout.addWidget(due_label)

        dates_layout.addStretch()
        layout.addLayout(dates_layout)

        # Indicators row (mindmap, scheduled)
        indicators_layout = QHBoxLayout()
        indicators_layout.setSpacing(5)

        # Mindmap indicator
        if self.project.mindmap_id:
            mindmap_label = QLabel("🧠 Mindmap")
            mindmap_label.setStyleSheet("""
                QLabel {
                    font-size: 10px;
                    color: #3498db;
                    background-color: #e8f4f8;
                    padding: 3px 6px;
                    border-radius: 3px;
                }
            """)
            indicators_layout.addWidget(mindmap_label)

        indicators_layout.addStretch()
        layout.addLayout(indicators_layout)

        # Add spacer at bottom
        layout.addStretch()

    def createStatusBadge(self):
        """Create a colored badge for the project status"""
        badge = QLabel(self.project.status.value)
        badge_color = self.getStatusColor()

        badge.setStyleSheet(f"""
            QLabel {{
                background-color: {badge_color};
                color: white;
                font-size: 10px;
                font-weight: bold;
                padding: 4px 8px;
                border-radius: 4px;
            }}
        """)
        badge.setAlignment(Qt.AlignCenter)
        return badge

    def getStatusColor(self):
        """Get color for status badge"""
        status_colors = {
            ProjectStatus.PLANNING: "#9b59b6",      # Purple
            ProjectStatus.ACTIVE: "#27ae60",        # Green
            ProjectStatus.ON_HOLD: "#f39c12",       # Orange
            ProjectStatus.COMPLETED: "#2ecc71",     # Light green
            ProjectStatus.CANCELLED: "#e74c3c"      # Red
        }
        return status_colors.get(self.project.status, "#95a5a6")

    def getPriorityColor(self):
        """Get color for priority text"""
        from models.task import TaskPriority

        priority_colors = {
            TaskPriority.CRITICAL: "#c0392b",   # Dark red
            TaskPriority.HIGH: "#e67e22",       # Orange
            TaskPriority.MEDIUM: "#f39c12",     # Yellow-orange
            TaskPriority.LOW: "#3498db",        # Blue
            TaskPriority.TRIVIAL: "#95a5a6"     # Gray
        }
        return priority_colors.get(self.project.priority, "#7f8c8d")

    def getPhaseInfo(self):
        """Get formatted phase information string"""
        if not self.project.phases:
            return "No phases yet"

        total_phases = len(self.project.phases)

        if self.project.current_phase_id:
            # Load phases to get current phase details
            phases = load_phases_from_json(self.logger)
            current_phase = phases.get(self.project.current_phase_id)

            if current_phase:
                # Find the order of current phase
                current_order = current_phase.order + 1  # +1 for human-readable numbering
                return f"📌 Phase {current_order} of {total_phases}: {current_phase.name}"

        return f"📌 {total_phases} phase{'s' if total_phases != 1 else ''}"

    def mousePressEvent(self, event):
        """Handle mouse click on card"""
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.project.id)
        super().mousePressEvent(event)
