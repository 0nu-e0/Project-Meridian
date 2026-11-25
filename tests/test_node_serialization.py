"""
Mindmap nodes save and restore their text, size, and position.

Uses real PyQt (offscreen). An earlier version replaced PyQt with hand-made fakes,
which went stale and also broke every test that ran after it.
"""
import logging
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication, QGraphicsScene

logger = logging.getLogger("test_node_serialization")


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_nodeitem_serialization_round_trip(app):
    from ui.custom_widgets.mindmap_nodes import NodeItem
    scene = QGraphicsScene()
    node = NodeItem(width=160, height=90, text="hello", logger=logger)
    scene.addItem(node)
    node.setPos(10, 15)  # snapped to the grid; whatever it lands on must come back

    data = node.serialize()

    other = NodeItem(logger=logger)
    scene.addItem(other)
    other.deserialize(data)

    assert other.id == node.id
    assert other.text_item.toPlainText() == "hello"
    assert (other.width, other.height) == (160, 90)
    assert (other.pos().x(), other.pos().y()) == (node.pos().x(), node.pos().y())
