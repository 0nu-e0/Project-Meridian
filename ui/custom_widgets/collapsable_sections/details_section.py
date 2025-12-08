import sys, os, json, copy
from functools import partial
from utils.tasks_io import load_tasks_from_json, save_task_to_json
from datetime import datetime
from pathlib import Path
from utils.directory_finder import resource_path
from models.task import Task, TaskCategory, TaskPriority, TaskStatus, Attachment, TaskEntry, TimeLog
from ui.custom_widgets.collapsable_section import CollapsibleSection
from resources.styles import AppColors
from resources.styles import AppStyles, AnimatedButton
from PyQt5.QtWidgets import (QApplication, QDesktopWidget, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSpacerItem,
                             QSizePolicy, QGridLayout, QPushButton, QGraphicsDropShadowEffect, QStyle, QComboBox, QTextEdit,
                             QDateTimeEdit, QLineEdit, QCalendarWidget, QToolButton, QSpinBox, QListWidget, QTabWidget,
                             QMessageBox, QInputDialog, QListWidgetItem, QScrollArea, QTreeWidget, QTreeWidgetItem, QFileDialog,
                             QStyleFactory, QListView
                             )
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QEvent, QSize, QDateTime, QUrl, QTimer
from PyQt5.QtGui import (QColor, QPainter, QBrush, QPen, QMovie, QTextCharFormat, QColor, QIcon, QPixmap, QDesktopServices,

                        )
from PyQt5.QtSvg import QSvgWidget


class DetailsCollapsableSection(QWidget):

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

            remove_button.clicked.connect(partial(self.remove_team_member, item))
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