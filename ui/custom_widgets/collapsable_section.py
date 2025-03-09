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
# File: collapsable_section.py
# Description: Used in task_card_expanded to create collapsable sections to add
#              functionality.
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

import os
from resources.styles import AppStyles, AppColors, AppBorders, AppPixelSizes
from PyQt5.QtWidgets import (QApplication, QDesktopWidget, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSpacerItem, 
                             QSizePolicy, QGridLayout, QPushButton, QGraphicsDropShadowEffect, QStyle, QComboBox, QTextEdit,
                             QDateTimeEdit, QLineEdit, QCalendarWidget, QToolButton, QSpinBox, QListWidget, QTabWidget,
                             QMessageBox, QInputDialog, QListWidgetItem, QScrollArea, QTreeWidget, QTreeWidgetItem, QCheckBox,
                             QListView
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

    checklist_item_added = pyqtSignal(str)
    checklist_item_removed = pyqtSignal(str)
    checkbox_state_changed = pyqtSignal(str, bool)

    def __init__(self, title, parent=None):
        super().__init__(parent)  
        self.title = title 
        self.is_collapsed = False

        # This is the key change
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)

        self.setupUI() 

    # Add these methods to your CollapsibleSection class
    def sizeHint(self):
        """Provide a proper size hint that allows horizontal expansion"""
        hint = super().sizeHint()
        hint.setWidth(200)  # Reasonable default width
        return hint

    def resizeEvent(self, event):
        """Handle resizing to ensure content fits within the available width"""
        super().resizeEvent(event)
        
        # Ensure the team list, dependencies list and attachments adapt to the container width
        available_width = self.width() - 30  # Account for margins
        
        # Update lists width if they exist
        if hasattr(self, 'team_list') and self.team_list:
            self.team_list.setMaximumWidth(available_width)
        
        if hasattr(self, 'dependencies_list') and self.dependencies_list:
            self.dependencies_list.setMaximumWidth(available_width)
        
        if hasattr(self, 'attachments_widget') and self.attachments_widget:
            self.attachments_widget.setMaximumWidth(available_width)

    def setupUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Header
        self.header = QWidget()
        self.header.setStyleSheet(AppStyles.header_widget())
        
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(8, 8, 8, 8)

        # Arrow and title
        self.arrow_button = QPushButton("▼")
        self.arrow_button.setFixedSize(20, 20)
        self.arrow_button.setStyleSheet(AppStyles.arrow_button())
        
        title_label = QLabel(self.title)
        title_label.setStyleSheet(AppStyles.label_trans_background())
        
        header_layout.addWidget(title_label)
        header_layout.addStretch(1)
        header_layout.addWidget(self.arrow_button)

        # Content area
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(15, 5, 8, 8)
        self.content_layout.setSpacing(8)
        
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
        self.team_input.setStyleSheet(AppStyles.line_edit_norm())

        add_button = QPushButton("Add")
        add_button.setStyleSheet(AppStyles.add_button())

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
        # print("Collapsing")
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
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)  # CHANGED: to Expanding

        # Create container for combobox section
        self.select_container = QWidget()
        self.select_container.setStyleSheet("border: none;")
        
        select_layout = QHBoxLayout(self.select_container)
        select_layout.setContentsMargins(0, 0, 0, 0)
        
        self.task_combo = QComboBox()
        self.task_combo.setStyleSheet(AppStyles.combo_box_norm())
        self.task_combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)  # ADDED: prevent excessive width expansion
        self.task_combo.setView(QListView())
        
        add_button = QPushButton("Add Dependency")
        add_button.setStyleSheet(AppStyles.add_button())

        select_layout.addWidget(self.task_combo)
        select_layout.addWidget(add_button)

        # Create container for the list
        self.list_container = QWidget()
        self.list_container.setStyleSheet("border: none;")
        self.list_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)  # ADDED: expandable width
        
        list_layout = QVBoxLayout(self.list_container)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(0)

        # Create list for dependencies
        self.dependencies_list = QListWidget()
        self.dependencies_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)  # CHANGED: to Expanding
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
        if task_title and task_title != "None":  # ADDED: check for "None"
            # Create item widget
            item_widget = QWidget()
            item_widget.setStyleSheet("border: none;")
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(5, 8, 5, 8)
            item_layout.setSpacing(8) 

            task_label = QLabel(task_title)
            task_label.setStyleSheet("""
                border: none;
                padding: 2px 0;
            """)
            task_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)  # ADDED: label expands
            
            remove_button = QPushButton("✕")
            remove_button.setStyleSheet(AppStyles.button_normal_delete())
            remove_button.setFixedSize(20, 20)  # ADDED: fixed size
            
            item_layout.addWidget(task_label)
            item_layout.addWidget(remove_button)
            
            # Create list item with FIXED height but adaptive width
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, 40))  # CHANGED: width=0 lets it adapt to container
            
            self.dependencies_list.addItem(item)
            self.dependencies_list.setItemWidget(item, item_widget)
            
            # Update height based on actual content
            total_height = self.dependencies_list.count() * 50  # 40px + some padding
            self.dependencies_list.setFixedHeight(total_height)
            
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
        self.attachments_layout.setSpacing(2)  # Reduce vertical spacing between elements
        self.attachments_widget = QWidget()
        self.attachments_widget.setContentsMargins(0, 0, 0, 3)
        self.attachments_widget.setStyleSheet("background: transparent; border: none")
        self.attachments_widget.setLayout(self.attachments_layout)
        
        # Add header with Add button
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins
        header_label = QLabel("Files:")
        add_button = QPushButton("+")
        add_button.setStyleSheet("""
            QPushButton {
                font-size: 15px;
            }
            QPushButton:hover {
                font-size: 20px;
                font-weight: bold;
            }
        """)
        add_button.setFixedSize(20, 20)
        add_button.clicked.connect(self.add_attachment_clicked.emit)
        
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        header_layout.addWidget(add_button)
        
        header_widget = QWidget()
        header_widget.setLayout(header_layout)
        self.attachments_layout.addWidget(header_widget)

        if attachments:
            open_all_widget = QWidget()
            open_all_layout = QHBoxLayout(open_all_widget)
            open_all_layout.setContentsMargins(0, 0, 0, 0)  # Remove all margins
            open_all_button = QPushButton("Open All")
            open_all_button.setStyleSheet("""
                QPushButton {
                    padding: 2px 4px;  /* Reduce padding */
                }
                QPushButton:hover {
                    text-decoration: underline;
                }
            """)
            open_all_button.clicked.connect(lambda: self.openAllAttachments(attachments))
            open_all_layout.addWidget(open_all_button)
            open_all_layout.setAlignment(Qt.AlignLeft)

            self.attachments_layout.addWidget(open_all_widget)
            self.attachments_layout.setAlignment(Qt.AlignTop)

        # Add attachments
        if attachments:
            for attachment in attachments:
                self.add_attachment_item(attachment)
        else:
            self.attachments_layout.addWidget(QLabel("No attachments"))
        
        self.attachments_layout.addStretch(1)   
        self.content_layout.addWidget(self.attachments_widget)
    
    def add_attachment_item(self, attachment):
        """Add a single attachment item with link and remove button."""
        item_layout = QHBoxLayout()
        item_layout.setContentsMargins(5, 2, 5, 2) 
        
        # Set up folder icon
        folder_label = QLabel()
        folder_label.setAlignment(Qt.AlignCenter)
        folder_label.setFixedSize(24, 24)
        
        # Set the folder icon
        folder_icon = QIcon.fromTheme("folder")  
        if folder_icon.isNull():
            folder_icon = self.style().standardIcon(self.style().SP_DirIcon)
        folder_label.setPixmap(folder_icon.pixmap(16, 16)) 
        
        # Display filename from the path - with constraints for long names
        filename = os.path.basename(attachment.file_path)
        
        # Create link with text elision for long filenames
        link = QLabel()
        link.setText(f"<a href='{attachment.file_path}' style='color: white;'>{filename}</a>")
        link.setTextInteractionFlags(Qt.TextBrowserInteraction)
        link.linkActivated.connect(lambda url: self.attachment_clicked.emit(url))
        
        # Important settings to handle long filenames
        link.setWordWrap(True) 
        link.setMaximumWidth(200) 
        link.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        
        # Create remove button
        remove_btn = QPushButton("×")
        remove_btn.setFixedSize(20, 20)
        remove_btn.clicked.connect(lambda: self.attachment_removed.emit(attachment))
        
        # Add widgets to layout
        item_layout.addWidget(folder_label)
        item_layout.addWidget(link, 1)  
        item_layout.addWidget(remove_btn)
        
        # Create the container widget with size constraints
        item_widget = QWidget()
        item_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        item_widget.setLayout(item_layout)
        
        self.attachments_layout.addWidget(item_widget)

    def openAllAttachments(self, attachments):
        for attachment in attachments:
            self.attachment_clicked.emit(attachment.file_path)

