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
# File: mindmap_nodes.py
# Description: Mindmap shapes (nodes) and the connections between them. Nodes
#              come in several shapes and colours, can be moved, resized, edited
#              in place, linked, and deleted.
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

import logging
import math
from uuid import uuid4

from PyQt5.QtCore import QEvent, QPointF, QRectF, Qt, QTimer
from PyQt5.QtGui import (QBrush, QColor, QFont, QLinearGradient, QPainter, QPainterPath,
                         QPainterPathStroker, QPen, QPixmap, QPolygonF, QTextOption)
from PyQt5.QtWidgets import (QApplication, QGraphicsEllipseItem, QGraphicsItem, QGraphicsPathItem,
                             QGraphicsRectItem, QGraphicsTextItem)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------- look

TEXT_COLOR = QColor("#1e293b")
SELECTION_COLOR = QColor("#2563eb")
CONNECTION_COLOR = QColor("#94a3b8")
HANDLE_FILL = QColor("#ffffff")

# Colours offered for nodes (name, hex). Nodes are drawn as a soft tint of the
# colour with a border in the colour itself.
NODE_COLORS = [
    ("Blue", "#3b82f6"), ("Indigo", "#6366f1"), ("Purple", "#a855f7"), ("Teal", "#14b8a6"),
    ("Green", "#22c55e"), ("Amber", "#f59e0b"), ("Rose", "#f43f5e"), ("Slate", "#64748b"),
]
DEFAULT_COLOR = "#3b82f6"

MIN_WIDTH, MIN_HEIGHT = 60, 40


def _rounded(w, h, radius):
    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, w, h), radius, radius)
    return path


def _polygon(points):
    path = QPainterPath()
    path.addPolygon(QPolygonF([QPointF(x, y) for x, y in points]))
    path.closeSubpath()
    return path


def _ellipse(w, h):
    path = QPainterPath()
    path.addEllipse(QRectF(0, 0, w, h))
    return path


def _note(w, h):
    fold = min(18.0, w / 4, h / 4)
    return _polygon([(0, 0), (w - fold, 0), (w, fold), (w, h), (0, h)])


class Shape:
    """One kind of node: its outline, the area its text goes in, and its starting size"""

    def __init__(self, key, label, size, outline, text_insets, color=DEFAULT_COLOR):
        self.key = key
        self.label = label
        self.size = size
        self.outline = outline          # (w, h) -> QPainterPath
        self.text_insets = text_insets  # (w, h) -> (left/right inset, top/bottom inset)
        self.color = color

    def text_rect(self, w, h):
        dx, dy = self.text_insets(w, h)
        return QRectF(dx, dy, max(10.0, w - 2 * dx), max(10.0, h - 2 * dy))


SHAPES = {shape.key: shape for shape in [
    Shape("rounded", "Rounded", (170, 70), lambda w, h: _rounded(w, h, 14), lambda w, h: (14, 10)),
    Shape("rectangle", "Box", (170, 70), lambda w, h: _rounded(w, h, 3), lambda w, h: (12, 10)),
    Shape("pill", "Pill", (170, 56), lambda w, h: _rounded(w, h, h / 2), lambda w, h: (h * 0.45, 8)),
    Shape("ellipse", "Ellipse", (170, 90), _ellipse, lambda w, h: (w * 0.15, h * 0.15)),
    Shape("circle", "Circle", (110, 110), _ellipse, lambda w, h: (w * 0.15, h * 0.15)),
    Shape("diamond", "Diamond", (170, 110), lambda w, h: _polygon([(w / 2, 0), (w, h / 2), (w / 2, h), (0, h / 2)]),
          lambda w, h: (w * 0.25, h * 0.25), color="#f59e0b"),
    Shape("hexagon", "Hexagon", (170, 80),
          lambda w, h: _polygon([(h * 0.3, 0), (w - h * 0.3, 0), (w, h / 2), (w - h * 0.3, h), (h * 0.3, h), (0, h / 2)]),
          lambda w, h: (h * 0.3 + 4, 8), color="#14b8a6"),
    Shape("note", "Sticky note", (150, 120), _note, lambda w, h: (12, 12), color="#f59e0b"),
]}
DEFAULT_SHAPE = "rounded"
LEGACY_SHAPE = "ellipse"  # nodes saved before shapes existed were ellipses


def tint(color, amount):
    """color mixed toward white by amount (0 = unchanged, 1 = white)"""
    color = QColor(color)
    return QColor(int(color.red() + (255 - color.red()) * amount),
                  int(color.green() + (255 - color.green()) * amount),
                  int(color.blue() + (255 - color.blue()) * amount))


def paint_shape(painter, path, color, note=False, hovered=False, selected=False, shadow=True):
    """Draw a node outline the way the canvas does (also used for the shape library previews)"""
    painter.setRenderHint(QPainter.Antialiasing)
    bounds = path.boundingRect()
    if shadow:
        painter.save()
        painter.translate(0, 3)
        painter.fillPath(path, QColor(15, 23, 42, 26))
        painter.restore()

    base = QColor(color)
    gradient = QLinearGradient(0, bounds.top(), 0, bounds.bottom())
    gradient.setColorAt(0, tint(base, 0.90 if not note else 0.70))
    gradient.setColorAt(1, tint(base, 0.80 if not note else 0.60))
    painter.fillPath(path, QBrush(gradient))

    if note:  # the folded corner
        fold = min(18.0, bounds.width() / 4, bounds.height() / 4)
        corner = QPainterPath()
        corner.moveTo(bounds.right() - fold, bounds.top())
        corner.lineTo(bounds.right() - fold, bounds.top() + fold)
        corner.lineTo(bounds.right(), bounds.top() + fold)
        corner.closeSubpath()
        painter.fillPath(corner, tint(base, 0.35))

    if selected:
        glow = QPen(QColor(SELECTION_COLOR.red(), SELECTION_COLOR.green(), SELECTION_COLOR.blue(), 60), 8)
        glow.setJoinStyle(Qt.RoundJoin)
        painter.strokePath(path, glow)
    border = QPen(SELECTION_COLOR if selected else base.darker(115 if hovered else 100), 2.5 if (selected or hovered) else 2)
    border.setJoinStyle(Qt.RoundJoin)
    painter.strokePath(path, border)


def shape_preview(shape_key, width=72, height=48):
    """A small picture of a shape, for the shape library"""
    shape = SHAPES[shape_key]
    pixmap = QPixmap(width, height)
    pixmap.fill(Qt.transparent)
    w0, h0 = shape.size
    scale = min((width - 8) / w0, (height - 10) / h0)
    w, h = w0 * scale, h0 * scale
    painter = QPainter(pixmap)
    painter.translate((width - w) / 2, (height - h) / 2 - 1)
    paint_shape(painter, shape.outline(w, h), shape.color, note=shape_key == "note", shadow=False)
    painter.end()
    return pixmap


def direction(flag):
    """Unit vector a line leaves a node in, for a link dot ("left", "right", "top", "bottom")"""
    return {"left": QPointF(-1, 0), "right": QPointF(1, 0),
            "top": QPointF(0, -1), "bottom": QPointF(0, 1)}.get(flag, QPointF(0, 0))


def _distance(a, b):
    return math.hypot(b.x() - a.x(), b.y() - a.y())


