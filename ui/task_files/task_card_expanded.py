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
# File: task_card_expanded.py
# Description: Used to view and modify tasks. 
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

import sys, os, json, copy
from utils.tasks_io import load_tasks_from_json, save_task_to_json
from datetime import datetime
from pathlib import Path
from functools import partial
from utils.directory_finder import resource_path
from models.task import Task, TaskCategory, TaskPriority, TaskStatus, Attachment, TaskEntry, TimeLog
from ui.custom_widgets.collapsable_section import CollapsibleSection
from resources.styles import AppColors
from resources.styles import AppStyles, AnimatedButton
from ui.task_files.task_settings_menu import TaskSettingsMenu
from PyQt5.QtWidgets import (QApplication, QDesktopWidget, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSpacerItem, 
                             QSizePolicy, QGridLayout, QPushButton, QGraphicsDropShadowEffect, QStyle, QComboBox, QTextEdit,
                             QDateTimeEdit, QLineEdit, QCalendarWidget, QToolButton, QSpinBox, QListWidget, QTabWidget,
                             QMessageBox, QInputDialog, QListWidgetItem, QScrollArea, QTreeWidget, QTreeWidgetItem, QFileDialog,
                             QStyleFactory, QListView, QLayout
                             )
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QEvent, QSize, QDateTime, QUrl, QTimer
from PyQt5.QtGui import (QColor, QPainter, QBrush, QPen, QMovie, QTextCharFormat, QColor, QIcon, QPixmap, QDesktopServices,
                            QGuiApplication, QResizeEvent,
                        )
from PyQt5.QtSvg import QSvgWidget