#################################################################################################################################

### Checklist Section

    def add_checklist(self, section_title="Checklist"):
        """Add a checklist section with items that can be checked off"""
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        
        # Store checklist data internally
        if not hasattr(self, 'checklist_data'):
            self.checklist_data = []
        
        # Create the title for the checklist
        checklist_label = QLabel(section_title)
        checklist_label.setStyleSheet(AppStyles.label_lgfnt_bold())
        checklist_label.setContentsMargins(0, 5, 0, 0)
        self.content_layout.addWidget(checklist_label)
        
        # Create input and button in horizontal layout
        input_row = QWidget()
        input_row.setStyleSheet("border: none;")
        input_layout = QHBoxLayout(input_row)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(4)
        
        self.checklist_input = QLineEdit()
        self.checklist_input.setPlaceholderText("Add new item...")
        self.checklist_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #ddd;
                border-radius: 3px;
                padding: 5px;
            }
        """)
        
        add_button = QPushButton("Add")
        add_button.setStyleSheet(AppStyles.add_button())
        
        input_layout.addWidget(self.checklist_input)
        input_layout.addWidget(add_button)
        
        # Create a container for checklist items
        self.checklist_layout = QVBoxLayout()
        self.checklist_layout.setAlignment(Qt.AlignTop)  
        self.checklist_layout.setSpacing(2) 
        self.checklist_layout.setContentsMargins(0, 0, 0, 0)
        
        self.checklist_widget = QWidget()
        self.checklist_widget.setStyleSheet("background: transparent; border: none")
        self.checklist_widget.setLayout(self.checklist_layout)
        
        # Create a scroll area for the checklist widget
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("background: transparent; border: none")
        scroll_area.setFixedHeight(200)
        scroll_area.setWidget(self.checklist_widget)
        
        # Add everything to the content layout
        self.content_layout.addWidget(input_row)
        self.content_layout.addWidget(scroll_area)
        
        # Connect signals
        add_button.clicked.connect(self.add_checklist_item)
        self.checklist_input.returnPressed.connect(self.add_checklist_item)

    def add_checklist_item(self):
        """Add a new item to the checklist"""
        text = self.checklist_input.text().strip()
        if text:
            # Create item layout with fixed height
            item_layout = QHBoxLayout()
            item_layout.setContentsMargins(5, 2, 5, 2)
            item_layout.setSpacing(5)
            
            # Create checkbox (keeping original style)
            checkbox = QCheckBox()
            checkbox.setStyleSheet("""
                QCheckBox::indicator {
                    width: 10px;
                    height: 16px;
                }
                QCheckBox {
                    border: 1px solid #C4C4C4;
                }
            """)
            
            # Create label with fixed height
            label = QLabel(text)
            label.setStyleSheet(f"""
                QLabel {{
                    border: none;
                    background-color: transparent;
                    font-size: {AppPixelSizes.font_norm};
                    padding-left: 5px;
                    }}
            """)
            label.setWordWrap(True)
            
            # Create remove button
            remove_button = QPushButton("✕")
            remove_button.setStyleSheet("""
                QPushButton {
                    border: none;
                    background-color: transparent;
                    color: #999;
                }
                QPushButton:hover {
                    color: #000000;
                }
            """)
            remove_button.setFixedSize(20, 20)
            
            # Add widgets to layout
            item_layout.addWidget(checkbox)
            item_layout.addWidget(label, 1)
            item_layout.addWidget(remove_button)
            
            # Create container widget with fixed height
            item_widget = QWidget()
            item_widget.setStyleSheet("background: transparent")
            item_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
            item_widget.setLayout(item_layout)
            
            # Add to layout (without extra alignment parameters)
            self.checklist_layout.addWidget(item_widget)
            
            # Add to internal data store
            item_data = {
                'text': text,
                'checked': False,
                'widget': item_widget,
                'checkbox': checkbox,
                'label': label
            }
            self.checklist_data.append(item_data)
            
            # Connect signals
            idx = len(self.checklist_data) - 1
            checkbox.stateChanged.connect(lambda state, idx=idx: 
                                        self.update_checklist_item_state(idx, state == Qt.Checked))
            remove_button.clicked.connect(lambda checked=False, item_text=text, idx=idx: 
                                     self.remove_checklist_item(idx, item_text))
            
            # Emit signal for item added (if it exists)
            if hasattr(self, 'checklist_item_added'):
                self.checklist_item_added.emit(text)
            
            # Clear input field
            self.checklist_input.clear()

    def update_checklist_item_state(self, idx, checked):
        """Update the state of a checklist item"""
        if 0 <= idx < len(self.checklist_data):
            # Update the UI data structure with the new state
            self.checklist_data[idx]['checked'] = checked
            
            # Update the UI appearance
            label = self.checklist_data[idx].get('label')
            if label:
                if checked:
                    label.setStyleSheet(AppStyles.label_checklist())
                else:
                    label.setStyleSheet(AppStyles.label_checklist_empty())
            
            # Get the item text so we can pass it to the signal
            item_text = self.checklist_data[idx].get('text', '')
            
            # Emit signal with text and checked state
            self.checkbox_state_changed.emit(item_text, checked)
        
        # Signal that the task has been modified
        if hasattr(self, 'modified'):
            self.modified.emit()

    def remove_checklist_item(self, idx, item_text):
        """Remove an item from the checklist and emit signal with text"""
        if 0 <= idx < len(self.checklist_data):
            # Get the widget to remove
            widget = self.checklist_data[idx]['widget']
            
            # Remove from layout
            self.checklist_layout.removeWidget(widget)
            widget.deleteLater()
            
            # Remove from data store
            self.checklist_data.pop(idx)
            
            # Update indices for remaining items
            self._update_checklist_indices()
            
            # Emit signal with the removed item's text
            self.checklist_item_removed.emit(item_text)

    def _update_checklist_indices(self):
        """Update the indices of checklist items after removal"""
        for i, item_data in enumerate(self.checklist_data):
            # Disconnect old connections
            checkbox = item_data['checkbox']
            checkbox.disconnect()
            
            # Connect with new index
            checkbox.stateChanged.connect(lambda state, idx=i: 
                                        self.update_checklist_item_state(idx, state == Qt.Checked))

    