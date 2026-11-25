"""
Tests for editing mind maps by hand: adding shapes from the library, moving,
resizing, linking, typing, deleting, and the right-click menu. Uses real mouse
and key events on an offscreen view, against a temporary data directory.
"""
import logging
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import QEvent, QMimeData, QPointF, Qt
from PyQt5.QtGui import QDropEvent, QMouseEvent
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication

logger = logging.getLogger("test_mindmap_editing")


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def screen(app):
    from ui.mindmap_screen import MindMapScreen
    screen = MindMapScreen(logger=logger)
    screen.resize(1400, 900)
    screen.show()
    screen.view.centerOn(0, 0)
    app.processEvents()
    yield screen
    screen.close()


def nodes(screen):
    from ui.custom_widgets.mindmap_nodes import NodeItem
    return [item for item in screen.scene.items() if isinstance(item, NodeItem)]


def connections(screen):
    from ui.custom_widgets.mindmap_nodes import ConnectionItem
    return [item for item in screen.scene.items() if isinstance(item, ConnectionItem)]


def view_point(screen, scene_pos):
    return screen.view.mapFromScene(scene_pos)


def drag(screen, start_scene, end_scene, steps=6):
    """Press at start, move in steps with the button held, release at end (scene coordinates)"""
    viewport = screen.view.viewport()
    start, end = view_point(screen, start_scene), view_point(screen, end_scene)
    QTest.mousePress(viewport, Qt.LeftButton, Qt.NoModifier, start)
    for step in range(1, steps + 1):
        point = start + (end - start) * step / steps
        move = QMouseEvent(QEvent.MouseMove, QPointF(point), Qt.NoButton, Qt.LeftButton, Qt.NoModifier)
        QApplication.sendEvent(viewport, move)
    QTest.mouseRelease(viewport, Qt.LeftButton, Qt.NoModifier, end)


def finish_editing(screen):
    for node in nodes(screen):
        node.text_item.stopEditing()


# ---------------------------------------------------------------- adding

def test_every_library_shape_can_be_added(screen):
    from ui.custom_widgets.mindmap_nodes import SHAPES
    assert [tile.shape_key for tile in screen.shapeLibrary.tiles] == list(SHAPES)
    for key in SHAPES:
        screen.shapeLibrary.shapeClicked.emit(key)
    assert sorted(node.shape_key for node in nodes(screen)) == sorted(SHAPES)


def test_dropping_a_shape_adds_it_where_it_was_dropped(screen):
    from ui.mindmap_screen import SHAPE_MIME
    mime = QMimeData()
    mime.setData(SHAPE_MIME, b"diamond")
    target = view_point(screen, QPointF(200, 100))
    drop = QDropEvent(QPointF(target), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier)
    screen.view.dropEvent(drop)

    (node,) = nodes(screen)
    assert node.shape_key == "diamond"
    center = node.sceneCenter()
    assert abs(center.x() - 200) <= 13 and abs(center.y() - 100) <= 13  # snapped to the 25px grid


def test_a_new_shape_is_ready_to_type_into(screen):
    node = screen.add_node("rounded")
    assert node.text_item.isEditing()
    assert node.isSelected()


# ---------------------------------------------------------------- moving and resizing

def test_dragging_a_shape_moves_it(screen):
    node = screen.add_node("rounded", QPointF(0, 0))
    finish_editing(screen)
    before = node.sceneCenter()
    drag(screen, before, before + QPointF(150, 100))
    after = node.sceneCenter()
    assert (after.x() - before.x(), after.y() - before.y()) == (150, 100)


def test_moving_a_shape_moves_its_lines(screen):
    from ui.custom_widgets.mindmap_nodes import ConnectionItem
    first = screen.add_node("rounded", QPointF(-200, 0))
    second = screen.add_node("rounded", QPointF(200, 0))
    finish_editing(screen)
    line = ConnectionItem(first, "right", second, "left")
    screen.scene.addItem(line)
    end_before = line.path().pointAtPercent(1)
    drag(screen, second.sceneCenter(), second.sceneCenter() + QPointF(0, 100))
    assert line.path().pointAtPercent(1).y() == end_before.y() + 100


def test_resizing_keeps_the_opposite_corner_in_place(screen):
    node = screen.add_node("rounded", QPointF(0, 0))
    finish_editing(screen)
    top_left = node.sceneBoundingRectOfShape().topLeft()
    corner = node.handle_bottom_right.scenePos()
    drag(screen, corner, corner + QPointF(80, 40))
    rect = node.sceneBoundingRectOfShape()
    assert rect.topLeft() == top_left
    assert abs(rect.width() - (170 + 80)) <= 2 and abs(rect.height() - (70 + 40)) <= 2


def test_a_shape_cannot_be_resized_to_nothing(screen):
    from ui.custom_widgets.mindmap_nodes import MIN_HEIGHT, MIN_WIDTH
    node = screen.add_node("rounded", QPointF(0, 0))
    finish_editing(screen)
    corner = node.handle_bottom_right.scenePos()
    drag(screen, corner, corner - QPointF(500, 500))
    assert node.width >= MIN_WIDTH and node.height >= MIN_HEIGHT


# ---------------------------------------------------------------- linking

def test_dragging_from_a_link_dot_to_another_shape_connects_them(screen):
    first = screen.add_node("rounded", QPointF(-250, 0))
    second = screen.add_node("hexagon", QPointF(250, 0))
    finish_editing(screen)
    first.setLinkHandlesVisible(True)
    start = first.link_handle_right.scenePos()
    # Drop anywhere on the other shape, not just on one of its dots
    drag(screen, start, second.sceneCenter() + QPointF(-30, 5))
    (line,) = connections(screen)
    assert (line.start_node, line.start_handle, line.end_node, line.end_handle) == (first, "right", second, "left")


def test_dropping_a_link_on_empty_canvas_does_nothing(screen):
    first = screen.add_node("rounded", QPointF(-250, 0))
    finish_editing(screen)
    first.setLinkHandlesVisible(True)
    drag(screen, first.link_handle_right.scenePos(), QPointF(300, 300))
    assert connections(screen) == []


# ---------------------------------------------------------------- text

def test_typing_into_a_shape_grows_it_to_fit(screen):
    node = screen.add_node("rounded", QPointF(0, 0))
    height = node.height
    for line in range(8):
        QTest.keyClicks(screen.view.viewport(), f"line {line} of a long thought")
        QTest.keyClick(screen.view.viewport(), Qt.Key_Return, Qt.ShiftModifier)
    assert node.height > height
    text_bottom = node.text_item.pos().y() + node.text_item.boundingRect().height()
    assert text_bottom <= node.height


