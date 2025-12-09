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
# File: project_detail_view.py
# Description: Detailed view for a single project with phases
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QProgressBar, QMessageBox, QGridLayout
)

from models.project import Project
from utils.projects_io import (
    load_projects_from_json, load_phases_from_json,
    save_projects_to_json, save_phases_to_json, create_phase
)
from resources.styles import AppStyles, AnimatedButton
from ui.project_files.project_dialog import ProjectDialog
from ui.project_files.phase_widget import PhaseWidget


class ProjectDetailView(QWidget):
    """
    Detailed view of a project showing all phases and tasks
    """

    backClicked = pyqtSignal()  # Emitted when back button is clicked

    def __init__(self, project_id: str, logger, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.logger = logger
        self.project = None
        self.phases = []
        self.phase_widgets = []

        self.loadProjectData()
        self.initUI()

    def loadProjectData(self):
        """Load project and phase data from JSON"""
        projects = load_projects_from_json(self.logger)
        self.project = projects.get(self.project_id)

        if not self.project:
            self.logger.error(f"Project {self.project_id} not found")
            return

        # Load phases for this project
        all_phases = load_phases_from_json(self.logger)
        self.phases = [
            all_phases[phase_id]
            for phase_id in self.project.phases
            if phase_id in all_phases
        ]
        # Sort by order
        self.phases.sort(key=lambda p: p.order)

    def initUI(self):
        """Initialize the user interface"""
        if not self.project:
            # Show error state
            layout = QVBoxLayout(self)
            error_label = QLabel("Project not found")
            error_label.setStyleSheet("font-size: 18px; color: #e74c3c;")
            layout.addWidget(error_label, alignment=Qt.AlignCenter)
            return

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # Header section
        header_layout = self.createHeader()
        main_layout.addLayout(header_layout)

        # Info section (status, priority, dates, progress)
        info_section = self.createInfoSection()
        main_layout.addWidget(info_section)

        # Action buttons (View Mindmap, Add to Planning)
        action_buttons = self.createActionButtons()
        main_layout.addLayout(action_buttons)

        # Scrollable area for phases
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
        """)

        # Container for phases
        self.phases_container = QWidget()
        phases_main_layout = QVBoxLayout(self.phases_container)
        phases_main_layout.setContentsMargins(0, 0, 0, 0)
        phases_main_layout.setSpacing(15)

        # Grid layout for phases (2 columns)
        self.phases_layout = QGridLayout()
        self.phases_layout.setSpacing(15)
        self.phases_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        phases_main_layout.addLayout(self.phases_layout)

        # Populate phases
        self.populatePhases()

        # Add "+ Add Phase" button at bottom
        add_phase_btn = AnimatedButton("+ Add Phase")
        add_phase_btn.setStyleSheet(AppStyles.add_button())
        add_phase_btn.setFixedHeight(40)
        add_phase_btn.clicked.connect(self.onAddPhase)
        phases_main_layout.addWidget(add_phase_btn)

        scroll_area.setWidget(self.phases_container)
        main_layout.addWidget(scroll_area)

    def createHeader(self):
        """Create header with back button, title, and action buttons"""
        header_layout = QHBoxLayout()
        header_layout.setSpacing(15)

        # Back button
        back_btn = QPushButton("← Back")
        back_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #3498db;
                font-size: 14px;
                font-weight: bold;
                padding: 5px 10px;
            }
            QPushButton:hover {
                color: #2980b9;
                text-decoration: underline;
            }
        """)
        back_btn.clicked.connect(self.onBackClicked)
        header_layout.addWidget(back_btn)

        # Project title with folder icon
        title_label = QLabel(f"📁 {self.project.title}")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #2c3e50;
            }
        """)
        header_layout.addWidget(title_label)

        # Spacer
        header_layout.addStretch()

        # Edit button
        edit_btn = AnimatedButton("Edit")
        edit_btn.setStyleSheet(AppStyles.button_normal())
        edit_btn.setFixedSize(80, 35)
        edit_btn.clicked.connect(self.onEditProject)
        header_layout.addWidget(edit_btn)

        # Menu button (⋮) for additional actions
        menu_btn = QPushButton("⋮")
        menu_btn.setStyleSheet("""
            QPushButton {
                background-color: #ecf0f1;
                border: none;
                border-radius: 5px;
                font-size: 20px;
                font-weight: bold;
                color: #7f8c8d;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #bdc3c7;
            }
        """)
        menu_btn.setFixedSize(50, 35)
        menu_btn.clicked.connect(self.onMenuClicked)
        header_layout.addWidget(menu_btn)

        return header_layout

    def createInfoSection(self):
        """Create info section showing project details"""
        info_widget = QFrame()
        info_widget.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 15px;
            }
        """)

        main_layout = QHBoxLayout(info_widget)
        main_layout.setSpacing(20)

        # Left column: Description
        left_column = QVBoxLayout()
        left_column.setSpacing(5)

        if self.project.description:
            desc_label = QLabel(self.project.description)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("font-size: 12px; color: #7f8c8d;")
            left_column.addWidget(desc_label)
        else:
            desc_label = QLabel("No description")
            desc_label.setStyleSheet("font-size: 12px; color: #bdc3c7; font-style: italic;")
            left_column.addWidget(desc_label)

        left_column.addStretch()
        main_layout.addLayout(left_column, 2)

        # Right column: Status, Priority, Progress
        right_column = QVBoxLayout()
        right_column.setSpacing(8)

        # Status and Priority in a compact row
        status_row = QHBoxLayout()
        status_label = QLabel(f"Status: {self.project.status.value}")
        status_label.setStyleSheet("font-size: 12px; color: #34495e;")
        status_row.addWidget(status_label)

        priority_label = QLabel(f"Priority: {self.project.priority.name}")
        priority_label.setStyleSheet("font-size: 12px; color: #34495e;")
        status_row.addWidget(priority_label)
        status_row.addStretch()
        right_column.addLayout(status_row)

        # Due date
        if self.project.target_completion:
            due_label = QLabel(f"Due: {self.project.target_completion.strftime('%m/%d/%Y')}")
            due_label.setStyleSheet("font-size: 12px; color: #34495e;")
            right_column.addWidget(due_label)

        # Progress bar (smaller)
        progress_bar = QProgressBar()
        progress = int(self.project.get_progress_percentage())
        progress_bar.setValue(progress)
        progress_bar.setFormat(f"{progress}%")
        progress_bar.setFixedHeight(18)
        progress_bar.setFixedWidth(150)
        progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                text-align: center;
                font-size: 10px;
                font-weight: bold;
                background-color: #ecf0f1;
            }}
            QProgressBar::chunk {{
                background-color: {self.project.color};
                border-radius: 3px;
            }}
        """)
        right_column.addWidget(progress_bar)

        # Task count
        total_tasks = self.project.get_total_tasks()
        completed_tasks = self.project.get_completed_tasks()
        task_count_label = QLabel(f"📋 {completed_tasks}/{total_tasks} tasks")
        task_count_label.setStyleSheet("font-size: 11px; color: #7f8c8d;")
        right_column.addWidget(task_count_label)

        right_column.addStretch()
        main_layout.addLayout(right_column, 1)

        return info_widget

    def createActionButtons(self):
        """Create action buttons row"""
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        # View Mindmap button (if linked)
        if self.project.mindmap_id:
            mindmap_btn = AnimatedButton("🧠 View Mindmap")
            mindmap_btn.setStyleSheet(AppStyles.button_normal())
            mindmap_btn.setFixedHeight(35)
            mindmap_btn.clicked.connect(self.onViewMindmap)
            buttons_layout.addWidget(mindmap_btn)

        # Add to Planning button
        planning_btn = AnimatedButton("📅 Add to Planning")
        planning_btn.setStyleSheet(AppStyles.button_normal())
        planning_btn.setFixedHeight(35)
        planning_btn.clicked.connect(self.onAddToPlanning)
        buttons_layout.addWidget(planning_btn)

        buttons_layout.addStretch()

        return buttons_layout

    def populatePhases(self):
        """Populate the phases container with phase widgets in a grid"""
        # Clear existing widgets from grid
        while self.phases_layout.count():
            item = self.phases_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.phase_widgets.clear()

        # Show empty state if no phases
        if not self.phases:
            empty_label = QLabel("No phases yet. Click '+ Add Phase' to create one.")
            empty_label.setStyleSheet("""
                QLabel {
                    font-size: 14px;
                    color: #95a5a6;
                    padding: 20px;
                }
            """)
            empty_label.setAlignment(Qt.AlignCenter)
            self.phases_layout.addWidget(empty_label, 0, 0, 1, 2)  # Span 2 columns
            return

        # Create phase widgets in a 2-column grid
        columns = 2
        for index, phase in enumerate(self.phases):
            row = index // columns
            col = index % columns

            phase_widget = PhaseWidget(phase, self.project, self.logger)
            phase_widget.phaseUpdated.connect(self.onPhaseUpdated)
            phase_widget.phaseDeleted.connect(self.onPhaseDeleted)

            # Set a minimum width for phase widgets
            phase_widget.setMinimumWidth(300)

            self.phase_widgets.append(phase_widget)
            self.phases_layout.addWidget(phase_widget, row, col)

    def onBackClicked(self):
        """Handle back button click"""
        self.backClicked.emit()

    def onEditProject(self):
        """Handle edit project button click"""
        dialog = ProjectDialog(mode="edit", project=self.project, logger=self.logger, parent=self)
        dialog.projectSaved.connect(self.onProjectEdited)
        dialog.exec_()

    def onProjectEdited(self, project_data):
        """Handle project edited from dialog"""
        # Update project fields
        self.project.title = project_data['title']
        self.project.description = project_data['description']
        self.project.status = project_data['status']
        self.project.priority = project_data['priority']
        self.project.color = project_data['color']

        if project_data.get('start_date'):
            self.project.start_date = project_data['start_date']

        if project_data.get('target_completion'):
            self.project.target_completion = project_data['target_completion']

        # Save to JSON
        projects = load_projects_from_json(self.logger)
        projects[self.project_id] = self.project
        save_projects_to_json(projects, self.logger)

        # Refresh UI
        self.refresh()

    def onMenuClicked(self):
        """Handle menu button click"""
        # For now, show a simple message
        # In Phase 7, this will show a context menu
        QMessageBox.information(self, "Menu", "Additional actions coming in Phase 7")

    def onViewMindmap(self):
        """Handle view mindmap button click"""
        # This will be implemented in Phase 6
        QMessageBox.information(self, "Mindmap", f"View mindmap: {self.project.mindmap_id}\n(Feature coming in Phase 6)")

    def onAddToPlanning(self):
        """Handle add to planning button click"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QCalendarWidget, QPushButton, QHBoxLayout
        from PyQt5.QtCore import QDate
        from utils.projects_io import schedule_project

        # Create a simple date picker dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Schedule Project")
        dialog.setModal(True)
        dialog.setMinimumWidth(400)

        layout = QVBoxLayout(dialog)

        # Label
        label = QLabel(f"Select a date to schedule '{self.project.title}':")
        label.setStyleSheet("font-size: 14px; padding: 10px;")
        layout.addWidget(label)

        # Calendar widget
        calendar = QCalendarWidget()
        calendar.setMinimumDate(QDate.currentDate())
        calendar.setGridVisible(True)
        layout.addWidget(calendar)

        # Buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        buttons_layout.addWidget(cancel_btn)

        schedule_btn = QPushButton("Schedule")
        schedule_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        schedule_btn.clicked.connect(dialog.accept)
        buttons_layout.addWidget(schedule_btn)

        layout.addLayout(buttons_layout)

        # Show dialog
        if dialog.exec_() == QDialog.Accepted:
            selected_date = calendar.selectedDate()
            date_string = selected_date.toString("yyyy-MM-dd")

            # Schedule the project
            schedule_id = schedule_project(self.project_id, date_string, self.logger)

            if schedule_id:
                QMessageBox.information(
                    self,
                    "Success",
                    f"Project '{self.project.title}' scheduled for {selected_date.toString('MMMM d, yyyy')}"
                )
            else:
                QMessageBox.warning(
                    self,
                    "Error",
                    "Failed to schedule project. Please try again."
                )

    def onAddPhase(self):
        """Handle add phase button click"""
        from ui.project_files.phase_dialog import PhaseDialog

        dialog = PhaseDialog(mode="create", project_id=self.project_id, logger=self.logger, parent=self)
        dialog.phaseSaved.connect(self.onPhaseSaved)
        dialog.exec_()

    def onPhaseSaved(self, phase_data):
        """Handle phase saved from dialog"""
        # Create the phase
        phase = create_phase(
            project_id=self.project_id,
            name=phase_data['name'],
            description=phase_data['description'],
            order=len(self.project.phases),  # Add at the end
            logger=self.logger
        )

        # Refresh the view
        self.refresh()

    def onPhaseUpdated(self, phase_id):
        """Handle phase updated signal"""
        self.refresh()

    def onPhaseDeleted(self, phase_id):
        """Handle phase deleted signal"""
        self.refresh()

    def refresh(self):
        """Refresh the entire view"""
        self.loadProjectData()

        # Simply repopulate the phases without rebuilding the entire UI
        self.populatePhases()

