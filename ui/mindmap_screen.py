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
# File: mindmap_screen.py
# Description: Used to view and create mindmaps
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

import sys, os, json, copy
from utils.tasks_io import load_tasks_from_json, save_task_to_json
from datetime import datetime
from pathlib import Path
from utils.directory_finder import resource_path
from ui.custom_widgets.mindmap_nodes import NodeItem
from ui.custom_widgets.collapsable_section import CollapsibleSection
from resources.styles import AppColors
from resources.styles import AppStyles, AnimatedButton
from PyQt5.QtWidgets import (QApplication, QDesktopWidget, QGraphicsScene, QGraphicsView, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSpacerItem, 
                             QSizePolicy, QGridLayout, QPushButton, QGraphicsDropShadowEffect, QStyle, QComboBox, QTextEdit,
                             QDateTimeEdit, QLineEdit, QCalendarWidget, QToolButton, QSpinBox, QListWidget, QTabWidget,
                             QMessageBox, QInputDialog, QListWidgetItem, QScrollArea, QTreeWidget, QTreeWidgetItem, QFileDialog,
                             QStyleFactory, QListView, QLayout, 
                             )
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QEvent, QSize, QDateTime, QUrl, QTimer, QLineF
from PyQt5.QtGui import (QColor, QPainter, QBrush, QPen, QMovie, QTextCharFormat, QColor, QIcon, QPixmap, QDesktopServices

                        )
from PyQt5.QtSvg import QSvgWidget



