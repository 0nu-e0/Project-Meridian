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
# File: display_watch.py
# Description: Keeps the window at the right size after sleep or a monitor change.
#
#   When the PC sleeps, a monitor can disconnect and Windows moves the app to
#   another display (say a laptop screen at 300%). Qt rescales for it, but when
#   the first monitor comes back Qt 5 can keep the old scale, leaving the text and
#   everything else huge. This watches for display changes and wake-ups, asks
#   Windows which monitor the window is really on, and if Qt's scale doesn't
#   match it, moves the window to that screen and re-shows it so Qt rescales.
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

import ctypes
import logging
import sys
from ctypes import wintypes

from PyQt5.QtCore import QAbstractNativeEventFilter, QObject, QTimer
from PyQt5.QtGui import QGuiApplication

_logger = logging.getLogger(__name__)

# Windows messages that mean the displays (or their scaling) may have changed
WM_DISPLAYCHANGE = 0x007E
WM_SETTINGCHANGE = 0x001A
WM_POWERBROADCAST = 0x0218
WM_DPICHANGED = 0x02E0
WM_WTSSESSION_CHANGE = 0x02B1  # signing back in
DISPLAY_MESSAGES = {WM_DISPLAYCHANGE, WM_SETTINGCHANGE, WM_POWERBROADCAST, WM_DPICHANGED, WM_WTSSESSION_CHANGE}

# Check soon after a change, and again once slow monitors have finished waking up
CHECK_DELAYS_MS = (800, 3000, 8000)
DPR_TOLERANCE = 0.01


def needs_fix(qt_screen_name, qt_ratio, actual_screen_name, actual_ratio):
    """True if Qt's idea of the window's screen or scale doesn't match the monitor it's on"""
    if actual_screen_name is None:
        return False  # couldn't tell: leave it alone
    return qt_screen_name != actual_screen_name or abs(qt_ratio - actual_ratio) > DPR_TOLERANCE


class _MONITORINFOEXW(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT), ("rcWork", wintypes.RECT),
                ("dwFlags", wintypes.DWORD), ("szDevice", wintypes.WCHAR * 32)]


def monitor_name_for_window(hwnd):
    """The Windows device name (e.g. \\\\.\\DISPLAY2) of the monitor a window is mostly on"""
    if sys.platform != "win32" or not hwnd:
        return None
    try:
        user32 = ctypes.windll.user32
        user32.MonitorFromWindow.restype = wintypes.HMONITOR
        user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
        monitor = user32.MonitorFromWindow(wintypes.HWND(int(hwnd)), 2)  # MONITOR_DEFAULTTONEAREST
        info = _MONITORINFOEXW()
        info.cbSize = ctypes.sizeof(_MONITORINFOEXW)
        if not user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
            return None
        return info.szDevice
    except Exception as e:
        _logger.debug(f"Couldn't ask Windows for the window's monitor: {e}")
        return None


class _DisplayMessageFilter(QAbstractNativeEventFilter):
    def __init__(self, on_change):
        super().__init__()
        self.on_change = on_change

    def nativeEventFilter(self, event_type, message):
        if event_type == b"windows_generic_MSG":
            try:
                msg = wintypes.MSG.from_address(int(message))
                if msg.message in DISPLAY_MESSAGES:
                    self.on_change(f"Windows message 0x{msg.message:04X}")
            except Exception:
                pass
        return False, 0


class DisplayWatcher(QObject):
    """Watches for display changes and fixes a window whose scale got stuck"""

    def __init__(self, window, monitor_lookup=monitor_name_for_window, parent=None):
        super().__init__(parent)
        self.window = window
        self.monitor_lookup = monitor_lookup
        self.fixes = 0
        self._timers = []

        app = QGuiApplication.instance()
        app.screenAdded.connect(lambda _screen: self.schedule("screen added"))
        app.screenRemoved.connect(lambda _screen: self.schedule("screen removed"))
        app.primaryScreenChanged.connect(lambda _screen: self.schedule("primary screen changed"))
        self._filter = _DisplayMessageFilter(self.schedule)
        if sys.platform == "win32":
            app.installNativeEventFilter(self._filter)
            self._registerForSignIn()

    def _registerForSignIn(self):
        """Ask Windows to tell the window when the user signs back in"""
        try:
            ctypes.windll.wtsapi32.WTSRegisterSessionNotification(wintypes.HWND(int(self.window.winId())), 0)
        except Exception as e:
            _logger.debug(f"Couldn't register for sign-in notices: {e}")

    def schedule(self, reason=""):
        """Check the window a few times over the next seconds (monitors settle slowly after waking)"""
        if self._timers:
            return  # checks already on the way
        _logger.debug(f"Display change ({reason}): checking the window's scale")
        for delay in CHECK_DELAYS_MS:
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.timeout.connect(self.check)
            timer.start(delay)
            self._timers.append(timer)
        QTimer.singleShot(max(CHECK_DELAYS_MS) + 100, self._timers.clear)

    def check(self):
        """Fix the window if Qt's screen or scale doesn't match the monitor it's actually on"""
        window = self.window
        handle = window.windowHandle()
        if handle is None or not window.isVisible():
            return False
        actual_name = self.monitor_lookup(window.winId())
        actual = next((s for s in QGuiApplication.screens() if s.name() == actual_name), None)
        if actual is None:
            return False
        qt_screen = handle.screen()
        if not needs_fix(qt_screen.name() if qt_screen else None, window.devicePixelRatioF(),
                         actual.name(), actual.devicePixelRatio()):
            return False

        _logger.info(f"Window scale out of step after a display change: Qt has it on "
                     f"{qt_screen.name() if qt_screen else '?'} at {window.devicePixelRatioF():g}x, "
                     f"but it's on {actual.name()} ({actual.devicePixelRatio():g}x). Rescaling.")
        maximized, full_screen = window.isMaximized(), window.isFullScreen()
        geometry = window.geometry()
        handle.setScreen(actual)
        # Re-showing the window makes Qt work out its scale again for the screen it's on
        window.hide()
        if full_screen:
            window.showFullScreen()
        elif maximized:
            window.showMaximized()
        else:
            window.setGeometry(geometry)
            window.show()
        self.fixes += 1
        return True