def test_enter_finishes_typing(screen):
    node = screen.add_node("rounded", QPointF(0, 0))
    QTest.keyClicks(screen.view.viewport(), "Launch plan")
    QTest.keyClick(screen.view.viewport(), Qt.Key_Return)
    assert not node.text_item.isEditing()
    assert node.text_item.toPlainText() == "Launch plan"


def test_double_click_edits_the_text(screen):
    node = screen.add_node("rounded", QPointF(0, 0))
    finish_editing(screen)
    QTest.mouseDClick(screen.view.viewport(), Qt.LeftButton, Qt.NoModifier, view_point(screen, node.sceneCenter()))
    assert node.text_item.isEditing()


# ---------------------------------------------------------------- deleting

def test_delete_key_removes_a_shape_and_its_lines(screen):
    from ui.custom_widgets.mindmap_nodes import ConnectionItem
    first = screen.add_node("rounded", QPointF(-200, 0))
    second = screen.add_node("rounded", QPointF(200, 0))
    finish_editing(screen)
    screen.scene.addItem(ConnectionItem(first, "right", second, "left"))

    screen.scene.clearSelection()
    second.setSelected(True)
    QTest.keyClick(screen.view.viewport(), Qt.Key_Delete)
    assert nodes(screen) == [first]
    assert connections(screen) == [] and first.connections == set()


def test_delete_key_removes_a_selected_line_only(screen):
    from ui.custom_widgets.mindmap_nodes import ConnectionItem
    first = screen.add_node("rounded", QPointF(-200, 0))
    second = screen.add_node("rounded", QPointF(200, 0))
    finish_editing(screen)
    line = ConnectionItem(first, "right", second, "left")
    screen.scene.addItem(line)

    screen.scene.clearSelection()
    line.setSelected(True)
    QTest.keyClick(screen.view.viewport(), Qt.Key_Delete)
    assert len(nodes(screen)) == 2 and connections(screen) == []


def test_delete_while_typing_edits_the_text_instead(screen):
    node = screen.add_node("rounded", QPointF(0, 0))
    QTest.keyClick(screen.view.viewport(), Qt.Key_Delete)  # text is all selected: clears it
    assert nodes(screen) == [node]
    assert node.text_item.toPlainText() == ""


def test_several_shapes_can_be_deleted_together(screen):
    for x in (-300, 0, 300):
        screen.add_node("rounded", QPointF(x, 0))
    finish_editing(screen)
    for node in nodes(screen):
        node.setSelected(True)
    screen.delete_selected()
    assert nodes(screen) == []


# ---------------------------------------------------------------- right-click menu

def menu_actions(menu):
    return {action.text(): action for action in menu.actions()}


def test_right_click_changes_shape_and_colour(screen):
    from ui.custom_widgets.mindmap_nodes import NODE_COLORS
    node = screen.add_node("rounded", QPointF(0, 0))
    finish_editing(screen)
    menu = screen.build_context_menu(node.sceneCenter())
    actions = menu_actions(menu)
    assert {"Edit text", "Shape", "Colour", "Delete"} <= set(actions)

    menu_actions(actions["Shape"].menu())["Diamond"].trigger()
    assert node.shape_key == "diamond"
    name, color = NODE_COLORS[4]
    menu_actions(actions["Colour"].menu())[name].trigger()
    assert node.color == color

    actions["Delete"].trigger()
    assert nodes(screen) == []


def test_right_click_on_empty_canvas_adds_a_shape_there(screen):
    menu = screen.build_context_menu(QPointF(400, 200))
    menu_actions(menu_actions(menu)["Add shape here"].menu())["Sticky note"].trigger()
    (node,) = nodes(screen)
    assert node.shape_key == "note"
    assert abs(node.sceneCenter().x() - 400) <= 13


# ---------------------------------------------------------------- saving

def test_shape_and_colour_are_saved(app):
    from ui.custom_widgets.mindmap_nodes import NodeItem
    node = NodeItem(text="Idea", logger=logger, shape="hexagon", color="#f43f5e")
    copy = NodeItem(logger=logger)
    copy.deserialize(node.serialize())
    assert (copy.shape_key, copy.color) == ("hexagon", "#f43f5e")


def test_mind_maps_saved_before_shapes_still_load(app):
    from ui.custom_widgets.mindmap_nodes import LEGACY_SHAPE, NodeItem
    node = NodeItem(logger=logger)
    node.deserialize({"id": "n1", "text": "Old idea", "width": 120, "height": 75, "position": {"x": 40, "y": 60}})
    assert node.shape_key == LEGACY_SHAPE
    assert (node.width, node.height) == (120, 75)
    assert (node.pos().x(), node.pos().y()) == (40, 60)


# ---------------------------------------------------------------- linking when things go wrong

def start_link_drag(screen, node, to_scene):
    """Press on a node's right dot and move toward to_scene without releasing"""
    viewport = screen.view.viewport()
    node.setLinkHandlesVisible(True)
    start = view_point(screen, node.link_handle_right.scenePos())
    QTest.mousePress(viewport, Qt.LeftButton, Qt.NoModifier, start)
    end = view_point(screen, to_scene)
    for step in range(1, 5):
        point = start + (end - start) * step / 4
        QApplication.sendEvent(viewport, QMouseEvent(QEvent.MouseMove, QPointF(point), Qt.NoButton,
                                                     Qt.LeftButton, Qt.NoModifier))


def dashed_lines(screen):
    from PyQt5.QtWidgets import QGraphicsPathItem
    from ui.custom_widgets.mindmap_nodes import ConnectionItem
    return [item for item in screen.scene.items()
            if isinstance(item, QGraphicsPathItem) and not isinstance(item, ConnectionItem)]


def test_a_link_drag_cut_short_still_finishes(screen):
    first = screen.add_node("rounded", QPointF(-250, 0))
    second = screen.add_node("rounded", QPointF(250, 0))
    finish_editing(screen)
    start_link_drag(screen, first, second.sceneCenter())
    assert len(dashed_lines(screen)) == 1

    screen.scene.mouseGrabberItem().ungrabMouse()  # e.g. a window popped up mid-drag
    assert dashed_lines(screen) == []
    (line,) = connections(screen)
    assert (line.start_node, line.end_node) == (first, second)


