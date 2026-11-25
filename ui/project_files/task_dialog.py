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
# File: task_dialog.py
# Description: Simple dialog for creating tasks within a phase
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QLineEdit

from models.task import TaskPriority, TaskStatus
from ui.project_files.form_dialog import FormDialog


class TaskDialog(FormDialog):
    """Add a task to a phase: a title, and optionally a description, priority, and status.
    Open the task afterwards for everything else (dates, checklist, people…)."""

    taskSaved = pyqtSignal(dict)  # the task's data, when saved

    def __init__(self, project_id=None, phase_id=None, logger=None, parent=None, phase_name=None):
        self.project_id = project_id
        self.phase_id = phase_id
        self.logger = logger
        self.task_data = None
        self._saving = False  # one task per press, even if Enter is held
        super().__init__(parent, f"Add a task to “{phase_name}”" if phase_name else "Add a task",
                         "Click it afterwards to add dates, a checklist, and more.",
                         icon="☑", save_label="Add task")
        self.title_input = self.addRow("Title", QLineEdit())
        self.title_input.setPlaceholderText("What needs doing")
        self.description_input = self.addRow("Description", self.textArea("Details (optional)", 70))
        self.priority_combo = self.addRow("Priority", self.combo([(p.name.title(), p) for p in TaskPriority],
                                                                 TaskPriority.MEDIUM))
        self.status_combo = self.addRow("Status", self.combo([(s.value, s) for s in TaskStatus]))
        self.title_input.setFocus()

    def validate(self):
        if self._saving:
            return False
        title = self.title_input.text().strip()
        if not title:
            self.showError("Give the task a title.", self.title_input)
            return False
        self._saving = True
        self.task_data = {
            'title': title,
            'description': self.description_input.toPlainText().strip(),
            'priority': self.priority_combo.currentData(),
            'status': self.status_combo.currentData(),
            'project_id': self.project_id,
            'phase_id': self.phase_id,
        }
        self.taskSaved.emit(self.task_data)
        return True

    def onSave(self):
        self._save()
