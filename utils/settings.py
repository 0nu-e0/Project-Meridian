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
# File: settings.py
# Description: User settings (colours, startup screen, screen defaults), stored
#              in settings.json in the app data folder.
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

import logging
import re

from PyQt5.QtCore import QObject, pyqtSignal

from utils.app_config import AppConfig
from utils.safe_io import read_json, write_json

_logger = logging.getLogger(__name__)

# Screens the app can open on
STARTUP_SCREENS = {
    "welcome": "Welcome",
    "dashboard_screen": "Dashboard",
    "planning_screen": "Planning",
    "projects_screen": "Projects",
    "notes_screen": "Notes",
    "mindmaps_screen": "Mindmaps",
}

PLANNING_VIEWS = {"daily": "Daily", "weekly": "Weekly", "monthly": "Monthly"}

DEFAULTS = {
    "colors": {},                      # AppColors attribute -> "#rrggbb" overrides
    "startup_screen": "welcome",
    "planning_default_view": "weekly",
    "planning_show_weekends": False,
    "dashboard_show_archived": True,
    "mindmap_show_grid": True,
    "mindmap_snap_to_grid": True,
    "new_task_category": "Feature",
    "interface_scale": "auto",         # "auto" or a percentage such as 125
    "task_card_layout": {},            # remembered splitter positions in the task card
    "seen_guide": False,               # the first-run notice offering the guide has been shown
    "task_card_sections": {},          # sections task cards show by default (missing = shown)
}

# Colours offered in Settings, with the label shown for each
EDITABLE_COLORS = [
    ("main_background_color", "App background"),
    ("banner_color", "Banner"),
    ("accent_background_color", "Drawer"),
    ("accent", "Accent (buttons, highlights)"),
    ("accent_dark", "Accent when pressed"),
    ("accent_light", "Accent when hovered"),
    ("surface", "Panels and cards"),
    ("surface_raised", "Inputs and borders"),
    ("surface_sunken", "Lists"),
    ("text_primary", "Main text"),
    ("text_secondary", "Labels"),
    ("text_muted", "Muted text"),
    ("success", "Success / done"),
    ("danger", "Danger / delete"),
    ("warning", "Warning"),
    ("highlight", "Highlight"),
]

_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


class Settings(QObject):
    """App settings, loaded once and saved on every change"""

    # Emitted with the key that changed
    changed = pyqtSignal(str)

    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = Settings()
        return cls._instance

    def __init__(self):
        super().__init__()
        self._path = AppConfig().settings_file
        stored = read_json(self._path, _logger)
        self._values = {key: stored.get(key, default) for key, default in DEFAULTS.items()}
        if not isinstance(self._values["colors"], dict):
            self._values["colors"] = {}

    def get(self, key):
        return self._values.get(key, DEFAULTS.get(key))

    def set(self, key, value):
        if self._values.get(key) == value:
            return
        self._values[key] = value
        self.save()
        self.changed.emit(key)

    def save(self):
        return write_json(self._path, self._values, _logger)

    # ---- colours ---------------------------------------------------------

    def color_overrides(self):
        return dict(self._values["colors"])

    def set_color(self, name, hex_value):
        colors = dict(self._values["colors"])
        if hex_value is None:
            colors.pop(name, None)
        else:
            colors[name] = hex_value
        self.set("colors", colors)

    def reset_colors(self):
        self.set("colors", {})


# Default values of AppColors before any overrides, so Settings can show and restore them
_default_colors = {}


def default_color(name):
    from resources.styles import AppColors
    return _default_colors.get(name, getattr(AppColors, name))


def apply_color_overrides():
    """Apply saved colours to AppColors. Call before any screen is built."""
    from resources.styles import AppColors
    for name, _label in EDITABLE_COLORS:
        _default_colors.setdefault(name, getattr(AppColors, name))
    for name, value in Settings.instance().color_overrides().items():
        if name in _default_colors and isinstance(value, str) and _HEX.match(value):
            setattr(AppColors, name, value)
        else:
            _logger.warning(f"Ignoring invalid colour setting {name!r}: {value!r}")
