

import sys, os, json, copy
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from utils.tasks_io import load_tasks_from_json, save_task_to_json
from utils.directory_finder import resource_path
from models.task import Task, TaskCategory, TaskPriority, TaskStatus, Attachment, TaskEntry, TimeLog
from ui.custom_widgets.collapsable_section import CollapsibleSection
from resources.styles import AppColors
from resources.styles import AppStyles, AnimatedButton
from PyQt5.QtWidgets import (QApplication, QDesktopWidget, QGraphicsLineItem, QGraphicsEllipseItem, QGraphicsItem, QGraphicsTextItem, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSpacerItem, 
                             QSizePolicy, QGridLayout, QPushButton, QGraphicsDropShadowEffect, QStyle, QComboBox, QTextEdit,
                             QDateTimeEdit, QLineEdit, QCalendarWidget, QToolButton, QSpinBox, QListWidget, QTabWidget, QGraphicsRectItem,
                             QMessageBox, QInputDialog, QListWidgetItem, QScrollArea, QTreeWidget, QTreeWidgetItem, QFileDialog,
                             QStyleFactory, QListView, QLayout
                             )
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QEvent, QSize, QDateTime, QUrl, QTimer, QPointF
from PyQt5.QtGui import (QColor, QPainter, QBrush, QPen, QMovie, QTextCharFormat, QColor, QIcon, QPixmap, QDesktopServices, 
                        
                        )
from PyQt5.QtSvg import QSvgWidget

class LinkHandle(QGraphicsEllipseItem):
    def __init__(self, parent_node, handle_position_flag, radius=6):
        super().__init__(0, 0, radius * 2, radius * 2, parent_node)
        self.parent_node = parent_node
        self.handle_position_flag = handle_position_flag

        # Style: gray fill, no outline
        self.setBrush(QBrush(QColor(150, 150, 150)))
        self.setPen(QPen(Qt.NoPen))

        # We do manual dragging to avoid recursion with ItemIsMovable
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.LeftButton)

        self.dragging = False
        self.temp_line = None  # QGraphicsLineItem for the leader line
        self.start_scene_pos = None
        self.last_hovered_node = None  # To track the previously hovered node

    def find_node_item(self, item):
        """
        Recursively check if the given item or one of its parents is a NodeItem
        (i.e., has a setLinkHandlesVisible method). This helps us find the underlying node
        even if the top item is a temporary line or another child item.
        """
        while item is not None:
            if hasattr(item, 'setLinkHandlesVisible'):
                return item
            item = item.parentItem()
        return None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True

            # The handle's center in scene coords:
            local_center = self.rect().center()
            self.start_scene_pos = self.mapToScene(local_center)

            # Create a temporary line from start_scene_pos -> start_scene_pos
            if self.scene():
                pen = QPen(QColor("blue"))
                pen.setWidth(2)
                self.temp_line = QGraphicsLineItem()
                self.temp_line.setPen(pen)
                self.temp_line.setLine(
                    self.start_scene_pos.x(), self.start_scene_pos.y(),
                    self.start_scene_pos.x(), self.start_scene_pos.y()
                )
                # Make the line ignore mouse events so it doesn't block detection.
                self.temp_line.setAcceptedMouseButtons(Qt.NoButton)
                self.scene().addItem(self.temp_line)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        current_pos = event.scenePos()
        if self.dragging and self.temp_line is not None:
            # Update the temporary line's endpoint.
            self.temp_line.setLine(
                self.start_scene_pos.x(), self.start_scene_pos.y(),
                current_pos.x(), current_pos.y()
            )
            
            # Print the source (originating) node's info.
            print(f"Source node id: {self.parent_node.id}, handle: {self.handle_position_flag}")

            # Iterate through all NodeItems in the scene.
            for item in self.scene().items():
                if isinstance(item, NodeItem):
                    # Skip the source node.
                    if item == self.parent_node:
                        continue

                    # Convert the current scene position to the node's coordinate space.
                    pos_in_item = item.mapFromScene(current_pos)
                    if item.contains(pos_in_item):
                        # The mouse is over this node.
                        hovered_handle = None
                        # Check which link handle of the node is under the cursor.
                        for handle in (item.link_handle_top, item.link_handle_bottom, 
                                    item.link_handle_left, item.link_handle_right):
                            pos_in_handle = handle.mapFromScene(current_pos)
                            if handle.contains(pos_in_handle):
                                hovered_handle = handle
                                break
                        if hovered_handle:
                            print(f"Hovered node id: {item.id}, handle: {hovered_handle.handle_position_flag}")
                        else:
                            print(f"Hovered node id: {item.id}, but no specific handle hovered")
                        # Ensure the node shows its link handles.
                        item.setLinkHandlesVisible(True)
                    else:
                        item.setLinkHandlesVisible(False)
            event.accept()
        else:
            super().mouseMoveEvent(event)



    def mouseReleaseEvent(self, event):
        if self.dragging and event.button() == Qt.LeftButton:
            self.dragging = False

            # Remove the temporary line.
            if self.temp_line and self.scene():
                self.scene().removeItem(self.temp_line)
            self.temp_line = None

            # Clear any hovered node state.
            if self.last_hovered_node:
                self.last_hovered_node.setLinkHandlesVisible(False)
                self.last_hovered_node = None

            # Check if we're over another node to finalize the link.
            release_pos = event.scenePos()
            item_at_pos = None
            if self.scene() and self.scene().views():
                view = self.scene().views()[0]
                item_at_pos = self.scene().itemAt(release_pos, view.transform())
            target_node = self.find_node_item(item_at_pos)
            if target_node and hasattr(target_node, 'is_node_item') and target_node != self.parent_node:
                # Finalize the link between self.parent_node and target_node.
                # e.g. self.scene().create_link(self.parent_node, target_node)
                pass

            event.accept()
        else:
            super().mouseReleaseEvent(event)