def smooth_path(points, start_flag=None, end_flag=None):
    """A smooth curve through points. It leaves the first point in the direction of
    start_flag and arrives at the last from end_flag's side (no flag: head straight on)."""
    start, end = points[0], points[-1]
    path = QPainterPath(start)
    if len(points) == 2:
        reach = max(40.0, min(160.0, _distance(start, end) * 0.45))
        path.cubicTo(start + direction(start_flag) * reach, end + direction(end_flag) * reach, end)
        return path

    # Through bend points: a Catmull-Rom style curve, with the ends pointing out of their dots
    tangents = []
    last = len(points) - 1
    for i, point in enumerate(points):
        if i == 0:
            reach = min(_distance(point, points[1]), 200.0) * 1.2
            tangent = direction(start_flag) * reach if start_flag else points[1] - point
        elif i == last:
            reach = min(_distance(points[-2], point), 200.0) * 1.2
            tangent = direction(end_flag) * -reach if end_flag else point - points[-2]
        else:
            tangent = (points[i + 1] - points[i - 1]) * 0.5
        tangents.append(tangent)
    for i in range(last):
        path.cubicTo(points[i] + tangents[i] / 3, points[i + 1] - tangents[i + 1] / 3, points[i + 1])
    return path


def find_node(item):
    """The node an item belongs to (the item itself, or one of its parents)"""
    while item is not None:
        if isinstance(item, NodeItem):
            return item
        item = item.parentItem()
    return None


# ---------------------------------------------------------------- connections

class EditableText(QGraphicsTextItem):
    """Text that becomes editable on request; Enter or Esc (or clicking away) finishes.
    on_finish(text) is called when typing ends."""

    def __init__(self, parent, on_finish=None, point_size=9, bold=False, color=TEXT_COLOR):
        super().__init__("", parent)
        self.on_finish = on_finish
        font = QFont()
        font.setPointSize(point_size)
        font.setBold(bold)
        self.setFont(font)
        self.setDefaultTextColor(color)
        self._editing = False
        self.stopEditing(notify=False)

    def isEditing(self):
        return self._editing

    def startEditing(self):
        self._editing = True
        self.setTextInteractionFlags(Qt.TextEditorInteraction)
        self.setFocus(Qt.MouseFocusReason)
        cursor = self.textCursor()
        cursor.select(cursor.Document)
        self.setTextCursor(cursor)

    def stopEditing(self, notify=True):
        was_editing, self._editing = self._editing, False
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        cursor = self.textCursor()
        cursor.clearSelection()
        self.setTextCursor(cursor)
        self.clearFocus()
        if notify and was_editing and self.on_finish is not None:
            self.on_finish(self.toPlainText())

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        if self._editing:
            self.stopEditing()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Escape, Qt.Key_Return, Qt.Key_Enter):
            self.stopEditing()
            event.accept()
            return
        super().keyPressEvent(event)


class LineLabel(EditableText):
    """A line's label: a small tag in the middle of the line. Double-click it (or the line) to edit."""

    PADDING = 4

    def __init__(self, connection):
        super().__init__(connection, on_finish=connection.setLabel)
        self.connection = connection
        self.setAcceptedMouseButtons(Qt.LeftButton)
        self.setCursor(Qt.IBeamCursor)
        self.setToolTip("Double-click to edit the label")
        self.document().contentsChanged.connect(lambda: self.connection._placeLabel())

    def boundingRect(self):
        p = self.PADDING
        return super().boundingRect().adjusted(-p, -p / 2, p, p / 2)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing)
        border = SELECTION_COLOR if self.connection.isSelected() else self.connection.baseColor()
        painter.setPen(QPen(border, 1.2))
        painter.setBrush(QColor("#ffffff"))
        painter.drawRoundedRect(self.boundingRect().adjusted(1, 1, -1, -1), 6, 6)
        super().paint(painter, option, widget)

    def mousePressEvent(self, event):
        if self.isEditing():
            super().mousePressEvent(event)
            return
        scene = self.scene()
        if scene is not None and not self.connection.isSelected():
            scene.clearSelection()
            self.connection.setSelected(True)
        event.accept()

    def mouseDoubleClickEvent(self, event):
        if not self.isEditing():
            self.startEditing()
        event.accept()


FRAME_TITLE_HEIGHT = 30
FRAME_EDGE = 8  # how far in from its border a frame can be grabbed
DEFAULT_FRAME_COLOR = "#64748b"


class FrameItem(QGraphicsRectItem):
    """A titled box behind shapes, to group them. Drag it by its title or edge and the
    shapes inside move with it; clicks inside it reach the canvas (for drag-to-select)."""

    kind = "frame"

    def __init__(self, width=420, height=280, title="Frame", color=DEFAULT_FRAME_COLOR, logger=None):
        self.width, self.height = width, height
        super().__init__(0, 0, width, height)
        self.id = str(uuid4())
        self.color = color
        self.resizing = False
        self._placing = False
        self._carried = []  # shapes moving with the frame during a drag
        self._carried_lines = []
        self._last_pos = None
        self._drag_start = None
        self.setZValue(-10)
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable |
                      QGraphicsItem.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        self.setPen(QPen(Qt.NoPen))
        self.title_item = EditableText(self, on_finish=self.setTitle, point_size=10, bold=True)
        self.title_item.setAcceptedMouseButtons(Qt.NoButton)
        self.title_item.setPlainText(title)
        self.title_item.setPos(10, 4)
        self.handles = [ResizeHandle(self, corner) for corner in ("top_left", "top_right", "bottom_left", "bottom_right")]
        self._layout()
        for handle in self.handles:
            handle.setVisible(False)

    # -- look --------------------------------------------------------------
    @property
    def title(self):
        return self.title_item.toPlainText().strip()

    def setTitle(self, text):
        self.title_item.setPlainText((text or "").strip() or "Frame")
        self.title_item.setAcceptedMouseButtons(Qt.NoButton)

    def editTitle(self):
        self.title_item.setAcceptedMouseButtons(Qt.LeftButton)
        self.title_item.startEditing()

    def setColor(self, color):
        self.color = color
        self.title_item.setDefaultTextColor(QColor(color).darker(150))
        self.update()

    def boundingRect(self):
        return QRectF(0, 0, self.width, self.height).adjusted(-4, -4, 4, 4)

    def shape(self):
        """Only the title bar and the border can be grabbed"""
        path = QPainterPath()
        path.addRect(QRectF(0, 0, self.width, FRAME_TITLE_HEIGHT))
        edge = QPainterPath()
        edge.addRect(QRectF(0, 0, self.width, self.height))
        stroker = QPainterPathStroker()
        stroker.setWidth(FRAME_EDGE * 2)
        return path.united(stroker.createStroke(edge))

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing)
        base = QColor(self.color)
        rect = QRectF(0, 0, self.width, self.height)
        fill = tint(base, 0.88)
        fill.setAlpha(150)
        painter.setPen(Qt.NoPen)
        painter.setBrush(fill)
        painter.drawRoundedRect(rect, 10, 10)
        title_bar = QPainterPath()
        title_bar.addRoundedRect(QRectF(0, 0, self.width, FRAME_TITLE_HEIGHT + 10), 10, 10)
        clip = QPainterPath()
        clip.addRect(QRectF(0, 0, self.width, FRAME_TITLE_HEIGHT))
        bar = tint(base, 0.7)
        bar.setAlpha(170)
        painter.fillPath(title_bar.intersected(clip), bar)
        selected = self.isSelected()
        pen = QPen(SELECTION_COLOR if selected else base, 2.5 if selected else 1.5)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect, 10, 10)

    def _layout(self):
        self.prepareGeometryChange()
        self.setRect(0, 0, self.width, self.height)
        for handle, (x, y) in zip(self.handles, ((0, 0), (self.width, 0), (0, self.height), (self.width, self.height))):  # noqa: B905 (always 4 corners; strict= needs Python 3.10)
            handle.setPos(x, y)
        self.title_item.setTextWidth(max(60, self.width - 20))
        self.setColor(self.color)

    # -- the ResizeHandle interface -------------------------------------------
    def sceneBoundingRectOfShape(self):
        return QRectF(self.pos(), QPointF(self.pos().x() + self.width, self.pos().y() + self.height))

    def setSceneGeometry(self, rect):
        self.width, self.height = max(160, rect.width()), max(100, rect.height())
        self._placing = True
        self.setPos(rect.topLeft())
        self._placing = False
        self._layout()

    def fitText(self):
        pass

    # -- carrying its contents ----------------------------------------------
    def contents(self):
        """The shapes whose centre is inside the frame"""
        area = self.sceneBoundingRectOfShape()
        return [item for item in (self.scene().items(area) if self.scene() else [])
                if isinstance(item, NodeItem) and area.contains(item.sceneCenter())]

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Shapes inside move with the frame (selected ones are moved by the selection anyway)
            self._carried = [node for node in self.contents() if not node.isSelected()]
            carried = set(self._carried)
            self._carried_lines = {line for node in self._carried for line in node.connections
                                   if line.start_node in carried and line.end_node in carried}
            self._last_pos = self._drag_start = self.pos()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self._carried, self._carried_lines, self._last_pos, self._drag_start = [], set(), None, None

    def mouseDoubleClickEvent(self, event):
        if event.pos().y() <= FRAME_TITLE_HEIGHT:
            self.editTitle()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedHasChanged:
            for handle in self.handles:
                handle.setVisible(bool(value))
            self.update()
        elif change == QGraphicsItem.ItemPositionChange and not self._placing and self._drag_start is not None \
                and self.scene() is not None and getattr(self.scene(), "snap_to_grid", False):
            # Snap the distance moved (not the position), so the shapes inside stay on the grid
            grid = getattr(self.scene(), "grid_size", 25)
            moved = value - self._drag_start
            return self._drag_start + QPointF(round(moved.x() / grid) * grid, round(moved.y() / grid) * grid)
        elif change == QGraphicsItem.ItemPositionHasChanged and self._last_pos is not None:
            delta = self.pos() - self._last_pos
            self._last_pos = self.pos()
            for line in self._carried_lines:
                line.waypoints = [point + delta for point in line.waypoints]
            for node in self._carried:
                node._placing = True
                node.setPos(node.pos() + delta)
                node._placing = False
        return super().itemChange(change, value)

    # -- saving ----------------------------------------------------------------
    def serialize(self):
        return {"kind": self.kind, "id": self.id, "title": self.title, "color": self.color,
                "position": {"x": self.pos().x(), "y": self.pos().y()}, "width": self.width, "height": self.height}

    def deserialize(self, data):
        self.id = data.get("id", self.id)
        self.color = data.get("color") or DEFAULT_FRAME_COLOR
        self.width = data.get("width") or self.width
        self.height = data.get("height") or self.height
        self.setTitle(data.get("title", "Frame"))
        self._layout()
        pos = data.get("position", {})
        self._placing = True
        self.setPos(pos.get("x", 0), pos.get("y", 0))
        self._placing = False

    def remove_from_scene(self, with_contents=False):
        scene = self.scene()
        if scene is None:
            return
        if with_contents:
            for node in self.contents():
                node.remove_from_scene()
        scene.removeItem(self)


