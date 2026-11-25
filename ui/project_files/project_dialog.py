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
# File: project_dialog.py
# Description: Dialog for creating and editing projects
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

from PyQt5.QtCore import QDate, pyqtSignal
from PyQt5.QtWidgets import QLineEdit

from models.project import ProjectStatus
from models.task import TaskPriority
from ui.project_files.form_dialog import ColorChoice, FormDialog, OptionalDate
from ui.project_files.project_look import PROJECT_SWATCHES


class ProjectDialog(FormDialog):
    """Create or edit a project: its name, description, status, priority, dates, and colour.
    After exec_(), project_data holds what was entered (None if cancelled)."""

    projectSaved = pyqtSignal(dict)  # the project's data, when saved

    def __init__(self, mode="create", project=None, logger=None, parent=None):
        self.mode = mode
        self.project = project
        self.logger = logger
        self.project_data = None
        editing = mode == "edit" and project is not None
        super().__init__(parent, "Edit project" if editing else "New project",
                         "Change the details, then press Save." if editing
                         else "Give it a name; everything else can be changed later.",
                         icon="📁", save_label="Save" if editing else "Create project")

        self.title_input = self.addRow("Name", QLineEdit())
        self.title_input.setPlaceholderText("e.g. Plant room upgrade")
        self.description_input = self.addRow("Description", self.textArea("What it's for (optional)"))
        self.status_combo = self.addRow("Status", self.combo([(s.value, s) for s in ProjectStatus]))
        self.priority_combo = self.addRow("Priority", self.combo([(p.name.title(), p) for p in TaskPriority],
                                                                 TaskPriority.MEDIUM))
        self.start_date_edit = self.addRow("Starts", OptionalDate("Start date", default=QDate.currentDate()))
        self.target_date_edit = self.addRow("Due", OptionalDate("Due date",
                                                                default=QDate.currentDate().addMonths(1)))
        self.color_choice = self.addRow("Colour", ColorChoice(PROJECT_SWATCHES,
                                                              project.color if editing else PROJECT_SWATCHES[0]))
        if editing:
            self.fillFields()
        else:
            self.start_date_edit.setValue(QDate.currentDate().toPyDate())
        self.title_input.setFocus()

    @property
    def selected_color(self):
        return self.color_choice.color()

    def fillFields(self):
        project = self.project
        self.title_input.setText(project.title)
        self.description_input.setPlainText(project.description or "")
        for combo, value in ((self.status_combo, project.status), (self.priority_combo, project.priority)):
            index = combo.findData(value)
            if index >= 0:
                combo.setCurrentIndex(index)
        self.start_date_edit.setValue(project.start_date)
        self.target_date_edit.setValue(project.target_completion)

    def validate(self):
        title = self.title_input.text().strip()
        if not title:
            self.showError("Give the project a name.", self.title_input)
            return False
        start, due = self.start_date_edit.value(), self.target_date_edit.value()
        if start and due and due < start:
            self.showError("The due date is before the start date.")
            return False
        self.project_data = {
            'title': title,
            'description': self.description_input.toPlainText().strip(),
            'status': self.status_combo.currentData(),
            'priority': self.priority_combo.currentData(),
            'color': self.selected_color,
            'start_date': start,
            'target_completion': due,
        }
        if self.mode == "edit" and self.project:
            self.project_data['project_id'] = self.project.id
        self.projectSaved.emit(self.project_data)
        return True

    def onSave(self):
        """Kept for callers: check and save, as the Save button does"""
        self._save()

    def getProjectData(self):
        return self.project_data
