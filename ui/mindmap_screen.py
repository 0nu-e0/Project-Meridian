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

import json
from utils.constants import MAIN_PANEL_STRETCH, SIDE_PANEL_STRETCH
from ui.custom_widgets.mindmap_nodes import (NODE_COLORS, SHAPES, BendHandle, ConnectionItem, EndGrip, FrameItem,
                                             LineLabel, NodeItem, find_frame, find_node, group_items,
                                             set_active_bend, ungroup_items,
                                             shape_preview)
from resources.styles import AppColors
from ui.custom_widgets import dialogs
from PyQt5.QtWidgets import (QGraphicsScene, QGraphicsView, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
                             QSizePolicy, QPushButton, QMessageBox, QSlider, QGridLayout, QMenu, QApplication,
                             QShortcut, QToolButton, QStackedWidget, QLineEdit, QListWidget, QListWidgetItem, QScrollArea)
from PyQt5.QtCore import Qt, QEvent, QMimeData, QPoint, QPointF, QRectF, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QDrag, QIcon, QKeySequence, QPainter, QPen, QPixmap

# Drag-and-drop format for a shape dragged from the library onto the canvas
SHAPE_MIME = "application/x-meridian-shape"

CANVAS_COLOR = QColor("#f8fafc")
DOT_COLOR = QColor("#cbd5e1")
DOT_MAJOR_COLOR = QColor("#94a3b8")

PANEL_BUTTON_STYLE = f"""
    QPushButton {{ background-color: {AppColors.surface_raised}; color: {AppColors.text_primary};
                   border: 1px solid {AppColors.surface_hover_alt}; border-radius: 6px;
                   padding: 6px 10px; font-size: 12px; }}
    QPushButton:hover {{ border-color: {AppColors.accent}; }}
    QPushButton:checked {{ background-color: {AppColors.accent}; border-color: {AppColors.accent}; color: white;
                           font-weight: bold; }}
    QPushButton:disabled {{ background-color: transparent; color: {AppColors.text_faint};
                            border-color: {AppColors.surface_raised}; }}
"""
PRIMARY_BUTTON_STYLE = f"""
    QPushButton {{ background-color: {AppColors.accent}; border-color: {AppColors.accent}; color: white; font-weight: bold; }}
    QPushButton:hover {{ background-color: {AppColors.accent_dark}; }}
"""
MENU_STYLE = f"""
    QMenu {{ background-color: {AppColors.surface_raised}; color: {AppColors.text_primary};
             border: 1px solid {AppColors.surface_hover_alt}; padding: 4px; }}
    QMenu::item {{ padding: 6px 22px 6px 10px; border-radius: 3px; }}
    QMenu::item:selected {{ background-color: {AppColors.accent}; }}
    QMenu::separator {{ height: 1px; background: {AppColors.surface_hover_alt}; margin: 4px 6px; }}
"""


def color_swatch(color, size=14):
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(QPen(QColor(color).darker(120), 1))
    painter.setBrush(QColor(color))
    painter.drawRoundedRect(1, 1, size - 2, size - 2, 3, 3)
    painter.end()
    return pixmap


class ColorSwatches(QWidget):
    """A row of colour swatches; picking one colours the selected shapes and lines"""
    colorPicked = pyqtSignal(object)  # hex colour, or None for a line's standard grey

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self.buttons = {}
        for index, (name, color) in enumerate(NODE_COLORS):
            button = QToolButton()
            button.setToolTip(name)
            button.setFixedSize(26, 26)
            button.setCursor(Qt.PointingHandCursor)
            button.setStyleSheet(f"""
                QToolButton {{ background-color: {color}; border: 2px solid {QColor(color).darker(130).name()};
                               border-radius: 13px; }}
                QToolButton:hover {{ border: 2px solid white; }}
                QToolButton:disabled {{ background-color: {QColor(color).darker(220).name()};
                                        border-color: {AppColors.surface_raised}; }}""")
            button.clicked.connect(lambda _=False, color=color: self.colorPicked.emit(color))
            layout.addWidget(button, 0, index)
            self.buttons[name] = button
        layout.setColumnStretch(len(NODE_COLORS), 1)


class SegmentedTabs(QWidget):
    """Pages switched by a segmented control: big buttons side by side in a rounded track,
    the current one filled. Easier to see than a plain tab bar."""
    currentChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        self.track = QFrame()
        self.track.setObjectName("segmentTrack")
        self.track.setStyleSheet(f"""
            QFrame#segmentTrack {{ background-color: {AppColors.surface}; border: 1px solid {AppColors.surface_hover_alt};
                                   border-radius: 10px; }}
            QPushButton {{ background: transparent; color: {AppColors.text_secondary}; border: none;
                           border-radius: 7px; padding: 9px 6px; font-size: 13px; font-weight: bold; }}
            QPushButton:hover:!checked {{ background-color: {AppColors.surface_raised}; color: {AppColors.text_primary}; }}
            QPushButton:checked {{ background-color: {AppColors.accent}; color: white; }}""")
        self.track_layout = QHBoxLayout(self.track)
        self.track_layout.setContentsMargins(4, 4, 4, 4)
        self.track_layout.setSpacing(4)
        layout.addWidget(self.track)
        self.pages = QStackedWidget()
        layout.addWidget(self.pages, 1)
        self.buttons = []

    def addTab(self, widget, text):
        index = len(self.buttons)
        button = QPushButton(text)
        button.setCheckable(True)
        button.setCursor(Qt.PointingHandCursor)
        button.clicked.connect(lambda: self.setCurrentIndex(index))
        self.track_layout.addWidget(button, 1)
        self.buttons.append(button)
        self.pages.addWidget(widget)
        if index == 0:
            button.setChecked(True)
        return index

    def count(self):
        return len(self.buttons)

    def tabText(self, index):
        return self.buttons[index].text().strip()

    def currentIndex(self):
        return self.pages.currentIndex()

    def setCurrentIndex(self, index):
        for i, button in enumerate(self.buttons):
            button.setChecked(i == index)
        if index != self.pages.currentIndex():
            self.pages.setCurrentIndex(index)
            self.currentChanged.emit(index)


