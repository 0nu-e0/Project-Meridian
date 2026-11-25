"""
At fractional interface sizes (e.g. 112%), repainting part of the mind map must not
leave outlines: hovering a shape or line used to draw a box around it, and dragging
a link left trails. Runs in its own process, since the scale is fixed once Qt starts.
"""
import os
import subprocess
import sys

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def stray_pixels_after_partial_repaints():
    """Repaint only each item's rectangle (what hovering does) and count edge pixels
    that differ from a full repaint"""
    import logging
    from PyQt5.QtCore import QPointF
    from PyQt5.QtGui import QRegion
    from PyQt5.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from resources.styles import AppColors
    app.setStyleSheet(f"QWidget {{ background-color: {AppColors.main_background_color}; color: white }}")
    from ui.custom_widgets.mindmap_nodes import ConnectionItem
    from ui.mindmap_screen import MindMapScreen

    screen = MindMapScreen(logger=logging.getLogger("repaint"))
    screen.resize(1200, 800)
    screen.show()
    screen.view.centerOn(0, 0)
    first = screen.add_node("rounded", QPointF(-200, -60))
    second = screen.add_node("hexagon", QPointF(200, 80))
    for node in (first, second):
        node.text_item.stopEditing()
    screen.scene.clearSelection()
    line = ConnectionItem(first, "right", second, "left")
    screen.scene.addItem(line)
    app.processEvents()

    viewport = screen.view.viewport()
    full = viewport.grab().toImage()
    stray = 0
    for item in (first, second, line):
        region = screen.view.mapFromScene(item.sceneBoundingRect()).boundingRect().adjusted(-2, -2, 2, 2)
        partial = viewport.grab()
        viewport.render(partial, region.topLeft(), QRegion(region))
        image, ratio = partial.toImage(), partial.devicePixelRatio()
        left, right = int(region.left() * ratio), int(region.right() * ratio)
        top, bottom = int(region.top() * ratio), int(region.bottom() * ratio)
        edge = [(x, y) for x in range(left, right + 1) for y in (top, bottom)]
        edge += [(x, y) for y in range(top, bottom + 1) for x in (left, right)]
        for x, y in edge:
            if 0 <= x < image.width() and 0 <= y < image.height():
                if abs(image.pixelColor(x, y).lightness() - full.pixelColor(x, y).lightness()) > 30:
                    stray += 1
    return stray


def test_no_outlines_at_a_fractional_interface_size(tmp_path):
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", QT_SCALE_FACTOR="1.125", LOCALAPPDATA=str(tmp_path))
    result = subprocess.run([sys.executable, os.path.abspath(__file__)], cwd=PROJECT, env=env,
                            capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr
    stray = int(result.stdout.strip().splitlines()[-1])
    # A few pixels differ where an outline or line crosses the edge; a box outline is hundreds
    assert stray < 30, f"{stray} stray pixels: partial repaints leave outlines"


if __name__ == "__main__":
    sys.path.insert(0, PROJECT)
    print(stray_pixels_after_partial_repaints())