def test_a_link_drag_cut_short_over_empty_canvas_leaves_nothing(screen):
    first = screen.add_node("rounded", QPointF(-250, 0))
    finish_editing(screen)
    start_link_drag(screen, first, QPointF(300, 300))
    screen.scene.mouseGrabberItem().ungrabMouse()
    assert dashed_lines(screen) == [] and connections(screen) == []


def test_the_dot_being_dragged_from_stays_visible(screen):
    first = screen.add_node("rounded", QPointF(-250, 0))
    finish_editing(screen)
    start_link_drag(screen, first, QPointF(0, 200))
    first.setLinkHandlesVisible(False)  # what leaving the shape does
    assert first.link_handle_right.isVisible()
    assert screen.scene.mouseGrabberItem() is first.link_handle_right
    QTest.mouseRelease(screen.view.viewport(), Qt.LeftButton, Qt.NoModifier, view_point(screen, QPointF(0, 200)))


def test_the_canvas_behind_the_shapes_is_the_canvas_colour(screen):
    from ui.mindmap_screen import CANVAS_COLOR
    # Any sliver the canvas doesn't repaint shows this, so it must match (no dark trails)
    assert CANVAS_COLOR.name() in screen.view.styleSheet()


def test_the_grid_is_drawn_and_can_be_turned_off(screen, app):
    def dot_pixels():
        image = screen.view.viewport().grab().toImage()
        return sum(1 for x in range(image.width()) for y in range(0, image.height(), 2)
                   if image.pixelColor(x, y).lightness() < 235)
    screen.gridToggleButton.setChecked(True)
    screen.toggle_grid()
    app.processEvents()
    assert dot_pixels() > 100  # dots across the canvas
    screen.gridToggleButton.setChecked(False)
    screen.toggle_grid()
    app.processEvents()
    assert dot_pixels() == 0


# ---------------------------------------------------------------- moving a line's end

def linked(screen):
    """Two linked shapes and a third to move the line to"""
    from ui.custom_widgets.mindmap_nodes import ConnectionItem
    first = screen.add_node("rounded", QPointF(-250, 0))
    second = screen.add_node("rounded", QPointF(250, -100))
    third = screen.add_node("rounded", QPointF(250, 150))
    finish_editing(screen)
    screen.scene.clearSelection()
    line = ConnectionItem(first, "right", second, "left")
    screen.scene.addItem(line)
    return first, second, third, line


def hover(item, on=True):
    """Offscreen tests can't move a real pointer, so set what hovering sets"""
    item.hovered = on
    item.refreshGrips()


def test_hovering_a_line_shows_grips_off_the_shapes(screen):
    from ui.custom_widgets.mindmap_nodes import node_at
    first, second, third, line = linked(screen)
    assert line.grips == {} or not any(g.isVisible() for g in line.grips.values())
    hover(line)
    grips = line.grips
    assert set(grips) == {"start", "end"} and all(g.isVisible() for g in grips.values())
    # Each grip is on the line just outside its shape, above everything, so it can be grabbed
    for grip in grips.values():
        assert node_at(screen.scene, grip.scenePos()) is None
        assert screen.scene.items(grip.scenePos())[0] is grip


def test_grips_hide_after_the_pointer_leaves(screen, app):
    first, second, third, line = linked(screen)
    hover(line)
    line.hovered = False
    line.refreshGrips(delayed=True)
    assert line.grips["end"].isVisible()  # a moment to move onto a grip
    QTest.qWait(line.GRIP_HIDE_DELAY_MS + 150)
    assert not line.grips["end"].isVisible()


def test_hovering_a_link_dot_highlights_its_lines(screen):
    from ui.custom_widgets.mindmap_nodes import ConnectionItem
    first, second, third, line = linked(screen)
    other = ConnectionItem(first, "bottom", third, "left")
    screen.scene.addItem(other)
    first.setLinkHandlesVisible(True)
    first.link_handle_right.hoverEnterEvent(None)
    assert line.highlighted and not other.highlighted
    assert line.grips["start"].isVisible()
    first.link_handle_right.hoverLeaveEvent(None)
    assert not line.highlighted


def test_dragging_a_grip_previews_and_moves_the_line(screen):
    first, second, third, line = linked(screen)
    hover(line)
    grip = line.grips["end"]
    viewport = screen.view.viewport()
    start = view_point(screen, grip.scenePos())
    target = view_point(screen, third.sceneCenter() + QPointF(-40, 0))
    QTest.mousePress(viewport, Qt.LeftButton, Qt.NoModifier, start)
    for step in range(1, 5):
        point = start + (target - start) * step / 4
        QApplication.sendEvent(viewport, QMouseEvent(QEvent.MouseMove, QPointF(point), Qt.NoButton,
                                                     Qt.LeftButton, Qt.NoModifier))

    # While dragging: the line is in preview, snapped to the dot it would attach to,
    # and that shape shows its dots with that one enlarged
    assert line.dragging_end_name == "end"
    assert line.path().pointAtPercent(1) == line._handle_pos(third, "left")
    assert third.link_handle_left.isVisible() and third.link_handle_left.scale() > 1
    assert third.link_handle_top.scale() == 1

    QTest.mouseRelease(viewport, Qt.LeftButton, Qt.NoModifier, target)
    assert (line.end_node, line.end_handle) == (third, "left")
    assert line in third.connections and line not in second.connections
    assert line.dragging_end_name is None
    assert third.link_handle_left.scale() == 1  # the snap highlight is cleared


def test_dropping_a_grip_on_empty_canvas_puts_the_line_back(screen):
    first, second, third, line = linked(screen)
    before = line.path().pointAtPercent(1)
    hover(line)
    drag(screen, line.grips["end"].scenePos(), QPointF(0, 350))
    assert (line.end_node, line.end_handle) == (second, "left")
    assert line.path().pointAtPercent(1) == before


def test_a_grip_drag_cut_short_puts_the_line_back(screen):
    first, second, third, line = linked(screen)
    hover(line)
    viewport = screen.view.viewport()
    QTest.mousePress(viewport, Qt.LeftButton, Qt.NoModifier, view_point(screen, line.grips["start"].scenePos()))
    QApplication.sendEvent(viewport, QMouseEvent(QEvent.MouseMove, QPointF(view_point(screen, third.sceneCenter())),
                                                 Qt.NoButton, Qt.LeftButton, Qt.NoModifier))
    screen.scene.mouseGrabberItem().ungrabMouse()
    assert (line.start_node, line.start_handle) == (first, "right")
    assert line.dragging_end_name is None


