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
# File: data_history.py
# Description: Undo and redo for changes saved straight to the data files (the
#              Dashboard and Planning save as you go).
#
#   An action is wrapped so the data files are read before and after it. What
#   changed is kept per record (a task, a phase, a schedule entry...), so undo
#   puts back only those records: a later change to another task isn't lost.
#   Files that aren't lists of records (the dashboard's group layout) are put
#   back whole.
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

import glob
import json
import logging
import os
from contextlib import contextmanager

import yaml

from utils.app_config import AppConfig
from utils.safe_io import write_json, write_yaml

_logger = logging.getLogger(__name__)
MISSING = object()  # a record (or file) that didn't exist
LIMIT = 50


def _data_files():
    config = AppConfig()
    files = glob.glob(os.path.join(config.data_dir, "*.json"))
    files += glob.glob(os.path.join(config.app_data_dir, "config", "*.yaml"))
    return files


def _read(path):
    try:
        with open(path, encoding="utf-8") as file:
            return yaml.safe_load(file) if path.endswith(".yaml") else json.load(file)
    except FileNotFoundError:
        return MISSING
    except Exception as e:
        _logger.debug(f"Undo couldn't read {path}: {e}")
        return MISSING


def snapshot():
    """The data files' contents right now"""
    return {path: _read(path) for path in _data_files()}


def diff(before, after):
    """{path: change}. A change is ("records", {key: (old, new)}) for files of records,
    or ("file", old, new) for anything else."""
    changes = {}
    for path in set(before) | set(after):
        old, new = before.get(path, MISSING), after.get(path, MISSING)
        if old == new:
            continue
        if isinstance(old, dict) and isinstance(new, dict) and not path.endswith(".yaml"):
            keys = {key: (old.get(key, MISSING), new.get(key, MISSING))
                    for key in set(old) | set(new) if old.get(key, MISSING) != new.get(key, MISSING)}
            changes[path] = ("records", keys)
        else:
            changes[path] = ("file", old, new)
    return changes


def _apply(changes, use_old):
    """Write back one side of each change"""
    for path, change in changes.items():
        if change[0] == "records":
            current = _read(path)
            current = current if isinstance(current, dict) else {}
            for key, (old, new) in change[1].items():
                value = old if use_old else new
                if value is MISSING:
                    current.pop(key, None)
                else:
                    current[key] = value
            write_json(path, current, _logger)
        else:
            value = change[1] if use_old else change[2]
            if value is MISSING:
                if os.path.exists(path):
                    os.remove(path)
            elif path.endswith(".yaml"):
                write_yaml(path, value, _logger)
            else:
                write_json(path, value, _logger)


class Signal:
    """A plain callback list (the history outlives any one Qt window, so it isn't a QObject)"""

    def __init__(self):
        self._callbacks = []

    def connect(self, callback):
        self._callbacks.append(callback)

    def emit(self, *args):
        for callback in list(self._callbacks):
            try:
                callback(*args)
            except RuntimeError:  # a window that has since closed
                self._callbacks.remove(callback)


class DataHistory:
    """Undo / redo for saved data. Use history().action("Deleted …") around a change."""

    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.undo_stack = []  # (label, changes)
        self.redo_stack = []
        self.changed = Signal()  # what can be undone or redone changed
        self.recorded = Signal()  # an action was recorded (its label)
        self.restored = Signal()  # (label, True for undo / False for redo): screens reload

    @contextmanager
    def action(self, label):
        """Record whatever the wrapped code changes in the data files as one undoable step"""
        before = snapshot()
        yield
        self.record(label, before)

    def record(self, label, before, after=None):
        """Record the change from before (a snapshot) to now. Returns True if anything changed."""
        changes = diff(before, snapshot() if after is None else after)
        if not changes:
            return False
        self.undo_stack.append((label, changes))
        del self.undo_stack[:-LIMIT]
        self.redo_stack.clear()
        self.changed.emit()
        self.recorded.emit(label)
        return True

    def canUndo(self):
        return bool(self.undo_stack)

    def canRedo(self):
        return bool(self.redo_stack)

    def undoLabel(self):
        return self.undo_stack[-1][0] if self.undo_stack else ""

    def undo(self):
        if not self.undo_stack:
            return None
        label, changes = self.undo_stack.pop()
        _apply(changes, use_old=True)
        self.redo_stack.append((label, changes))
        self._after_restore(label, True)
        return label

    def redo(self):
        if not self.redo_stack:
            return None
        label, changes = self.redo_stack.pop()
        _apply(changes, use_old=False)
        self.undo_stack.append((label, changes))
        self._after_restore(label, False)
        return label

    def _after_restore(self, label, undone):
        from utils.tasks_io import invalidate_tasks_cache
        invalidate_tasks_cache()
        self.changed.emit()
        self.restored.emit(label, undone)


def history():
    return DataHistory.instance()