class ResizeHandle(QGraphicsRectItem):
    def __init__(self, parent_node, corner_flag, size=10):
        super().__init__(0, 0, size, size, parent_node)
        self.parent_node = parent_node
        self.corner_flag = corner_flag
        # Set a transparent brush for no fill.
        self.setBrush(QBrush(Qt.transparent))
        # Set a pen for the outline (here a gray color).
        self.setPen(QPen(QColor(150, 150, 150)))
        
        # We do NOT set ItemIsMovable to avoid recursion.
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.LeftButton)

        self.dragging = False
        self.orig_width = None
        self.orig_height = None
        self.drag_start_scene_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.orig_width = self.parent_node.width
            self.orig_height = self.parent_node.height
            self.drag_start_scene_pos = event.scenePos()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.dragging:
            dx = event.scenePos().x() - self.drag_start_scene_pos.x()
            dy = event.scenePos().y() - self.drag_start_scene_pos.y()

            new_w = self.orig_width
            new_h = self.orig_height

            if self.corner_flag == "bottom_right":
                new_w = self.orig_width + dx
                new_h = self.orig_height + dy
            elif self.corner_flag == "bottom_left":
                new_w = self.orig_width - dx
                new_h = self.orig_height + dy
            elif self.corner_flag == "top_right":
                new_w = self.orig_width + dx
                new_h = self.orig_height - dy
            elif self.corner_flag == "top_left":
                new_w = self.orig_width - dx
                new_h = self.orig_height - dy

            min_w, min_h = 50, 40
            if new_w < min_w:
                new_w = min_w
            if new_h < min_h:
                new_h = min_h

            self.parent_node.setSizeKeepCenter(new_w, new_h)
            self.parent_node.update_node_layout()
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.dragging and event.button() == Qt.LeftButton:
            self.dragging = False
            event.accept()
        else:
            super().mouseReleaseEvent(event)