class GroupOutline(QGraphicsItem):
    """A dashed outline around each selected group (one item draws them all)"""

    PAD = 12

    def __init__(self):
        super().__init__()
        self.setZValue(15)
        self.setAcceptedMouseButtons(Qt.NoButton)
        self.setAcceptHoverEvents(False)
        self._rects = []
        self._bounds = QRectF()

    def refresh(self):
        scene = self.scene()
        groups = {item.group_id for item in scene.selectedItems() if isinstance(item, NodeItem) and item.group_id}
        rects = []
        for group_id in groups:
            members = [item for item in scene.items() if isinstance(item, NodeItem) and item.group_id == group_id]
            area = members[0].sceneBoundingRectOfShape()
            for member in members[1:]:
                area = area.united(member.sceneBoundingRectOfShape())
            rects.append(area.adjusted(-self.PAD, -self.PAD, self.PAD, self.PAD))
        bounds = QRectF()
        for rect in rects:
            bounds = bounds.united(rect.adjusted(-4, -24, 4, 4))
        self.prepareGeometryChange()
        self._rects, self._bounds = rects, bounds
        self.update()

    def boundingRect(self):
        return self._bounds

    def shape(self):
        """Nothing to hit: what's under the pointer is always the shape below, not the outline"""
        return QPainterPath()

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(SELECTION_COLOR, 1.5, Qt.DashLine)
        font = QFont()
        font.setPointSize(8)
        font.setBold(True)
        painter.setFont(font)
        for rect in self._rects:
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(rect, 10, 10)
            tag = QRectF(rect.left() + 8, rect.top() - 18, 46, 16)
            painter.setPen(Qt.NoPen)
            painter.setBrush(SELECTION_COLOR)
            painter.drawRoundedRect(tag, 4, 4)
            painter.setPen(QColor("#ffffff"))
            painter.drawText(tag, Qt.AlignCenter, "Group")


def refresh_group_outlines(scene):
    """Redraw the outlines around selected groups (made the first time it's needed)"""
    if scene is None:
        return
    outline = getattr(scene, "group_outline", None)
    try:
        alive = outline is not None and outline.scene() is scene
    except RuntimeError:  # removed when the canvas was cleared
        alive = False
    if not alive:
        outline = GroupOutline()
        scene.addItem(outline)
        scene.group_outline = outline
    outline.refresh()


def group_items(nodes):
    """Make shapes one group (any groups they were in are merged into it). Returns the group id."""
    group_id = str(uuid4())
    for node in nodes:
        node.group_id = group_id
        node.setHandlesVisible(False)
    if nodes:
        refresh_group_outlines(nodes[0].scene())
    return group_id


def ungroup_items(nodes):
    """Break up the groups these shapes are in (every member, not just these)"""
    scene = nodes[0].scene() if nodes else None
    group_ids = {node.group_id for node in nodes if node.group_id}
    if scene is None or not group_ids:
        return
    for item in scene.items():
        if isinstance(item, NodeItem) and item.group_id in group_ids:
            item.group_id = None
            item.setHandlesVisible(item.isSelected() and len(scene.selectedItems()) == 1)
    refresh_group_outlines(scene)


def find_frame(item):
    """The frame an item belongs to (the item itself, or its title)"""
    while item is not None:
        if isinstance(item, FrameItem):
            return item
        item = item.parentItem()
    return None


class EndGrip(QGraphicsEllipseItem):
    """A round grip near one end of a line, shown while the line is hovered or selected.
    Drag it to another shape to move that end of the line there.

    Grips sit above everything (a line's ends are underneath the shapes they join, so
    the ends themselves can't be grabbed), a little way along the line so they don't
    cover the shape's own link dot."""

    RADIUS = 6
    OFFSET = 18  # distance along the line from the end

    def __init__(self, connection, end):
        r = self.RADIUS
        super().__init__(-r, -r, 2 * r, 2 * r)
        self.connection = connection
        self.end = end  # "start" or "end"
        self.hovered = False
        self.setZValue(20)
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.LeftButton)
        self.setCursor(Qt.OpenHandCursor)
        self.setToolTip("Drag to another shape to move this end of the line")
        self.setPen(QPen(SELECTION_COLOR, 2))
        self.setBrush(QBrush(HANDLE_FILL))
        self.setVisible(False)

    def hoverEnterEvent(self, event):
        self.hovered = True
        self.setScale(1.3)
        self.setBrush(QBrush(SELECTION_COLOR))
        self.connection.refreshGrips()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.hovered = False
        self.setScale(1.0)
        self.setBrush(QBrush(HANDLE_FILL))
        self.connection.refreshGrips(delayed=True)
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setCursor(Qt.ClosedHandCursor)
            self.connection.beginEndDrag(self.end)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.connection.dragging_end_name == self.end:
            self.connection.dragEndTo(event.scenePos())
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.connection.dragging_end_name == self.end and event.button() == Qt.LeftButton:
            self.setCursor(Qt.OpenHandCursor)
            self.connection.finishEndDrag(event.scenePos())
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def sceneEvent(self, event):
        # Mouse taken away mid-drag: put the line back the way it was
        if event.type() == QEvent.UngrabMouse and self.connection.dragging_end_name == self.end:
            self.setCursor(Qt.OpenHandCursor)
            self.connection.finishEndDrag(None)
        return super().sceneEvent(event)