class MindMapScreen(QWidget):
    def __init__(self, logger, parent=None):
        super().__init__(parent)
        self.logger = logger
        self.current_mindmap_id = None  # Track currently loaded mindmap

        # Create the QGraphicsScene and QGraphicsView.
        self.scene = GridScene(grid_size=25, parent=self)
        self.view = QGraphicsView(self.scene)

        # Create buttons for user actions.
        self.addButton = QPushButton("Add Node")
        self.saveButton = QPushButton("Save Mind Map")
        self.loadButton = QPushButton("Load Mind Map")
        self.clearButton = QPushButton("Clear Map")
        self.viewProjectButton = QPushButton("📁 View Project")
        self.viewProjectButton.setVisible(False)  # Hidden by default

        # Connect buttons to their respective functions.
        self.addButton.clicked.connect(self.add_node)
        self.saveButton.clicked.connect(self.save_mind_map)
        self.loadButton.clicked.connect(self.load_mind_map)
        self.clearButton.clicked.connect(self.clear_map)
        self.viewProjectButton.clicked.connect(self.view_linked_project)

        self.installEventFilter(self)

        # Initialize UI panels.
        self.initUI()

    def eventFilter(self, watched, event):
        # We filter mouse move events
        if event.type() == QEvent.GraphicsSceneMouseMove:
            pos = event.scenePos()
            # Query the scene directly for the item under the mouse using the
            # view's current transform.
            item = self.scene.itemAt(pos, self.view.transform())

            # Walk up the parent chain to find a node item (has
            # setLinkHandlesVisible) if the immediate item isn't a node itself.
            node = item
            while node and not hasattr(node, 'setLinkHandlesVisible'):
                node = node.parentItem()

            if node and hasattr(node, 'setLinkHandlesVisible'):
                node.setLinkHandlesVisible(True)
                # Hide link handles for all other nodes
                for other in self.scene.items():
                    if other is not node and hasattr(other, 'setLinkHandlesVisible'):
                        other.setLinkHandlesVisible(False)
            else:
                # Hide link handles for all nodes when nothing relevant is hovered
                for other in self.scene.items():
                    if hasattr(other, 'setLinkHandlesVisible'):
                        other.setLinkHandlesVisible(False)
        return super().eventFilter(watched, event)

    def initUI(self):
        self.initCentralWidget()
        self.initBannerSpacer()
        self.addSeparator()
        self.initPanelHorizontalContainer()

    def initCentralWidget(self):
        central_widget = QWidget()
        central_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.main_layout = QVBoxLayout(central_widget)
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

    def initPanelHorizontalContainer(self):
        panel_widget = QWidget()
        panel_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        panel_layout = QHBoxLayout(panel_widget)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.addLayout(self.initLeftPanelWidget(), 1)
        panel_layout.addLayout(self.initRightPanelWidget(), 5)

        self.main_layout.addWidget(panel_widget)

    def initLeftPanelWidget(self):
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(15, 15, 15, 15)
        left_layout.setSpacing(10)

        # Add the buttons to the left panel.
        left_layout.addWidget(self.addButton)
        left_layout.addWidget(self.saveButton)
        left_layout.addWidget(self.loadButton)
        left_layout.addWidget(self.clearButton)

        # Add separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFixedHeight(2)
        separator.setStyleSheet("background-color: #d0d0d0;")
        left_layout.addWidget(separator)

        # Add View Project button (shown only when linked)
        left_layout.addWidget(self.viewProjectButton)

        left_layout.addStretch(1)  # Push the buttons to the top.

        # Add the left panel to the main layout.
        return left_layout

    def initRightPanelWidget(self):
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(15, 15, 15, 15)
        right_layout.addWidget(self.view)

        # Add the right panel to the main layout.
        return right_layout

    def add_node(self):
        # Create a new node and add it to the scene.
        node = NodeItem(0, 0, text="New Node", logger=self.logger)
        self.scene.addItem(node)

    def save_mind_map(self):
        # Serialize and save all NodeItems in the scene.
        nodes = [item.serialize() for item in self.scene.items() if isinstance(item, NodeItem)]
        connections = getattr(self.scene, "connections", [])

        from utils.mindmap_io import update_mindmap, create_mindmap

        # If we have a current mindmap loaded, update it
        if self.current_mindmap_id:
            success = update_mindmap(
                mindmap_id=self.current_mindmap_id,
                nodes=nodes,
                connections=connections,
                logger=self.logger
            )

            if success:
                QMessageBox.information(self, "Success", "Mindmap saved successfully!")
                self.update_view_project_button()
            else:
                QMessageBox.warning(self, "Error", "Failed to save mindmap.")
        else:
            # Create new mindmap - ask for title
            title, ok = QInputDialog.getText(self, "Save Mindmap", "Enter mindmap title:")
            if ok and title:
                mindmap = create_mindmap(
                    title=title,
                    nodes=nodes,
                    connections=connections,
                    logger=self.logger
                )
                self.current_mindmap_id = mindmap.id
                QMessageBox.information(self, "Success", f"Mindmap '{title}' created and saved!")
                self.update_view_project_button()

    def load_mind_map(self):
        # Load mindmap from centralized storage
        from utils.mindmap_io import load_mindmaps_from_json

        mindmaps = load_mindmaps_from_json(self.logger)

        if not mindmaps:
            QMessageBox.information(self, "No Mindmaps", "No saved mindmaps found.")
            return

        # Create dialog to select mindmap
        dialog = QDialog(self)
        dialog.setWindowTitle("Load Mindmap")
        dialog.setModal(True)
        dialog.setMinimumWidth(400)
        dialog.setMinimumHeight(300)

        layout = QVBoxLayout(dialog)

        # Label
        label = QLabel("Select a mindmap to load:")
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

        for mindmap in mindmaps.values():
            item_text = f"🧠 {mindmap.title}"
            if mindmap.project_id:
                item_text += " 📁"  # Indicator for linked project
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, mindmap.id)
            if mindmap.description:
                item.setToolTip(mindmap.description)
            list_widget.addItem(item)

        layout.addWidget(list_widget)

        # Buttons
        from PyQt5.QtWidgets import QDialogButtonBox
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        # Show dialog
        if dialog.exec_() == QDialog.Accepted:
            selected_items = list_widget.selectedItems()
            if selected_items:
                mindmap_id = selected_items[0].data(Qt.UserRole)
                mindmap = mindmaps.get(mindmap_id)

                if mindmap:
                    self.load_mindmap_data(mindmap)

    def load_mindmap_data(self, mindmap):
        """Load mindmap data into the scene"""
        self.clear_map()

        nodes_data = mindmap.nodes or []
        connections_data = mindmap.connections or []

        node_map = {}

        for node_data in nodes_data:
            node = NodeItem(0, 0, logger=self.logger)
            node.deserialize(node_data)
            node_map[node.id] = node
            self.scene.addItem(node)

        # Placeholder for future connection handling
        if connections_data and hasattr(self.scene, "connections"):
            self.scene.connections = connections_data

        # Set current mindmap
        self.current_mindmap_id = mindmap.id
        self.update_view_project_button()

        self.logger.info(f"Loaded mindmap: {mindmap.title}")

    def load_mindmap_by_id(self, mindmap_id: str):
        """Load a specific mindmap by ID (for View Mindmap from project)"""
        from utils.mindmap_io import load_mindmaps_from_json

        mindmaps = load_mindmaps_from_json(self.logger)
        mindmap = mindmaps.get(mindmap_id)

        if mindmap:
            self.load_mindmap_data(mindmap)
        else:
            QMessageBox.warning(self, "Error", f"Mindmap not found: {mindmap_id}")

    def clear_map(self):
        # Remove all items from the scene.
        self.scene.clear()
        self.current_mindmap_id = None
        self.update_view_project_button()

    def update_view_project_button(self):
        """Update View Project button visibility based on linked project"""
        if self.current_mindmap_id:
            from utils.mindmap_io import load_mindmaps_from_json

            mindmaps = load_mindmaps_from_json(self.logger)
            mindmap = mindmaps.get(self.current_mindmap_id)

            if mindmap and mindmap.project_id:
                self.viewProjectButton.setVisible(True)
                self.viewProjectButton.setStyleSheet("""
                    QPushButton {
                        background-color: #3498db;
                        color: white;
                        border: none;
                        padding: 8px;
                        border-radius: 4px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #2980b9;
                    }
                """)
            else:
                self.viewProjectButton.setVisible(False)
        else:
            self.viewProjectButton.setVisible(False)

    def view_linked_project(self):
        """Open the linked project detail view"""
        if not self.current_mindmap_id:
            return

        from utils.mindmap_io import load_mindmaps_from_json

        mindmaps = load_mindmaps_from_json(self.logger)
        mindmap = mindmaps.get(self.current_mindmap_id)

        if mindmap and mindmap.project_id:
            # Signal to main window to open project detail
            if hasattr(self.parent(), 'openProjectDetail'):
                self.parent().openProjectDetail(mindmap.project_id)
            else:
                QMessageBox.information(
                    self,
                    "View Project",
                    f"Project ID: {mindmap.project_id}\n\nProject detail integration will be completed in the next step."
                )


class GridScene(QGraphicsScene):
    """
    A QGraphicsScene that renders a visible grid in the background.
    """
    def __init__(self, grid_size=25, parent=None):
        super().__init__(parent)
        self.grid_size = grid_size

    def drawBackground(self, painter, rect):
        # Fill the background with white (or any color you want)
        painter.fillRect(rect, Qt.white)

        # Make lines for the grid. We'll start at the nearest multiple of grid_size
        left = int(rect.left()) - (int(rect.left()) % self.grid_size)
        top = int(rect.top()) - (int(rect.top()) % self.grid_size)

        lines = []
        # Create vertical grid lines
        x = left
        while x < rect.right():
            lines.append(QLineF(x, rect.top(), x, rect.bottom()))
            x += self.grid_size

        # Create horizontal grid lines
        y = top
        while y < rect.bottom():
            lines.append(QLineF(rect.left(), y, rect.right(), y))
            y += self.grid_size

        # Draw them with a light pen so you see the grid
        pen = QPen(Qt.lightGray)
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawLines(lines)
