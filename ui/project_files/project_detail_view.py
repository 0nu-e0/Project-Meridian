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
    QScrollArea, QFrame, QProgressBar, QMessageBox, QGridLayout,
    QDialog, QListWidget, QListWidgetItem, QDialogButtonBox, QMenu,
    QFileDialog, QSizePolicy, QSpacerItem
)

from utils.constants import (DRAWER_SPACING, LAYOUT_NO_SPACING, WINDOW_DEFAULT_HEIGHT_RATIO,
                             WINDOW_DEFAULT_WIDTH_RATIO, WINDOW_MIN_HEIGHT_RATIO,
                             WINDOW_MIN_WIDTH_RATIO)

from models.project import Project, ProjectStatus
from utils.projects_io import (
    load_projects_from_json, load_phases_from_json,
    save_projects_to_json, save_phases_to_json, create_phase,
    export_project_to_json, import_project_from_json
)
from utils.mindmap_io import (
    load_mindmaps_from_json, link_mindmap_to_project,
    unlink_mindmap_from_project, get_unlinked_mindmaps
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

        self.initCentralWidget()
        self.initBannerSpacer()
        self.setupLayout()

    def initCentralWidget(self):
        self.central_widget = QWidget()
        self.central_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.setLayout(self.main_layout)    
        
    def initBannerSpacer(self):
        self.banner_widget = QWidget()
        self.banner_layout = QVBoxLayout(self.banner_widget)
        banner_height = int(self.height()*0.10) 
        self.banner_spacer = QSpacerItem(1, banner_height, QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.banner_layout.addSpacerItem(self.banner_spacer)
        self.main_layout.addWidget(self.banner_widget)

    def setupLayout(self):

        if not self.project:
            # Show error state
            layout = QVBoxLayout(self)
            error_label = QLabel("Project not found")
            error_label.setStyleSheet("font-size: 18px; color: #e74c3c;")
            layout.addWidget(error_label, alignment=Qt.AlignCenter)
            return
    
        # Main layout

        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
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

        self.main_layout.addWidget(main_widget)

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
        header_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Minimum))
        header_layout.addWidget(back_btn)

        # Project title with folder icon
        title_label = QLabel(f"📁 {self.project.title}")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #ecf0f1;
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
                background-color: #34495e;
                border: 2px solid #3498db;
                border-radius: 5px;
                font-size: 20px;
                font-weight: bold;
                color: #ecf0f1;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #3498db;
            }
        """)
        menu_btn.setFixedSize(50, 35)
        menu_btn.clicked.connect(self.onMenuClicked)
        header_layout.addWidget(menu_btn)

        return header_layout

    def createInfoSection(self):
        """Create condensed info section showing project details"""
        info_widget = QFrame()
        info_widget.setStyleSheet("""
            QFrame {
                background-color: #2c3e50;
                border: 2px solid #3498db;
                border-radius: 8px;
                padding: 8px 12px;
            }
        """)

        # Main horizontal layout - everything in one row
        main_layout = QHBoxLayout(info_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(5, 5, 5, 5)

        # Description (shortened)
        if self.project.description:
            desc_label = QLabel(self.project.description[:100] + ("..." if len(self.project.description) > 100 else ""))
            desc_label.setWordWrap(False)
            desc_label.setStyleSheet("font-size: 11px; color: #bdc3c7;")
            desc_label.setMaximumWidth(200)
            main_layout.addWidget(desc_label, stretch=1)

        # Vertical separator
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setStyleSheet("background-color: #3498db;")
        separator.setFixedWidth(2)
        main_layout.addWidget(separator)

        # Status badge
        status_badge = QLabel(self.project.status.value)
        status_color = self.getStatusColor()
        status_badge.setStyleSheet(f"""
            QLabel {{
                background-color: {status_color};
                color: white;
                font-size: 9px;
                font-weight: bold;
                padding: 3px 6px;
                border-radius: 3px;
            }}
        """)
        main_layout.addWidget(status_badge)

        # Priority badge
        priority_badge = QLabel(self.project.priority.name)
        priority_color = self.getPriorityColor()
        priority_badge.setStyleSheet(f"""
            QLabel {{
                background-color: {priority_color};
                color: white;
                font-size: 9px;
                font-weight: bold;
                padding: 3px 6px;
                border-radius: 3px;
            }}
        """)
        main_layout.addWidget(priority_badge)

        # Due date
        if self.project.target_completion:
            due_label = QLabel(f"Due: {self.project.target_completion.strftime('%m/%d/%y')}")
            due_label.setStyleSheet("font-size: 11px; color: #ecf0f1;")
            main_layout.addWidget(due_label)

        # Progress bar (compact) - store reference for updates
        self.info_progress_bar = QProgressBar()
        progress = int(self.project.get_progress_percentage())
        self.info_progress_bar.setValue(progress)
        self.info_progress_bar.setFormat(f"{progress}%")
        self.info_progress_bar.setFixedHeight(16)
        self.info_progress_bar.setFixedWidth(120)
        self.info_progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 2px solid #3498db;
                border-radius: 3px;
                text-align: center;
                font-size: 9px;
                font-weight: bold;
                background-color: #34495e;
                color: #ecf0f1;
            }}
            QProgressBar::chunk {{
                background-color: {self.project.color};
                border-radius: 2px;
            }}
        """)
        main_layout.addWidget(self.info_progress_bar)

        # Task count - store reference for updates
        total_tasks = self.project.get_total_tasks()
        completed_tasks = self.project.get_completed_tasks()
        self.info_task_count_label = QLabel(f"📋 {completed_tasks}/{total_tasks}")
        self.info_task_count_label.setStyleSheet("font-size: 10px; color: #bdc3c7;")
        main_layout.addWidget(self.info_task_count_label)

        main_layout.addStretch()

        return info_widget

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
        """Get color for priority badge"""
        from models.task import TaskPriority

        priority_colors = {
            TaskPriority.CRITICAL: "#c0392b",   # Dark red
            TaskPriority.HIGH: "#e67e22",       # Orange
            TaskPriority.MEDIUM: "#f39c12",     # Yellow-orange
            TaskPriority.LOW: "#3498db",        # Blue
            TaskPriority.TRIVIAL: "#95a5a6"     # Gray
        }
        return priority_colors.get(self.project.priority, "#7f8c8d")

    def createActionButtons(self):
        """Create action buttons row"""
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        # View Mindmap button (if linked) or Link Mindmap button (if not linked)
        if self.project.mindmap_id:
            mindmap_btn = AnimatedButton("🧠 View Mindmap")
            mindmap_btn.setStyleSheet(AppStyles.button_normal())
            mindmap_btn.setFixedHeight(35)
            mindmap_btn.clicked.connect(self.onViewMindmap)
            buttons_layout.addWidget(mindmap_btn)

            # Unlink button
            unlink_btn = AnimatedButton("🔗 Unlink Mindmap")
            unlink_btn.setStyleSheet("""
                QPushButton {
                    background-color: #e74c3c;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    padding: 8px 16px;
                    font-size: 12px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #c0392b;
                }
            """)
            unlink_btn.setFixedHeight(35)
            unlink_btn.clicked.connect(self.onUnlinkMindmap)
            buttons_layout.addWidget(unlink_btn)
        else:
            link_btn = AnimatedButton("🔗 Link Mindmap")
            link_btn.setStyleSheet(AppStyles.button_normal())
            link_btn.setFixedHeight(35)
            link_btn.clicked.connect(self.onLinkMindmap)
            buttons_layout.addWidget(link_btn)

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
        """Handle menu button click - show context menu"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #d0d0d0;
                border-radius: 5px;
                padding: 5px;
            }
            QMenu::item {
                padding: 8px 20px;
                border-radius: 3px;
            }
            QMenu::item:selected {
                background-color: #3498db;
                color: white;
            }
        """)

        # Export action
        export_action = menu.addAction("📤 Export Project")
        export_action.triggered.connect(self.onExportProject)

        menu.addSeparator()

        # Archive/Unarchive action
        if self.project.archived:
            restore_action = menu.addAction("📂 Restore from Archive")
            restore_action.triggered.connect(self.onRestoreProject)
        else:
            archive_action = menu.addAction("📦 Archive Project")
            archive_action.triggered.connect(self.onArchiveProject)

        menu.addSeparator()

        # Delete action
        delete_action = menu.addAction("🗑️ Delete Project")
        delete_action.triggered.connect(self.onDeleteProject)

        # Show menu at cursor position
        menu.exec_(self.sender().mapToGlobal(self.sender().rect().bottomLeft()))

    def onLinkMindmap(self):
        """Handle link mindmap button click"""
        # Get all unlinked mindmaps
        unlinked_mindmaps = get_unlinked_mindmaps(self.logger)

        if not unlinked_mindmaps:
            # No mindmaps available - offer to create one
            reply = QMessageBox.question(
                self,
                "No Mindmaps Available",
                "There are no available mindmaps to link. Would you like to create a new mindmap for this project?",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                # Create a new mindmap
                from utils.mindmap_io import create_mindmap

                mindmap = create_mindmap(
                    title=f"{self.project.title} Mindmap",
                    description=f"Mindmap for project: {self.project.title}",
                    project_id=self.project_id,
                    logger=self.logger
                )

                # Update project
                self.project.mindmap_id = mindmap.id
                projects = load_projects_from_json(self.logger)
                projects[self.project_id] = self.project
                save_projects_to_json(projects, self.logger)

                QMessageBox.information(
                    self,
                    "Success",
                    f"Created and linked new mindmap: {mindmap.title}"
                )

                # Refresh the view
                self.refresh()
            return

        # Create dialog to select mindmap
        dialog = QDialog(self)
        dialog.setWindowTitle("Link Mindmap")
        dialog.setModal(True)
        dialog.setMinimumWidth(400)
        dialog.setMinimumHeight(300)

        layout = QVBoxLayout(dialog)

        # Label
        label = QLabel("Select a mindmap to link to this project:")
        label.setStyleSheet("font-size: 14px; padding: 10px;")
        layout.addWidget(label)

        # List widget
        list_widget = QListWidget()
        list_widget.setStyleSheet("""
            QListWidget {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                background-color: white;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f0f0f0;
            }
            QListWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #ecf0f1;
            }
        """)

        for mindmap in unlinked_mindmaps:
            item = QListWidgetItem(f"🧠 {mindmap.title}")
            item.setData(Qt.UserRole, mindmap.id)
            if mindmap.description:
                item.setToolTip(mindmap.description)
            list_widget.addItem(item)

        layout.addWidget(list_widget)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        # Show dialog
        if dialog.exec_() == QDialog.Accepted:
            selected_items = list_widget.selectedItems()
            if selected_items:
                mindmap_id = selected_items[0].data(Qt.UserRole)

                # Link the mindmap to the project
                if link_mindmap_to_project(mindmap_id, self.project_id, self.logger):
                    QMessageBox.information(
                        self,
                        "Success",
                        "Mindmap linked successfully!"
                    )

                    # Refresh the view
                    self.refresh()
                else:
                    QMessageBox.warning(
                        self,
                        "Error",
                        "Failed to link mindmap. Please try again."
                    )

    def onUnlinkMindmap(self):
        """Handle unlink mindmap button click"""
        reply = QMessageBox.question(
            self,
            "Unlink Mindmap",
            "Are you sure you want to unlink this mindmap from the project?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if unlink_mindmap_from_project(self.project.mindmap_id, self.logger):
                QMessageBox.information(
                    self,
                    "Success",
                    "Mindmap unlinked successfully!"
                )

                # Refresh the view
                self.refresh()
            else:
                QMessageBox.warning(
                    self,
                    "Error",
                    "Failed to unlink mindmap. Please try again."
                )

    def onViewMindmap(self):
        """Handle view mindmap button click"""
        # Emit a signal to open the mindmap screen
        # This will be handled by the main window
        if hasattr(self.parent(), 'openMindmapScreen'):
            self.parent().openMindmapScreen(self.project.mindmap_id)
        else:
            QMessageBox.information(
                self,
                "View Mindmap",
                f"Mindmap ID: {self.project.mindmap_id}\n\nMindmap screen integration will be completed in the next step."
            )

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

    def updateInfoSection(self):
        """Update the info section widgets with fresh data"""
        if not hasattr(self, 'info_progress_bar') or not hasattr(self, 'info_task_count_label'):
            return

        # Update progress bar
        progress = int(self.project.get_progress_percentage())
        self.info_progress_bar.setValue(progress)
        self.info_progress_bar.setFormat(f"{progress}%")

        # Update task count
        total_tasks = self.project.get_total_tasks()
        completed_tasks = self.project.get_completed_tasks()
        self.info_task_count_label.setText(f"📋 {completed_tasks}/{total_tasks} tasks")

    def onPhaseUpdated(self, phase_id):
        """Handle phase updated signal"""
        self.refresh()

    def onPhaseDeleted(self, phase_id):
        """Handle phase deleted signal"""
        self.refresh()

    def refresh(self):
        """Refresh the entire view"""
        # Invalidate task cache before reloading to get fresh data
        if self.project:
            self.project.invalidate_task_cache()

        self.loadProjectData()

        # Invalidate cache on the newly loaded project instance too
        if self.project:
            self.project.invalidate_task_cache()

        # Simply repopulate the phases without rebuilding the entire UI
        self.populatePhases()

        # Update the info section to reflect any task changes
        self.updateInfoSection()

    def onArchiveProject(self):
        """Handle archive project action"""
        reply = QMessageBox.question(
            self,
            "Archive Project",
            f"Are you sure you want to archive '{self.project.title}'?\n\n"
            "Archived projects will be hidden from the main view but can be restored later.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.project.archived = True
            projects = load_projects_from_json(self.logger)
            projects[self.project_id] = self.project
            save_projects_to_json(projects, self.logger)

            QMessageBox.information(
                self,
                "Success",
                f"Project '{self.project.title}' has been archived."
            )

            # Go back to projects list
            self.backClicked.emit()

    def onRestoreProject(self):
        """Handle restore project from archive action"""
        self.project.archived = False
        projects = load_projects_from_json(self.logger)
        projects[self.project_id] = self.project
        save_projects_to_json(projects, self.logger)

        QMessageBox.information(
            self,
            "Success",
            f"Project '{self.project.title}' has been restored from archive."
        )

        # Go back to projects list
        self.backClicked.emit()

    def onDeleteProject(self):
        """Handle delete project action"""
        from utils.projects_io import delete_project

        reply = QMessageBox.warning(
            self,
            "Delete Project",
            f"Are you sure you want to DELETE '{self.project.title}'?\n\n"
            "⚠️ This action cannot be undone!\n\n"
            "All phases and task associations will be removed.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Double confirmation for destructive action
            confirm = QMessageBox.warning(
                self,
                "Final Confirmation",
                f"This will permanently delete '{self.project.title}'.\n\n"
                "Type the project name to confirm deletion.",
                QMessageBox.Ok | QMessageBox.Cancel,
                QMessageBox.Cancel
            )

            if confirm == QMessageBox.Ok:
                # Delete the project
                if delete_project(self.project_id, self.logger):
                    QMessageBox.information(
                        self,
                        "Success",
                        f"Project '{self.project.title}' has been deleted."
                    )

                    # Go back to projects list
                    self.backClicked.emit()
                else:
                    QMessageBox.critical(
                        self,
                        "Error",
                        "Failed to delete project. Please try again."
                    )

    def onExportProject(self):
        """Handle export project action"""
        # Open file dialog to select export location
        default_filename = f"{self.project.title.replace(' ', '_')}_export.json"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Project",
            default_filename,
            "JSON Files (*.json)"
        )

        if file_path:
            # Export the project
            success = export_project_to_json(self.project_id, file_path, self.logger)

            if success:
                QMessageBox.information(
                    self,
                    "Success",
                    f"Project '{self.project.title}' has been exported to:\n{file_path}"
                )
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    "Failed to export project. Please try again."
                )