def test_deleting_a_line_removes_its_grips(screen):
    from ui.custom_widgets.mindmap_nodes import EndGrip
    first, second, third, line = linked(screen)
    hover(line)
    screen.scene.clearSelection()
    line.setSelected(True)
    screen.delete_selected()
    assert not [item for item in screen.scene.items() if isinstance(item, EndGrip)]


def test_right_clicking_a_grip_offers_the_line_menu(screen):
    first, second, third, line = linked(screen)
    hover(line)
    menu = screen.build_context_menu(line.grips["end"].scenePos())
    assert "Delete line" in menu_actions(menu)


# ---------------------------------------------------------------- dragging a dot that has lines

def drag_with(screen, start_scene, end_scene, modifiers=Qt.NoModifier, steps=6):
    viewport = screen.view.viewport()
    start, end = view_point(screen, start_scene), view_point(screen, end_scene)
    QTest.mousePress(viewport, Qt.LeftButton, modifiers, start)
    for step in range(1, steps + 1):
        point = start + (end - start) * step / steps
        QApplication.sendEvent(viewport, QMouseEvent(QEvent.MouseMove, QPointF(point), Qt.NoButton,
                                                     Qt.LeftButton, modifiers))
    QTest.mouseRelease(viewport, Qt.LeftButton, modifiers, end)


def test_dragging_a_dot_with_a_line_moves_the_line(screen):
    first, second, third, line = linked(screen)
    second.setLinkHandlesVisible(True)
    dot = second.link_handle_left
    dot.hoverEnterEvent(None)
    assert line.highlighted and dot.toolTip() == dot.TIP_MOVE

    drag_with(screen, dot.scenePos(), third.sceneCenter() + QPointF(0, -20))
    assert (line.end_node, line.end_handle) == (third, "top")
    assert len(connections(screen)) == 1  # moved, not a new line
    assert not line.highlighted and line.dragging_end_name is None


def test_dragging_a_dot_shows_the_move_preview(screen):
    first, second, third, line = linked(screen)
    second.setLinkHandlesVisible(True)
    viewport = screen.view.viewport()
    start = view_point(screen, second.link_handle_left.scenePos())
    QTest.mousePress(viewport, Qt.LeftButton, Qt.NoModifier, start)
    QApplication.sendEvent(viewport, QMouseEvent(QEvent.MouseMove, QPointF(view_point(screen, third.sceneCenter())),
                                                 Qt.NoButton, Qt.LeftButton, Qt.NoModifier))
    assert line.dragging_end_name == "end"
    assert dashed_lines(screen) == []  # no "new line" being drawn
    QTest.mouseRelease(viewport, Qt.LeftButton, Qt.NoModifier, view_point(screen, third.sceneCenter()))


def test_dropping_a_moved_dot_on_empty_canvas_leaves_the_line(screen):
    first, second, third, line = linked(screen)
    second.setLinkHandlesVisible(True)
    drag_with(screen, second.link_handle_left.scenePos(), QPointF(0, 350))
    assert (line.end_node, line.end_handle) == (second, "left")


def test_ctrl_dragging_a_dot_with_a_line_starts_a_new_line(screen):
    first, second, third, line = linked(screen)
    second.setLinkHandlesVisible(True)
    drag_with(screen, second.link_handle_left.scenePos(), third.sceneCenter(), Qt.ControlModifier)
    assert (line.end_node, line.end_handle) == (second, "left")  # untouched
    new_lines = [c for c in connections(screen) if c is not line]
    assert len(new_lines) == 1 and (new_lines[0].start_node, new_lines[0].end_node) == (second, third)


def test_a_dot_with_several_lines_moves_them_all(screen):
    from ui.custom_widgets.mindmap_nodes import ConnectionItem
    first, second, third, line = linked(screen)
    hub_line = ConnectionItem(first, "right", third, "left")
    screen.scene.addItem(hub_line)
    first.setLinkHandlesVisible(True)
    drag_with(screen, first.link_handle_right.scenePos(), first.sceneCenter() + QPointF(0, 30))
    assert (line.start_handle, hub_line.start_handle) == ("bottom", "bottom")


# ---------------------------------------------------------------- bending lines

def straight_pair(screen):
    """Two shapes side by side, joined by a line"""
    from ui.custom_widgets.mindmap_nodes import ConnectionItem
    first = screen.add_node("rounded", QPointF(-300, 0))
    second = screen.add_node("rounded", QPointF(300, 0))
    finish_editing(screen)
    screen.scene.clearSelection()
    line = ConnectionItem(first, "right", second, "left")
    screen.scene.addItem(line)
    return first, second, line


def passes_through(line, point, tolerance=3):
    from ui.custom_widgets.mindmap_nodes import _distance
    path = line.path()
    return min(_distance(path.pointAtPercent(i / 400), point) for i in range(401)) <= tolerance


def test_dragging_the_middle_of_a_line_bends_it_there(screen):
    first, second, line = straight_pair(screen)
    middle = line.path().pointAtPercent(0.5)
    drag(screen, middle, middle + QPointF(0, 150))
    assert len(line.waypoints) == 1
    bend = line.waypoints[0]
    assert abs(bend.x() - middle.x()) <= 2 and abs(bend.y() - (middle.y() + 150)) <= 2
    assert passes_through(line, bend)
    assert line.path().pointAtPercent(0) == line._handle_pos(first, "right")  # ends stay attached
    assert line.path().pointAtPercent(1) == line._handle_pos(second, "left")


def test_a_click_on_a_line_selects_it_without_bending(screen):
    first, second, line = straight_pair(screen)
    QTest.mouseClick(screen.view.viewport(), Qt.LeftButton, Qt.NoModifier,
                     view_point(screen, line.path().pointAtPercent(0.5)))
    assert line.isSelected() and line.waypoints == []


def test_bends_stay_in_order_along_the_line(screen):
    first, second, line = straight_pair(screen)
    right_part = line.path().pointAtPercent(0.7)
    drag(screen, right_part, right_part + QPointF(0, 100))
    left_part = line.path().pointAtPercent(0.25)  # on the line as it is now
    drag(screen, left_part, left_part + QPointF(0, -100))
    assert len(line.waypoints) == 2
    assert line.waypoints[0].x() < line.waypoints[1].x()  # the left bend comes first along the line
    for point in line.waypoints:
        assert passes_through(line, point)


