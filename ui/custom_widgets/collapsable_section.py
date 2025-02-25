# -----------------------------------------------------------------------------
# Project Manager
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
# File: collapsable_section.py
# Description: Used in task_card_expanded to create collapsable sections to add
#              functionality.
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

import os
from resources.styles import AppStyles, AppColors, AppBorders
from PyQt5.QtWidgets import (QApplication, QDesktopWidget, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSpacerItem, 
                             QSizePolicy, QGridLayout, QPushButton, QGraphicsDropShadowEffect, QStyle, QComboBox, QTextEdit,
                             QDateTimeEdit, QLineEdit, QCalendarWidget, QToolButton, QSpinBox, QListWidget, QTabWidget,
                             QMessageBox, QInputDialog, QListWidgetItem, QScrollArea, QTreeWidget, QTreeWidgetItem
                             )
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QEvent, QSize, QDateTime
from PyQt5.QtGui import QColor, QPainter, QBrush, QPen, QMovie, QTextCharFormat, QColor, QIcon, QPixmap, QFont
from PyQt5.QtSvg import QSvgWidget

from PyQt5.QtWidgets import QStyleFactory

class CollapsibleSection(QWidget):
    team_member_added = pyqtSignal(str)    
    team_member_removed = pyqtSignal(str)
     
    dependency_added = pyqtSignal(str)
    dependency_removed = pyqtSignal(str)

    attachment_clicked = pyqtSignal(str)
    add_attachment_clicked = pyqtSignal()
    attachment_removed = pyqtSignal(object)

    def __init__(self, title, parent=None):
        super().__init__(parent)  
        self.title = title 
        self.is_collapsed = False

        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)

        self.setupUI() 

    def setupUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Header
        self.header = QWidget()
        self.header.setStyleSheet(f"""
            QWidget {{
                background-color: {AppColors.main_background_color};
                border: none;
            }}
            QWidget:hover {{
                background-color: {AppColors.main_background_hover_color};
                border: none;
            }}
        """)
        
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(8, 8, 8, 8)

        # Arrow and title
        self.arrow_button = QPushButton("▼")
        self.arrow_button.setFixedSize(20, 20)
        self.arrow_button.setStyleSheet("""
            QPushButton {
                border: none;
                color: #6B778C;
                font-size: 14px;
                text-align: left;
                padding: 0;
                background-color: transparent;
            }

        """)
        
        title_label = QLabel(self.title)
        title_label.setStyleSheet("color: white; background-color: transparent; font-weight: bold; border: none;")
        
        header_layout.addWidget(title_label)
        header_layout.addStretch(1)
        header_layout.addWidget(self.arrow_button)

        # Content area
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(15, 5, 8, 8)
        self.content_layout.setSpacing(12)
        
        # Add widgets to main layout
        layout.addWidget(self.header)
        layout.addWidget(self.content)
        
        # Connect toggle
        self.arrow_button.clicked.connect(self.toggle_collapsed)
        self.header.mousePressEvent = lambda e: self.toggle_collapsed()
        
######################################################################################

