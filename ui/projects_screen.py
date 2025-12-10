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
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QGridLayout, QFrame, QPushButton,
    QLineEdit, QComboBox, QCheckBox, QFileDialog, QMessageBox
)

from models.project import ProjectStatus
from models.task import TaskPriority
from utils.projects_io import (
    load_projects_from_json, create_project,
    import_project_from_json
)
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
        self.search_text = ""
        self.filter_status = "All"
        self.filter_priority = "All"
        self.show_archived = False

        self.initUI()
        self.loadProjects()

    def initUI(self):
        """Initialize the user interface"""
        # Main layout - similar to dashboard
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Banner header
        self.initBannerHeader()

        # Separator
        self.addSeparator()

        # Filter section
        self.initFilterSection()

        # Separator
        self.addSeparator()

        # Scrollable content area
        self.initContentArea()

    def initBannerHeader(self):
        """Create banner header like dashboard"""
        banner_widget = QWidget()
        banner_widget.setStyleSheet("background-color: #2E2F73;")  # Purple banner
        banner_layout = QHBoxLayout(banner_widget)
        banner_layout.setContentsMargins(20, 15, 20, 15)
        banner_layout.setSpacing(15)

        # Title with icon
        title_label = QLabel("📋 Projects")
        title_label.setStyleSheet(AppStyles.banner_header())
        banner_layout.addWidget(title_label)

        # Spacer
        banner_layout.addStretch()

        # Import button
        self.import_project_btn = AnimatedButton("📥 Import")
        self.import_project_btn.setStyleSheet(AppStyles.button_normal())
        self.import_project_btn.setFixedHeight(40)
        self.import_project_btn.clicked.connect(self.onImportProject)
        banner_layout.addWidget(self.import_project_btn)

        # Add Project button
        self.add_project_btn = AnimatedButton("+ New Project")
        self.add_project_btn.setStyleSheet(AppStyles.add_button())
        self.add_project_btn.setFixedHeight(40)
        self.add_project_btn.clicked.connect(self.onAddProject)
        banner_layout.addWidget(self.add_project_btn)

        self.main_layout.addWidget(banner_widget)

    def addSeparator(self):
        """Add separator line like dashboard"""
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFixedHeight(2)
        separator.setStyleSheet("background-color: #00FFB2;")  # Cyan separator
        self.main_layout.addWidget(separator)

    def initFilterSection(self):
        """Create filter controls section"""
        filter_widget = QWidget()
        filter_widget.setStyleSheet("background-color: #13151A;")  # Dark accent background
        filter_layout = QHBoxLayout(filter_widget)
        filter_layout.setContentsMargins(20, 15, 20, 15)
        filter_layout.setSpacing(15)

        # Search box
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 Search projects...")
        self.search_box.setStyleSheet("""
            QLineEdit {
                background-color: #34495e;
                border: 2px solid #3498db;
                border-radius: 5px;
                padding: 8px 12px;
                color: #ecf0f1;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 2px solid #5dade2;
            }
            QLineEdit::placeholder {
                color: #7f8c8d;
            }
        """)
        self.search_box.setFixedWidth(300)
        self.search_box.setFixedHeight(36)
        self.search_box.textChanged.connect(self.onSearchTextChanged)
        filter_layout.addWidget(self.search_box)

        # Status filter
        status_label = QLabel("Status:")
        status_label.setStyleSheet(AppStyles.label_bold())
        filter_layout.addWidget(status_label)

        self.status_filter = QComboBox()
        self.status_filter.addItem("All")
        for status in ProjectStatus:
            self.status_filter.addItem(status.value)
        self.status_filter.setStyleSheet("""
            QComboBox {
                background-color: #34495e;
                border: 2px solid #3498db;
                border-radius: 5px;
                padding: 6px 10px;
                color: #ecf0f1;
                font-size: 13px;
            }
            QComboBox:hover {
                border: 2px solid #5dade2;
            }
            QComboBox::drop-down {
                width: 20px;
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid #ecf0f1;
                margin-right: 5px;
            }
            QComboBox QAbstractItemView {
                background-color: #2c3e50;
                border: 2px solid #3498db;
                selection-background-color: #3498db;
                color: #ecf0f1;
                padding: 4px;
            }
        """)
        self.status_filter.setFixedHeight(36)
        self.status_filter.setMinimumWidth(140)
        self.status_filter.currentTextChanged.connect(self.onStatusFilterChanged)
        filter_layout.addWidget(self.status_filter)

        # Priority filter
        priority_label = QLabel("Priority:")
        priority_label.setStyleSheet(AppStyles.label_bold())
        filter_layout.addWidget(priority_label)

        self.priority_filter = QComboBox()
        self.priority_filter.addItem("All")
        for priority in TaskPriority:
            self.priority_filter.addItem(priority.name)
        self.priority_filter.setStyleSheet("""
            QComboBox {
                background-color: #34495e;
                border: 2px solid #3498db;
                border-radius: 5px;
                padding: 6px 10px;
                color: #ecf0f1;
                font-size: 13px;
            }
            QComboBox:hover {
                border: 2px solid #5dade2;
            }
            QComboBox::drop-down {
                width: 20px;
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid #ecf0f1;
                margin-right: 5px;
            }
            QComboBox QAbstractItemView {
                background-color: #2c3e50;
                border: 2px solid #3498db;
                selection-background-color: #3498db;
                color: #ecf0f1;
                padding: 4px;
            }
        """)
        self.priority_filter.setFixedHeight(36)
        self.priority_filter.setMinimumWidth(140)
        self.priority_filter.currentTextChanged.connect(self.onPriorityFilterChanged)
        filter_layout.addWidget(self.priority_filter)

        # Show archived checkbox
        self.archived_checkbox = QCheckBox("Show Archived")
        self.archived_checkbox.setStyleSheet("""
            QCheckBox {
                color: #ecf0f1;
                font-size: 13px;
                font-weight: bold;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #3498db;
                border-radius: 3px;
                background-color: #34495e;
            }
            QCheckBox::indicator:checked {
                background-color: #3498db;
                border-color: #3498db;
            }
            QCheckBox::indicator:hover {
                border: 2px solid #5dade2;
            }
        """)
        self.archived_checkbox.stateChanged.connect(self.onArchivedCheckboxChanged)
        filter_layout.addWidget(self.archived_checkbox)

        # Spacer
        filter_layout.addStretch()

        # Clear filters button
        clear_btn = AnimatedButton("Clear Filters")
        clear_btn.setStyleSheet(AppStyles.button_normal())
        clear_btn.setFixedHeight(36)
        clear_btn.clicked.connect(self.onClearFilters)
        filter_layout.addWidget(clear_btn)

        self.main_layout.addWidget(filter_widget)

    def initContentArea(self):
        """Create scrollable content area"""
        # Scroll area with AppStyles
        scroll_area = QScrollArea()
        scroll_area.setStyleSheet(AppStyles.scroll_area())
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Container widget
        self.container_widget = QWidget()
        self.container_widget.setStyleSheet(AppStyles.background_color())
        self.container_layout = QVBoxLayout(self.container_widget)
        self.container_layout.setContentsMargins(20, 20, 20, 20)
        self.container_layout.setSpacing(20)

        # Grid layout for project cards
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(20)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.container_layout.addLayout(self.grid_layout)

        # Empty state widget
        self.empty_state_widget = self.createEmptyState()
        self.container_layout.addWidget(self.empty_state_widget)

        # Add spacer
        self.container_layout.addStretch()

        scroll_area.setWidget(self.container_widget)
        self.main_layout.addWidget(scroll_area)

    def createEmptyState(self):
        """Create empty state widget"""
        empty_widget = QWidget()
        empty_widget.setStyleSheet(AppStyles.background_color())
        empty_layout = QVBoxLayout(empty_widget)
        empty_layout.setAlignment(Qt.AlignCenter)
        empty_layout.setSpacing(20)

        # Icon
        icon_label = QLabel("📋")
        icon_label.setStyleSheet("font-size: 80px;")
        icon_label.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(icon_label)

        # Title
        title_label = QLabel("No Projects Yet")
        title_label.setStyleSheet(AppStyles.label_lgfnt_bold())
        title_label.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(title_label)

        # Description
        desc_label = QLabel("Create your first project to get started")
        desc_label.setStyleSheet(AppStyles.label_small())
        desc_label.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(desc_label)

        # Create button
        create_btn = AnimatedButton("+ Create Project")
        create_btn.setStyleSheet(AppStyles.add_button())
        create_btn.setFixedSize(150, 40)
        create_btn.clicked.connect(self.onAddProject)
        empty_layout.addWidget(create_btn, alignment=Qt.AlignCenter)

        empty_widget.hide()
        return empty_widget

    def loadProjects(self):
        """Load projects from storage"""
        self.projects = load_projects_from_json(self.logger)
        self.displayProjects()

    def displayProjects(self):
        """Display project cards in grid"""
        # Clear existing cards
        for card in self.project_cards:
            card.deleteLater()
        self.project_cards.clear()

        # Clear grid layout
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Apply filters
        filtered_projects = self.applyFilters()

        # Show/hide empty state
        if not filtered_projects:
            self.empty_state_widget.show()
            return
        else:
            self.empty_state_widget.hide()

        # Create cards
        cols = 3
        for idx, project in enumerate(filtered_projects):
            row = idx // cols
            col = idx % cols

            card = ProjectCard(project, self.logger)
            card.clicked.connect(lambda pid=project.id: self.onProjectClicked(pid))

            self.grid_layout.addWidget(card, row, col)
            self.project_cards.append(card)

    def applyFilters(self):
        """Apply search and filter criteria"""
        filtered = []

        for project in self.projects.values():
            # Archived filter
            if project.archived and not self.show_archived:
                continue

            # Search filter
            if self.search_text:
                search_lower = self.search_text.lower()
                if (search_lower not in project.title.lower() and
                    search_lower not in project.description.lower()):
                    continue

            # Status filter
            if self.filter_status != "All":
                if project.status.value != self.filter_status:
                    continue

            # Priority filter
            if self.filter_priority != "All":
                if project.priority.name != self.filter_priority:
                    continue

            filtered.append(project)

        # Sort by creation date (most recent first)
        filtered.sort(key=lambda p: p.creation_date, reverse=True)
        return filtered

    def onSearchTextChanged(self, text):
        """Handle search text changes"""
        self.search_text = text
        self.displayProjects()

    def onStatusFilterChanged(self, status):
        """Handle status filter changes"""
        self.filter_status = status
        self.displayProjects()

    def onPriorityFilterChanged(self, priority):
        """Handle priority filter changes"""
        self.filter_priority = priority
        self.displayProjects()

    def onArchivedCheckboxChanged(self, state):
        """Handle archived checkbox changes"""
        self.show_archived = state == Qt.Checked
        self.displayProjects()

    def onClearFilters(self):
        """Clear all filters"""
        self.search_box.setText("")
        self.status_filter.setCurrentIndex(0)
        self.priority_filter.setCurrentIndex(0)
        self.archived_checkbox.setChecked(False)
        self.search_text = ""
        self.filter_status = "All"
        self.filter_priority = "All"
        self.show_archived = False
        self.displayProjects()

    def onAddProject(self):
        """Handle add project button click"""
        from ui.project_files.project_dialog import ProjectDialog

        dialog = ProjectDialog(self.logger, self)
        if dialog.exec_():
            project_data = dialog.getProjectData()
            if project_data:
                # Create project
                project = create_project(
                    title=project_data['title'],
                    description=project_data['description'],
                    status=project_data['status'],
                    priority=project_data['priority'],
                    color=project_data['color'],
                    logger=self.logger
                )

                if project:
                    self.logger.info(f"Created project: {project.title}")
                    self.loadProjects()

                    # Show success message
                    QMessageBox.information(
                        self,
                        "Success",
                        f"Project '{project.title}' created successfully!"
                    )

    def onImportProject(self):
        """Handle import project button click"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Project",
            "",
            "JSON Files (*.json)"
        )

        if file_path:
            try:
                new_project_id = import_project_from_json(file_path, self.logger)
                if new_project_id:
                    self.loadProjects()
                    QMessageBox.information(
                        self,
                        "Success",
                        "Project imported successfully!"
                    )
                else:
                    QMessageBox.warning(
                        self,
                        "Import Failed",
                        "Failed to import project. Check the log for details."
                    )
            except Exception as e:
                self.logger.error(f"Error importing project: {e}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Error importing project: {str(e)}"
                )

    def onProjectClicked(self, project_id):
        """Handle project card click"""
        self.projectClicked.emit(project_id)

    def refreshProjects(self):
        """Refresh the projects display"""
        self.loadProjects()
