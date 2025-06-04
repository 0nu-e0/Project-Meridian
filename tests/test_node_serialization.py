import os
import sys
import types

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Stub modules that bring in heavy PyQt dependencies
dummy_collapsible = types.ModuleType("ui.custom_widgets.collapsable_section")
dummy_collapsible.CollapsibleSection = type("CollapsibleSection", (), {})
sys.modules.setdefault("ui.custom_widgets.collapsable_section", dummy_collapsible)

dummy_styles = types.ModuleType("resources.styles")
dummy_styles.AppColors = type("AppColors", (), {})
dummy_styles.AppStyles = type("AppStyles", (), {})
dummy_styles.AnimatedButton = type("AnimatedButton", (), {})
sys.modules.setdefault("resources.styles", dummy_styles)
sys.modules.setdefault("resources.styles.styles", dummy_styles)

# ---- PyQt5 stubs ----
qt_pkg = types.ModuleType("PyQt5")
sys.modules.setdefault("PyQt5", qt_pkg)

qtcore = types.ModuleType("PyQt5.QtCore")
class DummyPointF:
    def __init__(self, x=0, y=0):
        self._x = x
        self._y = y
    def x(self):
        return self._x
    def y(self):
        return self._y
qtcore.QPointF = DummyPointF
qtcore.Qt = types.SimpleNamespace(NoButton=0)
qtcore.QObject = object
qtcore.QPropertyAnimation = type('QPropertyAnimation', (), {})
qtcore.QEasingCurve = type('QEasingCurve', (), {})
qtcore.QSize = type('QSize', (), {})
qtcore.QEvent = type('QEvent', (), {})
qtcore.QDateTime = type('QDateTime', (), {})
qtcore.QUrl = type('QUrl', (), {})
qtcore.QTimer = type('QTimer', (), {})
qtcore.pyqtSignal = lambda *a, **k: None
qtcore.pyqtSlot = lambda *a, **k: None
sys.modules["PyQt5.QtCore"] = qtcore

qtwidgets = types.ModuleType("PyQt5.QtWidgets")
class DummyEllipseItem:
    ItemIsSelectable = 1
    ItemIsMovable = 2
    ItemSendsGeometryChanges = 4
    def __init__(self, *a, **kw):
        self._pos = DummyPointF(0, 0)
    def setPen(self, *a, **kw):
        pass
    def setBrush(self, *a, **kw):
        pass
    def setFlags(self, *a, **kw):
        pass
    def setAcceptHoverEvents(self, *a, **kw):
        pass
    def setRect(self, *a, **kw):
        self.rect = a
    def setPos(self, x, y=None):
        if y is None and hasattr(x, "x"):
            self._pos = x
        else:
            self._pos = DummyPointF(x, y)
    def pos(self):
        return self._pos
qtwidgets.QGraphicsEllipseItem = DummyEllipseItem

class DummyTextItem:
    def __init__(self, text="", parent=None):
        self._text = text
    def toPlainText(self):
        return self._text
    def setPlainText(self, text):
        self._text = text
    def setDefaultTextColor(self, color):
        pass
    def setTextWidth(self, width):
        pass
    def document(self):
        return self
    def adjustSize(self):
        pass
    def boundingRect(self):
        class R:
            def width(self):
                return 0
            def height(self):
                return 0
        return R()
qtwidgets.QGraphicsTextItem = DummyTextItem

for name in [
    'QApplication','QDesktopWidget','QGraphicsLineItem','QGraphicsItem','QWidget','QVBoxLayout','QHBoxLayout',
    'QLabel','QFrame','QSpacerItem','QSizePolicy','QGridLayout','QPushButton',
    'QGraphicsDropShadowEffect','QStyle','QComboBox','QTextEdit','QDateTimeEdit',
    'QLineEdit','QCalendarWidget','QToolButton','QSpinBox','QListWidget',
    'QTabWidget','QGraphicsRectItem','QMessageBox','QInputDialog','QListWidgetItem',
    'QScrollArea','QTreeWidget','QTreeWidgetItem','QFileDialog','QStyleFactory',

    'QListView','QLayout','QSplitter','QGraphicsPathItem']:

    setattr(qtwidgets, name, type(name, (), {}))

sys.modules["PyQt5.QtWidgets"] = qtwidgets

qtgui = types.ModuleType("PyQt5.QtGui")
for name in [
    'QColor','QPainter','QBrush','QPen','QMovie','QTextCharFormat','QIcon',
    'QPixmap','QDesktopServices']:
    setattr(qtgui, name, type(name, (), {}))
sys.modules['PyQt5.QtGui'] = qtgui

qtsvg = types.ModuleType('PyQt5.QtSvg')
qtsvg.QSvgWidget = type('QSvgWidget', (), {})
sys.modules['PyQt5.QtSvg'] = qtsvg

# ---- import NodeItem ----
from ui.custom_widgets.mindmap_nodes import NodeItem


def test_nodeitem_serialization_round_trip():
    node = NodeItem.__new__(NodeItem)
    DummyEllipseItem.__init__(node)
    node.id = 'node1'
    node.width = 120
    node.height = 80
    node.text_item = DummyTextItem('hello')
    node.update_node_layout = lambda: None
    node.setRect = lambda *a, **k: None
    node.setPos(10, 15)

    data = node.serialize()

    other = NodeItem.__new__(NodeItem)
    DummyEllipseItem.__init__(other)
    other.text_item = DummyTextItem()
    other.update_node_layout = lambda: None
    other.setRect = lambda *a, **k: None
    other.id = None
    other.width = 0
    other.height = 0
    other.deserialize(data)

    assert other.id == node.id
    assert other.text_item.toPlainText() == 'hello'
    assert other.width == 120 and other.height == 80
    assert other.pos().x() == 10
    assert other.pos().y() == 15
