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
# File: projects_screen.py
# Description: Main screen for displaying and managing projects
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QGridLayout, QSpacerItem, QSizePolicy, QFrame
)
from PyQt5.QtGui import QIcon

from models.project import Project, ProjectStatus
from models.task import TaskPriority
from utils.projects_io import load_projects_from_json, create_project, save_projects_to_json
from resources.styles import AppStyles, AnimatedButton
from ui.project_files.project_card import ProjectCard


class ProjectsScreen(QWidget):
    """
    Main screen for displaying all projects in a grid layout
    """

    projectClicked = pyqtSignal(str)  # Emits project_id when clicked

    def __init__(self, logger):
        super().__init__()
        self.logger = logger
        self.projects = {}
        self.project_cards = []
        self.detail_view = None  # Will hold the detail view when shown

        self.initUI()
        self.loadProjects()

    def initUI(self):
        """Initialize the user interface"""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # Header section
        header_layout = self.createHeader()
        main_layout.addLayout(header_layout)

        # Scrollable area for project cards
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
        """)

        # Container widget for the grid
        self.container_widget = QWidget()
        self.container_layout = QVBoxLayout(self.container_widget)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(20)

        # Grid layout for project cards
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(20)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.container_layout.addLayout(self.grid_layout)

        # Empty state widget (shown when no projects exist)
        self.empty_state_widget = self.createEmptyState()
        self.container_layout.addWidget(self.empty_state_widget)

        # Add spacer to push content to top
        self.container_layout.addStretch()

        scroll_area.setWidget(self.container_widget)
        main_layout.addWidget(scroll_area)

    def createHeader(self):
        """Create the header section with title and add button"""
        header_layout = QHBoxLayout()
        header_layout.setSpacing(15)

        # Title
        title_label = QLabel("Projects")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 28px;
                font-weight: bold;
                color: #2c3e50;
            }
        """)
        header_layout.addWidget(title_label)

        # Spacer
        header_layout.addStretch()

        # Add Project Button
        self.add_project_btn = AnimatedButton("+ New Project")
        self.add_project_btn.setStyleSheet(AppStyles.add_button())
        self.add_project_btn.setFixedHeight(40)
        self.add_project_btn.clicked.connect(self.onAddProject)
        header_layout.addWidget(self.add_project_btn)

        return header_layout

    def createEmptyState(self):
        """Create the empty state widget shown when no projects exist"""
        empty_widget = QWidget()
        empty_layout = QVBoxLayout(empty_widget)
        empty_layout.setAlignment(Qt.AlignCenter)
        empty_layout.setSpacing(15)

        # Icon/Image
        icon_label = QLabel("📁")
        icon_label.setStyleSheet("""
            QLabel {
                font-size: 72px;
            }
        """)
        icon_label.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(icon_label)

        # Title
        title_label = QLabel("No Projects Yet")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #7f8c8d;
            }
        """)
        title_label.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(title_label)

        # Description
        desc_label = QLabel("Create your first project to get started")
        desc_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #95a5a6;
            }
        """)
        desc_label.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(desc_label)

        # Create button
        create_btn = AnimatedButton("+ Create Project")
        create_btn.setStyleSheet(AppStyles.add_button())
        create_btn.setFixedSize(150, 40)
        create_btn.clicked.connect(self.onAddProject)
        empty_layout.addWidget(create_btn, alignment=Qt.AlignCenter)

        empty_widget.hide()  # Hidden by default
        return empty_widget

    def loadProjects(self):
        """Load projects from JSON and display them"""
        self.projects = load_projects_from_json(self.logger)
        self.refreshUI()

    def refreshUI(self):
        """Refresh the UI to display current projects"""
        # Clear existing project cards
        self.clearGrid()
        self.project_cards.clear()

        # Check if we have projects
        if not self.projects:
            self.showEmptyState()
            return

        self.hideEmptyState()

        # Get non-archived projects
        active_projects = {
            pid: proj for pid, proj in self.projects.items()
            if not proj.archived
        }

        if not active_projects:
            self.showEmptyState()
            return

        # Sort projects by priority and creation date
        sorted_projects = sorted(
            active_projects.values(),
            key=lambda p: (p.priority.value, p.creation_date),
            reverse=True
        )

        # Add project cards to grid (3 columns)
        columns = 3
        for index, project in enumerate(sorted_projects):
            row = index // columns
            col = index % columns

            # Create project card (will implement in next task)
            card = self.createProjectCard(project)
            self.project_cards.append(card)
            self.grid_layout.addWidget(card, row, col)

    def createProjectCard(self, project):
        """Create a ProjectCard widget for the given project"""
        card = ProjectCard(project, self.logger)
        card.clicked.connect(self.onProjectCardClicked)
        return card

    def onProjectCardClicked(self, project_id):
        """Handle project card click"""
        self.logger.info(f"Project card clicked: {project_id}")
        self.showProjectDetail(project_id)

    def clearGrid(self):
        """Clear all widgets from the grid layout"""
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def showEmptyState(self):
        """Show the empty state widget"""
        self.empty_state_widget.show()

    def hideEmptyState(self):
        """Hide the empty state widget"""
        self.empty_state_widget.hide()

    def onAddProject(self):
        """
        Handle Add Project button click
        Will implement dialog in Task 2.3
        """
        from ui.project_files.project_dialog import ProjectDialog

        dialog = ProjectDialog(mode="create", logger=self.logger, parent=self)
        dialog.projectSaved.connect(self.onProjectSaved)
        dialog.exec_()

    def onProjectSaved(self, project_data):
        """Handle project saved from dialog"""
        # Create the project
        project = create_project(
            title=project_data['title'],
            description=project_data['description'],
            status=project_data['status'],
            priority=project_data['priority'],
            color=project_data['color'],
            logger=self.logger
        )

        if project_data.get('start_date'):
            project.start_date = project_data['start_date']

        if project_data.get('target_completion'):
            project.target_completion = project_data['target_completion']

        # Save the project
        self.projects[project.id] = project
        save_projects_to_json(self.projects, self.logger)

        # Refresh the UI
        self.loadProjects()

        self.logger.info(f"Project created: {project.title}")

    def showProjectDetail(self, project_id):
        """Show the detail view for a project"""
        from ui.project_files.project_detail_view import ProjectDetailView

        # Hide the container widget (projects grid)
        self.container_widget.hide()

        # Create or update detail view
        if self.detail_view:
            self.detail_view.deleteLater()

        self.detail_view = ProjectDetailView(project_id, self.logger, parent=self)
        self.detail_view.backClicked.connect(self.showProjectsList)

        # Add detail view to the main layout (before the scroll area position)
        self.layout().insertWidget(1, self.detail_view)

    def showProjectsList(self):
        """Show the projects list (hide detail view)"""
        if self.detail_view:
            self.detail_view.hide()
            self.detail_view.deleteLater()
            self.detail_view = None

        # Show the container widget (projects grid)
        self.container_widget.show()

        # Refresh projects in case changes were made in detail view
        self.loadProjects()
