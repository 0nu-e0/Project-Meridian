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
# File: dashboard_screen.py
# Description: Used to generate the grid spaces needed to display task and 
#              dialog boxes associated with tasks.
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

# Standard library imports
import json
import os
from functools import partial

# Third-party imports
from PyQt5.QtCore import QEvent, QSize, Qt, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap, QResizeEvent
from PyQt5.QtWidgets import (QComboBox, QFrame, QHBoxLayout, QLabel, QLayout, QMessageBox,
                             QPushButton, QScrollArea, QSizePolicy, QSpacerItem, QVBoxLayout, QWidget)

# Local application imports
from models.task import TaskCategory
from resources.styles import AnimatedButton, AppStyles
from ui.task_files.task_card_expanded import TaskCardExpanded
from utils.dashboard_config import DashboardConfigManager
from utils.directory_finder import resource_path
from utils.data_manager import DataManager
from .dashboard_child_view.add_task_group import AddGridDialog
from .dashboard_child_view.grid_layout import GridLayout

class DashboardScreen(QWidget):

    refreshPlanningUI =  pyqtSignal()

    def __init__(self, logger, width):
        super().__init__()

        self.logger = logger
        self.dashboard_width = width
        # Get tasks from centralized DataManager instead of loading from JSON
        self.data_manager = DataManager(self.logger)
        self.tasks = self.data_manager.get_tasks()

        # first_key = next(iter(self.tasks))
        # print(f"Task Loaded Types: {type(self.tasks[first_key])}")

        self.saved_grid_layouts = self.loadGridLayouts() or []
        self.consoles = {}
        self.taskCards = []
        self.grid_layouts = []
        self.initComplete = False

        # Initialize widget references to None for proper cleanup
        self.expanded_card = None
        self.overlay = None
        self.dialog_container = None
        self.add_group_dialog = None
        self.overlay_grid_dialog = None

        self.initUI()

        # Install event filter to handle mouse leaving the dashboard
        self.installEventFilter(self)

    def loadGridLayouts(self):
        return DashboardConfigManager.get_all_grid_layouts()

    def eventFilter(self, source, event):
        # If overlay was clicked, close dialog
        if hasattr(self, 'overlay') and self.overlay is not None and source == self.overlay and event.type() == QEvent.MouseButtonPress:
            self.dialog_container.close()
            return True

        # Collapse cards when mouse leaves the dashboard widget itself
        if event.type() == QEvent.Leave and source == self:
            for grid_layout in getattr(self, 'grid_layouts', []):
                if hasattr(grid_layout, 'collapseAllCards'):
                    grid_layout.collapseAllCards()
            # do not swallow the event unless you need to
        return super().eventFilter(source, event)


    def initUI(self):
        self.initCentralWidget()
        self.initBannerSpacer()
        self.addSeparator()
        self.initTasksLayout()
        self.addSeparator()

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
        banner_height = int(self.height()*0.15) 
        self.banner_spacer = QSpacerItem(1, banner_height, QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.banner_layout.addSpacerItem(self.banner_spacer)
        self.main_layout.addWidget(self.banner_widget)

    def addSeparator(self):
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFixedHeight(2)
        self.main_layout.addWidget(separator)

    def initLayoutGrouping(self):
        layout_group_widget = QWidget()
        self.layout_group_layout = QHBoxLayout(layout_group_widget)

    def initTasksLayout(self):
        # Create main container
        main_container = QWidget()
        main_container_layout = QVBoxLayout(main_container)
        main_container_layout.setContentsMargins(0, 0, 0, 0)
        main_container_layout.setSpacing(0)

        # Create header with project filter (ONCE, not recreated on refresh)
        self.createDashboardHeader()
        main_container_layout.addWidget(self.dashboard_header)

        # Create container for all grid layouts
        task_layout_widget = QWidget()
        task_layout_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.task_layout_container = QVBoxLayout(task_layout_widget)
        self.task_layout_container.setContentsMargins(0, 0, 0, 0)
        self.task_layout_container.setSpacing(0)

        tasks_scroll_area = QScrollArea()
        tasks_scroll_area.setStyleSheet(AppStyles.scroll_area())
        tasks_scroll_area.setWidgetResizable(True)
        tasks_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        tasks_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        tasks_scroll_area.setWidget(task_layout_widget)
        self.task_layout_container.setSizeConstraint(QLayout.SetNoConstraint)

        main_container_layout.addWidget(tasks_scroll_area)

        # Add main container to layout
        self.main_layout.addWidget(main_container)

        self.iterrateGridLayouts()

        # If no grid layouts, create at least one grid
        if not self.saved_grid_layouts:
            from uuid import uuid4
            grid_layout = GridLayout(logger=self.logger, id=str(uuid4()), tasks=self.tasks)

            # Connect signals for the default grid
            grid_layout.taskDeleted.connect(self.propagateTaskDeletion)
            grid_layout.sendTaskInCardClicked.connect(self.openExpandedCardOverlay)
            self.grid_layouts.append(grid_layout)

            self.task_layout_container.addWidget(grid_layout)
        
        self.main_layout.addWidget(tasks_scroll_area)

    def createDashboardHeader(self):
        """Create the dashboard header widget with project filter and action buttons (called once)"""
        # Main container widget
        self.dashboard_header = QWidget()
        manage_header_layout = QHBoxLayout(self.dashboard_header)
        manage_header_layout.setContentsMargins(10, 5, 10, 5)

        # Left side: Project filter
        filter_widget = QWidget()
        filter_layout = QVBoxLayout(filter_widget)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_layout.setSpacing(5)

        filter_label = QLabel("Filter by Project:")
        filter_label.setStyleSheet(AppStyles.label_bold())
        filter_layout.addWidget(filter_label)

        self.project_filter_combo = QComboBox()
        self.project_filter_combo.setStyleSheet(AppStyles.combo_box_norm())
        self.project_filter_combo.setMinimumWidth(200)
        # Connect signal ONCE here
        self.project_filter_combo.currentIndexChanged.connect(self.onProjectFilterChanged)
        filter_layout.addWidget(self.project_filter_combo)

        # Populate project filter
        self.loadProjectFilter()

        manage_header_layout.addWidget(filter_widget)

        # Right-aligned container for both rows
        buttons_widget = QWidget()
        buttons_container = QHBoxLayout(buttons_widget)
        buttons_container.setSpacing(10)
        buttons_container.setContentsMargins(0, 0, 10, 0)

        # Count non-archived tasks
        archived_tasks = 0
        for task in self.tasks.values():
            if task.category == TaskCategory.ARCHIVED:
                archived_tasks += 1

        card_count_widget = QLabel(f"Current Task Count: {len(self.tasks) - archived_tasks}")

        button_size = QSize(30, 30)

        # Task row
        task_row_widget = QWidget()
        task_row_layout = QHBoxLayout(task_row_widget)
        task_row_layout.setContentsMargins(0, 0, 0, 0)

        manage_tasks_label = QLabel("Add New Task")
        manage_tasks_label.setStyleSheet(AppStyles.label_lgfnt())

        addTaskButton = AnimatedButton("+", blur=2, x=10, y=10, offsetX=1, offsetY=1)
        addTaskButton.setStyleSheet(AppStyles.button_normal())
        addTaskButton.setFixedSize(button_size)
        addTaskButton.clicked.connect(partial(self.openExpandedCardOverlay, task=None))

        task_row_layout.addWidget(card_count_widget)
        task_row_layout.addStretch(1)
        task_row_layout.addWidget(manage_tasks_label)
        task_row_layout.addWidget(addTaskButton)

        # Group row
        group_row_widget = QWidget()
        group_row_layout = QHBoxLayout(group_row_widget)
        group_row_layout.setContentsMargins(0, 0, 0, 0)

        manage_groups_label = QLabel("Add New Group")
        manage_groups_label.setStyleSheet(AppStyles.label_lgfnt())

        addGroupsButton = AnimatedButton("+", blur=2, x=10, y=10, offsetX=1, offsetY=1)
        addGroupsButton.setStyleSheet(AppStyles.button_normal())
        addGroupsButton.setFixedSize(button_size)
        addGroupsButton.clicked.connect(self.addGroupTask)

        group_row_layout.addWidget(manage_groups_label)
        group_row_layout.addWidget(addGroupsButton)

        # Add both rows to the container
        buttons_container.addWidget(task_row_widget)
        buttons_container.addWidget(group_row_widget)

        # Push everything to the right side
        manage_header_layout.addStretch(1)
        manage_header_layout.addWidget(buttons_widget)

        # Set minimum height to prevent cutoff
        self.dashboard_header.setMinimumHeight(100)

    def iterrateGridLayouts(self):
        # Get tasks from DataManager (already loaded in memory)
        # NOTE: Accessing internal _tasks directly to avoid any method call overhead/recursion
        all_tasks = self.data_manager._tasks

        # Apply project filter if set (use local variable to avoid modifying self.tasks)
        tasks_to_display = all_tasks
        if hasattr(self, 'current_project_filter') and self.current_project_filter is not None:
            filtered_tasks = {}
            if self.current_project_filter == "no_project":
                # Show only tasks without a project
                for task_id, task in all_tasks.items():
                    if not task.project_id:
                        filtered_tasks[task_id] = task
            else:
                # Show only tasks from selected project
                for task_id, task in all_tasks.items():
                    if task.project_id == self.current_project_filter:
                        filtered_tasks[task_id] = task
            tasks_to_display = filtered_tasks

        task_categories_dict = {}

        for task in tasks_to_display.values():
            # Get category value (handle both enum and string)
            category_value = task.category.value if hasattr(task.category, 'value') else task.category
            if category_value not in task_categories_dict:
                task_categories_dict[category_value] = []

        for task in tasks_to_display.values():
            # Get category value (handle both enum and string)
            category_value = task.category.value if hasattr(task.category, 'value') else task.category
            task_categories_dict[category_value].append(task)

        # NOTE: Header is now created once in createDashboardHeader() and added to the main layout
        # This method only creates/refreshes the grid layouts below the header

        self.grid_layout_map = {}

        for idx, grid in enumerate(self.saved_grid_layouts):

            self.logger.debug(f"Adding Grids for:: {grid.name}")
            self.logger.debug(f"Grid Total: {grid}, type: {type(grid)}")
            self.logger.debug(
                f"This thing: {grid.filter.category[0]}, type: {type(grid.filter.category[0])}"
            )

            # Check if this grid category has any tasks
            if grid.filter.category and grid.filter.category[0] not in task_categories_dict:
                self.logger.debug(f"Skipping grid '{grid.name}' - no tasks in category '{grid.filter.category[0]}'")
                continue

            # Create section with title for this grid
            self.grid_section = QWidget()
            grid_section_layout = QVBoxLayout(self.grid_section)
            grid_section_layout.setContentsMargins(20, 0, 0, 0)

            # Create header with hover capability
            grid_header_widget = QWidget()
            grid_header_widget.setMouseTracking(True)
            grid_header_layout = QHBoxLayout(grid_header_widget)

            toggle_button = QPushButton("▼")
            toggle_button.setMaximumWidth(20)
            toggle_button.setMaximumHeight(20)
            toggle_button.setVisible(False)
            grid_header_layout.addWidget(toggle_button)

            # Add title for this grid
            grid_title = QLabel(grid.name)
            grid_title.setStyleSheet("font-weight: bold; font-size: 16px;")
            grid_header_layout.addWidget(grid_title)

            # Create remove button (hidden initially)
            remove_grid_button = QPushButton()
            image_path = resource_path('resources/images/delete_button.png')
            pixmap = QPixmap(image_path)
            remove_icon = QIcon(pixmap)
            remove_grid_button.setIcon(remove_icon)
            remove_grid_button.setFixedSize(QSize(15, 15))
            remove_grid_button.setIconSize(QSize(15, 15))
            remove_grid_button.setStyleSheet(AppStyles.button_transparent())
            remove_grid_button.setVisible(False)
            remove_grid_button.clicked.connect(partial(self.removeGridSection, grid.id))
            grid_header_layout.addWidget(remove_grid_button)
            grid_header_layout.addStretch(1)

            # Event handlers for hover effects
            def make_enter_event(buttons, widget):
                def custom_enter_event(event):
                    for button in buttons:
                        button.setVisible(True)
                        QWidget.enterEvent(widget, event)
                return custom_enter_event

            def make_leave_event(buttons, widget):
                def custom_leave_event(event):
                    for button in buttons:
                        button.setVisible(False)
                        QWidget.leaveEvent(widget, event)
                return custom_leave_event

            grid_header_widget.enterEvent = make_enter_event([toggle_button, remove_grid_button], grid_header_widget)
            grid_header_widget.leaveEvent = make_leave_event([toggle_button, remove_grid_button], grid_header_widget)

            # --- Restore `filter_dict` ---
            filter_dict = {
                'status': grid.filter.status if hasattr(grid.filter, 'status') and grid.filter.status else [],
                'category': grid.filter.category if hasattr(grid.filter, 'category') and grid.filter.category else [],
                'due': grid.filter.due if hasattr(grid.filter, 'due') and grid.filter.due else []
            }

            self.logger.debug(f"filter dict: {filter_dict}")

            # Create grid layout with correct filter
            grid_layout = GridLayout(logger=self.logger, id=grid.id, grid_title=grid.filter.category[0], filter=filter_dict, tasks=self.tasks)
            
            self.grid_layout_map[grid.id] = grid_layout

            # Set size policies to allow proper scrolling
            # Grid sections should size to their content
            self.grid_section.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)

            # Grid layouts should expand horizontally but size to content vertically
            grid_layout.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

            # Add components to layout
            grid_section_layout.addWidget(grid_header_widget)
            grid_section_layout.addWidget(grid_layout)

            self.grid_layouts.append(grid_layout)
            grid_layout.taskDeleted.connect(self.propagateTaskDeletion)
            grid_layout.sendTaskInCardClicked.connect(self.openExpandedCardOverlay)

            toggle_button.clicked.connect(partial(self.toggleGridVisibility, grid_layout))

            self.task_layout_container.addWidget(self.grid_section)

            if grid.minimize == "true":
                grid_layout.hide()

            # Add a small spacer between grids
            spacer = QWidget()
            spacer.setFixedHeight(10)
            self.task_layout_container.addWidget(spacer)

        # Add stretch at the end to ensure proper scrolling
        self.task_layout_container.addStretch(1)

    def removeGridSection(self, grid_id):
        """Remove the grid section with the specified ID"""
        # Ask for confirmation
        confirm = QMessageBox.question(
            self,
            "Confirm Removal",
            "Are you sure you want to remove this grid section?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if confirm == QMessageBox.Yes:
            # Get current grid layouts
            grid_layouts = DashboardConfigManager.get_all_grid_layouts()
            
            # Find and remove the grid with matching ID
            for i, grid in enumerate(grid_layouts):
                if grid.id == grid_id:
                    grid_layouts.pop(i)
                    break
            
            # Update positions for remaining grids
            for i, grid in enumerate(grid_layouts):
                grid.position = i
            
            # Save updated grid layouts
            DashboardConfigManager.save_grid_layouts(grid_layouts)
            
            # Refresh the dashboard
            self.completeSaveActions()

    def updateSingleGridLayout(self, task, grid_id):
        if grid_id not in self.grid_layout_map:
            self.logger.warning(f"No grid layout found for grid_id: {grid_id}")
            return

        # Find the updated version of the task
        updated_task = self.tasks.get(task.title)  # or use task.id or task.uuid
        if updated_task is None:
            self.logger.warning(f"Updated task not found in JSON for: {task.title}")
            return

        # Get the layout to update
        grid_layout = self.grid_layout_map[grid_id]

        # Ask the GridLayout to update just that task
        grid_layout.updateSingleTask(updated_task)


    def openExpandedCardOverlay(self, task=None, grid_id=None):
        self.logger.debug(f"running openExpandedCardOverlay with task: {task}")
        self.logger.debug(f"running openExpandedCardOverlay with grid_id: {grid_id}")
        # Get the main window as parent
        window = self.window()
        
        # Create a container widget that covers the entire main window.
        self.dialog_container = QWidget(window)
        # Make the container completely transparent so it doesn't override child styling.
        self.dialog_container.setAttribute(Qt.WA_StyledBackground, True)
        self.dialog_container.setAttribute(Qt.WA_TranslucentBackground, True)
        self.dialog_container.setStyleSheet("background-color: transparent;")
        self.dialog_container.setWindowFlags(Qt.FramelessWindowHint)
        self.dialog_container.setGeometry(window.rect())
        
        # Create the semi-transparent overlay.
        self.overlay = QWidget(self.dialog_container)
        self.overlay.setStyleSheet("background-color: rgba(0, 0, 0, 0.5);")
        self.overlay.setGeometry(self.dialog_container.rect())
        self.overlay.installEventFilter(self)

        # pass_grid_id  = self.grid_layout_map[grid_id]
        
        # Create the expanded card as a child of the container.
        self.expanded_card = TaskCardExpanded(
            logger=self.logger,
            task=task,
            grid_id=grid_id,
            parent_view=self,
            parent=self.dialog_container
        )
        self.expanded_card.saveCompleted.connect(self.completeSaveActions)
        self.expanded_card.newTaskUpdate.connect(self.completeSaveActions)
        self.expanded_card.taskDeleted.connect(self.propagateTaskDeletion)
        self.expanded_card.cancelTask.connect(self.closeExpandedCard)
        # Set the object name so the style sheet applies.
        self.expanded_card.setObjectName("card_container")
        # Enable styled backgrounds so that the style sheet paints the background.
        self.expanded_card.setAttribute(Qt.WA_StyledBackground, True)
        # Notice: We do NOT set WA_TranslucentBackground here, so that the style sheet's background color is visible.
        self.expanded_card.setStyleSheet(AppStyles.expanded_task_card())

        # Calculate optimal dimensions and center the expanded card.
        card_width, card_height = self.expanded_card.calculate_optimal_card_size(window)
        center_x = (self.dialog_container.width() - card_width) // 2
        center_y = (self.dialog_container.height() - card_height) // 2
        self.expanded_card.setGeometry(center_x, center_y, card_width, card_height)
        self.expanded_card.setWindowFlags(Qt.FramelessWindowHint)
        self.expanded_card.raise_()
        
        # Show the container (which holds both the overlay and the expanded card)
        self.dialog_container.show()

    def addGroupTask(self):
        self.overlay_grid_dialog = QWidget(self)
        self.overlay_grid_dialog.setStyleSheet("""
            QWidget {
                background-color: rgba(0, 0, 0, 0.5);
            }
        """)
        self.overlay_grid_dialog.setGeometry(self.rect())

        self.add_group_dialog = AddGridDialog(logger=self.logger)
        self.add_group_dialog.setStyleSheet(AppStyles.expanded_task_card())

        self.add_group_dialog.addGroupCancel.connect(self.cancelAddGroup)
        self.add_group_dialog.addGroupSaveSignel.connect(self.completeSaveActions)

        window = self.window()
        window_geometry = window.geometry()

        card_width, card_height = self.add_group_dialog.calculate_optimal_size()

        center_x = window_geometry.x() + (window_geometry.width() - card_width) // 2
        center_y = window_geometry.y() + (window_geometry.height() - card_height) // 2
        
        self.add_group_dialog.setGeometry(center_x, center_y, card_width, card_height)

        #self.overlay_grid_dialog.show()
        self.add_group_dialog.show()

        self.overlay_grid_dialog.installEventFilter(self)
        self.overlay_grid_dialog.mousePressEvent = self.cancelAddGroup

    def cancelAddGroup(self, event=None):
        """Clean up add group dialog and overlay"""
        if hasattr(self, 'add_group_dialog') and self.add_group_dialog is not None:
            self.add_group_dialog.close()
            self.add_group_dialog.deleteLater()
            self.add_group_dialog = None
        if hasattr(self, 'overlay_grid_dialog') and self.overlay_grid_dialog is not None:
            self.overlay_grid_dialog.close()
            self.overlay_grid_dialog.deleteLater()
            self.overlay_grid_dialog = None

    def saveAddGroup(self):
        pass

    # In Dashboard class
    def propagateTaskDeletion(self, task_title):
        """Propagate task deletion to all grid layouts"""
        for grid_layout in self.grid_layouts:
            # Each grid layout should handle whether it contains this task
            grid_layout.removeTaskCard(task_title)

        # Close the expanded card
        self.closeExpandedCard()

    def checkAndPromptMissingCategory(self, task):
        """
        Check if the task's category has a corresponding grid in the dashboard.
        If not, prompt the user to add a grid for that category.

        Args:
            task: The task object that was just saved
        """
        if task is None or not hasattr(task, 'category'):
            return

        task_category = task.category.value

        # Check if any grid has this category in its filter
        category_exists = False
        for grid in self.saved_grid_layouts:
            if hasattr(grid.filter, 'category') and task_category in grid.filter.category:
                category_exists = True
                break

        # If category doesn't exist in any grid, prompt user
        if not category_exists:
            reply = QMessageBox.question(
                self,
                'Add Category Group?',
                f'The category "{task_category}" is not displayed in the dashboard.\n\n'
                f'Would you like to add a group for this category so the task will be visible?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )

            if reply == QMessageBox.Yes:
                # Create a new grid for this category
                new_grid_id = DashboardConfigManager.add_grid_layout(
                    name=f"{task_category} Tasks",
                    columns=3
                )

                # Update the grid's category filter to include this category
                DashboardConfigManager.update_grid_filter(
                    new_grid_id,
                    'category',
                    [task_category]
                )

                # Reload grid layouts to include the new one
                self.saved_grid_layouts = self.loadGridLayouts() or []

                # Show success message
                QMessageBox.information(
                    self,
                    'Group Added',
                    f'A new group for "{task_category}" has been added to the dashboard.'
                )

    def completeSaveActions(self, task=None, grid_id=None):
        self.logger.debug("closing layouts")
        self.saved_grid_layouts = self.loadGridLayouts() or []
        # Get updated tasks from DataManager
        self.tasks = self.data_manager.get_tasks()

        # Check if the saved task's category has a corresponding grid
        if task is not None:
            self.checkAndPromptMissingCategory(task)

        # Always do a full refresh to handle category changes
        # (task may have moved to a different grid if category changed)
        self.clear_layout(self.task_layout_container)
        self.grid_layouts = []  # Clear the grid_layouts list before rebuilding
        self.iterrateGridLayouts()
        self.refreshPlanningUI.emit()
        self.closeExpandedCard()

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            elif item.layout() is not None:
                self.clear_layout(item.layout())
            # else: it's a spacer item, just discard it 

    def closeExpandedCard(self, event=None):
        if hasattr(self, 'expanded_card') and self.expanded_card is not None:
            self.logger.debug("Closing expanded card")
            self.expanded_card.close()
            self.expanded_card.deleteLater()
            self.expanded_card = None
        if hasattr(self, 'overlay') and self.overlay is not None:
            self.logger.debug("Closing overlay")
            self.overlay.removeEventFilter(self)
            self.overlay.close()
            self.overlay.deleteLater()
            self.overlay = None
        if hasattr(self, 'dialog_container') and self.dialog_container is not None:
            self.logger.debug("Closing dialog container")
            self.dialog_container.close()
            self.dialog_container.deleteLater()
            self.dialog_container = None
        self.logger.debug("Cleanup complete")

    def loadProjectFilter(self):
        """Load projects into the filter dropdown"""
        # Add "All Projects" option first
        self.project_filter_combo.addItem("All Projects", None)

        # Get all projects from DataManager
        try:
            all_projects = self.data_manager.get_projects()

            # Add all non-archived projects
            for project_id, project in all_projects.items():
                if not project.archived:
                    self.project_filter_combo.addItem(project.title, project_id)

            # Add "Tasks without Project" option
            self.project_filter_combo.addItem("Tasks without Project", "no_project")

        except Exception as e:
            self.logger.error(f"Error loading projects for filter: {e}")

        # Default to "All Projects"
        self.project_filter_combo.setCurrentIndex(0)

    def onProjectFilterChanged(self, index):
        """Handle project filter change - reload dashboard with filtered tasks"""
        selected_project_id = self.project_filter_combo.itemData(index)

        # Store the filter selection
        self.current_project_filter = selected_project_id

        # Reload the dashboard with the filter applied
        self.refreshDashboard()

    def refreshDashboard(self):
        """Reload and refresh the entire dashboard"""
        # Guard against re-entrant calls
        if hasattr(self, '_refreshing') and self._refreshing:
            return

        self._refreshing = True
        try:
            # Clear existing grid layouts
            while self.task_layout_container.count():
                child = self.task_layout_container.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

            # Reload grid layouts with current filter
            self.iterrateGridLayouts()
        finally:
            self._refreshing = False

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        for grid in getattr(self, 'grid_layouts', []):
            grid.rearrangeGridLayout()

    def toggleGridVisibility(self, grid_layout):
        
        if grid_layout.isVisible():
            properties = {"minimize": "true"}
            DashboardConfigManager.update_grid_properties(grid_layout.grid_id, properties=properties)
            grid_layout.hide()
        else:
            properties = {"minimize": "false"}
            DashboardConfigManager.update_grid_properties(grid_layout.grid_id, properties=properties)
            grid_layout.show()
   