# Team Section

    def add_team_list(self):

        # Create team members label
        team_label = QLabel("Team Members")
        team_label.setStyleSheet(AppStyles.label_lgfnt_bold())
        self.content_layout.addWidget(team_label)

        # Create input and button in horizontal layout
        input_row = QWidget()
        input_row.setStyleSheet("border: none;")
        input_layout = QHBoxLayout(input_row)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(4)  # Small spacing between input and button

        self.team_input = QLineEdit()
        self.team_input.setPlaceholderText("Add team member...")
        self.team_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #ddd;
                border-radius: 3px;
                padding: 5px;
            }
        """)

        add_button = QPushButton("Add")
        add_button.setStyleSheet("""
            QPushButton {
                background-color: #0052CC;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #0747A6;
                border: none;
            }
        """)

        input_layout.addWidget(self.team_input)
        input_layout.addWidget(add_button)

        # Create list for team members
        self.team_list = QListWidget()
        self.team_list.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.team_list.setFixedHeight(100) 
        self.team_list.setFrameShape(QFrame.NoFrame)  
        self.team_list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.team_list.setStyleSheet(AppStyles.list_style())

        # Add everything to the content layout with specific spacing
        self.content_layout.addWidget(input_row)
        self.content_layout.addWidget(self.team_list)
        
        # Connect signals
        add_button.clicked.connect(self.add_team_member)
        self.team_input.returnPressed.connect(self.add_team_member)

    def add_team_member(self):
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        name = self.team_input.text().strip()
        if name:
            # Create item widget
            item_widget = QWidget()
            item_widget.setStyleSheet(f"border-style: {AppBorders.none}; ")
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(5, 5, 5, 5)

            name_label = QLabel(name)
            name_label.setStyleSheet(f"border: none; background-color: transparent;")
            remove_button = QPushButton("✕")
            remove_button.setStyleSheet(f"border: none; background-color: transparent;")

            item_layout.addWidget(name_label)
            item_layout.addStretch()
            item_layout.addWidget(remove_button)

            item = QListWidgetItem()
            item.setSizeHint(item_widget.sizeHint())
            self.team_list.addItem(item)
            self.team_list.setItemWidget(item, item_widget)
            items_height = self.team_list.count() * 26  # each item is 26 pixels
            self.team_list.setFixedHeight(min(items_height + 2, 200)) 

            remove_button.clicked.connect(lambda: self.remove_team_member(item))
            self.team_input.clear()
            
            # Emit signal with the name
            self.team_member_added.emit(name)

    def remove_team_member(self, item):
        widget = self.team_list.itemWidget(item)
        name = widget.layout().itemAt(0).widget().text()
        row = self.team_list.row(item)
        self.team_list.takeItem(row)
        
        # Emit signal with the name
        self.team_member_removed.emit(name)

    def get_team_members(self):
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        """Get list of all team members"""
        members = []
        for i in range(self.team_list.count()):
            item = self.team_list.item(i)
            widget = self.team_list.itemWidget(item)
            name_label = widget.layout().itemAt(0).widget()
            members.append(name_label.text())
        return members

    def toggle_collapsed(self):
        self.is_collapsed = not self.is_collapsed
        self.content.setVisible(not self.is_collapsed)
        self.arrow_button.setText("▶" if self.is_collapsed else "▼")
        
        if self.is_collapsed:
            self.header.setStyleSheet(f"""
                QWidget {{
                    background-color: {AppColors.main_background_color};
                    border: 1px solid #ccc;
                }}
                QWidget:hover {{
                    background-color: {AppColors.main_background_hover_color};
                    border: 1px solid #ccc;
                }}
            """)
        else:
            self.header.setStyleSheet(f"""
                QWidget {{
                    background-color: {AppColors.main_background_color};
                    border: none;
                }}
                QWidget:hover {{
                    background-color: {AppColors.main_background_hover_color};
                    border: none;
                }}
            """)
        
        # Make sure arrow button styling remains consistent
        self.arrow_button.setStyleSheet("""
            QPushButton {
                border: none;
                color: #6B778C;
                font-size: 14px;
                text-align: left;
                padding: 0;
                background-color: transparent;
            }
        """)

    def add_row(self, label, value):
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        row = QWidget()
        row.setStyleSheet(f"border: none; background-color: {AppColors.main_background_color};")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        
        label_widget = QLabel(label)
        label_widget.setStyleSheet(f"color: white; border: none; background-color: {AppColors.main_background_color};")
        value_widget = QLabel(value)
        value_widget.setStyleSheet(f"color: white; border: none; background-color: {AppColors.main_background_color};")
        
        row_layout.addWidget(label_widget)
        row_layout.addWidget(value_widget)
        #row_layout.addStretch()
        
        self.content_layout.addWidget(row)
        return row
    
    def add_dates(self, layout):
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        row = QWidget()
        row.setStyleSheet("border: none;")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        
        row_layout.addLayout(layout)
        row_layout.addStretch()
        
        self.content_layout.addWidget(row)
        return row
    
######################################################################################

# Dependencies Section
    
    def add_dependencies_list(self):
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)

        # Create container for combobox section
        self.select_container = QWidget()  # Make this a class member
        self.select_container.setStyleSheet("border: none;")

        select_layout = QHBoxLayout(self.select_container)
        select_layout.setContentsMargins(0, 0, 0, 0)
        
        self.task_combo = QComboBox()
        self.task_combo.setStyleSheet(AppStyles.combo_box_norm())
        
        add_button = QPushButton("Add Dependency")
        add_button.setStyleSheet("""
            QPushButton {
                background-color: #0052CC;
                color: white;
                border: none;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #0747A6;
            }
        """)

        select_layout.addWidget(self.task_combo)
        select_layout.addWidget(add_button)

        # Create container for the list
        self.list_container = QWidget()  # Make this a class member
        self.list_container.setStyleSheet("border: none;")
        list_layout = QVBoxLayout(self.list_container)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(0)

        # Create list for dependencies
        self.dependencies_list = QListWidget()
        self.dependencies_list.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.dependencies_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.dependencies_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.dependencies_list.setStyleSheet("""
            QListWidget {
                border: none;
                background-color: transparent;
            }
            QListWidget::item {
                padding: 5px;
            }
        """)
        self.dependencies_list.setSpacing(4)

        # Add list to container
        list_layout.addWidget(self.dependencies_list)

        # Add both containers to content layout
        self.content_layout.addWidget(self.select_container)
        self.content_layout.addWidget(self.list_container)

        # Connect signals
        add_button.clicked.connect(self.add_dependency)

    def update_available_tasks(self, current_task_title, all_tasks):
        """Update combobox with available tasks (excluding current task)"""
        self.task_combo.clear()
        self.task_combo.addItem("None")
        for task_title in all_tasks:
            if task_title != current_task_title:  # Don't include current task
                self.task_combo.addItem(task_title)

    def add_dependency(self):
        task_title = self.task_combo.currentText()
        if task_title:
            # Create item widget
            item_widget = QWidget()
            item_widget.setStyleSheet("border: none;")
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(5, 8, 5, 8)  # Increased vertical padding
            item_layout.setSpacing(8) 

            task_label = QLabel(task_title)
            task_label.setStyleSheet("""
                border: none;
                padding: 2px 0; \
            """)
            
            remove_button = QPushButton("✕")
            remove_button.setStyleSheet(AppStyles.button_normal_delete())
            
            item_layout.addWidget(task_label)
            item_layout.addStretch()
            item_layout.addWidget(remove_button)
            
            # Create list item with proper sizing
            item = QListWidgetItem()
            item_widget.adjustSize()  # Make sure widget is properly sized
 
            # Use the widget's size hint for height, maintain width based on content
            item.setSizeHint(QSize(item_widget.sizeHint().width(), 40))

            self.dependencies_list.addItem(item)
            self.dependencies_list.setItemWidget(item, item_widget)
            
            # Update height based on actual content
            total_height = 0
            for index in range(self.dependencies_list.count()):
                total_height += 50  # Since we're using 40 as item height in setSizeHint

            # Add a small buffer for borders
            self.dependencies_list.setFixedHeight(total_height )
            
            # Connect remove button
            remove_button.clicked.connect(lambda: self.remove_dependency(item))
            
            # Emit signal to save dependency
            self.dependency_added.emit(task_title)

    def remove_dependency(self, item):
        widget = self.dependencies_list.itemWidget(item)
        task_title = widget.layout().itemAt(0).widget().text()
        row = self.dependencies_list.row(item)
        self.dependencies_list.takeItem(row)
        
        # Emit signal to remove dependency
        self.dependency_removed.emit(task_title)


######################################################################################

# Attachment Section

    def add_attachments(self, attachments):
        """Add attachments to the section."""
        # Clear any existing attachment widgets
        if hasattr(self, 'attachments_widget'):
            self.content_layout.removeWidget(self.attachments_widget)
            self.attachments_widget.deleteLater()
            
        self.attachments_layout = QVBoxLayout()
        self.attachments_widget = QWidget()
        self.attachments_widget.setStyleSheet("background: transparent; border: none")
        self.attachments_widget.setLayout(self.attachments_layout)
        
        # Add header with Add button
        header_layout = QHBoxLayout()
        header_label = QLabel("Files:")
        add_button = QPushButton("+")
        add_button.setFixedSize(24, 24)
        add_button.clicked.connect(self.add_attachment_clicked.emit)
        
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        header_layout.addWidget(add_button)
        
        header_widget = QWidget()
        header_widget.setLayout(header_layout)
        self.attachments_layout.addWidget(header_widget)
        
        print(f"attachements: {attachments}")
        # Add attachments
        if attachments:
            for attachment in attachments:
                self.add_attachment_item(attachment)
        else:
            self.attachments_layout.addWidget(QLabel("No attachments"))
            
        self.content_layout.addWidget(self.attachments_widget)
    
    def add_attachment_item(self, attachment):
        """Add a single attachment item with link and remove button."""
        item_layout = QHBoxLayout()
        item_layout.setContentsMargins(5, 2, 5, 2)  # Reduced margins
        
        # Set up folder icon
        folder_label = QLabel()
        folder_label.setAlignment(Qt.AlignCenter)
        folder_label.setFixedSize(24, 24)  # Fixed size for icon container
        
        # Set the folder icon
        folder_icon = QIcon.fromTheme("folder")  # Using system theme icon
        if folder_icon.isNull():
            folder_icon = self.style().standardIcon(self.style().SP_DirIcon)
        folder_label.setPixmap(folder_icon.pixmap(16, 16))  # Smaller icon
        
        # Display filename from the path - with constraints for long names
        filename = os.path.basename(attachment.file_path)
        
        # Create link with text elision for long filenames
        link = QLabel()
        link.setText(f"<a href='{attachment.file_path}'>{filename}</a>")
        link.setTextInteractionFlags(Qt.TextBrowserInteraction)
        link.linkActivated.connect(lambda url: self.attachment_clicked.emit(url))
        
        # Important settings to handle long filenames
        link.setWordWrap(True)  # Enable word wrapping
        link.setMaximumWidth(200)  # Set a maximum width
        link.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        
        # Create remove button
        remove_btn = QPushButton("×")
        remove_btn.setFixedSize(20, 20)
        remove_btn.clicked.connect(lambda: self.attachment_removed.emit(attachment))
        
        # Add widgets to layout
        item_layout.addWidget(folder_label)
        item_layout.addWidget(link, 1)  # Add stretch factor
        item_layout.addWidget(remove_btn)
        
        # Create the container widget with size constraints
        item_widget = QWidget()
        item_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        item_widget.setLayout(item_layout)
        
        self.attachments_layout.addWidget(item_widget)