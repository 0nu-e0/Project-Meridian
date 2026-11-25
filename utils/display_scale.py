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
# File: display_scale.py
# Description: Works out how much to enlarge the whole interface (text and
#              controls together) for the monitor, or uses the size picked in
#              Settings. Applied before the app starts, through QT_SCALE_FACTOR.
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

import logging
import math
import os
import sys

_logger = logging.getLogger(__name__)

# Sizes offered in Settings, as percentages
INTERFACE_SIZES = [90, 100, 110, 125, 150, 175]

# Windows lays out at 96 pixels per inch; a monitor with more real pixels per inch
# (after its own scaling setting) shows everything smaller than intended
DESIGN_DPI = 96.0
STEP = 0.125
MAX_AUTO = 1.5


def detect_auto_scale():
    """
    Extra scale for the primary monitor beyond Windows' own display scaling.

    A large monitor at 100% scaling (like a 38" ultrawide) shows about 110 real
    pixels per inch, so 96-dpi text comes out smaller than it should. This measures
    that and rounds down to steps of 12.5%, so ordinary monitors stay at 100%.
    """
    if sys.platform != 'win32':
        return 1.0
    try:
        import ctypes
        user32, gdi32 = ctypes.windll.user32, ctypes.windll.gdi32
        HORZSIZE, HORZRES, LOGPIXELSX = 4, 8, 88  # width in mm, width in pixels, Windows DPI
        hdc = user32.GetDC(0)
        try:
            width_mm = gdi32.GetDeviceCaps(hdc, HORZSIZE)
            # Windows reports either raw or already-scaled pixels depending on how the
            # process is set up; dividing by its DPI gives scaled pixels either way
            width_px = gdi32.GetDeviceCaps(hdc, HORZRES) * DESIGN_DPI / max(1, gdi32.GetDeviceCaps(hdc, LOGPIXELSX))
        finally:
            user32.ReleaseDC(0, hdc)
    except Exception as e:
        _logger.debug(f"Could not measure the monitor: {e}")
        return 1.0

    # Projectors, VMs, and some docks report no (or nonsense) physical size
    if width_mm <= 50 or width_px <= 0:
        return 1.0
    pixels_per_inch = width_px / (width_mm / 25.4)
    ratio = pixels_per_inch / DESIGN_DPI
    if not 0.5 <= ratio <= 3.0:
        return 1.0
    return min(MAX_AUTO, max(1.0, math.floor(ratio / STEP) * STEP))


def interface_scale(setting):
    """The scale to use for a Settings value: "auto" or a percentage"""
    if setting == "auto" or setting is None:
        return detect_auto_scale()
    try:
        return max(0.5, min(3.0, float(setting) / 100.0))
    except (TypeError, ValueError):
        return 1.0


def apply_interface_scale(setting):
    """Set QT_SCALE_FACTOR from Settings. Must run before the QApplication is created."""
    if "QT_SCALE_FACTOR" in os.environ:
        return float(os.environ["QT_SCALE_FACTOR"])  # set by hand: respect it
    scale = interface_scale(setting)
    if abs(scale - 1.0) > 0.001:
        os.environ["QT_SCALE_FACTOR"] = f"{scale:g}"
    return scale
