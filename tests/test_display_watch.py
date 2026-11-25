"""
Tests for putting the window back at the right scale after sleep or a monitor change.
A real sleep can't be simulated here, so these check the decision and the fix itself.
"""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtGui import QGuiApplication
from PyQt5.QtWidgets import QApplication, QWidget


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_needs_fix():
    from utils.display_watch import needs_fix
    assert not needs_fix("DISPLAY2", 1.0, "DISPLAY2", 1.0)
    assert needs_fix("DISPLAY1", 3.0, "DISPLAY2", 1.0)  # stuck on the laptop screen's scale
    assert needs_fix("DISPLAY2", 3.0, "DISPLAY2", 1.0)  # right screen, wrong scale
    assert not needs_fix("DISPLAY1", 3.0, None, 1.0)  # couldn't tell: leave it alone


class StuckWindow(QWidget):
    """A window Qt thinks is at 3x after the monitor came back at 1x"""
    ratio = 3.0

    def devicePixelRatioF(self):
        return self.ratio


def test_a_stuck_window_is_rescaled(app):
    from utils.display_watch import DisplayWatcher
    window = StuckWindow()
    window.resize(800, 600)
    window.show()
    screen_name = QGuiApplication.primaryScreen().name()
    watcher = DisplayWatcher(window, monitor_lookup=lambda hwnd: screen_name)

    assert watcher.check()
    assert watcher.fixes == 1 and window.isVisible()
    assert window.windowHandle().screen().name() == screen_name


def test_a_window_at_the_right_scale_is_left_alone(app):
    from utils.display_watch import DisplayWatcher
    window = QWidget()
    window.resize(800, 600)
    window.show()
    screen_name = QGuiApplication.primaryScreen().name()
    watcher = DisplayWatcher(window, monitor_lookup=lambda hwnd: screen_name)
    assert not watcher.check()
    assert watcher.fixes == 0


def test_an_unknown_monitor_changes_nothing(app):
    from utils.display_watch import DisplayWatcher
    window = StuckWindow()
    window.show()
    watcher = DisplayWatcher(window, monitor_lookup=lambda hwnd: None)
    assert not watcher.check()


def test_a_burst_of_changes_is_checked_a_few_times_not_per_message(app):
    from utils.display_watch import CHECK_DELAYS_MS, DisplayWatcher
    window = QWidget()
    window.show()
    watcher = DisplayWatcher(window, monitor_lookup=lambda hwnd: None)
    for _ in range(10):
        watcher.schedule("test")
    assert len(watcher._timers) == len(CHECK_DELAYS_MS)
