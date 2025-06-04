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

        # Create the QGraphicsScene and QGraphicsView.
        self.scene = GridScene(grid_size=25, parent=self)
        self.view = QGraphicsView(self.scene)

        # Create buttons for user actions.
        self.addButton = QPushButton("Add Node")
        self.saveButton = QPushButton("Save Mind Map")
        self.loadButton = QPushButton("Load Mind Map")
        self.clearButton = QPushButton("Clear Map")

        # Connect buttons to their respective functions.
        self.addButton.clicked.connect(self.add_node)
        self.saveButton.clicked.connect(self.save_mind_map)
        self.loadButton.clicked.connect(self.load_mind_map)
        self.clearButton.clicked.connect(self.clear_map)

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
        fileName, _ = QFileDialog.getSaveFileName(self, "Save Mind Map", "", "JSON Files (*.json)")
        if fileName:
            with open(fileName, 'w') as f:
                json.dump(nodes, f, indent=4)

    def load_mind_map(self):
        # Load and deserialize nodes from a JSON file.
        fileName, _ = QFileDialog.getOpenFileName(self, "Load Mind Map", "", "JSON Files (*.json)")
        if fileName:
            with open(fileName, 'r') as f:
                nodes_data = json.load(f)
            self.clear_map()  # Clear existing items in the scene.
            for node_data in nodes_data:
                node = NodeItem(0, 0, logger=self.logger)
                node.deserialize(node_data)
                self.scene.addItem(node)

    def clear_map(self):
        # Remove all items from the scene.
        self.scene.clear()


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
