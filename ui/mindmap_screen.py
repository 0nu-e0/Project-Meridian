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
                             QStyleFactory, QListView, QLayout, QDialog, QSlider
                             )
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QEvent, QSize, QDateTime, QUrl, QTimer, QLineF
from PyQt5.QtGui import (QColor, QPainter, QBrush, QPen, QMovie, QTextCharFormat, QColor, QIcon, QPixmap, QDesktopServices

                        )
from PyQt5.QtSvg import QSvgWidget


class ZoomableGraphicsView(QGraphicsView):
    """
    QGraphicsView with built-in zoom controls via mouse wheel and keyboard.
    """
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setDragMode(QGraphicsView.NoDrag)

        # Zoom limits
        self.min_zoom = 0.1
        self.max_zoom = 5.0
        self.zoom_factor = 1.15

    def wheelEvent(self, event):
        """Handle mouse wheel for zooming"""
        # Only zoom with Ctrl key pressed
        if event.modifiers() & Qt.ControlModifier:
            # Get the current zoom level
            current_scale = self.transform().m11()

            # Determine zoom direction
            if event.angleDelta().y() > 0:
                # Zoom in
                new_scale = current_scale * self.zoom_factor
                if new_scale <= self.max_zoom:
                    self.scale(self.zoom_factor, self.zoom_factor)
                    self._notify_zoom_change()
            else:
                # Zoom out
                new_scale = current_scale / self.zoom_factor
                if new_scale >= self.min_zoom:
                    self.scale(1 / self.zoom_factor, 1 / self.zoom_factor)
                    self._notify_zoom_change()

            event.accept()
        else:
            # Normal scrolling
            super().wheelEvent(event)

    def _notify_zoom_change(self):
        """Notify parent widget of zoom change"""
        parent = self.parent()
        while parent:
            if hasattr(parent, 'update_zoom_ui'):
                parent.update_zoom_ui()
                break
            parent = parent.parent()

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts for zoom"""
        if event.modifiers() & Qt.ControlModifier:
            if event.key() == Qt.Key_Plus or event.key() == Qt.Key_Equal:
                # Zoom in
                current_scale = self.transform().m11()
                if current_scale * self.zoom_factor <= self.max_zoom:
                    self.scale(self.zoom_factor, self.zoom_factor)
                    self._notify_zoom_change()
                event.accept()
                return
            elif event.key() == Qt.Key_Minus:
                # Zoom out
                current_scale = self.transform().m11()
                if current_scale / self.zoom_factor >= self.min_zoom:
                    self.scale(1 / self.zoom_factor, 1 / self.zoom_factor)
                    self._notify_zoom_change()
                event.accept()
                return
            elif event.key() == Qt.Key_0:
                # Reset zoom to 100%
                self.resetTransform()
                self._notify_zoom_change()
                event.accept()
                return

        super().keyPressEvent(event)

    def get_zoom_percentage(self):
        """Get current zoom level as percentage"""
        return int(self.transform().m11() * 100)


class SpatialTracker:
    """
    Efficiently tracks objects in scene space for fast queries.
    Maintains incrementally-updated bounding box of all content.
    """
    def __init__(self):
        self.objects = {}  # {node_id: QRectF (scene bounds)}
        self._content_bounds = None  # Cached bounding box of all content
        self._dirty = False  # Flag to recalculate bounds

    def add_object(self, node_id, bounds_rect):
        """Add or update object bounds"""
        self.objects[node_id] = bounds_rect
        self._expand_bounds(bounds_rect)

    def remove_object(self, node_id):
        """Remove object and mark bounds for recalculation"""
        if node_id in self.objects:
            del self.objects[node_id]
            self._dirty = True

    def update_object(self, node_id, new_bounds):
        """Update object position/size"""
        self.objects[node_id] = new_bounds
        self._expand_bounds(new_bounds)

    def get_content_bounds(self):
        """Get bounding box of all content - O(1) if not dirty"""
        if self._dirty or self._content_bounds is None:
            self._recalculate_bounds()
        return self._content_bounds

    def _expand_bounds(self, rect):
        """Incrementally expand bounds (faster than full recalc)"""
        if self._content_bounds is None:
            from PyQt5.QtCore import QRectF
            self._content_bounds = QRectF(rect)
        else:
            self._content_bounds = self._content_bounds.united(rect)

    def _recalculate_bounds(self):
        """Full recalculation when object is removed"""
        from PyQt5.QtCore import QRectF
        if not self.objects:
            self._content_bounds = QRectF(0, 0, 0, 0)
        else:
            bounds = None
            for rect in self.objects.values():
                if bounds is None:
                    bounds = QRectF(rect)
                else:
                    bounds = bounds.united(rect)
            self._content_bounds = bounds
        self._dirty = False

    def get_objects_in_rect(self, query_rect):
        """Find all objects intersecting a rectangle (for selection)"""
        return [oid for oid, rect in self.objects.items()
                if rect.intersects(query_rect)]

    def clear(self):
        """Clear all tracked objects"""
        self.objects.clear()
        self._content_bounds = None
        self._dirty = False


class MindMapScreen(QWidget):
    def __init__(self, logger, parent=None):
        super().__init__(parent)
        self.logger = logger
        self.current_mindmap_id = None  # Track currently loaded mindmap

        # Create the QGraphicsScene and ZoomableGraphicsView.
        self.scene = GridScene(grid_size=25, parent=self)
        self.view = ZoomableGraphicsView(self.scene)

        # Create buttons for user actions.
        self.addButton = QPushButton("Add Node")
        self.saveButton = QPushButton("Save Mind Map")
        self.loadButton = QPushButton("Load Mind Map")
        self.clearButton = QPushButton("Clear Map")
        self.zoomToFitButton = QPushButton("🔍 Zoom to Fit")
        self.viewProjectButton = QPushButton("📁 View Project")
        self.viewProjectButton.setVisible(False)  # Hidden by default

        # Create zoom control widgets
        self.zoomInButton = QPushButton("+")
        self.zoomOutButton = QPushButton("-")
        self.zoomResetButton = QPushButton("100%")
        self.zoomLabel = QLabel("Zoom: 100%")
        self.zoomLabel.setAlignment(Qt.AlignCenter)

        # Create zoom slider (10% to 500%)
        self.zoomSlider = QSlider(Qt.Horizontal)
        self.zoomSlider.setMinimum(10)  # 10%
        self.zoomSlider.setMaximum(500)  # 500%
        self.zoomSlider.setValue(100)  # Start at 100%
        self.zoomSlider.setTickPosition(QSlider.TicksBelow)
        self.zoomSlider.setTickInterval(50)

        # Create grid and snap toggle buttons
        self.gridToggleButton = QPushButton("✓ Show Grid")
        self.gridToggleButton.setCheckable(True)
        self.gridToggleButton.setChecked(True)  # Grid on by default
        self.snapToggleButton = QPushButton("✓ Snap to Grid")
        self.snapToggleButton.setCheckable(True)
        self.snapToggleButton.setChecked(True)  # Snap on by default

        # Connect buttons to their respective functions.
        self.addButton.clicked.connect(self.add_node)
        self.saveButton.clicked.connect(self.save_mind_map)
        self.loadButton.clicked.connect(self.load_mind_map)
        self.clearButton.clicked.connect(self.clear_map)
        self.zoomToFitButton.clicked.connect(self.zoom_to_content)
        self.viewProjectButton.clicked.connect(self.view_linked_project)

        # Connect zoom controls
        self.zoomInButton.clicked.connect(self.zoom_in)
        self.zoomOutButton.clicked.connect(self.zoom_out)
        self.zoomResetButton.clicked.connect(self.zoom_reset)
        self.zoomSlider.valueChanged.connect(self.on_zoom_slider_changed)

        # Connect grid and snap toggles
        self.gridToggleButton.clicked.connect(self.toggle_grid)
        self.snapToggleButton.clicked.connect(self.toggle_snap)

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

        # Add Zoom Controls section
        zoom_label_header = QLabel("Zoom Controls")
        zoom_label_header.setStyleSheet("font-weight: bold; font-size: 12px;")
        left_layout.addWidget(zoom_label_header)

        # Add zoom percentage display
        left_layout.addWidget(self.zoomLabel)

        # Add zoom slider
        left_layout.addWidget(self.zoomSlider)

        # Add zoom buttons in a horizontal layout
        zoom_buttons_layout = QHBoxLayout()
        zoom_buttons_layout.addWidget(self.zoomOutButton)
        zoom_buttons_layout.addWidget(self.zoomResetButton)
        zoom_buttons_layout.addWidget(self.zoomInButton)
        left_layout.addLayout(zoom_buttons_layout)

        # Add Zoom to Fit button
        left_layout.addWidget(self.zoomToFitButton)

        # Add separator
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.HLine)
        separator2.setFixedHeight(2)
        separator2.setStyleSheet("background-color: #d0d0d0;")
        left_layout.addWidget(separator2)

        # Add Grid Options section
        grid_label_header = QLabel("Grid Options")
        grid_label_header.setStyleSheet("font-weight: bold; font-size: 12px;")
        left_layout.addWidget(grid_label_header)

        # Add grid toggle buttons
        left_layout.addWidget(self.gridToggleButton)
        left_layout.addWidget(self.snapToggleButton)

        # Add separator
        separator3 = QFrame()
        separator3.setFrameShape(QFrame.HLine)
        separator3.setFixedHeight(2)
        separator3.setStyleSheet("background-color: #d0d0d0;")
        left_layout.addWidget(separator3)

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

    def zoom_to_content(self, padding=50):
        """Zoom view to fit all content with padding"""
        content_bounds = self.scene.get_content_bounds()

        if content_bounds.isNull() or content_bounds.isEmpty():
            # No content, reset to center
            self.view.resetTransform()
            self.update_zoom_ui()
            return

        # Add padding around content
        padded_bounds = content_bounds.adjusted(-padding, -padding,
                                                padding, padding)

        # Fit the view to show padded bounds
        self.view.fitInView(padded_bounds, Qt.KeepAspectRatio)

        # Optional: Clamp zoom level to reasonable range
        current_scale = self.view.transform().m11()
        if current_scale > 3.0:  # Too zoomed in
            self.view.resetTransform()
            self.view.scale(3.0, 3.0)
            self.view.centerOn(content_bounds.center())
        elif current_scale < 0.1:  # Too zoomed out
            self.view.resetTransform()
            self.view.scale(0.1, 0.1)
            self.view.centerOn(content_bounds.center())

        self.update_zoom_ui()

    def zoom_in(self):
        """Zoom in using the view's zoom method"""
        current_scale = self.view.transform().m11()
        if current_scale * self.view.zoom_factor <= self.view.max_zoom:
            self.view.scale(self.view.zoom_factor, self.view.zoom_factor)
            self.update_zoom_ui()

    def zoom_out(self):
        """Zoom out using the view's zoom method"""
        current_scale = self.view.transform().m11()
        if current_scale / self.view.zoom_factor >= self.view.min_zoom:
            self.view.scale(1 / self.view.zoom_factor, 1 / self.view.zoom_factor)
            self.update_zoom_ui()

    def zoom_reset(self):
        """Reset zoom to 100%"""
        self.view.resetTransform()
        self.update_zoom_ui()

    def on_zoom_slider_changed(self, value):
        """Handle zoom slider value change"""
        # Convert slider value (10-500) to scale factor
        target_scale = value / 100.0

        # Get current scale
        current_scale = self.view.transform().m11()

        # Calculate the ratio to reach target scale
        if current_scale > 0:
            ratio = target_scale / current_scale
            self.view.scale(ratio, ratio)

        # Update UI without triggering slider again
        self.update_zoom_ui(update_slider=False)

    def update_zoom_ui(self, update_slider=True):
        """Update zoom percentage label and slider"""
        zoom_percent = self.view.get_zoom_percentage()

        # Update label
        self.zoomLabel.setText(f"Zoom: {zoom_percent}%")

        # Update slider (avoid feedback loop)
        if update_slider:
            self.zoomSlider.blockSignals(True)
            self.zoomSlider.setValue(zoom_percent)
            self.zoomSlider.blockSignals(False)

    def toggle_grid(self):
        """Toggle grid visibility"""
        is_checked = self.gridToggleButton.isChecked()
        self.scene.grid_visible = is_checked

        # Update button text
        if is_checked:
            self.gridToggleButton.setText("✓ Show Grid")
        else:
            self.gridToggleButton.setText("Show Grid")

        # Force scene redraw
        self.scene.update()

    def toggle_snap(self):
        """Toggle snap-to-grid"""
        is_checked = self.snapToggleButton.isChecked()
        self.scene.snap_to_grid = is_checked

        # Update button text
        if is_checked:
            self.snapToggleButton.setText("✓ Snap to Grid")
        else:
            self.snapToggleButton.setText("Snap to Grid")

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
        self.spatial_tracker = SpatialTracker()
        self.grid_visible = True  # Grid visibility toggle
        self.snap_to_grid = True  # Snap to grid toggle

    def addItem(self, item):
        """Override to track NodeItems"""
        super().addItem(item)
        if isinstance(item, NodeItem):
            bounds = item.sceneBoundingRect()
            self.spatial_tracker.add_object(item.id, bounds)

    def removeItem(self, item):
        """Override to untrack NodeItems"""
        if isinstance(item, NodeItem):
            self.spatial_tracker.remove_object(item.id)
        super().removeItem(item)

    def clear(self):
        """Override to clear spatial tracker"""
        self.spatial_tracker.clear()
        super().clear()

    def get_content_bounds(self):
        """Public API for getting all content bounds"""
        return self.spatial_tracker.get_content_bounds()

    def drawBackground(self, painter, rect):
        # Fill the background with white
        painter.fillRect(rect, Qt.white)

        # Skip grid rendering if grid is not visible
        if not self.grid_visible:
            return

        # Get current scale/zoom level from the view
        scale_factor = 1.0
        if self.views():
            view = self.views()[0]
            scale_factor = view.transform().m11()

        # Adaptive grid spacing based on zoom level
        # At high zoom (>2x), show finer grid
        # At low zoom (<0.5x), show coarser grid
        fine_grid = self.grid_size
        major_grid = self.grid_size * 4

        if scale_factor > 2.0:
            # Zoomed in - show fine grid
            fine_grid = self.grid_size / 2
            major_grid = self.grid_size * 2
        elif scale_factor < 0.5:
            # Zoomed out - show coarse grid only
            fine_grid = self.grid_size * 2
            major_grid = self.grid_size * 8

        # Calculate grid starting points
        left = int(rect.left()) - (int(rect.left()) % int(fine_grid))
        top = int(rect.top()) - (int(rect.top()) % int(fine_grid))

        fine_lines = []
        major_lines = []

        # Create vertical grid lines
        x = left
        while x < rect.right():
            line = QLineF(x, rect.top(), x, rect.bottom())
            if int(x) % int(major_grid) == 0:
                major_lines.append(line)
            else:
                fine_lines.append(line)
            x += fine_grid

        # Create horizontal grid lines
        y = top
        while y < rect.bottom():
            line = QLineF(rect.left(), y, rect.right(), y)
            if int(y) % int(major_grid) == 0:
                major_lines.append(line)
            else:
                fine_lines.append(line)
            y += fine_grid

        # Draw fine grid lines (lighter)
        if fine_lines and scale_factor > 0.25:  # Don't draw fine lines when too zoomed out
            pen = QPen(QColor(240, 240, 240))
            pen.setWidth(1)
            painter.setPen(pen)
            painter.drawLines(fine_lines)

        # Draw major grid lines (darker)
        if major_lines:
            pen = QPen(QColor(200, 200, 200))
            pen.setWidth(1)
            painter.setPen(pen)
            painter.drawLines(major_lines)