def test_a_bend_can_be_dragged_and_removed(screen):
    first, second, line = straight_pair(screen)
    middle = line.path().pointAtPercent(0.5)
    drag(screen, middle, middle + QPointF(0, 120))
    line.hovered = True
    line.refreshGrips()
    (handle,) = line.bend_handles
    assert handle.isVisible() and handle.pos() == line.waypoints[0]

    drag(screen, handle.scenePos(), handle.scenePos() + QPointF(50, 60))
    assert abs(line.waypoints[0].x() - (middle.x() + 50)) <= 2
    assert passes_through(line, line.waypoints[0])

    QTest.mouseDClick(screen.view.viewport(), Qt.LeftButton, Qt.NoModifier, view_point(screen, handle.scenePos()))
    assert line.waypoints == [] and line.bend_handles == []


def test_straighten_from_the_menu(screen):
    first, second, line = straight_pair(screen)
    middle = line.path().pointAtPercent(0.5)
    drag(screen, middle, middle + QPointF(0, 120))
    actions = menu_actions(screen.build_context_menu(line.waypoints[0] + QPointF(0, 0)))
    assert "Remove this bend" in actions or "Straighten line" in actions
    menu_actions(screen.build_context_menu(line.path().pointAtPercent(0.25)))["Straighten line"].trigger()
    assert line.waypoints == []


def test_moving_one_shape_keeps_the_bends_where_they_are(screen):
    first, second, line = straight_pair(screen)
    middle = line.path().pointAtPercent(0.5)
    drag(screen, middle, middle + QPointF(0, 150))
    bend = QPointF(line.waypoints[0])
    drag(screen, second.sceneCenter(), second.sceneCenter() + QPointF(0, -100))
    assert line.waypoints[0] == bend
    assert passes_through(line, bend)


def test_moving_both_shapes_together_carries_the_bends(screen):
    first, second, line = straight_pair(screen)
    middle = line.path().pointAtPercent(0.5)
    drag(screen, middle, middle + QPointF(0, 150))
    bend = QPointF(line.waypoints[0])
    screen.scene.clearSelection()
    first.setSelected(True)
    second.setSelected(True)
    drag(screen, first.sceneCenter(), first.sceneCenter() + QPointF(100, 50))
    assert line.waypoints[0] == bend + QPointF(100, 50)


def test_bends_are_saved_and_restored(screen, monkeypatch):
    from ui.custom_widgets import dialogs
    monkeypatch.setattr(dialogs, "information", lambda *a, **k: None)
    monkeypatch.setattr(dialogs, "ask_text", lambda *a, **k: ("Bends", True))
    first, second, line = straight_pair(screen)
    middle = line.path().pointAtPercent(0.5)
    drag(screen, middle, middle + QPointF(0, 150))
    assert screen.has_unsaved_changes()
    saved_points = line.serializedPoints()
    screen.save_mind_map()
    mindmap_id = screen.current_mindmap_id

    screen.clear_map()
    screen.load_mindmap_by_id(mindmap_id)
    (reloaded,) = connections(screen)
    assert reloaded.serializedPoints() == saved_points
    assert not screen.has_unsaved_changes()


def test_lines_saved_without_bends_still_load(screen):
    from utils.mindmap_io import create_mindmap
    mindmap = create_mindmap(
        "Old", logger=logger,
        nodes=[{"id": "a", "text": "A", "width": 120, "height": 75, "position": {"x": 0, "y": 0}},
               {"id": "b", "text": "B", "width": 120, "height": 75, "position": {"x": 400, "y": 0}}],
        connections=[{"from": "a", "from_handle": "right", "to": "b", "to_handle": "left"}])
    screen.load_mindmap_by_id(mindmap.id)
    (line,) = connections(screen)
    assert line.waypoints == []


# ---------------------------------------------------------------- drop highlight for new lines

def test_drawing_a_new_line_lights_up_the_dot_it_will_attach_to(screen):
    first = screen.add_node("rounded", QPointF(-250, 0))
    second = screen.add_node("rounded", QPointF(250, 100))
    finish_editing(screen)
    first.setLinkHandlesVisible(True)
    viewport = screen.view.viewport()
    start = view_point(screen, first.link_handle_right.scenePos())
    over = view_point(screen, second.sceneCenter() + QPointF(0, -25))  # near its top dot
    QTest.mousePress(viewport, Qt.LeftButton, Qt.NoModifier, start)
    QApplication.sendEvent(viewport, QMouseEvent(QEvent.MouseMove, QPointF(over), Qt.NoButton,
                                                 Qt.LeftButton, Qt.NoModifier))
    assert second.link_handle_top.isVisible() and second.link_handle_top.scale() > 1
    assert second.link_handle_left.scale() == 1
    (preview,) = dashed_lines(screen)
    assert preview.path().pointAtPercent(1) == second.mapToScene(second.anchor_point("top"))
    QTest.mouseRelease(viewport, Qt.LeftButton, Qt.NoModifier, over)
    (line,) = connections(screen)
    assert line.end_handle == "top" and second.link_handle_top.scale() == 1


def test_resizing_a_selected_shape_leaves_the_bends(screen):
    first, second, line = straight_pair(screen)
    middle = line.path().pointAtPercent(0.5)
    drag(screen, middle, middle + QPointF(0, 150))
    bend = QPointF(line.waypoints[0])
    screen.scene.clearSelection()
    first.setSelected(True)
    second.setSelected(True)
    corner = second.handle_bottom_right.scenePos()
    drag(screen, corner, corner + QPointF(60, 60))
    assert line.waypoints[0] == bend


# ---------------------------------------------------------------- undo and redo

def ctrl(screen, key, shift=False):
    modifiers = Qt.ControlModifier | (Qt.ShiftModifier if shift else Qt.NoModifier)
    QTest.keyClick(screen.view.viewport(), key, modifiers)


def node_ids(screen):
    return sorted(node.id for node in nodes(screen))


def test_undo_and_redo_adding_a_shape(screen):
    assert not screen.undoButton.isEnabled() and not screen.redoButton.isEnabled()
    node = screen.add_node("rounded", QPointF(0, 0))
    QTest.keyClick(screen.view.viewport(), Qt.Key_Return)  # finish typing
    node_id = node.id
    assert screen.undoButton.isEnabled()

    ctrl(screen, Qt.Key_Z)
    assert nodes(screen) == []
    assert screen.redoButton.isEnabled()
    ctrl(screen, Qt.Key_Y)
    assert node_ids(screen) == [node_id]