class BendHandle(QGraphicsRectItem):
    """A small diamond on a bend point of a line. Drag it to reshape the line; click it
    and press Delete (or double-click it) to remove the bend.

    The clicked bend is remembered on the scene (scene.active_bend), so Delete knows to
    remove just that bend rather than the selected line."""

    SIZE = 9

    def __init__(self, connection, index):
        size = self.SIZE
        super().__init__(-size / 2, -size / 2, size, size)
        self.connection = connection
        self.index = index
        self.hovered = False
        self.dragging = False
        self.setRotation(45)
        self.setZValue(21)
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.LeftButton)
        self.setCursor(Qt.SizeAllCursor)
        self.setToolTip("Drag to reshape the line\nClick, then Delete to remove this bend (or double-click it)")
        self.setPen(QPen(SELECTION_COLOR, 1.5))
        self.setBrush(QBrush(HANDLE_FILL))
        self.setVisible(False)

    def isActive(self):
        return self.scene() is not None and getattr(self.scene(), "active_bend", None) is self

    def _restyle(self):
        lit = self.hovered or self.isActive()
        self.setScale(1.5 if self.isActive() else (1.3 if self.hovered else 1.0))
        self.setBrush(QBrush(SELECTION_COLOR if lit else HANDLE_FILL))
        self.setPen(QPen(HANDLE_FILL if self.isActive() else SELECTION_COLOR, 1.5))

    def hoverEnterEvent(self, event):
        self.hovered = True
        self._restyle()
        self.connection.refreshGrips()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.hovered = False
        self._restyle()
        self.connection.refreshGrips(delayed=True)
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.activate()
            event.accept()
        else:
            super().mousePressEvent(event)

    def activate(self):
        """Make this the bend Delete removes; keep its line selected so its bends stay shown"""
        scene = self.scene()
        if scene is None:
            return
        set_active_bend(scene, self)
        scene.clearSelection()
        self.connection.setSelected(True)

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.connection.moveWaypoint(self.index, event.scenePos())
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.dragging and event.button() == Qt.LeftButton:
            self.dragging = False
            self.connection.refreshGrips(delayed=True)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        self.connection.removeWaypoint(self.index)
        event.accept()


