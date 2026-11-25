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
# File: task_sections.py
# Description: Which sections a task card shows. Settings holds the defaults
#              (Settings > Behaviour > Task card sections); each task keeps only
#              the sections it changes, so a task you haven't customized follows
#              the defaults, even when they change later.
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

from utils.settings import Settings

# (key, label, where it is in the card)
SECTIONS = [
    ("description", "Description", "Left"),
    ("activity", "Activity (comments and work logs)", "Left"),
    ("status_priority", "Status and priority", "Right"),
    ("details", "Details (dates and team)", "Right"),
    ("dependencies", "Dependencies", "Right"),
    ("attachments", "Attachments", "Right"),
    ("checklist", "Checklist", "Right"),
    ("category", "Category", "Right"),
    ("project_phase_selection", "Project and phase", "Right"),
]
KEYS = [key for key, _label, _where in SECTIONS]
LABELS = {key: label for key, label, _where in SECTIONS}


def defaults():
    """{section: shown?} for tasks that haven't been customized (all shown unless changed)"""
    saved = Settings.instance().get("task_card_sections") or {}
    return {key: bool(saved.get(key, True)) for key in KEYS}


def set_default(key, shown):
    saved = dict(Settings.instance().get("task_card_sections") or {})
    saved[key] = bool(shown)
    Settings.instance().set("task_card_sections", saved)


def is_shown(task, key):
    own = getattr(task, "visible_sections", None) or {}
    return bool(own[key]) if key in own else defaults()[key]


def shown_sections(task):
    return {key: is_shown(task, key) for key in KEYS}


def set_shown(task, key, shown):
    """Show or hide a section on this task only. Matching the default means "follow the
    default", so it's stored only when it differs."""
    own = dict(getattr(task, "visible_sections", None) or {})
    if bool(shown) == defaults()[key]:
        own.pop(key, None)
    else:
        own[key] = bool(shown)
    task.visible_sections = own


def is_customized(task):
    own = getattr(task, "visible_sections", None) or {}
    current = defaults()
    return any(bool(value) != current.get(key, True) for key, value in own.items() if key in current)


def reset(task):
    """Back to the defaults"""
    task.visible_sections = {}


def make_defaults(task):
    """This task's sections become the defaults (and the task then just follows them)"""
    Settings.instance().set("task_card_sections", shown_sections(task))
    task.visible_sections = {}