def test_undo_a_move(screen):
    node = screen.add_node("rounded", QPointF(0, 0))
    finish_editing(screen)
    screen.checkpoint()
    before = node.sceneCenter()
    drag(screen, before, before + QPointF(200, 100))
    ctrl(screen, Qt.Key_Z)
    (restored,) = nodes(screen)
    assert restored.sceneCenter() == before
    ctrl(screen, Qt.Key_Z, shift=True)  # Ctrl+Shift+Z redoes too
    assert nodes(screen)[0].sceneCenter() == before + QPointF(200, 100)


def test_undo_a_delete_brings_back_shapes_and_lines(screen):
    first, second, line = straight_pair(screen)
    screen.checkpoint()
    screen.scene.clearSelection()
    second.setSelected(True)
    QTest.keyClick(screen.view.viewport(), Qt.Key_Delete)
    assert len(nodes(screen)) == 1 and connections(screen) == []

    ctrl(screen, Qt.Key_Z)
    assert node_ids(screen) == sorted([first.id, second.id])
    (restored,) = connections(screen)
    assert (restored.start_node.id, restored.end_node.id) == (first.id, second.id)


def test_undo_typing(screen):
    node = screen.add_node("rounded", QPointF(0, 0))
    QTest.keyClicks(screen.view.viewport(), "First")
    QTest.keyClick(screen.view.viewport(), Qt.Key_Return)
    QTest.mouseDClick(screen.view.viewport(), Qt.LeftButton, Qt.NoModifier, view_point(screen, node.sceneCenter()))
    QTest.keyClicks(screen.view.viewport(), "Second")
    QTest.keyClick(screen.view.viewport(), Qt.Key_Return)
    assert nodes(screen)[0].text_item.toPlainText() == "Second"
    ctrl(screen, Qt.Key_Z)
    assert nodes(screen)[0].text_item.toPlainText() == "First"


def test_ctrl_z_while_typing_only_undoes_the_typing(screen):
    node = screen.add_node("rounded", QPointF(0, 0))
    QTest.keyClicks(screen.view.viewport(), "Draft")
    ctrl(screen, Qt.Key_Z)
    assert node.scene() is not None  # the shape is still there
    assert node.text_item.isEditing()


def test_undo_a_menu_change(screen):
    node = screen.add_node("rounded", QPointF(0, 0))
    finish_editing(screen)
    screen.checkpoint()
    actions = menu_actions(screen.build_context_menu(node.sceneCenter()))
    menu_actions(actions["Shape"].menu())["Hexagon"].trigger()
    screen.checkpoint()  # what closing the menu does
    ctrl(screen, Qt.Key_Z)
    assert nodes(screen)[0].shape_key == "rounded"


def test_undo_a_bend(screen):
    first, second, line = straight_pair(screen)
    screen.checkpoint()
    middle = line.path().pointAtPercent(0.5)
    drag(screen, middle, middle + QPointF(0, 150))
    assert connections(screen)[0].waypoints
    ctrl(screen, Qt.Key_Z)
    assert connections(screen)[0].waypoints == []
    ctrl(screen, Qt.Key_Y)
    assert len(connections(screen)[0].waypoints) == 1


def test_a_new_change_after_undo_clears_redo(screen):
    screen.add_node("rounded", QPointF(-200, 0))
    finish_editing(screen)
    screen.checkpoint()
    ctrl(screen, Qt.Key_Z)
    assert screen.redoButton.isEnabled()
    screen.add_node("pill", QPointF(200, 0))
    assert not screen.redoButton.isEnabled()


def test_undo_buttons(screen):
    screen.add_node("rounded", QPointF(0, 0))
    finish_editing(screen)
    screen.checkpoint()
    screen.undoButton.click()
    assert nodes(screen) == []
    screen.redoButton.click()
    assert len(nodes(screen)) == 1


def test_starting_or_opening_a_map_clears_the_history(screen):
    screen.add_node("rounded", QPointF(0, 0))
    finish_editing(screen)
    screen.checkpoint()
    screen.clear_map()
    assert not screen.undoButton.isEnabled() and not screen.redoButton.isEnabled()


def test_undoing_back_to_the_saved_state_is_not_an_unsaved_change(screen, monkeypatch):
    from ui.custom_widgets import dialogs
    monkeypatch.setattr(dialogs, "information", lambda *a, **k: None)
    monkeypatch.setattr(dialogs, "ask_text", lambda *a, **k: ("Undo", True))
    node = screen.add_node("rounded", QPointF(0, 0))
    finish_editing(screen)
    screen.save_mind_map()
    drag(screen, node.sceneCenter(), node.sceneCenter() + QPointF(100, 0))
    assert screen.has_unsaved_changes()
    ctrl(screen, Qt.Key_Z)
    assert not screen.has_unsaved_changes()


def test_bring_to_front_survives_undo_and_saving(app):
    from ui.custom_widgets.mindmap_nodes import NodeItem
    node = NodeItem(text="Top", logger=logger)
    node.setZValue(3)
    copy = NodeItem(logger=logger)
    copy.deserialize(node.serialize())
    assert copy.zValue() == 3


# ---------------------------------------------------------------- deleting a bend point

def bent_line(screen, bends=2):
    first, second, line = straight_pair(screen)
    for fraction, offset in ((0.3, 120), (0.75, -120))[:bends]:
        point = line.path().pointAtPercent(fraction)
        drag(screen, point, point + QPointF(0, offset))
    line.hovered = True
    line.refreshGrips()
    return first, second, line


def click(screen, scene_pos):
    QTest.mouseClick(screen.view.viewport(), Qt.LeftButton, Qt.NoModifier, view_point(screen, scene_pos))


def test_click_a_bend_then_delete_removes_just_that_bend(screen):
    first, second, line = bent_line(screen)
    keep = QPointF(line.waypoints[1])
    handle = line.bend_handles[0]
    click(screen, handle.scenePos())
    assert screen.scene.active_bend is handle and handle.scale() > 1
    assert line.isSelected()

    QTest.keyClick(screen.view.viewport(), Qt.Key_Delete)
    assert line.waypoints == [keep]
    assert passes_through(line, keep)
    assert connections(screen) == [line] and len(nodes(screen)) == 2  # the line and shapes stay
    assert screen.scene.active_bend is None