class ConnectionItem(QGraphicsPathItem):
    """A curved line with an arrowhead, from a point on one node to a point on another.

    - Hovering it (or the link dot it's attached to) highlights it and shows a grip at
      each end; dragging a grip moves that end to another node, with a live preview.
    - Pressing anywhere on it and dragging adds a bend point there, so the line can be
      pulled out of the way. Bend points show as diamonds; drag one to reshape the line,
      double-click it to remove it. They're saved with the mind map.
    """

    ARROW_SIZE = 9
    GRIP_HIDE_DELAY_MS = 300  # time to move from the line or dot onto a grip

    def __init__(self, start_node, start_handle, end_node, end_handle, points=None, color=None, label=""):
        super().__init__()
        self.color = color  # None: the standard grey
        self.label_item = LineLabel(self)
        self.label_item.setPlainText(label or "")
        self.label_item.setVisible(bool(label))
        self.start_node = start_node
        self.start_handle = start_handle
        self.end_node = end_node
        self.end_handle = end_handle
        self.waypoints = [QPointF(x, y) for x, y in (points or [])]  # bend points, in scene coordinates
        self.hovered = False
        self.highlighted = False  # its link dot is hovered
        self.grips = {}
        self.bend_handles = []
        self.dragging_end_name = None  # "start" or "end" while a grip is dragged
        self.drop_target = None
        self._anchors = None  # where the ends were last time, to carry bends along with both shapes
        self._press_pos = None  # pressed on the line: dragging adds a bend here
        self._bend_index = None  # the bend being dragged straight after adding it

        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.SizeAllCursor)
        self.setToolTip("Drag to bend this line")
        self.setZValue(-1)

        if self.start_node:
            self.start_node.add_connection(self)
        if self.end_node:
            self.end_node.add_connection(self)

        self.update_position()

    # -- geometry --------------------------------------------------------
    def _handle_pos(self, node, flag):
        return node.mapToScene(node.anchor_point(flag))

    def _curve(self, start, start_flag, end, end_flag):
        return smooth_path([start] + self.waypoints + [end], start_flag, end_flag)

    def update_position(self):
        if not (self.start_node and self.end_node) or self.dragging_end_name:
            return
        start = self._handle_pos(self.start_node, self.start_handle)
        end = self._handle_pos(self.end_node, self.end_handle)
        # Both shapes moving together (both selected and dragged): bring the bends along.
        # Qt moves selected shapes one at a time, so each shape's move carries the bends
        # half its distance; once both have moved they've gone the whole way.
        if self._anchors is not None and self.waypoints and self._movingTogether():
            moved = ((start - self._anchors[0]) + (end - self._anchors[1])) / 2
            if moved.manhattanLength() > 0:
                self.waypoints = [point + moved for point in self.waypoints]
        self._anchors = (start, end)
        self.setPath(self._curve(start, self.start_handle, end, self.end_handle))
        self._placeGrips()
        self._placeBendHandles()
        self._placeLabel()

    # -- label -----------------------------------------------------------
    @property
    def label(self):
        return self.label_item.toPlainText().strip()

    def setLabel(self, text):
        text = (text or "").strip()
        if self.label_item.toPlainText() != text:
            self.label_item.setPlainText(text)
        self.label_item.setVisible(bool(text) or self.label_item.isEditing())
        self._placeLabel()

    def editLabel(self):
        """Type a label for the line (Enter finishes; an empty label is removed)"""
        self.label_item.setVisible(True)
        self._placeLabel()
        self.label_item.startEditing()

    def _placeLabel(self):
        """Keep the label centred halfway along the line"""
        path = self.path()
        if path.length() <= 0:
            return
        middle = path.pointAtPercent(path.percentAtLength(path.length() / 2))
        self.label_item.setPos(middle - self.label_item.boundingRect().center())

    def mouseDoubleClickEvent(self, event):
        self.editLabel()
        event.accept()

    def _movingTogether(self):
        nodes = (self.start_node, self.end_node)
        return (self.start_node is not self.end_node and all(node.isSelected() for node in nodes)
                and not any(getattr(node, "resizing", False) for node in nodes))

    # -- bend points -------------------------------------------------------
    def serializedPoints(self):
        return [[round(point.x(), 1), round(point.y(), 1)] for point in self.waypoints]

    def percentAt(self, scene_pos, samples=160):
        """Roughly how far along the line (0 to 1) the point nearest scene_pos is"""
        path = self.path()
        return min((i / samples for i in range(samples + 1)),
                   key=lambda t: _distance(path.pointAtPercent(t), scene_pos))

    def insertWaypoint(self, scene_pos):
        """Add a bend at scene_pos, in order along the line; returns its index"""
        at = self.percentAt(scene_pos)
        index = sum(1 for point in self.waypoints if self.percentAt(point) < at)
        self.waypoints.insert(index, QPointF(scene_pos))
        self._rebuildBendHandles()
        self.update_position()
        return index

    def moveWaypoint(self, index, scene_pos):
        self.waypoints[index] = QPointF(scene_pos)
        self.update_position()

    def removeWaypoint(self, index):
        del self.waypoints[index]
        self._rebuildBendHandles()
        self.update_position()
        self.refreshGrips()

    def clearWaypoints(self):
        self.waypoints = []
        self._rebuildBendHandles()
        self.update_position()

    def _rebuildBendHandles(self):
        for handle in self.bend_handles:
            if handle.scene() is not None:
                if getattr(handle.scene(), "active_bend", None) is handle:
                    handle.scene().active_bend = None
                handle.scene().removeItem(handle)
        self.bend_handles = []
        if self.scene() is None:
            return
        for index in range(len(self.waypoints)):
            handle = BendHandle(self, index)
            self.scene().addItem(handle)
            self.bend_handles.append(handle)
        self._placeBendHandles()
        self._refreshGripsNow()

    def _placeBendHandles(self):
        for handle, point in zip(self.bend_handles, self.waypoints):  # noqa: B905 (handles rebuild lazily)  # handles rebuild lazily
            handle.setPos(point)

    def boundingRect(self):
        margin = self.ARROW_SIZE + 6
        return self.path().boundingRect().adjusted(-margin, -margin, margin, margin)

    def shape(self):
        stroker = QPainterPathStroker()
        stroker.setWidth(14)  # easy to click
        return stroker.createStroke(self.path())

    def setColor(self, color):
        self.color = color
        self.update()

    def baseColor(self):
        return QColor(self.color) if self.color else CONNECTION_COLOR

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing)
        dragging = self.dragging_end_name is not None
        active = self.isSelected() or self.highlighted or self.hovered or dragging
        base = self.baseColor()
        if self.color is None:
            color = SELECTION_COLOR if active else base  # grey lines light up blue
        else:
            color = base.darker(115) if active else base  # coloured lines keep their colour
        glow_color = SELECTION_COLOR if (self.isSelected() or self.color is None) else base
        pen = QPen(color, 3 if active else 2.5, Qt.DashLine if dragging else Qt.SolidLine)
        pen.setCapStyle(Qt.RoundCap)
        if active and not dragging:  # a soft glow so a highlighted line stands out
            glow = QPen(QColor(glow_color.red(), glow_color.green(), glow_color.blue(), 60), 9)
            glow.setCapStyle(Qt.RoundCap)
            painter.setPen(glow)
            painter.drawPath(self.path())
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(self.path())

        # Arrowhead at the end, pointing along the curve
        path = self.path()
        if path.length() > self.ARROW_SIZE:
            tip = path.pointAtPercent(1.0)
            angle = math.radians(path.angleAtPercent(1.0))
            back = QPointF(math.cos(angle), -math.sin(angle)) * -self.ARROW_SIZE
            side = QPointF(math.sin(angle), math.cos(angle)) * (self.ARROW_SIZE * 0.55)
            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            painter.drawPolygon(QPolygonF([tip, tip + back + side, tip + back - side]))

    # -- highlight and grips ----------------------------------------------
    def setHighlighted(self, highlighted):
        """Called while the link dot this line is attached to is hovered"""
        self.highlighted = highlighted
        self.update()
        self.refreshGrips(delayed=not highlighted)

    def _ensureGrips(self):
        if not self.grips and self.scene() is not None:
            for end in ("start", "end"):
                grip = EndGrip(self, end)
                self.scene().addItem(grip)
                self.grips[end] = grip
            self._placeGrips()

    def _placeGrips(self):
        path = self.path()
        length = path.length()
        if not self.grips or length <= 0:
            return
        offset = min(EndGrip.OFFSET, length / 3)
        self.grips["start"].setPos(path.pointAtPercent(path.percentAtLength(offset)))
        self.grips["end"].setPos(path.pointAtPercent(path.percentAtLength(length - offset)))

    def gripsWanted(self):
        return (self.hovered or self.highlighted or self.isSelected() or self.dragging_end_name is not None
                or self._bend_index is not None
                or any(grip.hovered for grip in self.grips.values())
                or any(handle.hovered or handle.dragging for handle in self.bend_handles))

    def refreshGrips(self, delayed=False):
        """Show the grips while the line is in use; hide them (after a moment, so the
        pointer can travel onto one) when it isn't"""
        if delayed:
            QTimer.singleShot(self.GRIP_HIDE_DELAY_MS, self._refreshGripsNow)
        else:
            self._refreshGripsNow()

    def _refreshGripsNow(self):
        try:
            if self.scene() is None:
                return
        except RuntimeError:  # deleted while the timer was waiting
            return
        wanted = self.gripsWanted()
        if wanted:
            self._ensureGrips()
            if len(self.bend_handles) != len(self.waypoints):
                self._rebuildBendHandles()
                return
        for handle in list(self.grips.values()) + self.bend_handles:
            handle.setVisible(wanted)

    # -- moving an end ---------------------------------------------------
    def beginEndDrag(self, end):
        self.dragging_end_name = end
        self.update()

    def dragEndTo(self, scene_pos):
        """Preview: the line follows the pointer; the node under it shows where it would attach"""
        if self.dragging_end_name == "start":
            fixed_node, fixed_flag = self.end_node, self.end_handle
        else:
            fixed_node, fixed_flag = self.start_node, self.start_handle
        target = node_at(self.scene(), scene_pos, exclude=fixed_node)
        self._setDropTarget(target, scene_pos)

        moving_pos, moving_flag = scene_pos, None
        if target is not None:  # snap the preview to the dot it would attach to
            moving_flag = target.nearest_anchor(scene_pos)
            moving_pos = self._handle_pos(target, moving_flag)
        fixed_pos = self._handle_pos(fixed_node, fixed_flag)
        if self.dragging_end_name == "start":
            self.setPath(self._curve(moving_pos, moving_flag, fixed_pos, fixed_flag))
        else:
            self.setPath(self._curve(fixed_pos, fixed_flag, moving_pos, moving_flag))
        self._placeBendHandles()
        grip = self.grips.get(self.dragging_end_name)
        if grip is not None:
            grip.setPos(scene_pos)
        self._placeLabel()

    def _setDropTarget(self, target, scene_pos):
        if self.drop_target is not None and self.drop_target is not target:
            self.drop_target.setDropHighlight(None)
        self.drop_target = target
        if target is not None:
            target.setDropHighlight(target.nearest_anchor(scene_pos))

    def finishEndDrag(self, scene_pos):
        """Attach the dragged end to the node it was dropped on (or put it back if none)"""
        end = self.dragging_end_name
        if end is None:
            return
        target = self.drop_target if scene_pos is not None else None
        self._setDropTarget(None, None)
        self.dragging_end_name = None
        if target is not None:
            flag = target.nearest_anchor(scene_pos)
            if end == "start":
                self.start_node.remove_connection(self)
                self.start_node, self.start_handle = target, flag
            else:
                self.end_node.remove_connection(self)
                self.end_node, self.end_handle = target, flag
            target.add_connection(self)
        self.update_position()
        self.update()
        self.refreshGrips(delayed=True)

    # -- life cycle ------------------------------------------------------
    def detach(self):
        if self.start_node:
            self.start_node.remove_connection(self)
        if self.end_node:
            self.end_node.remove_connection(self)

    def remove_from_scene(self):
        self.detach()
        scene = self.scene()
        if scene is not None:
            for handle in list(self.grips.values()) + self.bend_handles:
                if handle.scene() is scene:
                    scene.removeItem(handle)
            scene.removeItem(self)
        self.grips = {}
        self.bend_handles = []

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedHasChanged:
            self.refreshGrips()
        return super().itemChange(change, value)

    # -- mouse -----------------------------------------------------------
    def hoverEnterEvent(self, event):
        self.hovered = True
        self.update()
        self.refreshGrips()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.hovered = False
        self.update()
        self.refreshGrips(delayed=True)
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)  # selects the line
        if event.button() == Qt.LeftButton:
            self._press_pos = event.scenePos()
            self._bend_index = None
            event.accept()

    def mouseMoveEvent(self, event):
        if self._press_pos is None:
            super().mouseMoveEvent(event)
            return
        if self._bend_index is None:
            if (event.scenePos() - self._press_pos).manhattanLength() < QApplication.startDragDistance():
                return
            self._bend_index = self.insertWaypoint(self._press_pos)  # bend from where it was grabbed
        self.moveWaypoint(self._bend_index, event.scenePos())
        event.accept()

    def mouseReleaseEvent(self, event):
        self._press_pos = None
        self._bend_index = None
        self.refreshGrips(delayed=True)
        super().mouseReleaseEvent(event)


