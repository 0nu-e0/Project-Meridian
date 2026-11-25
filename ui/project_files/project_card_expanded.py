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
# File: project_card_expanded.py
# Description: Expanded view card for displaying project details in planning screen
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

from PyQt5.QtCore import Qt, pyqtSignal, QDate
from PyQt5.QtGui import QGuiApplication
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QProgressBar, QCheckBox
)

from models.task import TaskStatus
from utils.projects_io import load_projects_from_json, load_phases_from_json
from utils.tasks_io import load_tasks_from_json
from resources.styles import AppStyles
from resources.styles import AppColors


class ProjectCardExpanded(QWidget):
    """Expanded card view for project details in planning screen"""

    closeRequested = pyqtSignal()
    taskClicked = pyqtSignal(object)  # Emits task object when clicked

    @classmethod
    def calculate_optimal_card_size(cls, parent_window=None):
        """Calculate optimal card size based on parent window"""
        if parent_window:
            window_width = parent_window.width()
            window_height = parent_window.height()
        else:
            screen = QGuiApplication.primaryScreen().availableGeometry()
            window_width, window_height = screen.width(), screen.height()

        min_width = 700
        min_height = 500

        # Use 70% of window width and 80% of window height
        card_width = int(max(min_width, window_width * 0.70))
        card_height = int(max(min_height, window_height * 0.80))

        # Ensure card doesn't exceed window dimensions
        card_width = min(card_width, window_width - 40)
        card_height = min(card_height, window_height - 40)

        return card_width, card_height

    def __init__(self, project_id: str, scheduled_date: QDate, logger, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.scheduled_date = scheduled_date
        self.logger = logger
        self.project = None
        self.phases = []
        self.current_phase = None

        self.loadProjectData()
        self.initUI()

    def loadProjectData(self):
        """Load project, phases, and tasks data"""
        # Load project
        projects = load_projects_from_json(self.logger)
        if self.project_id not in projects:
            self.logger.error(f"Project {self.project_id} not found")
            return

        self.project = projects[self.project_id]

        # Load phases for this project
        all_phases = load_phases_from_json(self.logger)
        self.phases = [p for p in all_phases.values() if p.project_id == self.project_id]
        self.phases.sort(key=lambda p: p.order)

        # Find current phase
        self.current_phase = None  # Reset to ensure fresh lookup
        for phase in self.phases:
            if phase.is_current:
                self.current_phase = phase
                self.logger.info(f"Found current phase: {phase.name} (order {phase.order})")
                break

        # If no current phase, use first phase
        if not self.current_phase and self.phases:
            self.current_phase = self.phases[0]
            self.logger.info(f"No current phase marked, using first phase: {self.current_phase.name}")

    def refresh(self):
        """Refresh the project card by reloading data and rebuilding UI"""
        # Reload all data
        self.loadProjectData()

        # Get the current layout
        old_layout = self.layout()

        # Clear all widgets from the layout
        if old_layout:
            while old_layout.count():
                child = old_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

            # Delete the old layout
            from PyQt5.QtWidgets import QWidget
            QWidget().setLayout(old_layout)  # Transfer ownership to temp widget

        # Rebuild UI
        self.initUI()

    def initUI(self):
        """Initialize the expanded card UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header
        header = self.createHeader()
        main_layout.addWidget(header)

        # Scroll area for content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: {AppColors.surface};
                border: none;
            }}
            QScrollBar:vertical {{
                background-color: {AppColors.surface_raised};
                width: 12px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {AppColors.text_faint};
                border-radius: 6px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {AppColors.text_muted};
            }}
        """)

        # Content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(20)

        # Project info section
        if self.project:
            content_layout.addWidget(self.createProjectInfoSection())

            # Current phase tasks section (only show current phase)
            if self.current_phase:
                content_layout.addWidget(self.createCurrentPhaseTasksSection())

        content_layout.addStretch()
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)

        # Footer with close button
        footer = self.createFooter()
        main_layout.addWidget(footer)

    def createHeader(self):
        """Create the header section"""
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {AppColors.surface_raised};
                border-bottom: 2px solid {AppColors.accent};
            }}
        """)

        layout = QVBoxLayout(header)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(8)

        # Title
        title_label = QLabel(f"📁 {self.project.title if self.project else 'Project'}")
        title_label.setStyleSheet(f"""
            QLabel {{
                font-size: 24px;
                font-weight: bold;
                color: {AppColors.text_primary};
            }}
        """)
        layout.addWidget(title_label)

        # Scheduled date
        date_label = QLabel(f"Scheduled for: {self.scheduled_date.toString('dddd, MMMM d, yyyy')}")
        date_label.setStyleSheet(f"""
            QLabel {{
                font-size: 13px;
                color: {AppColors.text_secondary};
            }}
        """)
        layout.addWidget(date_label)

        return header

    def createProjectInfoSection(self):
        """Create project information section"""
        section = QFrame()
        section.setStyleSheet(f"""
            QFrame {{
                background-color: {AppColors.surface_raised};
                border-radius: 8px;
                padding: 15px;
            }}
        """)

        layout = QVBoxLayout(section)
        layout.setSpacing(10)

        # Section title
        section_title = QLabel("Project Information")
        section_title.setStyleSheet(f"""
            QLabel {{
                font-size: 16px;
                font-weight: bold;
                color: {AppColors.accent};
            }}
        """)
        layout.addWidget(section_title)

        # Description
        if self.project.description:
            desc_label = QLabel(self.project.description)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet(f"""
                QLabel {{
                    font-size: 13px;
                    color: {AppColors.text_primary};
                    padding: 5px;
                }}
            """)
            layout.addWidget(desc_label)

        # Status and dates in a grid
        info_layout = QHBoxLayout()

        # Status
        status_label = QLabel(f"Status: {self.project.status.value}")
        status_label.setStyleSheet(f"""
            QLabel {{
                font-size: 12px;
                color: {AppColors.text_secondary};
            }}
        """)
        info_layout.addWidget(status_label)

        # Created date
        if self.project.creation_date:
            created_label = QLabel(f"Created: {self.project.creation_date.strftime('%Y-%m-%d')}")
            created_label.setStyleSheet(f"""
                QLabel {{
                    font-size: 12px;
                    color: {AppColors.text_secondary};
                }}
            """)
            info_layout.addWidget(created_label)

        info_layout.addStretch()
        layout.addLayout(info_layout)

        return section

    def createPhaseProgressSection(self):
        """Create phase progress section"""
        section = QFrame()
        section.setStyleSheet(f"""
            QFrame {{
                background-color: {AppColors.surface_raised};
                border-radius: 8px;
                padding: 15px;
            }}
        """)

        layout = QVBoxLayout(section)
        layout.setSpacing(12)

        # Section title
        section_title = QLabel("Phase Progress")
        section_title.setStyleSheet(f"""
            QLabel {{
                font-size: 16px;
                font-weight: bold;
                color: {AppColors.accent};
            }}
        """)
        layout.addWidget(section_title)

        # Show each phase
        for i, phase in enumerate(self.phases):
            phase_widget = self.createPhaseItem(phase, i)
            layout.addWidget(phase_widget)

        return section

    def createPhaseItem(self, phase, index):
        """Create a widget for a single phase"""
        phase_frame = QFrame()
        is_current = phase.id == self.current_phase.id if self.current_phase else False

        border_color = AppColors.success if is_current else AppColors.text_faint
        phase_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {AppColors.surface};
                border-left: 4px solid {border_color};
                border-radius: 4px;
                padding: 10px;
            }}
        """)

        layout = QVBoxLayout(phase_frame)
        layout.setSpacing(8)

        # Phase name and status
        header_layout = QHBoxLayout()

        phase_name = QLabel(f"Phase {index + 1}: {phase.name}")
        phase_name.setStyleSheet(f"""
            QLabel {{
                font-size: 14px;
                font-weight: bold;
                color: {AppColors.text_primary};
            }}
        """)
        header_layout.addWidget(phase_name)

        if is_current:
            current_badge = QLabel("CURRENT")
            current_badge.setStyleSheet(f"""
                QLabel {{
                    background-color: {AppColors.success};
                    color: white;
                    padding: 2px 8px;
                    border-radius: 3px;
                    font-size: 10px;
                    font-weight: bold;
                }}
            """)
            header_layout.addWidget(current_badge)

        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Progress bar
        progress = phase.get_progress_percentage()
        progress_bar = QProgressBar()
        progress_bar.setValue(int(progress))
        progress_bar.setTextVisible(True)
        progress_bar.setFormat(f"{int(progress)}%")
        progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {AppColors.text_faint};
                border-radius: 4px;
                text-align: center;
                background-color: {AppColors.surface_raised};
                color: white;
                height: 20px;
            }}
            QProgressBar::chunk {{
                background-color: {AppColors.accent};
                border-radius: 3px;
            }}
        """)
        layout.addWidget(progress_bar)

        # Task count
        task_count = phase.get_task_count()
        completed_count = phase.get_completed_task_count()
        task_count_label = QLabel(f"{completed_count}/{task_count} tasks completed")
        task_count_label.setStyleSheet(f"""
            QLabel {{
                font-size: 11px;
                color: {AppColors.text_muted};
            }}
        """)
        layout.addWidget(task_count_label)

        return phase_frame

    def createCurrentPhaseTasksSection(self):
        """Create section showing tasks in current phase"""
        section = QFrame()
        section.setStyleSheet(f"""
            QFrame {{
                background-color: {AppColors.surface_raised};
                border-radius: 8px;
                padding: 15px;
            }}
        """)

        layout = QVBoxLayout(section)
        layout.setSpacing(12)

        # Section title
        section_title = QLabel(f"Current Phase Tasks: {self.current_phase.name}")
        section_title.setStyleSheet(f"""
            QLabel {{
                font-size: 16px;
                font-weight: bold;
                color: {AppColors.accent};
            }}
        """)
        layout.addWidget(section_title)

        # Load tasks for current phase - use phase_id from tasks instead of phase.task_ids
        all_tasks = load_tasks_from_json(self.logger)
        # Filter tasks by phase_id (more reliable than phase.task_ids)
        phase_tasks = [task for task in all_tasks.values() if task.phase_id == self.current_phase.id]
        self.logger.info(f"Current phase '{self.current_phase.name}' has {len(phase_tasks)} tasks (filtered by phase_id)")

        if not phase_tasks:
            no_tasks_label = QLabel("No tasks in this phase")
            no_tasks_label.setStyleSheet(f"""
                QLabel {{
                    font-size: 12px;
                    color: {AppColors.text_faint};
                    font-style: italic;
                    padding: 10px;
                }}
            """)
            layout.addWidget(no_tasks_label)
        else:
            # Add each task
            for task in phase_tasks:
                task_widget = self.createTaskItem(task)
                layout.addWidget(task_widget)

        return section

    def createTaskItem(self, task):
        """Create a widget for a single task with checklist and comments"""
        task_frame = QFrame()
        task_frame.setCursor(Qt.PointingHandCursor)
        task_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {AppColors.surface};
                border-radius: 5px;
                padding: 12px;
                border-left: 4px solid {AppColors.accent};
                border-top: 1px solid {AppColors.surface_raised};
                border-right: 1px solid {AppColors.surface_raised};
                border-bottom: 1px solid {AppColors.surface_raised};
            }}
            QFrame:hover {{
                background-color: {AppColors.surface_raised};
                border-left: 4px solid {AppColors.accent_light};
            }}
        """)

        # Store task reference for click handling
        task_frame.task = task
        # Store checkbox reference to check for clicks on it
        task_frame.task_checkbox = None

        def handle_frame_click(event):
            # Don't open task detail if clicking on a checkbox
            widget = task_frame.childAt(event.pos())
            if widget and isinstance(widget, QCheckBox):
                return
            # Also check parent widget (for indicator clicks)
            if widget and widget.parent() and isinstance(widget.parent(), QCheckBox):
                return
            self.onTaskFrameClicked(task)

        task_frame.mousePressEvent = handle_frame_click

        main_layout = QVBoxLayout(task_frame)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Top row: checkbox, title, priority
        top_layout = QHBoxLayout()
        top_layout.setSpacing(10)

        # Checkbox (interactive, toggles task completion status)
        checkbox = QCheckBox()
        checkbox.setChecked(task.status == TaskStatus.COMPLETED)
        checkbox.setEnabled(True)  # Make it interactive
        checkbox.setStyleSheet(f"""
            QCheckBox {{
                spacing: 5px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid {AppColors.text_faint};
                border-radius: 3px;
                background-color: {AppColors.surface_raised};
            }}
            QCheckBox::indicator:hover {{
                border-color: {AppColors.accent};
            }}
            QCheckBox::indicator:checked {{
                background-color: {AppColors.success};
                border-color: {AppColors.success};
            }}
        """)
        # Connect checkbox to task completion handler
        checkbox.stateChanged.connect(
            lambda state, t=task: self.onTaskCheckboxToggled(t, state)
        )
        top_layout.addWidget(checkbox)

        # Task title
        task_title = QLabel(task.title)
        task_title.setStyleSheet(f"""
            QLabel {{
                font-size: 14px;
                color: {AppColors.text_primary};
                font-weight: bold;
            }}
        """)
        top_layout.addWidget(task_title, 1)

        # Priority badge
        priority_badge = QLabel(task.priority.name)
        priority_colors = {
            'CRITICAL': AppColors.danger_dark,
            'HIGH': AppColors.danger,
            'MEDIUM': AppColors.warning,
            'LOW': AppColors.accent,
            'TRIVIAL': AppColors.text_muted
        }
        bg_color = priority_colors.get(task.priority.name, AppColors.text_muted)
        priority_badge.setStyleSheet(f"""
            QLabel {{
                background-color: {bg_color};
                color: white;
                padding: 3px 10px;
                border-radius: 3px;
                font-size: 10px;
                font-weight: bold;
            }}
        """)
        top_layout.addWidget(priority_badge)

        main_layout.addLayout(top_layout)

        # Checklist items (if any) - Show only incomplete items
        if hasattr(task, 'checklist') and task.checklist:
            # Filter for incomplete items only
            incomplete_items = [
                (i, item) for i, item in enumerate(task.checklist)
                if not item.get('checked', False) and not item.get('completed', False)
            ]

            if incomplete_items:
                checklist_container = QWidget()
                checklist_layout = QVBoxLayout(checklist_container)
                checklist_layout.setSpacing(4)
                checklist_layout.setContentsMargins(28, 4, 0, 0)

                # Show up to 3 incomplete checklist items
                for original_index, item in incomplete_items[:3]:
                    item_layout = QHBoxLayout()
                    item_layout.setSpacing(8)

                    # Checkbox for checklist item (interactive)
                    item_checkbox = QCheckBox()
                    item_checkbox.setChecked(False)  # Only showing incomplete items
                    item_checkbox.setEnabled(True)  # Make it interactive
                    item_checkbox.setStyleSheet(f"""
                        QCheckBox {{
                            spacing: 5px;
                        }}
                        QCheckBox::indicator {{
                            width: 14px;
                            height: 14px;
                            border: 2px solid {AppColors.text_faint};
                            border-radius: 2px;
                            background-color: {AppColors.surface_raised};
                        }}
                        QCheckBox::indicator:hover {{
                            border-color: {AppColors.accent};
                        }}
                        QCheckBox::indicator:checked {{
                            background-color: {AppColors.success};
                            border-color: {AppColors.success};
                        }}
                    """)
                    # Connect checkbox to update handler
                    item_checkbox.stateChanged.connect(
                        lambda state, t=task, idx=original_index: self.onChecklistItemToggled(t, idx, state)
                    )
                    item_layout.addWidget(item_checkbox)

                    # Checklist item text
                    item_text = QLabel(item.get('text', ''))
                    item_text.setStyleSheet(f"""
                        QLabel {{
                            color: {AppColors.text_secondary};
                            font-size: 12px;
                        }}
                    """)
                    item_text.setWordWrap(False)
                    # Truncate if too long
                    metrics = item_text.fontMetrics()
                    elided_text = metrics.elidedText(item.get('text', ''), Qt.ElideRight, 400)
                    item_text.setText(elided_text)
                    item_layout.addWidget(item_text, 1)

                    checklist_layout.addLayout(item_layout)

                # Show "X more items" if there are more than 3 incomplete items
                if len(incomplete_items) > 3:
                    more_label = QLabel(f"   +{len(incomplete_items) - 3} more items...")
                    more_label.setStyleSheet(f"""
                        QLabel {{
                            color: {AppColors.text_faint};
                            font-size: 11px;
                            font-style: italic;
                        }}
                    """)
                    checklist_layout.addWidget(more_label)

                main_layout.addWidget(checklist_container)

        # Comments (if any) - Task model uses 'entries' attribute
        if hasattr(task, 'entries') and task.entries:
            # Filter for comment-type entries only
            comment_entries = [e for e in task.entries if getattr(e, 'entry_type', 'comment') == 'comment']

            if comment_entries:
                comments_container = QWidget()
                comments_layout = QVBoxLayout(comments_container)
                comments_layout.setSpacing(6)
                comments_layout.setContentsMargins(28, 4, 0, 0)

                # Show up to 2 comments
                for entry in comment_entries[:2]:
                    comment_frame = QFrame()
                    comment_frame.setStyleSheet(f"""
                        QFrame {{
                            background-color: {AppColors.surface_raised};
                            border-left: 3px solid {AppColors.text_muted};
                            border-radius: 3px;
                            padding: 6px;
                        }}
                    """)

                    comment_layout = QVBoxLayout(comment_frame)
                    comment_layout.setSpacing(2)
                    comment_layout.setContentsMargins(6, 4, 6, 4)

                    # Comment text
                    text = getattr(entry, 'content', '')
                    if len(text) > 100:
                        text = text[:100] + '...'

                    comment_text = QLabel(text)
                    comment_text.setWordWrap(True)
                    comment_text.setStyleSheet(f"""
                        QLabel {{
                            color: {AppColors.text_primary};
                            font-size: 11px;
                        }}
                    """)
                    comment_layout.addWidget(comment_text)

                    # Comment author and date
                    author = getattr(entry, 'user_id', 'Unknown')
                    timestamp = getattr(entry, 'timestamp', None)
                    meta_text = f"{author}"
                    if timestamp:
                        from datetime import datetime
                        try:
                            if isinstance(timestamp, str):
                                dt = datetime.fromisoformat(timestamp)
                            else:
                                dt = timestamp
                            meta_text += f" • {dt.strftime('%b %d, %Y')}"
                        except (ValueError, TypeError):
                            pass

                    meta_label = QLabel(meta_text)
                    meta_label.setStyleSheet(f"""
                        QLabel {{
                            color: {AppColors.text_muted};
                            font-size: 10px;
                        }}
                    """)
                    comment_layout.addWidget(meta_label)

                    comments_layout.addWidget(comment_frame)

                # Show "X more comments" if there are more than 2
                if len(comment_entries) > 2:
                    more_label = QLabel(f"   +{len(comment_entries) - 2} more comments...")
                    more_label.setStyleSheet(f"""
                        QLabel {{
                            color: {AppColors.text_faint};
                            font-size: 11px;
                            font-style: italic;
                        }}
                    """)
                    comments_layout.addWidget(more_label)

                main_layout.addWidget(comments_container)

        return task_frame

    def onTaskFrameClicked(self, task):
        """Handle task frame click - emit signal to open task detail"""
        self.taskClicked.emit(task)

    def onChecklistItemToggled(self, task, item_index, state):
        """Handle checklist item checkbox toggle"""
        from PyQt5.QtCore import Qt

        # Update the checklist item
        if 0 <= item_index < len(task.checklist):
            is_checked = (state == Qt.Checked)
            task.checklist[item_index]['checked'] = is_checked
            task.checklist[item_index]['completed'] = is_checked

            # Save the updated task
            from utils.tasks_io import save_task_to_json
            save_task_to_json(task, self.logger)

            self.logger.info(f"Checklist item {item_index} in task '{task.title}' marked as {'completed' if is_checked else 'incomplete'}")

            # Refresh the project card to update the display
            self.refresh()

    def onTaskCheckboxToggled(self, task, state):
        """Handle main task checkbox toggle - marks entire task as complete/incomplete"""
        from PyQt5.QtCore import Qt
        from models.task import TaskStatus

        is_checked = (state == Qt.Checked)

        # Update task status
        if is_checked:
            task.status = TaskStatus.COMPLETED
        else:
            task.status = TaskStatus.NOT_STARTED

        # Save the updated task
        from utils.tasks_io import save_task_to_json
        save_task_to_json(task, self.logger)

        self.logger.info(f"Task '{task.title}' marked as {'completed' if is_checked else 'incomplete'}")

        # Check if all tasks in current phase are complete and advance if needed
        if is_checked and self.current_phase:
            self.checkAndAdvancePhase()

        # Refresh the project card to update the display
        self.refresh()

    def checkAndAdvancePhase(self):
        """Check if all tasks in current phase are complete and advance to next phase if so"""
        from models.task import TaskStatus

        # Load all tasks
        all_tasks = load_tasks_from_json(self.logger)

        # Get tasks in current phase
        phase_tasks = [all_tasks[tid] for tid in self.current_phase.task_ids if tid in all_tasks]

        if not phase_tasks:
            return

        # Check if all tasks are completed
        all_complete = all(task.status == TaskStatus.COMPLETED for task in phase_tasks)

        if all_complete:
            self.logger.info(f"All tasks in phase '{self.current_phase.name}' are complete. Advancing to next phase.")

            # Find the phase after this one (by position; stored orders can have gaps)
            ordered = sorted(self.phases, key=lambda p: p.order)
            position = next((i for i, p in enumerate(ordered) if p.id == self.current_phase.id), None)
            next_phase = ordered[position + 1] if position is not None and position + 1 < len(ordered) else None

            if next_phase:
                # Updates both the phases' flags and the project's current phase
                from utils.projects_io import set_current_phase
                set_current_phase(self.current_phase.project_id, next_phase.id, self.logger)

                self.logger.info(f"Advanced to next phase: {next_phase.name}")

                # Update local reference
                self.current_phase = next_phase
            else:
                self.logger.info("No next phase to advance to - project complete!")

    def createFooter(self):
        """Create footer with close button"""
        footer = QFrame()
        footer.setStyleSheet(f"""
            QFrame {{
                background-color: {AppColors.surface_raised};
                border-top: 2px solid {AppColors.accent};
            }}
        """)

        layout = QHBoxLayout(footer)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.addStretch()

        # Close button
        close_btn = QPushButton("Close")
        close_btn.setFixedSize(120, 40)
        close_btn.setStyleSheet(AppStyles.save_button())
        close_btn.clicked.connect(self.closeRequested.emit)
        layout.addWidget(close_btn)

        return footer