def test_backspace_removes_a_clicked_bend_too(screen):
    first, second, line = bent_line(screen, bends=1)
    click(screen, line.bend_handles[0].scenePos())
    QTest.keyClick(screen.view.viewport(), Qt.Key_Backspace)
    assert line.waypoints == [] and connections(screen) == [line]


def test_clicking_elsewhere_forgets_the_bend(screen):
    first, second, line = bent_line(screen, bends=1)
    click(screen, line.bend_handles[0].scenePos())
    click(screen, QPointF(0, 400))  # empty canvas
    assert screen.scene.active_bend is None
    line.setSelected(True)
    QTest.keyClick(screen.view.viewport(), Qt.Key_Delete)
    assert connections(screen) == []  # Delete is back to deleting the selected line


def test_deleting_a_bend_can_be_undone(screen):
    first, second, line = bent_line(screen, bends=1)
    bend = QPointF(line.waypoints[0])
    click(screen, line.bend_handles[0].scenePos())
    QTest.keyClick(screen.view.viewport(), Qt.Key_Delete)
    ctrl(screen, Qt.Key_Z)
    assert connections(screen)[0].waypoints == [bend]


def test_delete_after_undo_does_not_touch_a_vanished_bend(screen):
    first, second, line = bent_line(screen, bends=1)
    click(screen, line.bend_handles[0].scenePos())
    ctrl(screen, Qt.Key_Z)  # rebuilds the canvas: the clicked bend's handle is gone
    QTest.keyClick(screen.view.viewport(), Qt.Key_Delete)  # must not crash
    assert screen.scene.active_bend is None


# ---------------------------------------------------------------- labels on lines

def type_and_enter(screen, text):
    QTest.keyClicks(screen.view.viewport(), text)
    QTest.keyClick(screen.view.viewport(), Qt.Key_Return)


def test_double_click_a_line_to_label_it(screen):
    first, second, line = straight_pair(screen)
    middle = line.path().pointAtPercent(0.5)
    QTest.mouseDClick(screen.view.viewport(), Qt.LeftButton, Qt.NoModifier, view_point(screen, middle))
    assert line.label_item.isEditing()
    type_and_enter(screen, "depends on")
    assert line.label == "depends on" and line.label_item.isVisible()
    centre = line.label_item.mapToScene(line.label_item.boundingRect().center())
    assert abs(centre.x() - middle.x()) < 3 and abs(centre.y() - middle.y()) < 3


def test_a_label_follows_its_line(screen):
    first, second, line = straight_pair(screen)
    line.setLabel("feeds")
    drag(screen, second.sceneCenter(), second.sceneCenter() + QPointF(0, 200))
    middle = line.path().pointAtPercent(line.path().percentAtLength(line.path().length() / 2))
    centre = line.label_item.mapToScene(line.label_item.boundingRect().center())
    assert abs(centre.x() - middle.x()) < 3 and abs(centre.y() - middle.y()) < 3


def test_clearing_a_label_removes_it(screen):
    first, second, line = straight_pair(screen)
    line.setLabel("old")
    line.editLabel()
    QTest.keyClick(screen.view.viewport(), Qt.Key_Delete)  # text is all selected while editing
    QTest.keyClick(screen.view.viewport(), Qt.Key_Return)
    assert line.label == "" and not line.label_item.isVisible()
    assert connections(screen) == [line]  # Delete edited the label, not the line


def test_label_menu(screen):
    first, second, line = straight_pair(screen)
    actions = menu_actions(screen.build_context_menu(line.path().pointAtPercent(0.5)))
    assert "Add label" in actions and "Remove label" not in actions
    line.setLabel("yes")
    actions = menu_actions(screen.build_context_menu(line.label_item.mapToScene(line.label_item.boundingRect().center())))
    assert "Edit label" in actions  # right-clicking the label gives the line's menu
    actions["Remove label"].trigger()
    assert line.label == ""


def test_labels_are_saved_undoable_and_searchable(screen, monkeypatch):
    from PyQt5.QtWidgets import QMessageBox
    from ui.custom_widgets import dialogs
    from utils.search import search_everything
    monkeypatch.setattr(dialogs, "ask_text", lambda *a, **k: ("Labels", True))
    first, second, line = straight_pair(screen)
    screen.checkpoint()
    line.setLabel("approves")
    screen.checkpoint()
    screen.save_mind_map()
    mindmap_id = screen.current_mindmap_id
    assert [r.title for r in search_everything("approves", logger)] == ["Labels"]

    screen.clear_map()
    screen.load_mindmap_by_id(mindmap_id)
    assert connections(screen)[0].label == "approves"
    screen.history.reset(screen.snapshot())
    connections(screen)[0].setLabel("rejects")
    screen.checkpoint()
    screen.undo()
    assert connections(screen)[0].label == "approves"
    assert QMessageBox  # (keeps the import tidy)


# ---------------------------------------------------------------- frames

def frames(screen):
    from ui.custom_widgets.mindmap_nodes import FrameItem
    return [item for item in screen.scene.items() if isinstance(item, FrameItem)]


def test_frame_selected_shapes(screen):
    first, second, line = straight_pair(screen)
    first.setSelected(True)
    second.setSelected(True)
    frame = screen.frame_selection()
    QTest.keyClick(screen.view.viewport(), Qt.Key_Return)  # keep the default title
    area = frame.sceneBoundingRectOfShape()
    assert all(area.contains(node.sceneBoundingRectOfShape()) for node in (first, second))
    assert set(frame.contents()) == {first, second}
    assert frame.zValue() < line.zValue() < first.zValue()  # behind lines and shapes


def test_dragging_a_frame_moves_its_shapes_and_bends(screen):
    first, second, line = straight_pair(screen)
    middle = line.path().pointAtPercent(0.5)
    drag(screen, middle, middle + QPointF(0, 60))
    bend = QPointF(line.waypoints[0])
    first.setSelected(True)
    second.setSelected(True)
    frame = screen.frame_selection()
    QTest.keyClick(screen.view.viewport(), Qt.Key_Return)
    screen.scene.clearSelection()
    starts = {node: node.sceneCenter() for node in (first, second)}

    title = frame.mapToScene(QPointF(frame.width / 2, 12))
    drag(screen, title, title + QPointF(100, 50))
    for node, start in starts.items():
        assert node.sceneCenter() == start + QPointF(100, 50)
    assert line.waypoints[0] == bend + QPointF(100, 50)