def set_active_bend(scene, handle):
    """Remember which bend point was clicked (None to forget), and redraw old and new"""
    previous = getattr(scene, "active_bend", None)
    scene.active_bend = handle
    for item in (previous, handle):
        if item is not None and item.scene() is scene:
            item._restyle()


def node_at(scene, scene_pos, exclude=None):
    """The topmost node under a point in the scene, if any"""
    if scene is None:
        return None
    for item in scene.items(scene_pos):
        node = find_node(item)
        if node is not None and node is not exclude:
            return node
    return None


# ---------------------------------------------------------------- handles

class LinkHandle(QGraphicsEllipseItem):
    """A dot on the edge of a node.

    Dragging a dot that lines are attached to moves those lines' ends to wherever it's
    dropped (that's what highlighting them on hover promises). Dragging a dot with no
    lines, or Ctrl+dragging any dot, draws a new line to another node."""

    TIP_NEW = "Drag to another shape to connect"
    TIP_MOVE = "Drag to move this line to another shape\nCtrl+drag to start a new line from here"

    RADIUS = 6

    def __init__(self, parent_node, handle_position_flag, radius=RADIUS, logger=None):
        super().__init__(-radius, -radius, radius * 2, radius * 2, parent_node)
        self.parent_node = parent_node
        self.handle_position_flag = handle_position_flag
        self.logger = logger or logging.getLogger(__name__)
        self.setBrush(QBrush(HANDLE_FILL))
        self.setPen(QPen(SELECTION_COLOR, 2))
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.LeftButton)
        self.setCursor(Qt.CrossCursor)
        self.setToolTip(self.TIP_NEW)
        self.setZValue(2)

        self.dragging = False
        self.moving = []  # (line, "start"/"end") while moving attached lines
        self.highlighted = []  # lines lit up by hovering this dot
        self.temp_line = None
        self.start_scene_pos = None
        self.last_scene_pos = None
        self.target_node = None

    def attachedConnections(self):
        """The lines that end at this dot"""
        node, flag = self.parent_node, self.handle_position_flag
        return [c for c in node.connections
                if (c.start_node is node and c.start_handle == flag) or (c.end_node is node and c.end_handle == flag)]

    def setEmphasized(self, emphasized):
        self.setScale(1.6 if emphasized else 1.0)
        self.setBrush(QBrush(SELECTION_COLOR if emphasized else HANDLE_FILL))
        self.setPen(QPen(HANDLE_FILL if emphasized else SELECTION_COLOR, 2))

    def hoverEnterEvent(self, event):
        self.setEmphasized(True)
        self.highlighted = self.attachedConnections()
        for connection in self.highlighted:
            connection.setHighlighted(True)
        self.setToolTip(self.TIP_MOVE if self.highlighted else self.TIP_NEW)
        self.setCursor(Qt.OpenHandCursor if self.highlighted else Qt.CrossCursor)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setEmphasized(False)
        self._clearHighlights()
        super().hoverLeaveEvent(event)

    def _clearHighlights(self):
        for connection in self.highlighted:
            connection.setHighlighted(False)
        self.highlighted = []

    def _endAtThisDot(self, connection):
        node, flag = self.parent_node, self.handle_position_flag
        return "start" if (connection.start_node is node and connection.start_handle == flag) else "end"

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton or not self.scene():
            super().mousePressEvent(event)
            return
        attached = self.attachedConnections()
        if attached and not event.modifiers() & Qt.ControlModifier:
            # Move the lines attached here
            self._clearHighlights()
            self.dragging = True
            self.moving = [(connection, self._endAtThisDot(connection)) for connection in attached]
            for connection, end in self.moving:
                connection.beginEndDrag(end)
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
        self.dragging = True
        self.start_scene_pos = self.mapToScene(QPointF(0, 0))
        self.last_scene_pos = self.start_scene_pos
        self.temp_line = QGraphicsPathItem()
        pen = QPen(SELECTION_COLOR, 2, Qt.DashLine)
        pen.setCapStyle(Qt.RoundCap)
        self.temp_line.setPen(pen)
        self.temp_line.setAcceptedMouseButtons(Qt.NoButton)
        self.temp_line.setZValue(5)
        self.scene().addItem(self.temp_line)
        event.accept()

    def mouseMoveEvent(self, event):
        if self.dragging and self.moving:
            self.last_scene_pos = event.scenePos()
            for connection, _end in self.moving:
                connection.dragEndTo(event.scenePos())
            event.accept()
            return
        if not (self.dragging and self.temp_line is not None):
            super().mouseMoveEvent(event)
            return
        self.last_scene_pos = event.scenePos()

        # Over another node: light up the dot the line would attach to, and snap the preview to it
        target = node_at(self.scene(), event.scenePos(), exclude=self.parent_node)
        if target is not self.target_node and self.target_node is not None:
            self.target_node.setDropHighlight(None)
        self.target_node = target
        end, end_flag = event.scenePos(), None
        if target is not None:
            end_flag = target.nearest_anchor(event.scenePos())
            target.setDropHighlight(end_flag)
            end = target.mapToScene(target.anchor_point(end_flag))
        self.temp_line.setPath(smooth_path([self.start_scene_pos, end], self.handle_position_flag, end_flag))
        event.accept()

    def mouseReleaseEvent(self, event):
        if not (self.dragging and event.button() == Qt.LeftButton):
            super().mouseReleaseEvent(event)
            return
        self.finishLink(event.scenePos())
        event.accept()

    def sceneEvent(self, event):
        # Something took the mouse mid-drag (a window, a popup, the dot being hidden):
        # finish where the pointer last was instead of leaving the dashed line behind
        if event.type() == QEvent.UngrabMouse and self.dragging:
            self.finishLink(self.last_scene_pos)
        return super().sceneEvent(event)

    def finishLink(self, scene_pos):
        """End a drag: move the lines being moved, or connect a new line if it ended on another node"""
        if self.moving:
            moving, self.moving = self.moving, []
            self.dragging = False
            for connection, _end in moving:
                connection.finishEndDrag(scene_pos)
            self.setCursor(Qt.CrossCursor)
            return
        self.dragging = False
        scene = self.scene()
        if self.temp_line is not None and self.temp_line.scene():
            self.temp_line.scene().removeItem(self.temp_line)
        self.temp_line = None
        if self.target_node is not None:
            self.target_node.setDropHighlight(None)
            self.target_node = None

        # Dropped anywhere on another node: attach to its nearest link point
        target = node_at(scene, scene_pos, exclude=self.parent_node) if scene_pos is not None else None
        if target is not None and scene is not None:
            scene.addItem(ConnectionItem(self.parent_node, self.handle_position_flag,
                                         target, target.nearest_anchor(scene_pos)))