class NodeItem(QGraphicsEllipseItem):
    """
    A node:
      - Always visible ellipse with text in the center
      - Four corner handles (and link handles) that appear only if selected
      - Resizes around its center
      - Grows if text is bigger than default
      - Movable, selectable, and snaps its center to grid intersections
    """
    def __init__(self, width=120, height=80, text="Node", parent=None):
        super().__init__(0, 0, width, height, parent)
        self.id = str(uuid4())
        print(f"Dropping node id: {self.id}")
        self.width = width
        self.height = height

        # Make the ellipse easy to see:
        self.setPen(QPen(QColor("black"), 2))   # black outline, 2 px thick
        self.setBrush(QBrush(QColor("lightblue")))  # fill with light blue

        # Let the user select and move the node and send geometry changes
        self.setFlags(
            QGraphicsEllipseItem.ItemIsSelectable |
            QGraphicsEllipseItem.ItemIsMovable |
            QGraphicsEllipseItem.ItemSendsGeometryChanges
        )
        # Accept hover events on the node
        self.setAcceptHoverEvents(True)

        # Create a text item. By default, we'll wrap at (width - 10).
        self.text_item = QGraphicsTextItem(text, self)
        self.text_item.setDefaultTextColor(QColor("black"))
        self.text_item.setTextWidth(max(0, self.width - 10))
        self.text_item.document().adjustSize()
        # Make sure clicks on the text go through to the ellipse
        self.text_item.setAcceptedMouseButtons(Qt.NoButton)

        # Expand the node if the text is bigger than the default size
        self.text_item.document().adjustSize()
        txt_bounds = self.text_item.boundingRect()
        if txt_bounds.width() > self.width:
            self.width = txt_bounds.width() + 10
        if txt_bounds.height() > self.height:
            self.height = txt_bounds.height() + 10

        # Create the 4 corner handles, initially hidden
        self.handle_top_left = ResizeHandle(self, "top_left")
        self.handle_top_right = ResizeHandle(self, "top_right")
        self.handle_bottom_left = ResizeHandle(self, "bottom_left")
        self.handle_bottom_right = ResizeHandle(self, "bottom_right")

        self.link_handle_top = LinkHandle(self, "top")
        self.link_handle_bottom = LinkHandle(self, "bottom")
        self.link_handle_right = LinkHandle(self, "right")
        self.link_handle_left = LinkHandle(self, "left")

        # Hide the handles initially
        self.setHandlesVisible(False)
        self.setLinkHandlesVisible(False)

        self.update_node_layout()

        # Explicitly snap the initial position so that the node's center lies on a grid intersection.
        self.setPos(self.snapPosition())

    def snapPosition(self):
        """Compute and return a snapped top-left position so that the node’s center aligns with grid intersections."""
        grid_size = 25
        # current position (top-left)
        pos = self.pos()
        # compute center from current top-left:
        center = pos + QPointF(self.width / 2, self.height / 2)
        # Snap center:
        snapped_center_x = round(center.x() / grid_size) * grid_size
        snapped_center_y = round(center.y() / grid_size) * grid_size
        snapped_center = QPointF(snapped_center_x, snapped_center_y)
        # Compute new top-left so that the node’s center is at the snapped center.
        return snapped_center - QPointF(self.width / 2, self.height / 2)
    
    def hoverEnterEvent(self, event):
        # Show link handles on hover
        self.setLinkHandlesVisible(True)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        # Hide link handles when not hovered
        self.setLinkHandlesVisible(False)
        super().hoverLeaveEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        grid_size = 25
        # Compute the node's center based on its current position.
        center = self.pos() + QPointF(self.width / 2, self.height / 2)
        snapped_center_x = round(center.x() / grid_size) * grid_size
        snapped_center_y = round(center.y() / grid_size) * grid_size
        snapped_center = QPointF(snapped_center_x, snapped_center_y)
        # Compute new top-left position so that the center is at the snapped point.
        new_pos = snapped_center - QPointF(self.width / 2, self.height / 2)
        self.setPos(new_pos)

    def itemChange(self, change, value):

        if change == QGraphicsItem.ItemSelectedHasChanged:
            self.setHandlesVisible(bool(value))
        elif change == QGraphicsItem.ItemPositionChange:
            grid_size = 25  # grid spacing in pixels
            # 'value' is the proposed new top-left position.
            # Compute the center:
            center = value + QPointF(self.width / 2, self.height / 2)
            # Snap the center to the nearest grid intersection.
            snapped_center_x = round(center.x() / grid_size) * grid_size
            snapped_center_y = round(center.y() / grid_size) * grid_size
            snapped_center = QPointF(snapped_center_x, snapped_center_y)
            # Compute new top-left so that the node's center is at the snapped point.
            new_pos = snapped_center - QPointF(self.width / 2, self.height / 2)
            return new_pos
        return super().itemChange(change, value)

    def setHandlesVisible(self, visible):
        """Hide or show the 4 corner handles."""
        self.handle_top_left.setVisible(visible)
        self.handle_top_right.setVisible(visible)
        self.handle_bottom_left.setVisible(visible)
        self.handle_bottom_right.setVisible(visible)


    def setLinkHandlesVisible(self, visible):
        self.link_handle_top.setVisible(visible)
        self.link_handle_bottom.setVisible(visible)
        self.link_handle_right.setVisible(visible)
        self.link_handle_left.setVisible(visible)

    def setSizeKeepCenter(self, new_w, new_h):
        """
        Resize around the node's center in scene coords.
        """
        old_center = self.mapToScene(self.width / 2, self.height / 2)
        self.width = new_w
        self.height = new_h
        self.setRect(0, 0, new_w, new_h)
        new_center = self.mapToScene(self.width / 2, self.height / 2)
        offset = old_center - new_center
        self.setPos(self.pos() + offset)

    def update_node_layout(self):
        """
        Position bounding rect, corner handles, and text.
        """
        self.setRect(0, 0, self.width, self.height)

        # If you want the handles to be slightly outside the corners:
        size = self.handle_bottom_left.rect().width()  # typically 10
        half = size / 2

        # We place each handle so its center is at the corner
        # e.g. top-left corner is (0,0), we move handle's center to that point:
        self.handle_top_left.setPos(0 - half, 0 - half)
        self.handle_top_right.setPos(self.width - half, 0 - half)
        self.handle_bottom_left.setPos(0 - half, self.height - half)
        self.handle_bottom_right.setPos(self.width - half, self.height - half)

        self.link_handle_top.setPos(self.width / 2 - half, 0 - half)
        self.link_handle_bottom.setPos(self.width / 2 - half, self.height - half)
        self.link_handle_right.setPos(self.width - half, self.height / 2 - half)
        self.link_handle_left.setPos(0 - half, self.height / 2 - half)

        # Re-center the text
        self.center_text_item()

    def center_text_item(self):
        """
        Position the text in the middle of the ellipse.
        Re-check text wrapping for the new node width.
        """
        self.text_item.setTextWidth(self.width - 10)
        self.text_item.document().adjustSize()
        txt_bounds = self.text_item.boundingRect()
        new_x = (self.width - txt_bounds.width()) / 2
        new_y = (self.height - txt_bounds.height()) / 2
        self.text_item.setPos(new_x, new_y)