class TaskCardExpanded(QWidget):
    taskDeleted = pyqtSignal(str) 
    saveCompleted = pyqtSignal(str) 
    cancelTask = pyqtSignal()
    newTaskUpdate = pyqtSignal(object, str)
    
    @classmethod
    def calculate_optimal_card_size(cls):
        screen = QGuiApplication.primaryScreen().availableGeometry()
        screen_width, screen_height = screen.width(), screen.height()

        min_width = 600
        min_height_for_content = 120

        card_width = int(max(min_width, screen_width * 0.6))
        card_height = int(max(int(card_width / 1.5), min_height_for_content))
        # Optional: clamp very tall screens
        card_height = min(card_height, int(screen_height * 0.9))
        return card_width, card_height

    def __init__(self, logger, task=None, grid_id=None, parent_view=None, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.logger = logger
        self.task = task
        self.grid_id = grid_id
        print(f"Expanded card grid_id: {self.grid_id}")
        self.parent_view = parent_view
        self.initial_state = None
        self.isNewTask = False
        if self.task is not None:
            self.store_initial_task_state()
        else: 
            self.task = Task(
                title=""
            )
            self.isNewTask = True

        self._dirty = False
        self._initial_snapshot = None   # dict
        self._changes = {} 

        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setWindowModality(Qt.ApplicationModal)
        self.setObjectName("card_container")

        self.settingsOverlay = None

        screen = QGuiApplication.screenAt(self.geometry().center())
        if not screen:
            screen = QGuiApplication.primaryScreen()
        self._current_screen = screen
        self._current_dpi = screen.logicalDotsPerInch()

        self.initUI()

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        self.checkForDPIChange()

    def checkForDPIChange(self):
        """Check if we've moved to a screen with different DPI and update text accordingly"""
        screen = QGuiApplication.screenAt(self.geometry().center())
        
        if not screen:
            return
        
        new_dpi = screen.logicalDotsPerInch()
        
        # Check if screen or DPI has changed
        if not hasattr(self, '_current_dpi'):
            self._current_dpi = new_dpi
            self._current_screen = screen
            return
        
        if screen != self._current_screen or abs(new_dpi - self._current_dpi) > 1:
            self.logger.debug(f"DPI changed from {self._current_dpi} to {new_dpi}")
            self._current_dpi = new_dpi
            self._current_screen = screen
            self.refreshTextForDPI()

    def refreshTextForDPI(self):
        """Refresh all text elements to match the new screen's DPI"""
        # Force reapply all stylesheets to recalculate font sizes
        self.style().unpolish(self)
        self.style().polish(self)
        
        # Update all child widgets
        for widget in self.findChildren(QWidget):
            widget.style().unpolish(widget)
            widget.style().polish(widget)
        
        # Force a complete update
        self.updateGeometry()
        self.update()

    def store_initial_task_state(self):
        """Store the initial state of the task so we can restore it on cancel"""
        task = self.task
        print(task)
        self.initial_state = {
            'description': task.description,
            'status': task.status,
            'priority': task.priority,
            'percentage_complete': task.percentage_complete,
            'start_date': task.start_date,
            'due_date': task.due_date,
            'estimated_hours': task.estimated_hours,
            'assignee': task.assignee,
            'dependencies': set(task.dependencies) if task.dependencies else set(),
            'collaborators': set(task.collaborators) if task.collaborators else set(),
            'entries': list(task.entries), 
            'time_logs': list(task.time_logs),  
            'attachments': list(task.attachments),
            'checklist': list(self.task.checklist)
        }
        
    def initUI(self):
        self.initCentralWidget()
        self.initLeftPanelWidget()
        self.initRightPanelWidget()

    def initCentralWidget(self):
        central_widget = QWidget()
        central_widget.setObjectName("card_container")
        self.setObjectName("card_container")
        central_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.main_layout = QHBoxLayout(self)
        # central_widget.setStyleSheet(AppStyles.expanded_task_card())
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.setLayout(self.main_layout)

    def initLeftPanelWidget(self):
        main_widget = QWidget()
        main_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        left_layout = QVBoxLayout(main_widget)
        left_layout.setContentsMargins(15, 15, 0 , 0)
        left_layout.addLayout(self.createTitleSection(), 1)
        left_layout.addLayout(self.createDescriptionSection(), 2)
        left_layout.addWidget(self.createActivitySection(), 5)

        self.main_layout.addWidget(main_widget,stretch=3)

    def initRightPanelWidget(self):
        main_widget = QWidget()
        main_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        right_layout = QVBoxLayout(main_widget)
        right_layout.setContentsMargins(0, 15, 15, 0)

        right_layout.addLayout(self.createStatusPrioritySection())
        right_layout.addLayout(self.initCollapsableSections())
        right_layout.addLayout(self.createCategorySection())
        #right_layout.addStretch(1)
        right_layout.addLayout(self.createButtonSection())
        
        self.main_layout.addWidget(main_widget, stretch=2)

    def createTitleSection(self):
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 5, 0)
        title_edit = QLineEdit(self.task.title if self.task is not None else "")
        title_edit.setPlaceholderText("Set task name")
        title_edit.setStyleSheet(AppStyles.line_edit_norm())

        title_edit.editingFinished.connect(lambda: self.updateTaskTitle(title_edit.text()))

        title_layout.addWidget(title_edit)
        return title_layout
    
    def updateTaskTitle(self, new_title):
        """Update the task title in memory"""
        if self.task is not None:
            self.task.title = new_title

    def createStatusPrioritySection(self):
        status_priority_layout = QHBoxLayout()
        status_priority_layout.setContentsMargins(0, 0, 5, 0)
        
        status_widget = QWidget()
        status_layout = QHBoxLayout(status_widget)
        priority_widget = QWidget()
        priority_layout = QHBoxLayout(priority_widget)

        # Status combo box
        status_combo = QComboBox()
        status_combo.setStyleSheet(AppStyles.combo_box_norm())
        status_combo.addItems([status.value for status in TaskStatus])
        status_combo.setCurrentText(self.task.status.value if self.task is not None else status_combo.itemText(0))
        status_combo.currentTextChanged.connect(self.updateTaskStatus)
        status_combo.setView(QListView())

        status_combo.setMinimumWidth(150)  # Ensure it has enough space
        status_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)

        # Priority combo box
        priority_combo = QComboBox()
        priority_combo.setStyleSheet(AppStyles.combo_box_norm())
        priority_combo.addItems([priority.name for priority in TaskPriority])
        priority_combo.setCurrentText(self.task.priority.name if self.task is not None else priority_combo.itemText(0))
        priority_combo.currentTextChanged.connect(self.updateTaskPriority)
        priority_combo.setView(QListView())

        priority_combo.setMinimumWidth(150)
        priority_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)

        # Ensure layouts expand properly
        status_layout.addWidget(status_combo, 1)
        priority_layout.addWidget(priority_combo, 1)

        status_layout.setAlignment(Qt.AlignLeft)
        priority_layout.setAlignment(Qt.AlignRight)

        status_priority_layout.addWidget(status_widget, 1)
        status_priority_layout.addWidget(priority_widget, 1)

        return status_priority_layout

    def updateTaskStatus(self, new_status: str):
        if self.task is not None:
            for st in TaskStatus:
                if st.value == new_status:
                    self.task.status = st
                    break

    def updateTaskPriority(self, new_priority: str):
        if self.task is not None:
            for pr in TaskPriority:
                if pr.name == new_priority:
                    self.task.priority = pr
                    break

    def createDescriptionSection(self):
        desc_layout = QVBoxLayout()
        
        desc_edit = QTextEdit(self.task.description if self.task is not None else "")
        desc_edit.setStyleSheet(AppStyles.text_edit_norm())
        desc_edit.setMinimumHeight(50)
        
        # Connect the text changed signal to update description
        desc_edit.textChanged.connect(lambda: self.updateTaskDescription(desc_edit.toPlainText()))
        
        desc_layout.addWidget(QLabel("Description:"))
        desc_layout.addWidget(desc_edit)
        return desc_layout

    def updateTaskDescription(self, new_description):
        """Update the task description in memory"""
        if self.task is not None:
            self.task.description = new_description

    def createDatesSection(self):
        dates_layout = QGridLayout()
        
        # Creation Date (Read-only)
        creation_date_label = QLabel(f"Created: {self.task.creation_date.strftime('%m / %d / %Y') if self.task is not None else datetime.now().strftime('%m / %d / %Y')}")
        dates_layout.addWidget(creation_date_label, 0, 0)
        
        # Due Date with Calendar Icon
        due_date_container = QWidget()
        due_date_layout = QHBoxLayout(due_date_container)
        due_date_layout.setContentsMargins(0, 0, 0, 0)
    
        # Label to display selected date
        self.due_date_label = QLabel("Select due date")
        if self.task is not None:
            if self.task.due_date:
                self.due_date_label.setText(self.task.due_date.strftime('%m / %d / %Y'))
        else:
            self.due_date_label.setText(datetime.now().strftime('%m / %d / %Y'))

        # Calendar Button with icon
        calendar_button = QPushButton()
        image_path = resource_path('resources/images/Calendar.png')
        pixmap = QPixmap(image_path)
        calendar_icon = QIcon(pixmap)
        calendar_button.setIcon(calendar_icon)
        calendar_button.setFixedSize(30, 30)
        calendar_button.setIconSize(QSize(30, 30))
        calendar_button.setStyleSheet(AppStyles.button_transparent())
        calendar_button.clicked.connect(self.showCalendar)
        
        due_date_layout.addWidget(QLabel("Due Date:"))
        due_date_layout.addWidget(self.due_date_label)
        due_date_layout.addWidget(calendar_button)
        due_date_layout.addStretch()
        
        dates_layout.addWidget(due_date_container, 1, 0, 1, 2)
        
        return dates_layout

    def showCalendar(self):
        # Close any existing instance
        if hasattr(self, '_calendar_widget') and self._calendar_widget:
            self._calendar_widget.close()

        calendar = QCalendarWidget(self)
        self._calendar_widget = calendar
        calendar.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        calendar.setGridVisible(True)
        calendar.setSelectionMode(QCalendarWidget.SingleSelection)
        calendar.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        calendar.setDateEditEnabled(True)
        calendar.setFirstDayOfWeek(Qt.Sunday)

        # style tweaks ...
        format_saturday = calendar.weekdayTextFormat(Qt.Saturday)
        format_sunday = calendar.weekdayTextFormat(Qt.Sunday)
        format_saturday.setForeground(QColor('#5F9EA0'))
        format_sunday.setForeground(QColor('#5F9EA0'))
        calendar.setWeekdayTextFormat(Qt.Saturday, format_saturday)
        calendar.setWeekdayTextFormat(Qt.Sunday, format_sunday)

        # icons → text arrows
        prev_button = calendar.findChild(QToolButton, "qt_calendar_prevmonth")
        next_button = calendar.findChild(QToolButton, "qt_calendar_nextmonth")
        if prev_button:
            prev_button.setText("<"); prev_button.setIcon(QIcon()); prev_button.setStyleSheet(AppStyles.button_calendar_horizontal())
        if next_button:
            next_button.setText(">"); next_button.setIcon(QIcon()); next_button.setStyleSheet(AppStyles.button_calendar_horizontal())

        year_spinbox = calendar.findChild(QSpinBox, "qt_calendar_yearedit")
        if year_spinbox:
            up_button = year_spinbox.findChild(QToolButton, "qt_spinbox_upbutton")
            down_button = year_spinbox.findChild(QToolButton, "qt_spinbox_downbutton")
            if up_button:
                up_button.setText("▲"); up_button.setIcon(QIcon()); up_button.setStyleSheet(AppStyles.button_calendar_vertical())
            if down_button:
                down_button.setText("▼"); down_button.setIcon(QIcon()); down_button.setStyleSheet(AppStyles.button_calendar_vertical())
            year_spinbox.setAttribute(Qt.WA_MacShowFocusRect, 0)

        calendar.setStyleSheet(AppStyles.calendar_norm())

        if self.task and self.task.due_date:
            # QDate from Python date
            qd = QDateTime(self.task.due_date).date()
            calendar.setSelectedDate(qd)

        button = self.sender()
        pos = button.mapToGlobal(button.rect().bottomLeft())
        calendar.move(pos)

        calendar.clicked.connect(self.updateDueDate)
        calendar.show()

    def updateDueDate(self, date):
        self.task.due_date = date.toPyDate()
        self.due_date_label.setText(date.toString('MM / dd / yyyy'))
        if hasattr(self, '_calendar_widget') and self._calendar_widget:
            self._calendar_widget.close()
            self._calendar_widget = None

    def createCategorySection(self):
        category_layout = QHBoxLayout()
        category_combo = QComboBox()
        category_combo.setStyleSheet(AppStyles.combo_box_norm())
        category_combo.addItems([category.value for category in TaskCategory])
        category_combo.setCurrentText(self.task.category.value if self.task else category_combo.itemText(0))
        category_combo.setView(QListView())
        print(f"category_combo: {category_combo.objectName()} - Address: {hex(id(category_combo))}")
        
        # Connect the combo box change to the update method
        category_combo.currentTextChanged.connect(lambda text: self.updateTaskCategory(text))
        
        category_layout.addWidget(QLabel("Category:"))
        category_layout.addWidget(category_combo)
        return category_layout

    def updateTaskCategory(self, new_category):
        # Update the task object with the new category
        for category in TaskCategory:
            if category.value == new_category:
                self.task.category = category
                break

    def createButtonSection(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 15)

        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        delete_btn = QPushButton("Delete")
        settings_btn = QPushButton("Settings")

        save_btn.setStyleSheet(AppStyles.save_button())
        cancel_btn.setStyleSheet(AppStyles.save_button())
        delete_btn.setStyleSheet(AppStyles.save_button())
        settings_btn.setStyleSheet(AppStyles.save_button())

        # Persist task and notify parent appropriately
        save_btn.clicked.connect(lambda: save_task_to_json(self.task, self.logger))
        if self.task is None:
            save_btn.clicked.connect(lambda: self.saveCompleted.emit(self.grid_id))
        else:
            save_btn.clicked.connect(lambda: self.newTaskUpdate.emit(self.task, self.grid_id))

        cancel_btn.clicked.connect(self.cancelTaskChanges)
        delete_btn.clicked.connect(self.deleteTask)
        settings_btn.clicked.connect(self.settingsMenu)

        for b in (save_btn, cancel_btn, delete_btn, settings_btn):
            layout.addWidget(b)

        return layout
        
    def createActivitySection(self):
        # Create a container widget for the activity section
        activity_widget = QWidget()
        activity_layout = QVBoxLayout(activity_widget)
        
        # Create tab widget
        tab_widget = QTabWidget()
        tab_widget.setStyleSheet(AppStyles.tab_norm())
        
        # Comments tab
        comments_tab = QWidget()
        comments_layout = QVBoxLayout(comments_tab)
        
        # Add text entry for new comments
        comment_input = QTextEdit()
        comment_input.setPlaceholderText("Add a comment...")
        comment_input.setMaximumHeight(100)
        comment_input.setStyleSheet(AppStyles.text_edit_norm())
    
        # Create container for comment input and button
        comment_input_container = QWidget()
        comment_input_layout = QVBoxLayout(comment_input_container)
        comment_input_layout.addWidget(comment_input)
        
        # Add post button in a horizontal layout to push it right
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.addStretch()  
        post_button = QPushButton("Post Comment")
        post_button.setStyleSheet(AppStyles.post_button())
        button_layout.addWidget(post_button)
        
        comment_input_layout.addWidget(button_container)
        comments_layout.addWidget(comment_input_container)
        
        # Add comments list view
        self.comments_list = QListWidget() 
        self.comments_list.setStyleSheet(AppStyles.list_style())
        
        comments_scroll_area = QScrollArea()
        comments_scroll_area.setWidget(self.comments_list)
        comments_scroll_area.setStyleSheet(AppStyles.scroll_area())
        comments_scroll_area.setWidgetResizable(True)
        
        comments_layout.addWidget(comments_scroll_area)
        
        # Connect signals - pass the input widget
        post_button.clicked.connect(lambda: self.add_comment(comment_input))
        
        # Work Logs tab
        work_logs_tab = QWidget()
        work_logs_layout = QVBoxLayout(work_logs_tab)
        
        # Add new work log entry section
        log_entry = QWidget()
        log_layout = QHBoxLayout(log_entry)
        
        hours_input = QSpinBox()
        hours_input.setMinimum(0)
        hours_input.setMaximum(24)
        hours_input.setSuffix(" hours")
        
        log_description = QLineEdit()
        log_description.setPlaceholderText("Describe your work...")
        log_description.setStyleSheet(AppStyles.log_line_edit())
        
        log_button = QPushButton("Log Work")
        
        log_layout.addWidget(hours_input)
        log_layout.addWidget(log_description)
        log_layout.addWidget(log_button)
        work_logs_layout.addWidget(log_entry)
        
        # Add work logs list
        self.work_logs_list = QListWidget()  
        self.work_logs_list.setStyleSheet(AppStyles.log_list())
        
        work_scroll_area = QScrollArea()
        work_scroll_area.setWidgetResizable(True)
        work_scroll_area.setWidget(self.work_logs_list)
        work_scroll_area.setStyleSheet(AppStyles.scroll_area())
        
        work_logs_layout.addWidget(work_scroll_area)
        
        # Connect to work log method - pass both inputs
        log_button.clicked.connect(lambda: self.add_work_log(hours_input, log_description))
        
        # Add tabs to tab widget
        tab_widget.addTab(comments_tab, " Comments ")
        tab_widget.addTab(work_logs_tab, " Work Logs ")
        activity_layout.addWidget(tab_widget)
        
        # Display existing activities
        self.display_activities()
        QApplication.processEvents()
        
        return activity_widget

    # def post_comment(self, comment_input, comments_list, entry_type):
    #     if entry_type == "comment":
    #         comment_text = comment_input.toPlainText().strip()
    #     elif entry_type == "work_log":
    #         comment_text = comment_input.text().strip()
    #     else:
    #         return  # Handle invalid entry types

    #     if comment_text:
    #         timestamp = QDateTime.currentDateTime().toString("MM / dd / yyyy hh:mm")

    #         comment_widget = QWidget()
    #         comment_layout = QVBoxLayout(comment_widget)

    #         comment_label = QLabel(comment_text)
    #         timestamp_label = QLabel(timestamp)
    #         timestamp_label.setStyleSheet("font-size: 10px; color: gray;")

    #         actions_layout = QHBoxLayout()
    #         actions_layout.setAlignment(Qt.AlignLeft)

    #         edit_label = QLabel("Edit")
    #         delete_label = QLabel("Delete")

    #         for label in [edit_label, delete_label]:
    #             label.setStyleSheet("color: #ffffff; padding-right: 10px; text-decoration: none;")
    #             label.setCursor(Qt.PointingHandCursor)
    #             label.setTextInteractionFlags(Qt.TextBrowserInteraction)

    #         # def hover_enter(event, lbl):
    #         #     lbl.setStyleSheet("color: #ffffff; padding-right: 10px; text-decoration: underline;")

    #         # def hover_leave(event, lbl):
    #         #     lbl.setStyleSheet("color: #ffffff; padding-right: 10px; text-decoration: none;")

    #         # edit_label.enterEvent = lambda event, lbl=edit_label: hover_enter(event, lbl)
    #         # edit_label.leaveEvent = lambda event, lbl=edit_label: hover_leave(event, lbl)
    #         # delete_label.enterEvent = lambda event, lbl=delete_label: hover_enter(event, lbl)
    #         # delete_label.leaveEvent = lambda event, lbl=delete_label: hover_leave(event, lbl)

    #         edit_label.mousePressEvent = lambda event: self.edit_comment(item, comment_label)
    #         delete_label.mousePressEvent = lambda event: self.delete_comment(item)

    #         actions_layout.addWidget(edit_label)
    #         actions_layout.addWidget(delete_label)

    #         comment_layout.addWidget(comment_label)
    #         comment_layout.addWidget(timestamp_label)
    #         comment_layout.addLayout(actions_layout)

    #         item = QListWidgetItem()
    #         item.setSizeHint(comment_widget.sizeHint())
    #         comments_list.addItem(item)
    #         comments_list.setItemWidget(item, comment_widget)

    #         comment_input.clear()
    #         self.saveActivity(comment_text, timestamp, "comment")


    def edit_comment(self, item, comment_label):
        current_text = comment_label.text().split(" - ")[0]
        new_text, ok = QInputDialog.getText(None, "Edit Comment", "Edit your comment:", QLineEdit.Normal, current_text)
        
        if ok and new_text.strip():
            timestamp = QDateTime.currentDateTime().toString("MM / dd / yyyy hh:mm")
            comment_label.setText(f"{new_text} - {timestamp} (edited)")
            self.saveActivity(current_text, timestamp, "comment", is_edit=True)


    def delete_comment(self, item):
        comment_label = item.listWidget().itemWidget(item).layout().itemAt(0).widget().text()
        text = comment_label.split(" - ")[0]
        reply = QMessageBox.question(None, "Delete Comment", "Are you sure you want to delete this comment?", QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            row = item.listWidget().row(item)
            item.listWidget().takeItem(row)
            timestamp = QDateTime.currentDateTime().toString("MM / dd / yyyy hh:mm")
            self.saveActivity(text, timestamp, "comment", is_delete=True)

    def initCollapsableSections(self):
        # Create a vertical layout to return
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setStyleSheet(AppStyles.scroll_area())
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # Create content widget for the scroll area
        scroll_content = QWidget()
        scroll_content.setStyleSheet(AppStyles.widget_trans())
        scroll_layout = QVBoxLayout(scroll_content)
        
        # Add sections to the scroll content
        details_section = self.createDetailsSection()
        dependencies_section = self.createDependenciesSection()
        attachments_section = self.createAttachmentsSection()
        checklist_section = self.createChecklistSection() 
        
        scroll_layout.addLayout(details_section)
        scroll_layout.addLayout(dependencies_section)
        scroll_layout.addLayout(attachments_section)
        scroll_layout.addLayout(checklist_section)
        scroll_layout.addStretch(1)
        
        # Set the content widget to the scroll area
        scroll_area.setWidget(scroll_content)
        
        # Add scroll area to the main layout
        main_layout.addWidget(scroll_area)
        
        # CRITICAL FIX: Force layout adjustment after a brief delay 
        # This mimics what happens during collapse and fixes the layout
        QTimer.singleShot(10, lambda: self.forceLayoutUpdate(scroll_content))
        
        return main_layout

    def forceLayoutUpdate(self, widget):
        """Force the widget to update its layout to fit the available space"""
        # This triggers layout recalculation similar to what happens on collapse
        widget.adjustSize()
        widget.updateGeometry()
        # Force a resize of all child CollapsibleSection widgets
        for child in widget.findChildren(CollapsibleSection):
            child.updateGeometry()
    
    def createDetailsSection(self):
        # Create a layout without a parent widget
        section_layout = QVBoxLayout()
        section_layout.setContentsMargins(0, 0, 15, 0)
        section_layout.setSpacing(5)
        
        # Details section
        details_section = CollapsibleSection("Details", self)
        details_section.setStyleSheet(AppStyles.border_widget())

        details_section.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        # Add your regular details rows
        details_section.add_dates(self.createDatesSection())
        
        # Add the team list
        details_section.add_team_list()
        
        # Connect signals to your existing functions
        details_section.team_member_added.connect(self.add_team_member_to_task)
        details_section.team_member_removed.connect(self.remove_team_member_from_task)
        
        # Load existing team members from the Task object
        if hasattr(self.task, 'collaborators') and self.task.collaborators:
            for member in self.task.collaborators:
                details_section.team_input.setText(member)
                details_section.add_team_member()

        if not self.task.collaborators:
            print("No teams found")
            details_section.toggle_collapsed()
        else:
            print("found teams")
                
        # Add section to layout
        section_layout.addWidget(details_section)
        section_layout.addStretch()
        
        return section_layout

    def createDependenciesSection(self):
        section_layout = QVBoxLayout()
        section_layout.setContentsMargins(0, 0, 15, 0)
        section_layout.setSpacing(5)

        # Dependencies section
        dependencies_section = CollapsibleSection("Dependencies", self)
        dependencies_section.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        dependencies_section.setStyleSheet(AppStyles.border_widget())
        dependencies_section.add_dependencies_list()

        # Update available tasks
        all_tasks = self.load_dependencies()
        dependencies_section.update_available_tasks(self.task.title if self.task is not None else "", all_tasks)
        
        # Connect signals
        dependencies_section.dependency_added.connect(self.add_dependency_to_task)
        dependencies_section.dependency_removed.connect(self.remove_dependency_from_task)
        
        if hasattr(self.task, 'dependencies') and self.task.dependencies:
        # Create a list copy of the dependencies set
            deps_to_add = list(self.task.dependencies)
            for dep in deps_to_add:
                dependencies_section.task_combo.setCurrentText(dep)
                dependencies_section.add_dependency()

        if not self.task.dependencies:
            dependencies_section.toggle_collapsed()

        section_layout.addWidget(dependencies_section)
        section_layout.addStretch()
        
        return section_layout
    
    def createChecklistSection(self):
        section_layout = QVBoxLayout()
        section_layout.setContentsMargins(0, 0, 15, 0)
        section_layout.setSpacing(5)
        
        # Create section
        self.checklist_section = CollapsibleSection("Checklist", self)
        self.checklist_section.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.checklist_section.setStyleSheet(AppStyles.border_widget())
        
        # Add checklist functionality
        self.checklist_section.add_checklist("Task Items")
        
        # IMPORTANT: Load the existing data BEFORE connecting the signal
        # Load existing BEFORE signals
        for item in self.task.checklist:
            self.checklist_section.checklist_input.setText(item['text'])
            self.checklist_section.add_checklist_item()
            if item.get('checked', False):
                last_idx = len(self.checklist_section.checklist_data) - 1
                if last_idx >= 0:
                    checkbox = self.checklist_section.checklist_data[last_idx].get('checkbox')
                    if checkbox:
                        checkbox.setChecked(True)

        # Connect signals AFTER load
        self.checklist_section.checklist_item_added.connect(self.addChecklistItem)
        self.checklist_section.checkbox_state_changed.connect(self.updateCheckboxState)
        self.checklist_section.checklist_item_removed.connect(self.removeChecklistItem)

        if not self.task.checklist:
            self.checklist_section.toggle_collapsed()
        
        section_layout.addWidget(self.checklist_section)
        section_layout.addStretch()
        return section_layout
    
    def createAttachmentsSection(self):
        section_layout = QVBoxLayout()
        section_layout.setContentsMargins(0, 0, 15, 0)
        section_layout.setSpacing(5)
        
        attachments_section = CollapsibleSection("Attachments", self)
        attachments_section.setStyleSheet(AppStyles.border_widget())
        attachments_section.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        # Add attachments list
        if hasattr(self.task, 'attachments') and self.task.attachments:
            attachments_section.add_attachments(self.task.attachments)
        else:
            if self.task is not None:
                self.task.attachments = []
                attachments_section.add_attachments([])

        if not self.task.attachments:
            attachments_section.toggle_collapsed()
            
        # Connect signals
        attachments_section.attachment_clicked.connect(self.open_attachment)
        attachments_section.add_file_attachment_clicked.connect(self.add_file_attachment_to_task)
        attachments_section.attachment_removed.connect(self.remove_attachment_from_task)
        
        # Store reference to the section widget
        self.attachments_section = attachments_section
        
        section_layout.addWidget(attachments_section)
        section_layout.addStretch()
        
        return section_layout

    def open_attachment(self, path_or_url):
        self.saveCompleted.emit(self.grid_id)
        # Convert to an absolute path if needed
        if not os.path.isabs(path_or_url):
            path_or_url = os.path.abspath(path_or_url)
        
        url = QUrl.fromLocalFile(path_or_url)
        # print(f"Opening url: {url}")
        QDesktopServices.openUrl(url)
    
    def add_file_attachment_to_task(self):
        path_or_url, _ = QFileDialog.getOpenFileName(self, "Select Attachment", "", "All Files (*)")
        if path_or_url:
            path_or_url = os.path.abspath(path_or_url)
            attachment = Attachment(path_or_url, user_id="Current User", description="")
            self.task.attachments.append(attachment)
            self.attachments_section.add_attachments(self.task.attachments)  # single refresh

    def remove_attachment_from_task(self, attachment):
        """Remove an attachment from the task."""
        # Handle both object and dictionary attachments for backward compatibility
        if isinstance(attachment, dict):
            # Remove by matching file path
            path_or_url = attachment.get('path_or_url')
            self.task.attachments = [a for a in self.task.attachments 
                                    if getattr(a, 'path_or_url', '') != path_or_url]
        else:
            # Remove the attachment object
            if attachment in self.task.attachments:
                self.task.attachments.remove(attachment)
        
        # Refresh the UI
        self.attachments_section.add_attachments(self.task.attachments)

    def saveActivity(self, text, timestamp, activity_type, is_edit=False, is_delete=False):
        # Find existing activity if editing/deleting
        if is_edit or is_delete:
            for idx, entry in enumerate(self.task.entries):
                if entry.content == text:
                    if is_delete:
                        # Remove the entry
                        self.task.entries.pop(idx)
                        break
                    elif is_edit:
                        # Update the entry
                        entry.edit(text, "Current User")
                        break
        else:
            # Create new TaskEntry
            new_entry = TaskEntry(
                content=text,
                entry_type=activity_type,
                user_id="Current User"
            )
            self.task.entries.append(new_entry)

    def display_activities(self):
        """Display task entries in the appropriate lists, ordered by newest first."""
        # Clear existing items
        self.comments_list.clear()
        self.work_logs_list.clear()

        # Display entries by type
        if hasattr(self.task, 'entries'):
            # Sort entries by timestamp in descending order (newest first)
            sorted_entries = sorted(self.task.entries, key=lambda entry: entry.timestamp, reverse=True)

            for entry in sorted_entries:
                if entry.entry_type == "comment":
                    self.add_entry_to_list(entry, self.comments_list)
                elif entry.entry_type == "work_log":
                    self.add_entry_to_list(entry, self.work_logs_list)

    # def add_activity_to_list(self, entry):
    #     """Add a TaskEntry to the comments list with proper formatting"""

    #     """Need to impliment if necessary"""
    #     comment_widget = QWidget()
    #     comment_layout = QVBoxLayout(comment_widget)
        
    #     comment_label = QLabel(entry.content)
    #     comment_label.setWordWrap(True)
    #     timestamp_label = QLabel(entry.timestamp.strftime("%m/%d/%Y %H:%M"))
    #     timestamp_label.setStyleSheet(AppStyles.time_stamp_label())
    
    #     actions_layout = QHBoxLayout()
    #     actions_layout.setAlignment(Qt.AlignLeft)
        
    #     edit_label = QPushButton("Edit")
    #     edit_label.clicked.connect(lambda: self.edit_comment(entry))
    #     delete_label = QPushButton("Delete")
    #     delete_label.clicked.connect(lambda: self.delete_comment(entry))
        
    #     # for label in [edit_label, delete_label]:
    #     #     label.setStyleSheet(AppStyles.label_edit_delete())
    #     #     label.setCursor(Qt.PointingHandCursor)
    #     #     label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        
    #     actions_layout.addWidget(edit_label)
    #     actions_layout.addWidget(delete_label)
        
    #     comment_layout.addWidget(comment_label)
    #     comment_layout.addWidget(timestamp_label)
    #     comment_layout.addLayout(actions_layout)
        
    #     item = QListWidgetItem()
    #     item.setSizeHint(comment_widget.sizeHint())
    #     self.comments_list.addItem(item)
    #     self.comments_list.setItemWidget(item, comment_widget)
        
    #     # Store reference to the entry in the item's data
    #     item.setData(Qt.UserRole, entry)
        
    #     # Set up event handlers
    #     edit_label.mousePressEvent = lambda event, item=item: self.edit_activity(item)
    #     delete_label.mousePressEvent = lambda event, item=item: self.delete_activity(item)

    def add_entry_to_list(self, entry, list_widget):
        """Add a TaskEntry to a list widget with proper formatting"""
        entry_widget = QWidget()
        entry_layout = QVBoxLayout(entry_widget)
        
        # Content label
        content_label = QLabel(entry.content)
        content_label.setWordWrap(True)

        # horizontal_widget = QWidget()
        # horizontal_layout = QHBoxLayout(horizontal_widget)
        
        # Timestamp
        timestamp_label = QLabel(entry.timestamp.strftime("%m/%d/%Y %H:%M"))
        timestamp_label.setStyleSheet(AppStyles.time_stamp_label())
        
        # Action buttons
        actions_layout = QHBoxLayout()
        actions_layout.setAlignment(Qt.AlignLeft)
    
        edit_label = QLabel("Edit")
        delete_label = QLabel("Delete")
        
        for label in [edit_label, delete_label]:
            label.setStyleSheet(AppStyles.label_edit_delete())
            label.setCursor(Qt.PointingHandCursor)
            label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        
        actions_layout.addWidget(edit_label)
        actions_layout.addWidget(delete_label)
        actions_layout.addWidget(timestamp_label)
        
        # Add widgets to layout
        entry_layout.addWidget(content_label)
        # entry_layout.addWidget(timestamp_label)
        entry_layout.addLayout(actions_layout)
        
        # Create and set up list item
        item = QListWidgetItem()
        item.setSizeHint(entry_widget.sizeHint())
        list_widget.addItem(item)
        list_widget.setItemWidget(item, entry_widget)
        
        # Store reference to the entry
        item.setData(Qt.UserRole, entry)
        
        # Connect action signals
        edit_label.mousePressEvent = lambda event, item=item: self.edit_activity(item)
        delete_label.mousePressEvent = lambda event, item=item: self.delete_activity(item)
        
    def add_comment(self, comment_input):
        text = comment_input.toPlainText().strip()
        if text:
            ts = QDateTime.currentDateTime().toString("MM / dd / yyyy hh:mm")
            self.saveActivity(text, ts, "comment")
            comment_input.clear()
            self.display_activities()

    def add_work_log(self, hours_input, description_input):
        hours = hours_input.value()
        description = description_input.text().strip()
        if hours > 0 and description:
            ts = QDateTime.currentDateTime().toString("MM / dd / yyyy hh:mm")
            self.saveActivity(description, ts, "work_log")
            time_log = TimeLog(hours=float(hours), user_id="Current User", description=description)
            self.task.time_logs.append(time_log)
            self.task.actual_hours += float(hours)
            hours_input.setValue(0)
            description_input.clear()
            self.display_activities()

    def edit_activity(self, item):
        """Edit a TaskEntry"""
        entry = item.data(Qt.UserRole)
        if entry:
            text, ok = QInputDialog.getMultiLineText(
                self, "Edit Comment", "Update your comment:", entry.content
            )
            if ok and text:
                # Update the entry
                entry.edit(text, "Current User")
                
                # Refresh the UI
                self.display_activities()

    def delete_activity(self, item):
        """Delete a TaskEntry"""
        print(f"Attempting to delete item: {item}")
        entry = item.data(Qt.UserRole)
        print(f"found entry: {entry}")
        if entry:
            confirm = QMessageBox.question(
                self, "Confirm Delete", 
                "Are you sure you want to delete this comment?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if confirm == QMessageBox.Yes:
                # Remove from task entries
                if entry in self.task.entries:
                    self.task.entries.remove(entry)
                
                # Refresh the UI
                self.display_activities()
        else:
            print("failed to delete")

    def edit_work_log(self, item):
        """Edit a TimeLog"""

        """Need to impliment this"""
        log = item.data(Qt.UserRole)
        if log:
            hours, ok1 = QInputDialog.getDouble(
                self, "Edit Hours", "Hours worked:", 
                log.hours, 0, 24, 1
            )
            
            if ok1:
                description, ok2 = QInputDialog.getText(
                    self, "Edit Description", "Description:",
                    QLineEdit.Normal, log.description
                )
                
                if ok2:
                    # Update hours total
                    self.task.actual_hours -= log.hours
                    self.task.actual_hours += hours
                    
                    # Update the log
                    log.hours = hours
                    log.description = description
                    
                    # Refresh the UI
                    self.display_activities()

    def delete_work_log(self, item):
        """Delete a TimeLog"""

        """Need to impliment this"""
        log = item.data(Qt.UserRole)
        if log:
            confirm = QMessageBox.question(
                self, "Confirm Delete", 
                "Are you sure you want to delete this work log?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if confirm == QMessageBox.Yes:
                # Update hours total
                self.task.actual_hours -= log.hours
                
                # Remove from task time logs
                if log in self.task.time_logs:
                    self.task.time_logs.remove(log)
                
                # Refresh the UI
                self.display_activities()

    def add_team_member_to_task(self, member_name):
        """Add team member to the current task"""
        # Add to the Task object's collaborators set
        self.task.collaborators.add(member_name)

    def remove_team_member_from_task(self, member_name):
        """Remove team member from the current task"""
        # Remove from the Task object's collaborators set
        if member_name in self.task.collaborators:
            self.task.collaborators.remove(member_name)

    def load_dependencies(self):
        """Load all available tasks for dependencies"""
        # Get all task titles from the task objects
        tasks = load_tasks_from_json(self.logger)
        return list(tasks.keys())

    def add_dependency_to_task(self, dependency_task_title):
        """Add dependency to current task"""
        # Add to the Task object's dependencies set
        self.task.dependencies.add(dependency_task_title)

    def remove_dependency_from_task(self, dependency_task_title):
        """Remove dependency from current task"""
        # Remove from the Task object's dependencies set
        if dependency_task_title in self.task.dependencies:
            self.task.dependencies.remove(dependency_task_title)
        
    def cancelTaskChanges(self):
        """Close expanded card and restore original task state"""
        # Restore the task to its initial state
        if self.initial_state is not None:
            self.restore_task_state()
        
        # Hide overlay and close
        self.cancelTask.emit()

    def restore_task_state(self):
        """Restore the task to its original state"""
        task = self.task
        
        # Restore simple attributes
        task.description = self.initial_state['description']
        task.status = self.initial_state['status']
        task.priority = self.initial_state['priority']
        task.percentage_complete = self.initial_state['percentage_complete']
        task.start_date = self.initial_state['start_date']
        task.due_date = self.initial_state['due_date']
        task.estimated_hours = self.initial_state['estimated_hours']
        task.assignee = self.initial_state['assignee']
        
        # Restore collections
        task.dependencies = self.initial_state['dependencies']
        task.collaborators = self.initial_state['collaborators']
        
        # Restore lists
        task.entries = self.initial_state['entries']
        task.time_logs = self.initial_state['time_logs']
        task.attachments = self.initial_state['attachments']

        task.checklist = self.initial_state['checklist']

    def deleteTask(self):
        confirm = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete the task '{self.task.title}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        from utils.app_config import AppConfig
        app_config = AppConfig()
        json_file_path = app_config.tasks_file

        try:
            # Keep these for messages/signals
            task_id = self.task.id
            task_title = self.task.title

            with open(json_file_path, 'r') as f:
                tasks_data = json.load(f)

            if task_id in tasks_data:
                del tasks_data[task_id]
                with open(json_file_path, 'w') as f:
                    json.dump(tasks_data, f, indent=2)

                self.taskDeleted.emit(task_title)
                if hasattr(self, 'parent_view') and self.parent_view and hasattr(self.parent_view, 'overlay'):
                    self.parent_view.overlay.hide()
                self.close()

                QMessageBox.information(self, "Success", f"Task '{task_title}' was deleted.")
            else:
                QMessageBox.warning(self, "Warning", f"Task '{task_title}' not found in saved tasks.")
        except Exception as e:
            self.logger.error(f"Error deleting task: {e}")
            QMessageBox.critical(self, "Error", f"An error occurred while deleting the task: {str(e)}")

                
    def add_checklist_item_to_task(self, text):
        """Add a checklist item to the task"""
        if not hasattr(self.task, 'checklist'):
            self.task.checklist = []
            
        self.task.checklist.append({
            'text': text,
            'checked': False
        })

    def remove_checklist_item_from_task(self, text):
        """Remove a checklist item from the task"""
        if hasattr(self.task, 'checklist'):
            # Remove the item with matching text
            self.task.checklist = [item for item in self.task.checklist if item['text'] != text]
            
    def update_checklist_item_in_task(self, text, checked):
        """Update the checked state of a checklist item"""
        if hasattr(self.task, 'checklist'):
            for item in self.task.checklist:
                if item['text'] == text:
                    item['checked'] = checked
                    break

    def closeWindow(self):
        self.logger.debug("Closing expanded card")
        if self.parent_view and hasattr(self.parent_view, 'overlay') and self.parent_view.overlay:
            self.parent_view.overlay.hide()
        self.close()
        self.deleteLater()

    def addChecklistItem(self, text):
        """Add checklist item to the current task"""
        # Check the flag to prevent recursion during loading
        if hasattr(self, '_loading_checklist_items') and self._loading_checklist_items:
            return
            
        # Add to the Task object's checklist list
        self.task.checklist.append({
            'text': text,
            'checked': False
        })

    def removeChecklistItem(self, text):
        """Remove a checklist item from the task"""
        if hasattr(self.task, 'checklist'):
            # Remove the item with matching text
            self.task.checklist = [item for item in self.task.checklist if item['text'] != text]
    
    def updateCheckboxState(self, text, checked):
        """Update the task's checklist item state"""
        # Find the item with matching text in the task's checklist
        for i, item in enumerate(self.task.checklist):
            if item['text'] == text:
                # Update the checked state
                self.task.checklist[i]['checked'] = checked
                break
        
    def settingsMenu(self):
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
        self.task_settings_menu = TaskSettingsMenu(
            logger=self.logger,
            task=self.task,
            grid_id=self.grid_id,
            parent_view=self,
            parent=self.dialog_container
        )

        # Set the object name so the style sheet applies.
        self.task_settings_menu.setObjectName("card_container")
        # Enable styled backgrounds so that the style sheet paints the background.
        self.task_settings_menu.setAttribute(Qt.WA_StyledBackground, True)
        # Notice: We do NOT set WA_TranslucentBackground here, so that the style sheet's background color is visible.
        self.task_settings_menu.setStyleSheet(AppStyles.expanded_task_card())
        
        # Calculate optimal dimensions and center the expanded card.
        card_width, card_height = self.task_settings_menu.calculate_optimal_card_size()
        center_x = (self.dialog_container.width() - card_width) // 2
        center_y = (self.dialog_container.height() - card_height) // 2
        self.task_settings_menu.setGeometry(center_x, center_y, card_width, card_height)
        self.task_settings_menu.setWindowFlags(Qt.FramelessWindowHint)
        self.task_settings_menu.raise_()
        
        # Show the container (which holds both the overlay and the expanded card)
        self.dialog_container.show()