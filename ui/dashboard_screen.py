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

import os, json
from resources.styles import AppStyles, AnimatedButton
from utils.tasks_io import load_tasks_from_json
from utils.directory_finder import resource_path
from utils.dashboard_config import DashboardConfigManager
from models.task import Task, TaskCategory, TaskPriority, TaskEntry, TaskStatus
from .dashboard_child_view.grid_layout import GridLayout
from .dashboard_child_view.add_task_group import AddGridDialog
from ui.task_files.task_card_expanded import TaskCardExpanded
from PyQt5.QtWidgets import (QDesktopWidget, QApplication, QWidget, QVBoxLayout, QHBoxLayout, QFrame, QScrollArea,
                             QSpacerItem, QLabel, QSizePolicy, QStackedWidget, QGridLayout, QPushButton, QMessageBox,
                             QLayout, )
from PyQt5.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect, QTimer, pyqtSlot, QSize, QEvent
from PyQt5.QtGui import QResizeEvent, QPixmap, QIcon

class DashboardScreen(QWidget):
    sendTaskInCardClicked = pyqtSignal(object)
    savecomplete = pyqtSignal()

    def __init__(self, logger, width):
        super().__init__()

        self.logger = logger
        self.dashboard_width = width
        self.tasks = load_tasks_from_json(self.logger)

        # first_key = next(iter(self.tasks))
        # print(f"Task Loaded Types: {type(self.tasks[first_key])}")



        self.saved_grid_layouts = self.loadGridLayouts() or []
        # for grid in self.saved_grid_layouts:
            # print(f"Grid: {grid.id} - {grid.name}")
        self.consoles = {}
        self.taskCards = []
        self.grid_layouts = []
        self.initComplete = False
        self.initUI()

    def loadGridLayouts(self):
        return DashboardConfigManager.get_all_grid_layouts()
    
    
    
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
        # Create container for all grid layouts
        task_layout_widget = QWidget()
        self.task_layout_container = QVBoxLayout(task_layout_widget)
        self.task_layout_container.setContentsMargins(0, 0, 0, 0)
        tasks_scroll_area = QScrollArea()
        tasks_scroll_area.setStyleSheet(AppStyles.scroll_area())
        tasks_scroll_area.setWidgetResizable(True)
        tasks_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        tasks_scroll_area.setWidget(task_layout_widget)
        self.task_layout_container.setSizeConstraint(QLayout.SetNoConstraint)


        self.iterrateGridLayouts()

        # If no grid layouts, create at least one grid
        if not self.saved_grid_layouts:
            grid_layout = GridLayout(logger=self.logger, tasks=self.tasks)
            self.task_layout_container.addWidget(grid_layout)
        
        self.main_layout.addWidget(tasks_scroll_area)

    def iterrateGridLayouts(self):
        # Reload tasks and build category dictionary
        self.tasks = load_tasks_from_json(self.logger)
        # filtered_tasks = {}
        # for idx, grid in enumerate(self.saved_grid_layouts):
        #     filtered_tasks[grid.filter.category if hasattr(grid.filter, 'category') and grid.filter.category else []] = []

        task_categories_dict = {}

        for task in self.tasks.values():
            if task.category not in task_categories_dict:
                task_categories_dict[task.category.value] = []  # Use .value instead of .name

        for task in self.tasks.values():
            task_categories_dict[task.category.value].append(task)

        self.logger.debug(f"Task Category Dict: {task_categories_dict}")

        # Main container widget
        manage_header_widget = QWidget()
        manage_header_layout = QHBoxLayout(manage_header_widget)
        manage_header_layout.setContentsMargins(10, 5, 10, 5)
        
        # Right-aligned container for both rows
        buttons_widget = QWidget()
        buttons_container = QHBoxLayout(buttons_widget)
        buttons_container.setSpacing(10)
        buttons_container.setContentsMargins(0, 0, 10, 0)

        archived_tasks = 0
        for task, archived in self.tasks.items():
            if archived.category == TaskCategory.ARCHIVED:
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
        addTaskButton.setFixedSize(button_size)  # Set fixed size
        addTaskButton.clicked.connect(lambda: self.addNewTask(task=None))
        
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
        addGroupsButton.clicked.connect(lambda: self.addGroupTask())
        
        group_row_layout.addWidget(manage_groups_label)
        group_row_layout.addWidget(addGroupsButton)
        
        # Add both rows to the container
        buttons_container.addWidget(task_row_widget)
        buttons_container.addWidget(group_row_widget)
        
        # Push everything to the right side
        manage_header_layout.addStretch(1)
        manage_header_layout.addWidget(buttons_widget)
        
        # Set minimum height to prevent cutoff
        manage_header_widget.setMinimumHeight(100)
        
        self.task_layout_container.addWidget(manage_header_widget)

        for idx, grid in enumerate(self.saved_grid_layouts):
            

            self.logger.debug(f"Adding Grids for:: {grid.name}")
            self.logger.debug(f"Grid Total: {grid}, type: {type(grid)}")
            self.logger.debug(
                f"This thing: {grid.filter.category[0]}, type: {type(grid.filter.category[0])}"
            )
            

            if grid.filter.category[0] not in task_categories_dict:
                continue

            # Create section with title for this grid
            grid_section = QWidget()
            grid_section_layout = QVBoxLayout(grid_section)
            grid_section_layout.setContentsMargins(20, 0, 0, 0)

            # Create header with hover capability
            grid_header_widget = QWidget()
            grid_header_widget.setMouseTracking(True)
            grid_header_layout = QHBoxLayout(grid_header_widget)

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
            remove_grid_button.clicked.connect(lambda checked, g_id=grid.id: self.removeGridSection(g_id))
            grid_header_layout.addWidget(remove_grid_button)
            grid_header_layout.addStretch(1)

            # Event handlers for hover effects
            def make_enter_event(button, widget):
                def custom_enter_event(event):
                    button.setVisible(True)
                    QWidget.enterEvent(widget, event)
                return custom_enter_event

            def make_leave_event(button, widget):
                def custom_leave_event(event):
                    button.setVisible(False)
                    QWidget.leaveEvent(widget, event)
                return custom_leave_event

            grid_header_widget.enterEvent = make_enter_event(remove_grid_button, grid_header_widget)
            grid_header_widget.leaveEvent = make_leave_event(remove_grid_button, grid_header_widget)

            # --- Restore `filter_dict` ---
            filter_dict = {
                'status': grid.filter.status if hasattr(grid.filter, 'status') and grid.filter.status else [],
                'category': grid.filter.category if hasattr(grid.filter, 'category') and grid.filter.category else [],
                'due': grid.filter.due if hasattr(grid.filter, 'due') and grid.filter.due else []
            }

            self.logger.debug(f"filter dict: {filter_dict}")



            # Create grid layout with correct filter
            grid_layout = GridLayout(logger=self.logger, grid_title=grid.filter.category[0], filter=filter_dict, tasks=self.tasks)
            
            # --- Fix Resizing Issues ---
            if idx == 0:  # First grid (top one) should never resize
                grid_section.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            else:  # Allow lower grids to expand downward
                grid_section.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)

            # Ensure grid resizes only when needed
            grid_layout.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

            # Add components to layout
            grid_section_layout.addWidget(grid_header_widget)
            grid_section_layout.addWidget(grid_layout)

            self.grid_layouts.append(grid_layout)
            grid_layout.taskDeleted.connect(self.propagateTaskDeletion)
            grid_layout.sendTaskInCardClicked.connect(self.addNewTask)

            self.task_layout_container.addWidget(grid_section)

            # Add a small spacer between grids
            spacer = QWidget()
            spacer.setFixedHeight(10)
            self.task_layout_container.addWidget(spacer)


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

    def addNewTask(self, task=None):
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
        
        # Create the expanded card as a child of the container.
        self.expanded_card = TaskCardExpanded(
            logger=self.logger,
            task=task,
            parent_view=self,
            parent=self.dialog_container
        )
        self.expanded_card.saveCompleted.connect(self.closeExpandedCard)
        self.expanded_card.newTaskUpdate.connect(self.completeSaveActions)
        # Set the object name so the style sheet applies.
        self.expanded_card.setObjectName("card_container")
        # Enable styled backgrounds so that the style sheet paints the background.
        self.expanded_card.setAttribute(Qt.WA_StyledBackground, True)
        # Notice: We do NOT set WA_TranslucentBackground here, so that the style sheet's background color is visible.
        self.expanded_card.setStyleSheet(AppStyles.expanded_task_card())
        
        # Calculate optimal dimensions and center the expanded card.
        card_width, card_height = self.expanded_card.calculate_optimal_card_size()
        center_x = (self.dialog_container.width() - card_width) // 2
        center_y = (self.dialog_container.height() - card_height) // 2
        self.expanded_card.setGeometry(center_x, center_y, card_width, card_height)
        self.expanded_card.setWindowFlags(Qt.FramelessWindowHint)
        self.expanded_card.raise_()
        
        # Show the container (which holds both the overlay and the expanded card)
        self.dialog_container.show()
    
    def eventFilter(self, source, event):
        if hasattr(self, 'overlay') and source == self.overlay and event.type() == QEvent.MouseButtonPress:
            self.dialog_container.close()
            return True
        return super().eventFilter(source, event)


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

    def cancelAddGroup(self, event=None):  # Add event parameter with default value
        if hasattr(self, 'add_group_dialog'):
            self.add_group_dialog.close()
            self.add_group_dialog.deleteLater()
            delattr(self, 'add_group_dialog')  # Remove the attribute
        if hasattr(self, 'overlay_grid_dialog'):
            self.overlay_grid_dialog.close()
            self.overlay_grid_dialog.deleteLater()
            delattr(self, 'overlay_grid_dialog')  # Remove the attribute

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

    def completeSaveActions(self):
        self.logger.debug("closing layouts")
        self.loadGridLayouts()
        self.clear_layout(self.task_layout_container)
        self.iterrateGridLayouts()
        self.closeExpandedCard()

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()  # Properly delete the widget
            else:
                self.clear_layout(item.layout()) 

    def closeExpandedCard(self, event=None):
        if hasattr(self, 'expanded_card'):
            self.expanded_card.close()
            self.expanded_card.deleteLater()
            delattr(self, 'expanded_card')
        if hasattr(self, 'overlay'):
            self.overlay.removeEventFilter(self) 
            self.overlay.close()
            self.overlay.deleteLater()
            delattr(self, 'overlay')
        if hasattr(self, 'dialog_container'):
            self.dialog_container.close()
            self.dialog_container.deleteLater()
            delattr(self, 'dialog_container')
        self.logger.debug("Done")

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        for grid in getattr(self, 'grid_layouts', []):
            grid.rearrangeGridLayout()
            print("resizing card layout")
