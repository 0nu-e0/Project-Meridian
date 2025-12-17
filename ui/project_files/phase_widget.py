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
# File: phase_widget.py
# Description: Collapsible widget for displaying a project phase
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

from PyQt5.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QMimeData, QByteArray
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QFrame, QSizePolicy, QMessageBox
)
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QDrag, QCursor

from models.phase import Phase
from models.project import Project
from models.task import TaskStatus
from utils.projects_io import load_phases_from_json, save_phases_to_json, delete_phase, move_task_to_phase
from utils.tasks_io import load_tasks_from_json, save_task_to_json
from resources.styles import AppStyles
from ui.project_files.draggable_task_item import DraggableTaskItem


class PhaseWidget(QWidget):
    """
    Collapsible widget for displaying a phase with its tasks
    """

    phaseUpdated = pyqtSignal(str)  # Emits phase_id when updated
    phaseDeleted = pyqtSignal(str)  # Emits phase_id when deleted
    phaseReordered = pyqtSignal(str, int)  # Emits (phase_id, new_position) when dragged to new position

    def __init__(self, phase: Phase, project: Project, logger):
        super().__init__()
        self.phase = phase
        self.project = project
        self.logger = logger
        self.is_expanded = not phase.collapsed
        self.tasks = []
        self.drag_start_position = None

        # Enable drag and drop
        self.setAcceptDrops(True)

        self.loadTasks()
        self.initUI()

    def loadTasks(self):
        """Load tasks for this phase"""
        all_tasks = load_tasks_from_json(self.logger)
        # Filter tasks that belong to this phase
        self.tasks = [
            task for task in all_tasks.values()
            if task.phase_id == self.phase.id
        ]
        # Sort by priority (HIGH > MEDIUM > LOW)
        self.tasks.sort(key=lambda t: t.priority.value, reverse=True)

    def initUI(self):
        """Initialize the widget UI"""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Container frame
        self.container = QFrame()
        border_color = self.project.color if self.phase.is_current else "#3498db"
        background_color = "#2c3e50"

        self.container.setStyleSheet(f"""
            QFrame {{
                background-color: {background_color};
                border: 2px solid {border_color};
                border-radius: 8px;
            }}
        """)

        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(15, 15, 15, 15)
        container_layout.setSpacing(10)

        # Header section
        header_layout = self.createHeader()
        container_layout.addLayout(header_layout)

        # Collapsible content section
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 10, 0, 0)
        self.content_layout.setSpacing(10)

        # Task list
        if self.tasks:
            for task in self.tasks:
                task_item = self.createTaskItem(task)
                self.content_layout.addWidget(task_item)
        else:
            # Empty state
            empty_label = QLabel("No tasks in this phase yet")
            empty_label.setStyleSheet("font-size: 12px; color: #bdc3c7; padding: 10px;")
            empty_label.setAlignment(Qt.AlignCenter)
            self.content_layout.addWidget(empty_label)

        # "+ Add Task" button
        add_task_btn = QPushButton("+ Add Task")
        add_task_btn.setStyleSheet(AppStyles.add_button())
        add_task_btn.setFixedHeight(35)
        add_task_btn.clicked.connect(self.onAddTask)
        self.content_layout.addWidget(add_task_btn)

        # Add stretch to push content to the top when phase has fewer tasks
        self.content_layout.addStretch()

        container_layout.addWidget(self.content_widget)

        # Set initial visibility based on collapsed state
        self.content_widget.setVisible(self.is_expanded)

        main_layout.addWidget(self.container)

    def createHeader(self):
        """Create the phase header with expand/collapse button"""
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        # Drag handle
        drag_handle = QLabel("⋮⋮")
        drag_handle.setStyleSheet("""
            QLabel {
                color: #7f8c8d;
                font-size: 14px;
                padding: 0px 5px;
            }
        """)
        drag_handle.setToolTip("Drag to reorder phases")
        header_layout.addWidget(drag_handle)

        # Expand/collapse button
        self.expand_btn = QPushButton("▼" if self.is_expanded else "▶")
        self.expand_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                font-size: 16px;
                color: #bdc3c7;
                padding: 0px;
                min-width: 20px;
                max-width: 20px;
            }
            QPushButton:hover {
                color: #ecf0f1;
            }
        """)
        self.expand_btn.clicked.connect(self.toggleExpand)
        header_layout.addWidget(self.expand_btn)

        # Phase number and name
        phase_label_text = f"Phase {self.phase.order + 1}: {self.phase.name}"
        phase_name_label = QLabel(phase_label_text)
        phase_name_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #ecf0f1;
            }
        """)
        header_layout.addWidget(phase_name_label)

        # Current phase badge
        if self.phase.is_current:
            current_badge = QLabel("CURRENT")
            current_badge.setStyleSheet(f"""
                QLabel {{
                    background-color: {self.project.color};
                    color: white;
                    font-size: 10px;
                    font-weight: bold;
                    padding: 3px 8px;
                    border-radius: 3px;
                }}
            """)
            header_layout.addWidget(current_badge)

        # Spacer
        header_layout.addStretch()

        # Progress info
        progress = self.phase.get_progress_percentage()
        task_count = self.phase.get_task_count()
        completed_count = self.phase.get_completed_task_count()

        progress_label = QLabel(f"{completed_count}/{task_count} tasks ({progress:.0f}%)")
        progress_label.setStyleSheet("font-size: 12px; color: #bdc3c7;")
        header_layout.addWidget(progress_label)

        # Edit button (shows on hover - for now always visible)
        edit_btn = QPushButton("Edit")
        edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #34495e;
                border: 2px solid #3498db;
                border-radius: 4px;
                color: #ecf0f1;
                font-size: 11px;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background-color: #3498db;
            }
        """)
        edit_btn.clicked.connect(self.onEditPhase)
        header_layout.addWidget(edit_btn)

        # Delete button
        delete_btn = QPushButton("Delete")
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                border: none;
                border-radius: 4px;
                color: white;
                font-size: 11px;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        delete_btn.clicked.connect(self.onDeletePhase)
        header_layout.addWidget(delete_btn)

        # Mark as current button (if not already current)
        if not self.phase.is_current:
            current_btn = QPushButton("Mark Current")
            current_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.project.color};
                    border: none;
                    border-radius: 4px;
                    color: white;
                    font-size: 11px;
                    padding: 4px 8px;
                }}
                QPushButton:hover {{
                    opacity: 0.8;
                }}
            """)
            current_btn.clicked.connect(self.onMarkAsCurrent)
            header_layout.addWidget(current_btn)

        return header_layout

    def toggleExpand(self):
        """Toggle the expand/collapse state"""
        self.is_expanded = not self.is_expanded

        # Update button text
        self.expand_btn.setText("▼" if self.is_expanded else "▶")

        # Toggle content visibility
        self.content_widget.setVisible(self.is_expanded)

        # Update phase collapsed state in storage
        self.phase.collapsed = not self.is_expanded
        phases = load_phases_from_json(self.logger)
        phases[self.phase.id] = self.phase
        save_phases_to_json(phases, self.logger)

    def createTaskItem(self, task):
        """Create a draggable task list item widget"""
        task_widget = DraggableTaskItem(task)
        task_widget.clicked.connect(self.onTaskClicked)
        return task_widget

    def getStatusIcon(self, status):
        """Get icon for task status"""
        status_icons = {
            TaskStatus.NOT_STARTED: "○",
            TaskStatus.IN_PROGRESS: "◐",
            TaskStatus.COMPLETED: "●",
            TaskStatus.IN_REVIEW: "◑",
            TaskStatus.BLOCKED: "✖",
            TaskStatus.ON_HOLD: "⊝",
            TaskStatus.CANCELLED: "⊗"
        }
        return status_icons.get(status, "○")

    def getPriorityColor(self, priority_name):
        """Get color for priority badge"""
        priority_colors = {
            "HIGH": "#e74c3c",
            "MEDIUM": "#f39c12",
            "LOW": "#3498db"
        }
        return priority_colors.get(priority_name, "#95a5a6")

    def onTaskClicked(self, task):
        """Handle task item click - opens task detail view"""
        from ui.task_files.task_card_expanded import TaskCardExpanded
        from PyQt5.QtCore import Qt

        self.logger.info(f"Task clicked: {task.title}")

        # Create overlay to dim background
        self.overlay = QWidget(self.window())
        self.overlay.setStyleSheet("background-color: rgba(0, 0, 0, 128);")
        self.overlay.setGeometry(self.window().rect())
        self.overlay.show()
        self.overlay.raise_()

        # Create dialog container
        self.dialog_container = QWidget(self.window())
        self.dialog_container.setStyleSheet("background-color: transparent;")
        self.dialog_container.setGeometry(self.window().rect())
        # Make clicking outside close the dialog
        self.dialog_container.mousePressEvent = lambda event: self.closeTaskDetail() if event.button() == Qt.LeftButton else None
        self.dialog_container.show()
        self.dialog_container.raise_()

        # Create the expanded card
        self.expanded_card = TaskCardExpanded(
            logger=self.logger,
            task=task,
            grid_id=None,
            parent_view=None,
            parent=self.dialog_container
        )
        # Connect both save signals (saveCompleted for new tasks, newTaskUpdate for existing tasks)
        self.expanded_card.saveCompleted.connect(self.onTaskSaveCompleted)
        self.expanded_card.newTaskUpdate.connect(self.onTaskSaveCompleted)
        self.expanded_card.cancelTask.connect(self.onTaskCanceled)
        self.expanded_card.taskDeleted.connect(self.onTaskDeleted)
        self.expanded_card.setObjectName("card_container")
        self.expanded_card.setAttribute(Qt.WA_StyledBackground, True)
        self.expanded_card.setStyleSheet(AppStyles.expanded_task_card())

        # Prevent clicks on the card from closing the dialog
        self.expanded_card.mousePressEvent = lambda event: event.accept()

        # Center and show the card
        window = self.window()
        card_width, card_height = TaskCardExpanded.calculate_optimal_card_size(window)
        window_rect = window.rect()
        x = (window_rect.width() - card_width) // 2
        y = (window_rect.height() - card_height) // 2
        self.expanded_card.setGeometry(x, y, card_width, card_height)
        self.expanded_card.show()
        self.expanded_card.raise_()

    def onTaskSaveCompleted(self, task, grid_id):
        """Handle task save completion"""
        # Invalidate project task cache since a task was modified
        if self.project:
            self.project.invalidate_task_cache()
        self.closeTaskDetail()
        self.refreshTasks()

    def onTaskCanceled(self):
        """Handle task dialog cancel"""
        self.closeTaskDetail()

    def onTaskDeleted(self, task_title):
        """Handle task deletion"""
        # Invalidate project task cache since a task was deleted
        if self.project:
            self.project.invalidate_task_cache()
        self.closeTaskDetail()
        self.refreshTasks()

    def closeTaskDetail(self):
        """Close the task detail overlay"""
        if hasattr(self, 'expanded_card') and self.expanded_card:
            self.expanded_card.close()
            self.expanded_card.deleteLater()
            self.expanded_card = None

        if hasattr(self, 'dialog_container') and self.dialog_container:
            self.dialog_container.close()
            self.dialog_container.deleteLater()
            self.dialog_container = None

        if hasattr(self, 'overlay') and self.overlay:
            self.overlay.close()
            self.overlay.deleteLater()
            self.overlay = None

    def onAddTask(self):
        """Handle add task button click"""
        from ui.project_files.task_dialog import TaskDialog

        dialog = TaskDialog(
            project_id=self.project.id,
            phase_id=self.phase.id,
            logger=self.logger,
            parent=self
        )
        dialog.taskSaved.connect(self.onTaskSaved)
        dialog.exec_()

    def onTaskSaved(self, task_data):
        """Handle task saved from dialog"""
        from models.task import Task
        from datetime import datetime

        # Create the task
        task = Task(
            title=task_data['title'],
            description=task_data['description'],
        )

        task.priority = task_data['priority']
        task.status = task_data['status']

        # Set project and phase
        task.project_id = task_data['project_id']
        task.phase_id = task_data['phase_id']

        # Set priority and status (these are instance attributes, not constructor params)
        task.priority = task_data['priority']
        task.status = task_data['status']

        # Set creation date
        task.creation_date = datetime.now()

        # Save the task
        save_task_to_json(task, self.logger)

        # Add task to phase's task_ids list
        if task.phase_id:
            phases = load_phases_from_json(self.logger)
            if self.phase.id in phases:
                phase = phases[self.phase.id]
                if task.id not in phase.task_ids:
                    phase.task_ids.append(task.id)
                    save_phases_to_json(phases, self.logger)
                    self.logger.info(f"Added task {task.id} to phase {self.phase.id} task_ids list")

        # Invalidate project task cache since a new task was added
        if self.project:
            self.project.invalidate_task_cache()

        # Refresh the phase widget
        self.refreshTasks()

    def refreshTasks(self):
        """Refresh the task list in the content area"""
        # Reload tasks
        self.loadTasks()

        # Clear existing task widgets
        while self.content_layout.count() > 1:  # Keep the Add Task button
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Re-add task items
        if self.tasks:
            for task in self.tasks:
                task_item = self.createTaskItem(task)
                self.content_layout.insertWidget(self.content_layout.count() - 1, task_item)
        else:
            # Empty state
            empty_label = QLabel("No tasks in this phase yet")
            empty_label.setStyleSheet("font-size: 12px; color: #95a5a6; padding: 10px;")
            empty_label.setAlignment(Qt.AlignCenter)
            self.content_layout.insertWidget(0, empty_label)

    def onEditPhase(self):
        """Handle edit phase button click"""
        from ui.project_files.phase_dialog import PhaseDialog

        dialog = PhaseDialog(
            mode="edit",
            project_id=self.project.id,
            phase=self.phase,
            logger=self.logger,
            parent=self
        )
        dialog.phaseSaved.connect(self.onPhaseEdited)
        dialog.exec_()

    def onPhaseEdited(self, phase_data):
        """Handle phase edited from dialog"""
        # Update phase
        self.phase.name = phase_data['name']
        self.phase.description = phase_data['description']

        # Save to JSON
        phases = load_phases_from_json(self.logger)
        phases[self.phase.id] = self.phase
        save_phases_to_json(phases, self.logger)

        # Emit signal
        self.phaseUpdated.emit(self.phase.id)

    def onDeletePhase(self):
        """Handle delete phase button click"""
        # Show confirmation dialog
        reply = QMessageBox.question(
            self,
            "Delete Phase",
            f"Are you sure you want to delete the phase '{self.phase.name}'?\n\nTasks in this phase will not be deleted, but will no longer be associated with it.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Delete the phase
            success = delete_phase(self.phase.id, self.logger)

            if success:
                self.phaseDeleted.emit(self.phase.id)
            else:
                QMessageBox.warning(self, "Error", "Failed to delete phase")

    def onMarkAsCurrent(self):
        """Handle mark as current button click"""
        from utils.projects_io import load_projects_from_json, save_projects_to_json

        # Load all phases and projects
        phases = load_phases_from_json(self.logger)
        projects = load_projects_from_json(self.logger)

        # Unmark old current phase
        if self.project.current_phase_id:
            old_current = phases.get(self.project.current_phase_id)
            if old_current:
                old_current.is_current = False
                phases[old_current.id] = old_current

        # Mark this phase as current
        self.phase.is_current = True
        phases[self.phase.id] = self.phase

        # Update project's current_phase_id
        self.project.current_phase_id = self.phase.id
        projects[self.project.id] = self.project

        # Save changes
        save_phases_to_json(phases, self.logger)
        save_projects_to_json(projects, self.logger)

        # Emit signal
        self.phaseUpdated.emit(self.phase.id)

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter event"""
        if event.mimeData().hasFormat("application/x-task-id"):
            event.acceptProposedAction()
            # Highlight the phase to indicate it can accept the drop
            self.container.setStyleSheet(self.container.styleSheet() + """
                QFrame {
                    border: 2px dashed #3498db;
                    background-color: #ebf5fb;
                }
            """)
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        """Handle drag leave event"""
        # Remove highlight
        self.updateContainerStyle()

    def dropEvent(self, event: QDropEvent):
        """Handle drop event"""
        if event.mimeData().hasFormat("application/x-task-id"):
            task_id = bytes(event.mimeData().data("application/x-task-id")).decode()

            # Load tasks to get the task
            all_tasks = load_tasks_from_json(self.logger)
            task = all_tasks.get(task_id)

            if task:
                # Check if task is already in this phase
                if task.phase_id == self.phase.id:
                    self.logger.info(f"Task {task.title} already in phase {self.phase.name}")
                    self.updateContainerStyle()
                    return

                # Move task to this phase
                old_phase_id = task.phase_id
                success = move_task_to_phase(task_id, self.phase.id, self.logger)

                if success:
                    self.logger.info(f"Moved task {task.title} to phase {self.phase.name}")

                    # Refresh the task list
                    self.refreshTasks()

                    # Emit signal to notify parent
                    self.phaseUpdated.emit(self.phase.id)
                    if old_phase_id:
                        self.phaseUpdated.emit(old_phase_id)

                    event.acceptProposedAction()
                else:
                    QMessageBox.warning(self, "Error", "Failed to move task to this phase.")
                    event.ignore()
            else:
                event.ignore()

        # Remove highlight
        self.updateContainerStyle()

    def updateContainerStyle(self):
        """Update container styling based on phase state"""
        border_color = self.project.color if self.phase.is_current else "#e0e0e0"
        background = "#f8f9fa" if self.phase.is_current else "#ffffff"

        self.container.setStyleSheet(f"""
            QFrame {{
                background-color: {background};
                border: 2px solid {border_color};
                border-radius: 8px;
                padding: 0px;
            }}
        """)

    def mousePressEvent(self, event):
        """Handle mouse press to start drag"""
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.pos()

    def mouseMoveEvent(self, event):
        """Handle mouse move to initiate drag"""
        if not (event.buttons() & Qt.LeftButton):
            return
        if self.drag_start_position is None:
            return

        # Only start drag if moved far enough
        if (event.pos() - self.drag_start_position).manhattanLength() < 10:
            return

        # Create drag object
        from PyQt5.QtGui import QDrag
        from PyQt5.QtCore import QMimeData
        import sip

        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(self.phase.id)  # Store phase ID
        drag.setMimeData(mime_data)

        # Visual feedback - make widget semi-transparent during drag
        self.setStyleSheet("opacity: 0.5;")

        # Execute drag
        drag.exec_(Qt.MoveAction)

        # Reset opacity only if widget still exists (not deleted during refresh)
        try:
            if not sip.isdeleted(self):
                self.setStyleSheet("")
        except RuntimeError:
            # Widget was deleted during drag operation, ignore
            pass

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter for both tasks and phase reordering"""
        mime_data = event.mimeData()

        # Check if it's a task being dragged
        if mime_data.hasFormat("application/x-task-id"):
            event.acceptProposedAction()
            # Highlight the phase to indicate it can accept the drop
            self.container.setStyleSheet(self.container.styleSheet() + """
                QFrame {
                    border: 2px dashed #3498db;
                    background-color: #ebf5fb;
                }
            """)
        # Check if it's a phase being dragged
        elif mime_data.hasText():
            dragged_phase_id = mime_data.text()
            # Only accept if it's a different phase
            if dragged_phase_id != self.phase.id:
                event.acceptProposedAction()
                # Show drop indicator
                self.container.setStyleSheet(self.container.styleSheet() + """
                    QFrame {
                        border: 3px dashed #27ae60;
                    }
                """)
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        """Handle drag leave event"""
        # Remove highlight
        self.updateContainerStyle()

    def dropEvent(self, event: QDropEvent):
        """Handle drop event for both tasks and phase reordering"""
        mime_data = event.mimeData()

        # Handle task drop
        if mime_data.hasFormat("application/x-task-id"):
            task_id = bytes(mime_data.data("application/x-task-id")).decode()

            # Load tasks to get the task
            all_tasks = load_tasks_from_json(self.logger)
            task = all_tasks.get(task_id)

            if task:
                # Check if task is already in this phase
                if task.phase_id == self.phase.id:
                    self.logger.info(f"Task {task.title} already in phase {self.phase.name}")
                    self.updateContainerStyle()
                    return

                # Move task to this phase
                old_phase_id = task.phase_id
                success = move_task_to_phase(task_id, self.phase.id, self.logger)

                if success:
                    self.logger.info(f"Moved task {task.title} to phase {self.phase.name}")

                    # Refresh the task list
                    self.refreshTasks()

                    # Emit signal to notify parent
                    self.phaseUpdated.emit(self.phase.id)
                    if old_phase_id:
                        self.phaseUpdated.emit(old_phase_id)

                    event.acceptProposedAction()
                else:
                    QMessageBox.warning(self, "Error", "Failed to move task to this phase.")
                    event.ignore()
            else:
                event.ignore()

        # Handle phase reorder drop
        elif mime_data.hasText():
            dragged_phase_id = mime_data.text()
            if dragged_phase_id != self.phase.id:
                # Emit signal with the target position (this phase's order)
                self.phaseReordered.emit(dragged_phase_id, self.phase.order)
                event.acceptProposedAction()

        # Remove highlight
        self.updateContainerStyle()