class ResizeHandle(QGraphicsRectItem):
    """A corner square shown on a selected node; drag it to resize (the opposite corner stays put)"""

    SIZE = 9

    def __init__(self, parent_node, corner_flag, size=SIZE):
        super().__init__(-size / 2, -size / 2, size, size, parent_node)
        self.parent_node = parent_node
        self.corner_flag = corner_flag
        self.setBrush(QBrush(HANDLE_FILL))
        self.setPen(QPen(SELECTION_COLOR, 1.5))
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.LeftButton)
        self.setCursor(Qt.SizeFDiagCursor if corner_flag in ("top_left", "bottom_right") else Qt.SizeBDiagCursor)
        self.setZValue(3)

        self.dragging = False
        self.start_rect = None
        self.drag_start_scene_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.parent_node.resizing = True
            self.start_rect = self.parent_node.sceneBoundingRectOfShape()
            self.drag_start_scene_pos = event.scenePos()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not self.dragging:
            super().mouseMoveEvent(event)
            return
        delta = event.scenePos() - self.drag_start_scene_pos
        rect = QRectF(self.start_rect)
        if "left" in self.corner_flag:
            rect.setLeft(min(rect.left() + delta.x(), rect.right() - MIN_WIDTH))
        else:
            rect.setRight(max(rect.right() + delta.x(), rect.left() + MIN_WIDTH))
        if "top" in self.corner_flag:
            rect.setTop(min(rect.top() + delta.y(), rect.bottom() - MIN_HEIGHT))
        else:
            rect.setBottom(max(rect.bottom() + delta.y(), rect.top() + MIN_HEIGHT))
        self.parent_node.setSceneGeometry(rect)
        event.accept()

    def mouseReleaseEvent(self, event):
        if self.dragging and event.button() == Qt.LeftButton:
            self.dragging = False
            self.parent_node.resizing = False
            self.parent_node.fitText()
            event.accept()
        else:
            super().mouseReleaseEvent(event)


# ---------------------------------------------------------------- nodes

class NodeText(QGraphicsTextItem):
    """A node's text: passes clicks to the node, and becomes editable on double-click"""

    def __init__(self, text, node):
        super().__init__(text, node)
        self.node = node
        font = QFont()
        font.setPointSize(10)
        font.setWeight(QFont.Medium)
        self.setFont(font)
        self.setDefaultTextColor(TEXT_COLOR)
        option = QTextOption(Qt.AlignCenter)
        option.setWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        self.document().setDefaultTextOption(option)
        self.document().contentsChanged.connect(node.fitText)
        self.stopEditing()

    def isEditing(self):
        return bool(self.textInteractionFlags() & Qt.TextEditorInteraction)

    def startEditing(self):
        self.setTextInteractionFlags(Qt.TextEditorInteraction)
        self.setAcceptedMouseButtons(Qt.LeftButton | Qt.RightButton)
        self.setFocus(Qt.MouseFocusReason)
        cursor = self.textCursor()
        cursor.select(cursor.Document)
        self.setTextCursor(cursor)

    def stopEditing(self):
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        self.setAcceptedMouseButtons(Qt.NoButton)  # clicks go to the node, so it can be dragged
        cursor = self.textCursor()
        cursor.clearSelection()
        self.setTextCursor(cursor)
        self.clearFocus()

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.stopEditing()

    def keyPressEvent(self, event):
        # Enter or Esc finishes; Shift+Enter starts a new line
        if event.key() == Qt.Key_Escape or (event.key() in (Qt.Key_Return, Qt.Key_Enter)
                                            and not event.modifiers() & Qt.ShiftModifier):
            self.stopEditing()
            event.accept()
            return
        super().keyPressEvent(event)