def test_clicks_inside_a_frame_reach_the_canvas(screen):
    from ui.custom_widgets.mindmap_nodes import FrameItem
    frame = screen.add_frame(QPointF(0, 0))
    QTest.keyClick(screen.view.viewport(), Qt.Key_Return)
    inside = frame.mapToScene(QPointF(frame.width / 2, frame.height / 2))
    assert not any(isinstance(item, FrameItem) for item in screen.scene.items(inside)
                   if item.contains(item.mapFromScene(inside)))


def test_renaming_and_deleting_frames(screen):
    first, second, line = straight_pair(screen)
    first.setSelected(True)
    frame = screen.frame_selection()
    type_and_enter(screen, "Phase 1")
    assert frame.title == "Phase 1"

    screen.scene.clearSelection()
    frame.setSelected(True)
    QTest.keyClick(screen.view.viewport(), Qt.Key_Delete)  # the frame goes, its shape stays
    assert frames(screen) == [] and first.scene() is screen.scene

    first.setSelected(True)
    frame = screen.frame_selection()
    QTest.keyClick(screen.view.viewport(), Qt.Key_Return)
    title = frame.mapToScene(QPointF(frame.width / 2, 12))
    actions = menu_actions(screen.build_context_menu(title))
    actions["Delete frame and its 1 shape"].trigger()
    assert frames(screen) == [] and first.scene() is None


def test_frames_are_saved_and_exported(screen, monkeypatch, tmp_path):
    from ui.custom_widgets import dialogs
    monkeypatch.setattr(dialogs, "ask_text", lambda *a, **k: ("Framed", True))
    frame = screen.add_frame(QPointF(0, 0))
    type_and_enter(screen, "Ideas")
    frame.setColor("#22c55e")
    screen.save_mind_map()
    mindmap_id = screen.current_mindmap_id
    screen.clear_map()
    screen.load_mindmap_by_id(mindmap_id)
    (loaded,) = frames(screen)
    assert (loaded.title, loaded.color, loaded.width, loaded.height) == ("Ideas", "#22c55e", frame.width, frame.height)
    assert screen.export_mind_map("png", str(tmp_path / "framed.png"))


# ---------------------------------------------------------------- groups

def three_shapes(screen):
    shapes = [screen.add_node("rounded", QPointF(x, 0)) for x in (-300, 0, 300)]
    finish_editing(screen)
    screen.scene.clearSelection()
    return shapes


def select(screen, *nodes):
    screen.scene.clearSelection()
    for node in nodes:
        node.setSelected(True)


def test_ctrl_g_groups_and_clicking_one_selects_all(screen):
    first, second, third = three_shapes(screen)
    select(screen, first, second)
    QTest.keyClick(screen.view.viewport(), Qt.Key_G, Qt.ControlModifier)
    assert first.group_id and first.group_id == second.group_id and third.group_id is None

    screen.scene.clearSelection()
    QTest.mouseClick(screen.view.viewport(), Qt.LeftButton, Qt.NoModifier, view_point(screen, first.sceneCenter()))
    assert set(screen._selectedNodes()) == {first, second}
    assert not first.handle_top_left.isVisible()  # no resize corners on a group
    outline = screen.scene.group_outline
    assert outline.boundingRect().contains(first.sceneBoundingRectOfShape())
    assert outline.boundingRect().contains(second.sceneBoundingRectOfShape())


def test_dragging_one_member_moves_the_group(screen):
    from ui.custom_widgets.mindmap_nodes import ConnectionItem
    first, second, third = three_shapes(screen)
    line = ConnectionItem(first, "right", second, "left")
    screen.scene.addItem(line)
    middle = line.path().pointAtPercent(0.5)
    drag(screen, middle, middle + QPointF(0, 80))
    bend = QPointF(line.waypoints[0])
    select(screen, first, second)
    screen.group_selection()
    screen.scene.clearSelection()

    before = {node: node.sceneCenter() for node in (first, second, third)}
    drag(screen, first.sceneCenter(), first.sceneCenter() + QPointF(50, 100))
    assert first.sceneCenter() == before[first] + QPointF(50, 100)
    assert second.sceneCenter() == before[second] + QPointF(50, 100)
    assert third.sceneCenter() == before[third]
    assert line.waypoints[0] == bend + QPointF(50, 100)


def test_ungroup(screen):
    first, second, third = three_shapes(screen)
    select(screen, first, second)
    screen.group_selection()
    select(screen, first)  # selects the group
    QTest.keyClick(screen.view.viewport(), Qt.Key_G, Qt.ControlModifier | Qt.ShiftModifier)
    assert first.group_id is None and second.group_id is None
    select(screen, first)
    assert screen._selectedNodes() == [first]


def test_grouping_groups_merges_them(screen):
    first, second, third = three_shapes(screen)
    select(screen, first, second)
    screen.group_selection()
    select(screen, first, third)  # first's group plus third
    screen.group_selection()
    assert first.group_id == second.group_id == third.group_id


def test_group_menu(screen):
    first, second, third = three_shapes(screen)
    select(screen, first, second)
    actions = {a.text().split("\t")[0]: a for a in screen.build_context_menu(first.sceneCenter()).actions()}
    assert "Group these 2 shapes" in actions and "Ungroup" not in actions
    actions["Group these 2 shapes"].trigger()
    actions = {a.text().split("\t")[0]: a for a in screen.build_context_menu(first.sceneCenter()).actions()}
    assert "Ungroup" in actions and not any(text.startswith("Group these") for text in actions)


def test_groups_are_saved_and_undoable(screen, monkeypatch):
    from ui.custom_widgets import dialogs
    monkeypatch.setattr(dialogs, "ask_text", lambda *a, **k: ("Grouped", True))
    first, second, third = three_shapes(screen)
    screen.checkpoint()
    select(screen, first, second)
    screen.group_selection()
    screen.save_mind_map()
    mindmap_id = screen.current_mindmap_id
    screen.clear_map()
    screen.load_mindmap_by_id(mindmap_id)
    groups = {node.text_item.toPlainText() + str(i): node.group_id for i, node in enumerate(nodes(screen))}
    assert sorted(bool(g) for g in groups.values()) == [False, True, True]

    loaded = [node for node in nodes(screen) if node.group_id]
    select(screen, loaded[0])
    screen.ungroup_selection()
    screen.undo()
    assert sum(1 for node in nodes(screen) if node.group_id) == 2