class MindMapList(QWidget):
    """The saved mind maps, newest edit first: click one to open it, right-click for more"""
    openRequested = pyqtSignal(str)  # mind map id
    menuRequested = pyqtSignal(str, QPoint)  # mind map id, global position

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.newButton = QPushButton("+  New mind map")
        self.newButton.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.newButton)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search mind maps")
        self.search.setClearButtonEnabled(True)
        self.search.setStyleSheet(f"""
            QLineEdit {{ background-color: {AppColors.surface_raised}; color: {AppColors.text_primary};
                         border: 1px solid {AppColors.surface_hover_alt}; border-radius: 6px; padding: 6px 8px; }}
            QLineEdit:focus {{ border-color: {AppColors.accent}; }}""")
        self.search.textChanged.connect(self._filter)
        layout.addWidget(self.search)

        self.list = QListWidget()
        self.list.setSpacing(3)
        self.list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list.setStyleSheet(f"""
            QListWidget {{ background: transparent; border: none; outline: none; }}
            QListWidget::item {{ background-color: {AppColors.surface_raised}; border: 1px solid {AppColors.surface_hover_alt};
                                 border-radius: 8px; }}
            QListWidget::item:hover {{ border-color: {AppColors.accent}; }}
            QListWidget::item:selected {{ background-color: {AppColors.accent_background_color_dark};
                                          border: 1px solid {AppColors.accent}; }}""")
        self.list.itemClicked.connect(lambda item: self.openRequested.emit(item.data(Qt.UserRole)))
        self.list.customContextMenuRequested.connect(self._menu)
        layout.addWidget(self.list, 1)

        self.empty = QLabel("No saved mind maps yet.\nSave the one you're working on and it will appear here.")
        self.empty.setWordWrap(True)
        self.empty.setAlignment(Qt.AlignCenter)
        self.empty.setStyleSheet(f"color: {AppColors.text_muted}; font-size: 12px; padding: 20px;")
        layout.addWidget(self.empty)

    def populate(self, mindmaps, current_id, unsaved):
        self.list.clear()
        for mindmap in mindmaps:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, mindmap.id)
            item.setData(Qt.UserRole + 1, mindmap.title.lower())
            item.setToolTip(mindmap.description or mindmap.title)
            card = QWidget()
            card.setAttribute(Qt.WA_TransparentForMouseEvents)  # clicks go to the list item
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(10, 7, 10, 7)
            card_layout.setSpacing(2)
            current = mindmap.id == current_id
            title = QLabel(mindmap.title + ("  📁" if mindmap.project_id else "") + ("  ●" if current and unsaved else ""))
            title.setStyleSheet(f"color: {AppColors.text_primary}; font-size: 13px; font-weight: bold; background: transparent;")
            edited = mindmap.modified_date.strftime("%b %d").replace(" 0", " ") if mindmap.modified_date else ""
            count = sum(1 for node in mindmap.nodes or [] if node.get("kind") != "frame")
            meta = QLabel(("Open now  ·  " if current else "") + f"Edited {edited}  ·  {count} shape{'s' if count != 1 else ''}")
            meta.setStyleSheet(f"color: {AppColors.accent if current else AppColors.text_muted}; font-size: 11px; "
                               f"background: transparent;")
            card_layout.addWidget(title)
            card_layout.addWidget(meta)
            self.list.addItem(item)
            item.setSizeHint(card.sizeHint())
            self.list.setItemWidget(item, card)
            if current:
                item.setSelected(True)
        self.empty.setVisible(not mindmaps)
        self._filter(self.search.text())

    def ids(self):
        return [self.list.item(i).data(Qt.UserRole) for i in range(self.list.count())]

    def _filter(self, text):
        text = text.strip().lower()
        for i in range(self.list.count()):
            item = self.list.item(i)
            item.setHidden(bool(text) and text not in item.data(Qt.UserRole + 1))

    def _menu(self, pos):
        item = self.list.itemAt(pos)
        if item is not None:
            self.menuRequested.emit(item.data(Qt.UserRole), self.list.viewport().mapToGlobal(pos))


class UndoHistory:
    """Snapshots of the canvas, one per finished change, to step back and forward through"""

    LIMIT = 100

    def __init__(self):
        self.states = []
        self.index = -1

    def reset(self, state):
        self.states = [state]
        self.index = 0

    def record(self, state):
        """Add state if it differs from the current one; returns True if it was added"""
        if self.index >= 0 and self.states[self.index] == state:
            return False
        del self.states[self.index + 1:]  # a new change drops anything that was undone
        self.states.append(state)
        if len(self.states) > self.LIMIT:
            del self.states[0]
        self.index = len(self.states) - 1
        return True

    def canUndo(self):
        return self.index > 0

    def canRedo(self):
        return self.index < len(self.states) - 1

    def undo(self):
        self.index -= 1
        return self.states[self.index]

    def redo(self):
        self.index += 1
        return self.states[self.index]