class NodeItem(QGraphicsRectItem):
    """
    A shape on the mind map:
      - drawn as a soft tint of its colour with a crisp border and a light shadow
      - moved by dragging, with its centre snapping to the grid when snapping is on
      - resized from the corner squares that show while it's selected
      - linked to other shapes from the dots that show on hover
      - edited in place on double-click; grows to fit its text
    """

    def __init__(self, width=0, height=0, text="Node", parent=None, logger=None,
                 shape=DEFAULT_SHAPE, color=None):
        self.shape_key = shape if shape in SHAPES else DEFAULT_SHAPE
        default_w, default_h = SHAPES[self.shape_key].size
        self.width = width or default_w
        self.height = height or default_h
        super().__init__(0, 0, self.width, self.height, parent)
        self.logger = logger or logging.getLogger(__name__)
        self.id = str(uuid4())
        self.color = color or SHAPES[self.shape_key].color
        self.connections = set()
        self.is_hovered = False
        self._placing = False  # True while resizing: don't snap
        self.resizing = False
        self.group_id = None  # shapes with the same group id are selected and moved as one

        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable |
                      QGraphicsItem.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        self.setPen(QPen(Qt.NoPen))

        self.handle_top_left = ResizeHandle(self, "top_left")
        self.handle_top_right = ResizeHandle(self, "top_right")
        self.handle_bottom_left = ResizeHandle(self, "bottom_left")
        self.handle_bottom_right = ResizeHandle(self, "bottom_right")
        self.link_handle_top = LinkHandle(self, "top", logger=self.logger)
        self.link_handle_bottom = LinkHandle(self, "bottom", logger=self.logger)
        self.link_handle_right = LinkHandle(self, "right", logger=self.logger)
        self.link_handle_left = LinkHandle(self, "left", logger=self.logger)
        self.setHandlesVisible(False)
        self.setLinkHandlesVisible(False)

        self.text_item = NodeText(text, self)
        self.update_node_layout()
        self.fitText()
        self.setPos(self.snapPosition())

    # -- shape and look --------------------------------------------------
    @property
    def shape_def(self):
        return SHAPES[self.shape_key]

    def outline(self):
        return self.shape_def.outline(self.width, self.height)

    def shape(self):
        return self.outline()

    def boundingRect(self):
        return QRectF(0, 0, self.width, self.height).adjusted(-6, -6, 6, 8)

    def paint(self, painter, option, widget=None):
        paint_shape(painter, self.outline(), self.color, note=self.shape_key == "note",
                    hovered=self.is_hovered, selected=self.isSelected())

    def setShape(self, shape_key):
        if shape_key not in SHAPES or shape_key == self.shape_key:
            return
        center = self.sceneCenter()
        self.prepareGeometryChange()
        self.shape_key = shape_key
        self.width, self.height = SHAPES[shape_key].size
        self.update_node_layout()
        self.fitText()
        self.setCenter(center)

    def setColor(self, color):
        self.color = color
        self.update()

    def updateBrush(self, hovered, selected):
        """Kept for callers of the old API: the look now comes from paint()"""
        self.update()

    # -- geometry --------------------------------------------------------
    def anchor_point(self, flag):
        """Where a connection attaches, in this node's coordinates"""
        return {"top": QPointF(self.width / 2, 0), "bottom": QPointF(self.width / 2, self.height),
                "left": QPointF(0, self.height / 2), "right": QPointF(self.width, self.height / 2)
                }.get(flag, QPointF(self.width / 2, self.height / 2))

    def nearest_anchor(self, scene_pos):
        local = self.mapFromScene(scene_pos)
        return min(("top", "bottom", "left", "right"),
                   key=lambda flag: (self.anchor_point(flag) - local).manhattanLength())

    def sceneCenter(self):
        return self.mapToScene(QPointF(self.width / 2, self.height / 2))

    def setCenter(self, scene_center):
        self.setPos(scene_center - QPointF(self.width / 2, self.height / 2))

    def sceneBoundingRectOfShape(self):
        return QRectF(self.pos(), QPointF(self.pos().x() + self.width, self.pos().y() + self.height))

    def setSceneGeometry(self, rect):
        """Place and size the node to a scene rectangle (used while resizing)"""
        self.prepareGeometryChange()
        self.width, self.height = rect.width(), rect.height()
        self._placing = True
        self.setPos(rect.topLeft())
        self._placing = False
        self.update_node_layout()

    def setSizeKeepCenter(self, new_w, new_h):
        center = self.sceneCenter()
        self.prepareGeometryChange()
        self.width, self.height = max(MIN_WIDTH, new_w), max(MIN_HEIGHT, new_h)
        self.update_node_layout()
        self._placing = True
        self.setCenter(center)
        self._placing = False
        self._track()

    def update_node_layout(self):
        """Lay out the outline, handles, and text for the current size"""
        self.setRect(0, 0, self.width, self.height)
        for handle, (x, y) in ((self.handle_top_left, (0, 0)), (self.handle_top_right, (self.width, 0)),
                               (self.handle_bottom_left, (0, self.height)),
                               (self.handle_bottom_right, (self.width, self.height))):
            handle.setPos(x, y)
        for handle in (self.link_handle_top, self.link_handle_bottom, self.link_handle_left, self.link_handle_right):
            handle.setPos(self.anchor_point(handle.handle_position_flag))
        if hasattr(self, "text_item"):
            self.center_text_item()
        self.notify_connections()

    def center_text_item(self):
        area = self.shape_def.text_rect(self.width, self.height)
        self.text_item.setTextWidth(area.width())
        text_height = self.text_item.boundingRect().height()
        self.text_item.setPos(area.left(), area.top() + (area.height() - text_height) / 2)

    def fitText(self):
        """Grow taller (never shorter) so all the text fits inside the shape"""
        if not hasattr(self, "text_item"):
            return
        needed = self.text_item.document().size().height()
        height = self.height
        area = self.shape_def.text_rect(self.width, height)
        self.text_item.setTextWidth(area.width())
        while area.height() < needed and height < 2000:
            height += 4
            area = self.shape_def.text_rect(self.width, height)
        if height != self.height:
            self.setSizeKeepCenter(self.width, height)
        else:
            self.center_text_item()

    # -- snapping --------------------------------------------------------
    def _gridSize(self):
        return getattr(self.scene(), "grid_size", 25) if self.scene() else 25

    def _snapEnabled(self):
        return getattr(self.scene(), "snap_to_grid", True) if self.scene() else True

    def snapPosition(self, pos=None):
        """Top-left position that puts the node's centre on a grid point"""
        pos = self.pos() if pos is None else pos
        grid = self._gridSize()
        center = pos + QPointF(self.width / 2, self.height / 2)
        snapped = QPointF(round(center.x() / grid) * grid, round(center.y() / grid) * grid)
        return snapped - QPointF(self.width / 2, self.height / 2)

    # -- handles ---------------------------------------------------------
    def setHandlesVisible(self, visible):
        for handle in (self.handle_top_left, self.handle_top_right, self.handle_bottom_left, self.handle_bottom_right):
            handle.setVisible(visible)

    def setDropHighlight(self, flag):
        """While a line end is dragged over this node: show its dots and enlarge the one it
        would attach to (flag None clears it)"""
        self.is_hovered = flag is not None
        self.setLinkHandlesVisible(flag is not None)
        for handle in (self.link_handle_top, self.link_handle_bottom, self.link_handle_right, self.link_handle_left):
            handle.setEmphasized(handle.handle_position_flag == flag)
        self.update()

    def setLinkHandlesVisible(self, visible):
        for handle in (self.link_handle_top, self.link_handle_bottom, self.link_handle_right, self.link_handle_left):
            if handle.dragging:
                continue  # hiding the dot being dragged from would cancel the drag
            handle.setVisible(visible)

    # -- mouse -----------------------------------------------------------
    def hoverEnterEvent(self, event):
        self.is_hovered = True
        self.setLinkHandlesVisible(True)
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.is_hovered = False
        self.setLinkHandlesVisible(False)
        self.update()
        super().hoverLeaveEvent(event)

    def mouseDoubleClickEvent(self, event):
        self.text_item.startEditing()
        event.accept()

    def startEditing(self):
        self.text_item.startEditing()

    # -- saving ----------------------------------------------------------
    def serialize(self):
        """A JSON-ready description of this node"""
        pos = self.pos()
        return {
            "id": self.id,
            "text": self.text_item.toPlainText(),
            "width": self.width,
            "height": self.height,
            "position": {"x": pos.x(), "y": pos.y()},
            "shape": self.shape_key,
            "color": self.color,
            "z": self.zValue(),
            "group": self.group_id,
        }

    def deserialize(self, data: dict):
        """Restore a node from serialize() output (older saves have no shape or colour)"""
        self.id = data.get("id", self.id)
        self.prepareGeometryChange()
        self.shape_key = data.get("shape") if data.get("shape") in SHAPES else LEGACY_SHAPE
        self.color = data.get("color") or DEFAULT_COLOR
        self.width = data.get("width") or self.shape_def.size[0]
        self.height = data.get("height") or self.shape_def.size[1]
        self.text_item.setPlainText(data.get("text", ""))
        self.setZValue(data.get("z", 0))
        self.group_id = data.get("group")
        self.update_node_layout()
        pos = data.get("position", {})
        self._placing = True  # put it back exactly where it was saved
        self.setPos(pos.get("x", 0), pos.get("y", 0))
        self._placing = False
        self._track()

    # -- connections -----------------------------------------------------
    def add_connection(self, connection):
        self.connections.add(connection)

    def remove_connection(self, connection):
        self.connections.discard(connection)

    def notify_connections(self):
        for connection in list(self.connections):
            connection.update_position()

    def remove_from_scene(self):
        """Delete this node and every line attached to it"""
        for connection in list(self.connections):
            connection.remove_from_scene()
        if self.scene():
            self.scene().removeItem(self)

    def _track(self):
        if self.scene() and hasattr(self.scene(), "spatial_tracker"):
            self.scene().spatial_tracker.update_object(self.id, self.sceneBoundingRect())

    def groupMembers(self):
        """The other shapes in this shape's group"""
        if not self.group_id or self.scene() is None:
            return []
        return [item for item in self.scene().items()
                if isinstance(item, NodeItem) and item is not self and item.group_id == self.group_id]

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedHasChanged:
            scene = self.scene()
            if self.group_id and scene is not None and not getattr(scene, "_selecting_group", False):
                # A group is selected (and deselected) as a whole
                scene._selecting_group = True
                for member in self.groupMembers():
                    member.setSelected(bool(value))
                scene._selecting_group = False
            # Resize corners only for a shape selected on its own
            self.setHandlesVisible(bool(value) and not self.group_id)
            self.update()
            refresh_group_outlines(scene)
        elif change == QGraphicsItem.ItemPositionChange and not self._placing and self._snapEnabled():
            return self.snapPosition(value)
        elif change == QGraphicsItem.ItemPositionHasChanged:
            self.notify_connections()
            self._track()
            if self.group_id:
                refresh_group_outlines(self.scene())
        return super().itemChange(change, value)