class ShapeTile(QFrame):
    """One shape in the library: drag it onto the canvas, or click to add it in the middle"""

    def __init__(self, shape_key, library):
        super().__init__()
        self.shape_key = shape_key
        self.library = library
        self.press_pos = None
        self.setObjectName("shapeTile")
        self.setCursor(Qt.OpenHandCursor)
        self.setToolTip(f"Drag onto the canvas, or click to add a {SHAPES[shape_key].label.lower()}")
        self.setStyleSheet(f"""
            QFrame#shapeTile {{ background-color: {AppColors.surface_raised}; border: 1px solid {AppColors.surface_hover_alt};
                                border-radius: 8px; }}
            QFrame#shapeTile:hover {{ border-color: {AppColors.accent}; }}
            QLabel {{ background: transparent; border: none; }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 6, 4, 4)
        layout.setSpacing(2)
        picture = QLabel()
        picture.setPixmap(shape_preview(shape_key))
        picture.setAlignment(Qt.AlignCenter)
        name = QLabel(SHAPES[shape_key].label)
        name.setAlignment(Qt.AlignCenter)
        name.setStyleSheet(f"color: {AppColors.text_secondary}; font-size: 11px;")
        layout.addWidget(picture)
        layout.addWidget(name)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.press_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.press_pos is None or (event.pos() - self.press_pos).manhattanLength() < QApplication.startDragDistance():
            return
        self.press_pos = None
        mime = QMimeData()
        mime.setData(SHAPE_MIME, self.shape_key.encode())
        drag = QDrag(self)
        drag.setMimeData(mime)
        preview = shape_preview(self.shape_key, 96, 64)
        drag.setPixmap(preview)
        drag.setHotSpot(QPoint(preview.width() // 2, preview.height() // 2))
        drag.exec_(Qt.CopyAction)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.press_pos is not None:
            self.press_pos = None
            self.library.shapeClicked.emit(self.shape_key)
        super().mouseReleaseEvent(event)


class ShapeLibrary(QWidget):
    """The shapes that can be added to a mind map, as a grid of tiles"""
    shapeClicked = pyqtSignal(str)

    COLUMNS = 2

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self.tiles = []
        for index, key in enumerate(SHAPES):
            tile = ShapeTile(key, self)
            self.tiles.append(tile)
            layout.addWidget(tile, index // self.COLUMNS, index % self.COLUMNS)


class ZoomableGraphicsView(QGraphicsView):
    """
    QGraphicsView with built-in zoom controls via mouse wheel and keyboard, shapes
    dropped from the library, Delete for the selection, and drag-to-select.
    """
    shapeDropped = pyqtSignal(str, QPointF)  # shape key, scene position
    deleteRequested = pyqtSignal()
    groupRequested = pyqtSignal(bool)  # True: group, False: ungroup
    undoRequested = pyqtSignal()
    redoRequested = pyqtSignal()
    interactionFinished = pyqtSignal()  # a mouse or key action ended: time to record a change

    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setDragMode(QGraphicsView.RubberBandDrag)  # drag on empty space to select several
        # Shapes and lines smooth their own edges. The canvas itself is drawn without
        # smoothing: at fractional interface sizes (e.g. 112%) a smoothed background
        # leaves hairline gaps that showed the dark panel through as trails.
        self.setRenderHints(QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform)
        self.setViewportUpdateMode(QGraphicsView.SmartViewportUpdate)
        self.setAcceptDrops(True)
        self.setFrameShape(QFrame.NoFrame)
        # No view background brush: with one set, Qt paints only that colour and never calls
        # the scene's drawBackground, so the grid disappears. The stylesheet colour below
        # is what keeps unrepainted slivers light.
        self.setStyleSheet(f"QGraphicsView {{ background-color: {CANVAS_COLOR.name()}; border: none; }}")

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

    # -- shapes dragged in from the library --------------------------------
    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(SHAPE_MIME):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(SHAPE_MIME):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasFormat(SHAPE_MIME):
            shape_key = bytes(event.mimeData().data(SHAPE_MIME)).decode()
            self.shapeDropped.emit(shape_key, self.mapToScene(event.pos()))
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

    def keyPressEvent(self, event):
        """Delete removes the selection; Ctrl +, Ctrl -, Ctrl 0 zoom"""
        focus = self.scene().focusItem()
        editing = focus is not None and hasattr(focus, "isEditing") and focus.isEditing()
        if not editing and event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self.deleteRequested.emit()
            event.accept()
            return
        # Ctrl+G groups the selection, Ctrl+Shift+G ungroups it
        if not editing and event.modifiers() & Qt.ControlModifier and event.key() == Qt.Key_G:
            self.groupRequested.emit(not event.modifiers() & Qt.ShiftModifier)
            event.accept()
            return
        # Ctrl+Z / Ctrl+Y / Ctrl+Shift+Z (while typing in a shape they undo the typing instead)
        if not editing and event.modifiers() & Qt.ControlModifier:
            if event.key() == Qt.Key_Z:
                (self.redoRequested if event.modifiers() & Qt.ShiftModifier else self.undoRequested).emit()
                event.accept()
                return
            if event.key() == Qt.Key_Y:
                self.redoRequested.emit()
                event.accept()
                return
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

    def mousePressEvent(self, event):
        # A click anywhere forgets the clicked bend point (clicking a bend sets it again)
        if self.scene() is not None and getattr(self.scene(), "active_bend", None) is not None:
            set_active_bend(self.scene(), None)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.interactionFinished.emit()

    def keyReleaseEvent(self, event):
        super().keyReleaseEvent(event)
        if not event.isAutoRepeat():
            self.interactionFinished.emit()

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

        # Shapes are dragged onto the canvas from the library (or clicked to add one in the middle)
        self.shapeLibrary = ShapeLibrary()
        self.shapeLibrary.shapeClicked.connect(self.add_node)
        self.view.shapeDropped.connect(self.add_node)
        self.view.deleteRequested.connect(self.delete_selected)
        self.view.groupRequested.connect(lambda group: self.group_selection() if group else self.ungroup_selection())

        # Undo / redo: the canvas is recorded after each finished change
        self.history = UndoHistory()
        self.undoButton = QPushButton("↶ Undo")
        self.redoButton = QPushButton("↷ Redo")
        self.undoButton.setToolTip("Undo (Ctrl+Z)")
        self.redoButton.setToolTip("Redo (Ctrl+Y)")
        self.undoButton.clicked.connect(self.undo)
        self.redoButton.clicked.connect(self.redo)
        self.view.undoRequested.connect(self.undo)
        self.view.redoRequested.connect(self.redo)
        self.view.interactionFinished.connect(self.checkpoint)
        self.view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self.show_context_menu)

        # Create buttons for user actions.
        self.saveButton = QPushButton("Save")
        self.saveButton.setToolTip("Save (Ctrl+S)")
        self.savedLabel = QLabel("")
        self.savedLabel.setStyleSheet(f"color: {AppColors.text_muted}; font-size: 11px;")

        # The saved mind maps, in the Mind maps tab of the left panel
        self.mapList = MindMapList()
        self.mapList.openRequested.connect(self.open_from_list)
        self.mapList.menuRequested.connect(self.show_map_menu)
        self.mapList.newButton.clicked.connect(self.new_mind_map)
        # The open map's name, above the canvas
        self.mapTitle = QLabel()
        self.mapTitle.setStyleSheet(f"color: {AppColors.text_primary}; font-size: 15px; font-weight: bold; "
                                    f"padding: 0 0 8px 2px;")

        # Colour for the selected shapes and lines
        self.colorSwatches = ColorSwatches()
        self.colorSwatches.colorPicked.connect(self.color_selection)
        self.scene.selectionChanged.connect(self._updateColorSwatches)
        QShortcut(QKeySequence.Save, self, self.save_mind_map)
        self.zoomToFitButton = QPushButton("🔍 Zoom to Fit")
        self.zoomToFitButton.setToolTip("Zoom so the whole mind map fits")
        self.viewProjectButton = QPushButton("📁 View Project")
        self.viewProjectButton.setToolTip("Open the project this mind map belongs to")
        self.viewProjectButton.setVisible(False)  # Hidden by default

        # Create zoom control widgets
        self.zoomInButton = QPushButton("+")
        self.zoomInButton.setToolTip("Zoom in (Ctrl +)")
        self.zoomOutButton = QPushButton("-")
        self.zoomOutButton.setToolTip("Zoom out (Ctrl -)")
        self.zoomResetButton = QPushButton("100%")
        self.zoomResetButton.setToolTip("Actual size (Ctrl 0)")
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
        self.gridToggleButton.setToolTip("Show or hide the dot grid")
        self.gridToggleButton.setCheckable(True)
        self.gridToggleButton.setChecked(True)  # Grid on by default
        self.snapToggleButton = QPushButton("✓ Snap to Grid")
        self.snapToggleButton.setToolTip("Line shapes up with the grid when you move them")
        self.snapToggleButton.setCheckable(True)
        self.snapToggleButton.setChecked(True)  # Snap on by default

        # Connect buttons to their respective functions.
        self.saveButton.clicked.connect(self.save_mind_map)
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
        self.applyGridSettings()

        self.installEventFilter(self)

        # Initialize UI panels.
        self.initUI()
        self.history.reset(self.snapshot())
        self._updateUndoButtons()
        self._updateColorSwatches()
        self.refresh_list()

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
        self.addSeparator()
        self.initPanelHorizontalContainer()

    def initCentralWidget(self):
        central_widget = QWidget()
        central_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.setLayout(self.main_layout)

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
        panel_layout.addLayout(self.initLeftPanelWidget(), SIDE_PANEL_STRETCH)
        panel_layout.addLayout(self.initRightPanelWidget(), MAIN_PANEL_STRETCH)

        self.main_layout.addWidget(panel_widget)

    def initLeftPanelWidget(self):
        """Two tabs: Design (shapes, colour, zoom, grid) and Mind maps (open, new, rename, delete)"""
        design_page = QWidget()
        left_layout = QVBoxLayout(design_page)
        left_layout.setContentsMargins(4, 12, 10, 12)
        left_layout.setSpacing(10)

        # Undo, redo, and save in one row
        edit_row = QHBoxLayout()
        edit_row.setSpacing(6)
        edit_row.addWidget(self.undoButton)
        edit_row.addWidget(self.redoButton)
        edit_row.addWidget(self.saveButton)
        left_layout.addLayout(edit_row)
        left_layout.addWidget(self.savedLabel)

        left_layout.addWidget(self._sectionHeader("Shapes"))
        hint = QLabel("Drag a shape onto the canvas. Double-click a shape to type; right-click for colour and more.")
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {AppColors.text_muted}; font-size: 11px;")
        left_layout.addWidget(hint)
        left_layout.addWidget(self.shapeLibrary)
        self.addFrameButton = QPushButton("▭  Add frame")
        self.addFrameButton.setToolTip("A titled box to group shapes; select shapes and right-click to frame them")
        self.addFrameButton.clicked.connect(lambda: self.add_frame())
        left_layout.addWidget(self.addFrameButton)

        left_layout.addWidget(self._sectionHeader("Colour"))
        self.colorHint = QLabel("Select shapes or lines, then pick a colour.")
        self.colorHint.setWordWrap(True)
        self.colorHint.setStyleSheet(f"color: {AppColors.text_muted}; font-size: 11px;")
        left_layout.addWidget(self.colorHint)
        left_layout.addWidget(self.colorSwatches)
        self.lineGreyButton = QPushButton("Standard grey for lines")
        self.lineGreyButton.setToolTip("Put the selected lines back to the standard grey")
        self.lineGreyButton.clicked.connect(lambda: self.color_selection(None))
        left_layout.addWidget(self.lineGreyButton)

        left_layout.addWidget(self._sectionHeader("Export"))
        export_row = QHBoxLayout()
        export_row.setSpacing(6)
        self.exportPngButton = QPushButton("PNG image")
        self.exportPdfButton = QPushButton("PDF")
        self.exportPngButton.setToolTip("Save the whole mind map as a picture")
        self.exportPdfButton.setToolTip("Save the whole mind map as a PDF page")
        self.exportPngButton.clicked.connect(lambda: self.export_mind_map("png"))
        self.exportPdfButton.clicked.connect(lambda: self.export_mind_map("pdf"))
        export_row.addWidget(self.exportPngButton)
        export_row.addWidget(self.exportPdfButton)
        left_layout.addLayout(export_row)

        # Add Zoom Controls section
        left_layout.addWidget(self._sectionHeader("Zoom"))

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

        # Add Grid Options section
        left_layout.addWidget(self._sectionHeader("Grid"))
        grid_row = QHBoxLayout()
        grid_row.setSpacing(6)
        grid_row.addWidget(self.gridToggleButton)
        grid_row.addWidget(self.snapToggleButton)
        left_layout.addLayout(grid_row)

        # Add View Project button (shown only when linked)
        left_layout.addWidget(self.viewProjectButton)

        left_layout.addStretch(1)  # Push the buttons to the top.

        for button in (self.saveButton, self.lineGreyButton, self.undoButton, self.redoButton,
                       self.exportPngButton, self.exportPdfButton, self.addFrameButton,
                       self.zoomInButton, self.zoomOutButton,
                       self.zoomResetButton, self.zoomToFitButton, self.gridToggleButton, self.snapToggleButton):
            button.setStyleSheet(PANEL_BUTTON_STYLE)
            button.setCursor(Qt.PointingHandCursor)
        self.saveButton.setStyleSheet(PANEL_BUTTON_STYLE + PRIMARY_BUTTON_STYLE)
        self.mapList.newButton.setStyleSheet(PANEL_BUTTON_STYLE + PRIMARY_BUTTON_STYLE)

        design_scroll = QScrollArea()
        design_scroll.setWidget(design_page)
        design_scroll.setWidgetResizable(True)
        design_scroll.setFrameShape(QFrame.NoFrame)
        design_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        design_scroll.setStyleSheet(f"""
            QScrollArea {{ background: transparent; }}
            QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px; }}
            QScrollBar::handle:vertical {{ background: {AppColors.surface_raised}; border-radius: 3px; min-height: 30px; }}
            QScrollBar::handle:vertical:hover {{ background: {AppColors.accent}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}""")

        maps_page = QWidget()
        maps_layout = QVBoxLayout(maps_page)
        maps_layout.setContentsMargins(4, 12, 4, 12)
        maps_layout.addWidget(self.mapList)

        self.panelTabs = SegmentedTabs()
        self.panelTabs.addTab(design_scroll, "Design")
        self.panelTabs.addTab(maps_page, "Mind maps")
        self.panelTabs.currentChanged.connect(lambda index: index == 1 and self.refresh_list())

        left_layout_outer = QVBoxLayout()
        left_layout_outer.setContentsMargins(15, 15, 5, 15)
        left_layout_outer.addWidget(self.panelTabs)
        return left_layout_outer

    @staticmethod
    def _sectionHeader(text):
        label = QLabel(text.upper())
        label.setStyleSheet(f"color: {AppColors.text_muted}; font-size: 11px; font-weight: bold; "
                            f"letter-spacing: 1px; padding-top: 10px;")
        return label

    def initRightPanelWidget(self):
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(15, 15, 15, 15)
        right_layout.setSpacing(0)
        right_layout.addWidget(self.mapTitle)
        right_layout.addWidget(self.view)

        # Add the right panel to the main layout.
        return right_layout

    def add_node(self, shape="rounded", scene_pos=None):
        """Add a shape centred at scene_pos (the middle of the view if not given), ready to type into"""
        if scene_pos is None:
            scene_pos = self.view.mapToScene(self.view.viewport().rect().center())
        text = "Note" if shape == "note" else "New idea"
        node = NodeItem(text=text, logger=self.logger, shape=shape)
        self.scene.addItem(node)
        node.setCenter(scene_pos)
        self.scene.clearSelection()
        node.setSelected(True)
        self.checkpoint()  # the new shape is one step; what's typed into it is the next
        self.view.setFocus()
        node.startEditing()
        return node

    def delete_selected(self):
        """Delete the clicked bend point if there is one; otherwise the selected shapes
        (with their lines) and lines"""
        bend = getattr(self.scene, "active_bend", None)
        if bend is not None and bend.scene() is self.scene:
            connection = bend.connection
            set_active_bend(self.scene, None)
            connection.removeWaypoint(bend.index)
            self.checkpoint()
            return
        for item in list(self.scene.selectedItems()):
            if item.scene() is None:
                continue  # already gone with a deleted shape
            if isinstance(item, (NodeItem, ConnectionItem, FrameItem)):
                item.remove_from_scene()
        self.checkpoint()

    def show_context_menu(self, view_pos):
        """Right-click: shape and colour for a shape, delete for a line, add a shape on empty canvas"""
        menu = self.build_context_menu(self.view.mapToScene(view_pos))
        menu.exec_(self.view.viewport().mapToGlobal(view_pos))
        self.checkpoint()

    def build_context_menu(self, scene_pos):
        item = self.scene.itemAt(scene_pos, self.view.transform())
        bend = item if isinstance(item, BendHandle) else None
        if isinstance(item, (EndGrip, BendHandle, LineLabel)):
            item = item.connection  # a line's grip, bend, or label: the line's menu
        node = find_node(item)
        frame = find_frame(item) if node is None else None
        menu = QMenu(self.view)
        menu.setStyleSheet(MENU_STYLE)

        if node is not None:
            if not node.isSelected():
                self.scene.clearSelection()
                node.setSelected(True)
            menu.addAction("Edit text", node.startEditing)
            shape_menu = menu.addMenu("Shape")
            for key, shape in SHAPES.items():
                action = shape_menu.addAction(QIcon(shape_preview(key, 36, 24)), shape.label)
                action.setCheckable(True)
                action.setChecked(key == node.shape_key)
                action.triggered.connect(lambda _=False, key=key: self._forSelectedNodes(lambda n: n.setShape(key)))
            color_menu = menu.addMenu("Colour")
            for name, color in NODE_COLORS:
                action = color_menu.addAction(QIcon(color_swatch(color)), name)
                action.triggered.connect(lambda _=False, color=color: self._forSelectedNodes(lambda n: n.setColor(color)))
            menu.addAction("Bring to front", lambda: node.setZValue(max(
                [n.zValue() for n in self.scene.items() if isinstance(n, NodeItem)] or [0]) + 1))
            menu.addSeparator()
            count = len(self._selectedNodes())
            menu.addAction("Frame this" if count == 1 else f"Frame these {count} shapes", self.frame_selection)
            selected = self._selectedNodes()
            already_one_group = len({n.group_id for n in selected}) == 1 and selected[0].group_id is not None
            if len(selected) > 1 and not already_one_group:
                menu.addAction(f"Group these {count} shapes\tCtrl+G", self.group_selection)
            if any(n.group_id for n in selected):
                menu.addAction("Ungroup\tCtrl+Shift+G", self.ungroup_selection)
            menu.addAction("Delete" if count == 1 else f"Delete {count} shapes", self.delete_selected)
        elif isinstance(item, ConnectionItem):
            self.scene.clearSelection()
            item.setSelected(True)
            color_menu = menu.addMenu("Colour")
            color_menu.addAction(QIcon(color_swatch("#94a3b8")), "Standard grey", lambda: item.setColor(None))
            for name, color in NODE_COLORS:
                color_menu.addAction(QIcon(color_swatch(color)), name, lambda color=color: item.setColor(color))
            menu.addAction("Edit label" if item.label else "Add label", item.editLabel)
            if item.label:
                menu.addAction("Remove label", lambda: item.setLabel(""))
            if bend is not None:
                menu.addAction("Remove this bend", lambda: item.removeWaypoint(bend.index))
            if item.waypoints:
                menu.addAction("Straighten line", item.clearWaypoints)
            menu.addAction("Delete line", self.delete_selected)
        elif frame is not None:
            self.scene.clearSelection()
            frame.setSelected(True)
            menu.addAction("Rename", frame.editTitle)
            color_menu = menu.addMenu("Colour")
            for name, color in [("Slate", "#64748b")] + [c for c in NODE_COLORS if c[0] != "Slate"]:
                color_menu.addAction(QIcon(color_swatch(color)), name, lambda color=color: frame.setColor(color))
            menu.addSeparator()
            menu.addAction("Delete frame (keep the shapes)", self.delete_selected)
            count = len(frame.contents())
            menu.addAction(f"Delete frame and its {count} shape{'s' if count != 1 else ''}",
                           lambda: (frame.remove_from_scene(with_contents=True), self.checkpoint()))
        else:
            add_menu = menu.addMenu("Add shape here")
            for key, shape in SHAPES.items():
                add_menu.addAction(QIcon(shape_preview(key, 36, 24)), shape.label,
                                   lambda key=key: self.add_node(key, scene_pos))
            menu.addAction("Add frame here", lambda: self.add_frame(scene_pos))
        return menu

    # -- groups ------------------------------------------------------------
    def group_selection(self):
        """Make the selected shapes one group (Ctrl+G)"""
        nodes = self._selectedNodes()
        if len(nodes) < 2:
            return None
        group_id = group_items(nodes)
        self.checkpoint()
        return group_id

    def ungroup_selection(self):
        """Break up the selected groups (Ctrl+Shift+G)"""
        nodes = [n for n in self._selectedNodes() if n.group_id]
        if not nodes:
            return
        ungroup_items(nodes)
        self.checkpoint()

    # -- frames ------------------------------------------------------------
    FRAME_PADDING = 40

    def add_frame(self, scene_pos=None, rect=None, title="Frame"):
        """A new frame centred at scene_pos (or covering rect), with its title ready to type"""
        frame = FrameItem(title=title)
        self.scene.addItem(frame)
        if rect is not None:
            frame.setSceneGeometry(rect)
        else:
            if scene_pos is None:
                scene_pos = self.view.mapToScene(self.view.viewport().rect().center())
            frame.setSceneGeometry(QRectF(scene_pos.x() - frame.width / 2, scene_pos.y() - frame.height / 2,
                                          frame.width, frame.height))
        self.scene.clearSelection()
        frame.setSelected(True)
        self.checkpoint()
        self.view.setFocus()
        frame.editTitle()
        return frame

    def frame_selection(self):
        """Put a frame around the selected shapes"""
        nodes = self._selectedNodes()
        if not nodes:
            return None
        area = nodes[0].sceneBoundingRectOfShape()
        for node in nodes[1:]:
            area = area.united(node.sceneBoundingRectOfShape())
        pad = self.FRAME_PADDING
        return self.add_frame(rect=area.adjusted(-pad, -pad - 30, pad, pad))

    def _selectedNodes(self):
        return [item for item in self.scene.selectedItems() if isinstance(item, NodeItem)]

    def _forSelectedNodes(self, change):
        for node in self._selectedNodes():
            change(node)

    def save_mind_map(self):
        # Serialize and save all NodeItems and the connections between them
        nodes = [item.serialize() for item in self.scene.items() if isinstance(item, (NodeItem, FrameItem))]
        connections = [
            self._connectionData(item)
            for item in self.scene.items()
            if isinstance(item, ConnectionItem) and item.start_node and item.end_node
        ]

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
                self._saved_state = self._current_state()
                self._showSaved()
                self.update_view_project_button()
            else:
                dialogs.warning(self, "Error", "Failed to save mindmap.")
            return success
        else:
            # A new mind map: ask what to call it
            title, ok = dialogs.ask_text(self, "Name this mind map", "It will be listed under the Mind maps tab.",
                                         "", ok_label="Save")
            if ok and title:
                mindmap = create_mindmap(
                    title=title,
                    nodes=nodes,
                    connections=connections,
                    logger=self.logger
                )
                self.current_mindmap_id = mindmap.id
                self._saved_state = self._current_state()
                self._showSaved()
                self.update_view_project_button()
                return True
            return False

    def _showSaved(self):
        from datetime import datetime
        self.savedLabel.setText(f"Saved at {datetime.now().strftime('%I:%M %p').lstrip('0')}")
        self.refresh_list()

    # -- undo / redo -------------------------------------------------------
    def snapshot(self):
        """Everything needed to rebuild the canvas, as JSON"""
        nodes = sorted((item.serialize() for item in self.scene.items() if isinstance(item, (NodeItem, FrameItem))),
                       key=lambda node: node["id"])
        connections = sorted(
            (self._connectionData(item)
             for item in self.scene.items()
             if isinstance(item, ConnectionItem) and item.start_node and item.end_node),
            key=lambda c: json.dumps(c, sort_keys=True))
        return json.dumps({"nodes": nodes, "connections": connections}, sort_keys=True)

    @staticmethod
    def _connectionData(line):
        return {"from": line.start_node.id, "from_handle": line.start_handle,
                "to": line.end_node.id, "to_handle": line.end_handle,
                "points": line.serializedPoints(), "color": line.color, "label": line.label}

    def checkpoint(self):
        """Record the canvas after a change has finished (called when a press, key, menu,
        or drop ends, so never mid-drag; not while typing in a shape)"""
        focus = self.scene.focusItem()
        if focus is not None and hasattr(focus, "isEditing") and focus.isEditing():
            return
        if self.history.record(self.snapshot()):
            self._updateUndoButtons()
            self._markUnsavedTab()

    def undo(self):
        self.checkpoint()  # anything not yet recorded is undone first
        if self.history.canUndo():
            self._restore(self.history.undo())

    def redo(self):
        if self.history.canRedo():
            self._restore(self.history.redo())

    def _restore(self, state):
        data = json.loads(state)
        self.scene.clear()
        self._populate(data["nodes"], data["connections"])
        self._updateUndoButtons()

    def _updateUndoButtons(self):
        self.undoButton.setEnabled(self.history.canUndo())
        self.redoButton.setEnabled(self.history.canRedo())
        self._markUnsavedTab()

    # -- saved mind maps (the Mind maps tab) ----------------------------------
    def refresh_list(self):
        """Refill the Mind maps list (newest edit first) and the title above the canvas"""
        from utils.mindmap_io import load_mindmaps_from_json
        from datetime import datetime
        mindmaps = sorted(load_mindmaps_from_json(self.logger).values(),
                          key=lambda m: m.modified_date or datetime.min, reverse=True)
        self.mapList.populate(mindmaps, self.current_mindmap_id, self.has_unsaved_changes())
        self._updateTitle(mindmaps)

    def _updateTitle(self, mindmaps=None):
        if not hasattr(self, "mapTitle"):
            return
        if self.current_mindmap_id is None:
            name = "Untitled mind map"
        else:
            name = self._title_of(self.current_mindmap_id) or "Untitled mind map"
        self.mapTitle.setText(name + ("  ●" if self.has_unsaved_changes() else ""))
        self.mapTitle.setToolTip("Unsaved changes" if self.has_unsaved_changes() else "")

    def _markUnsavedTab(self):
        """Kept for callers: the unsaved dot is on the title above the canvas"""
        self._updateTitle()

    def open_from_list(self, mindmap_id):
        if mindmap_id == self.current_mindmap_id:
            return
        if not self.confirm_discard_changes():
            self.refresh_list()  # keep the open map selected
            return
        self._open_mindmap(mindmap_id)

    def _open_mindmap(self, mindmap_id):
        from utils.mindmap_io import load_mindmaps_from_json
        mindmap = load_mindmaps_from_json(self.logger).get(mindmap_id)
        if mindmap is not None:
            self.load_mindmap_data(mindmap)
            self.savedLabel.setText("")
        self.refresh_list()

    def show_map_menu(self, mindmap_id, global_pos):
        menu = QMenu(self.mapList)
        menu.setStyleSheet(MENU_STYLE)
        if mindmap_id != self.current_mindmap_id:
            menu.addAction("Open", lambda: self.open_from_list(mindmap_id))
        menu.addAction("Rename…", lambda: self.rename_mindmap(mindmap_id))
        menu.addSeparator()
        menu.addAction("Delete…", lambda: self.delete_mindmap(mindmap_id))
        menu.exec_(global_pos)

    def _title_of(self, mindmap_id):
        from utils.mindmap_io import load_mindmaps_from_json
        mindmap = load_mindmaps_from_json(self.logger).get(mindmap_id)
        return mindmap.title if mindmap else None

    def rename_mindmap(self, mindmap_id):
        from utils.mindmap_io import update_mindmap
        title, ok = dialogs.ask_text(self, "Rename mind map", "Give it a new name.", self._title_of(mindmap_id) or "",
                                     ok_label="Rename")
        if ok and title:
            update_mindmap(mindmap_id, title=title, logger=self.logger)
            self.refresh_list()

    def delete_mindmap(self, mindmap_id):
        from utils.mindmap_io import delete_mindmap
        title = self._title_of(mindmap_id)
        if not dialogs.confirm(self, f"Delete \u201c{title}\u201d?",
                               "The mind map will be removed for good. This can't be undone.", "Delete"):
            return
        if delete_mindmap(mindmap_id, self.logger) and mindmap_id == self.current_mindmap_id:
            self.clear_map()  # it was open: start fresh
        self.refresh_list()

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_list()  # mind maps may have been made elsewhere (e.g. from a project)

    def show_node(self, node_id):
        """Select a shape and bring it into view (from search)"""
        node = next((item for item in self.scene.items()
                     if isinstance(item, NodeItem) and item.id == node_id), None)
        if node is None:
            return False
        self.scene.clearSelection()
        node.setSelected(True)

        def bring_into_view():
            # Run once the canvas has caught up with a map that was just loaded (its
            # scrollable area grows a moment later); centring before that does nothing
            if node.scene() is self.scene:
                self.scene.growToFit()
                self.view.centerOn(node)
        bring_into_view()
        QTimer.singleShot(0, bring_into_view)
        return True

    # -- export --------------------------------------------------------------
    EXPORT_PADDING = 40
    EXPORT_PNG_SCALE = 2  # twice the screen resolution, so it stays sharp

    def content_bounds(self):
        """The area the shapes and lines cover (handles and the like not included)"""
        bounds = None
        for item in self.scene.items():
            if isinstance(item, (NodeItem, ConnectionItem, FrameItem)):
                rect = item.sceneBoundingRect()
                bounds = rect if bounds is None else bounds.united(rect)
        return bounds

    def export_mind_map(self, fmt, path=None):
        """Save the whole map as a PNG or PDF. Asks where unless path is given; returns the path or None"""
        bounds = self.content_bounds()
        if bounds is None:
            dialogs.information(self, "Nothing to export", "Add some shapes to the mind map first.")
            return None
        if path is None:
            from PyQt5.QtWidgets import QFileDialog
            name = (self._title_of(self.current_mindmap_id) if self.current_mindmap_id else None) or "Mind map"
            safe = "".join(c for c in name if c not in '\\/:*?"<>|').strip() or "Mind map"
            filters = {"png": "PNG image (*.png)", "pdf": "PDF document (*.pdf)"}
            path, _ = QFileDialog.getSaveFileName(self, "Export mind map", f"{safe}.{fmt}", filters[fmt])
            if not path:
                return None
            if not path.lower().endswith(f".{fmt}"):
                path += f".{fmt}"

        source = bounds.adjusted(-self.EXPORT_PADDING, -self.EXPORT_PADDING, self.EXPORT_PADDING, self.EXPORT_PADDING)
        with self._cleanForExport():
            ok = self._render_png(path, source) if fmt == "png" else self._render_pdf(path, source)
        if ok:
            import os
            self.savedLabel.setText(f"Exported {os.path.basename(path)}")
            return path
        dialogs.warning(self, "Export failed", f"The mind map couldn't be saved to:\n{path}")
        return None

    def _render_png(self, path, source):
        from PyQt5.QtCore import QRectF
        from PyQt5.QtGui import QImage
        scale = self.EXPORT_PNG_SCALE
        image = QImage(int(source.width() * scale), int(source.height() * scale), QImage.Format_ARGB32)
        image.fill(CANVAS_COLOR)
        painter = QPainter(image)
        painter.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform)
        self.scene.render(painter, QRectF(image.rect()), source)
        painter.end()
        return image.save(path)

    def _render_pdf(self, path, source):
        from PyQt5.QtCore import QMarginsF, QRectF
        from PyQt5.QtGui import QPageLayout, QPageSize
        from PyQt5.QtPrintSupport import QPrinter
        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(path)
        orientation = QPageLayout.Landscape if source.width() >= source.height() else QPageLayout.Portrait
        printer.setPageLayout(QPageLayout(QPageSize(QPageSize.Letter), orientation, QMarginsF(12, 12, 12, 12),
                                          QPageLayout.Millimeter))
        painter = QPainter()
        if not painter.begin(printer):
            return False
        painter.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)
        page = QRectF(printer.pageRect(QPrinter.DevicePixel))
        page.moveTo(0, 0)
        # Fit the map on the page, keeping its shape, centred
        scale = min(page.width() / source.width(), page.height() / source.height())
        target = QRectF(0, 0, source.width() * scale, source.height() * scale)
        target.moveCenter(page.center())
        self.scene.render(painter, target, source)
        painter.end()
        import os
        return os.path.exists(path)

    def _cleanForExport(self):
        """While exporting: no selection, handles, hover highlights, typing cursor, or grid"""
        screen = self

        class Clean:
            def __enter__(self):
                self.selected = screen.scene.selectedItems()
                self.grid = screen.scene.grid_visible
                screen.scene.clearSelection()
                screen.scene.grid_visible = False
                self.hidden = []
                for item in screen.scene.items():
                    if isinstance(item, (EndGrip, BendHandle)) or type(item).__name__ in ("LinkHandle", "ResizeHandle"):
                        if item.isVisible():
                            item.setVisible(False)
                            self.hidden.append(item)
                    if isinstance(item, NodeItem):
                        item.text_item.stopEditing()
                        item.is_hovered = False
                    if isinstance(item, ConnectionItem):
                        item.hovered = item.highlighted = False

            def __exit__(self, *exc):
                screen.scene.grid_visible = self.grid
                for item in self.hidden:
                    item.setVisible(True)
                for item in self.selected:
                    if item.scene() is screen.scene:
                        item.setSelected(True)
                screen.scene.update()
                return False

        return Clean()

    # -- colour --------------------------------------------------------------
    def color_selection(self, color):
        """Colour the selected shapes and lines (None: lines go back to standard grey)"""
        changed = False
        for item in self.scene.selectedItems():
            if isinstance(item, ConnectionItem):
                item.setColor(color)
                changed = True
            elif isinstance(item, NodeItem) and color is not None:
                item.setColor(color)
                changed = True
        if changed:
            self.checkpoint()

    def _updateColorSwatches(self):
        try:
            selected = self.scene.selectedItems()
        except RuntimeError:
            return
        has_items = any(isinstance(item, (NodeItem, ConnectionItem)) for item in selected)
        for button in self.colorSwatches.buttons.values():
            button.setEnabled(has_items)
        self.lineGreyButton.setVisible(any(isinstance(item, ConnectionItem) for item in selected))
        self.colorHint.setText("Pick a colour for the selection." if has_items
                               else "Select shapes or lines, then pick a colour.")

    def _populate(self, nodes_data, connections_data):
        """Put shapes and lines on the canvas from saved data"""
        node_map = {}
        for node_data in nodes_data:
            if node_data.get("kind") == FrameItem.kind:
                frame = FrameItem()
                frame.deserialize(node_data)
                self.scene.addItem(frame)
                continue
            node = NodeItem(0, 0, logger=self.logger)
            node.deserialize(node_data)
            node_map[node.id] = node
            self.scene.addItem(node)

        # Reconnect nodes; skip any link to a node that no longer exists
        for connection_data in connections_data:
            start = node_map.get(connection_data.get("from"))
            end = node_map.get(connection_data.get("to"))
            if start is None or end is None:
                self.logger.warning(f"Skipping connection to a missing node: {connection_data}")
                continue
            connection = ConnectionItem(start, connection_data.get("from_handle", "right"),
                                        end, connection_data.get("to_handle", "left"),
                                        points=connection_data.get("points"),
                                        color=connection_data.get("color"),
                                        label=connection_data.get("label", ""))
            self.scene.addItem(connection)

    def _current_state(self):
        """What's on the canvas, in a form that can be compared with what was saved"""
        nodes = sorted((item.serialize() for item in self.scene.items() if isinstance(item, (NodeItem, FrameItem))),
                       key=lambda node: node["id"])
        connections = sorted(
            (item.start_node.id, item.start_handle, item.end_node.id, item.end_handle, item.serializedPoints(),
             item.color or "", item.label)
            for item in self.scene.items()
            if isinstance(item, ConnectionItem) and item.start_node and item.end_node)
        return json.dumps([nodes, connections], sort_keys=True)

    def has_unsaved_changes(self):
        return self._current_state() != getattr(self, '_saved_state', self._empty_state())

    def _empty_state(self):
        return json.dumps([[], []])

    def confirm_discard_changes(self):
        """Offer to save unsaved changes. Returns False if the user cancels."""
        if not self.has_unsaved_changes():
            return True
        name = self._title_of(self.current_mindmap_id) if self.current_mindmap_id else None
        reply = dialogs.ask_to_save(self, "mind map", name)
        if reply == QMessageBox.Cancel:
            return False
        if reply == QMessageBox.Save:
            return self.save_mind_map()
        return True

    def new_mind_map(self):
        """Start an empty mindmap, offering to save the current one first"""
        if self.confirm_discard_changes():
            self.clear_map()
            self.savedLabel.setText("")
            self.refresh_list()

    def load_mindmap_data(self, mindmap):
        """Load mindmap data into the scene"""
        self.clear_map()
        self._populate(mindmap.nodes or [], mindmap.connections or [])

        # Set current mindmap; undo starts from here
        self.current_mindmap_id = mindmap.id
        self._saved_state = self._current_state()
        self.history.reset(self.snapshot())
        self._updateUndoButtons()
        self.update_view_project_button()

        self.logger.info(f"Loaded mindmap: {mindmap.title}")

    def load_mindmap_by_id(self, mindmap_id: str):
        """Load a specific mindmap by ID (for View Mindmap from project)"""
        from utils.mindmap_io import load_mindmaps_from_json

        if not self.confirm_discard_changes():
            return

        mindmaps = load_mindmaps_from_json(self.logger)
        mindmap = mindmaps.get(mindmap_id)

        if mindmap:
            self.load_mindmap_data(mindmap)
            self.refresh_list()
        else:
            dialogs.warning(self, "Error", f"Mindmap not found: {mindmap_id}")

    def clear_map(self):
        # Remove all items from the scene.
        self.scene.clear()
        self.current_mindmap_id = None
        self._saved_state = self._empty_state()
        self.history.reset(self.snapshot())
        self._updateUndoButtons()
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

    def applyGridSettings(self):
        """Use the grid and snap defaults from Settings"""
        from utils.settings import Settings
        settings = Settings.instance()
        self.gridToggleButton.setChecked(bool(settings.get("mindmap_show_grid")))
        self.snapToggleButton.setChecked(bool(settings.get("mindmap_snap_to_grid")))
        self.toggle_grid()
        self.toggle_snap()

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
                self.viewProjectButton.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {AppColors.accent};
                        color: white;
                        border: none;
                        padding: 8px;
                        border-radius: 4px;
                        font-weight: bold;
                    }}
                    QPushButton:hover {{
                        background-color: {AppColors.accent_dark};
                    }}
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
                dialogs.information(
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
        self.active_bend = None  # the bend point last clicked: Delete removes it
        # Room to scroll past the shapes on every side; grows as they spread out
        self.setSceneRect(QRectF(-self.CANVAS_MARGIN, -self.CANVAS_MARGIN, 2 * self.CANVAS_MARGIN, 2 * self.CANVAS_MARGIN))
        self.changed.connect(lambda _regions: self.growToFit())
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

    CANVAS_MARGIN = 1500

    def growToFit(self):
        """Keep a margin of canvas around the shapes (never shrinks while a map is open)"""
        wanted = self.itemsBoundingRect().adjusted(-self.CANVAS_MARGIN, -self.CANVAS_MARGIN,
                                                   self.CANVAS_MARGIN, self.CANVAS_MARGIN)
        grown = self.sceneRect().united(wanted)
        if grown != self.sceneRect():
            self.setSceneRect(grown)

    def clear(self):
        """Override to clear spatial tracker (and forget the clicked bend point, which goes too)"""
        self.spatial_tracker.clear()
        self.active_bend = None
        super().clear()
        margin = self.CANVAS_MARGIN
        self.setSceneRect(QRectF(-margin, -margin, 2 * margin, 2 * margin))

    def get_content_bounds(self):
        """Public API for getting all content bounds"""
        return self.spatial_tracker.get_content_bounds()

    def drawBackground(self, painter, rect):
        """A soft canvas with a dot grid (every fourth dot a little stronger)"""
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, False)
        painter.fillRect(rect.adjusted(-2, -2, 2, 2), CANVAS_COLOR)  # cover partly exposed edge pixels too
        painter.restore()
        if not self.grid_visible:
            return
        scale = self.views()[0].transform().m11() if self.views() else 1.0
        step = self.grid_size * (2 if scale < 0.5 else 1)
        if step * scale < 8:
            return  # too dense to be useful when zoomed far out

        left = int(rect.left() // step) * step
        top = int(rect.top() // step) * step
        minor, major = [], []
        x = left
        while x < rect.right():
            y = top
            while y < rect.bottom():
                is_major = round(x / step) % 4 == 0 and round(y / step) % 4 == 0
                (major if is_major else minor).append(QPointF(x, y))
                y += step
            x += step
        # Dots are drawn smoothed: without it, dots under 2px can vanish at fractional
        # interface sizes (e.g. 112%), and the grid looked like it did nothing
        size = max(2.0, 2.0 / scale)
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)
        if minor:
            painter.setPen(QPen(DOT_COLOR, size, Qt.SolidLine, Qt.RoundCap))
            painter.drawPoints(*minor)
        if major:
            painter.setPen(QPen(DOT_MAJOR_COLOR, size * 1.6, Qt.SolidLine, Qt.RoundCap))
            painter.drawPoints(*major)
        painter.restore()
