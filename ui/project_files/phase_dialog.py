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
# File: phase_dialog.py
# Description: Dialog for creating and editing project phases
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QLineEdit

from ui.project_files.form_dialog import FormDialog


class PhaseDialog(FormDialog):
    """Create or edit a phase: a name and an optional description"""

    phaseSaved = pyqtSignal(dict)  # the phase's data, when saved

    def __init__(self, mode="create", project_id=None, phase=None, logger=None, parent=None):
        self.mode = mode
        self.project_id = project_id
        self.phase = phase
        self.logger = logger
        self.phase_data = None
        editing = mode == "edit" and phase is not None
        super().__init__(parent, "Edit phase" if editing else "New phase",
                         "" if editing else "A stage of the project, such as Design or Build. "
                                            "It's added after the others; drag it to move it.",
                         icon="▤", save_label="Save" if editing else "Add phase")
        self.name_input = self.addRow("Name", QLineEdit())
        self.name_input.setPlaceholderText("e.g. Design")
        self.description_input = self.addRow("Description", self.textArea("What happens in this phase (optional)"))
        if editing:
            self.fillFields()
        self.name_input.setFocus()

    def fillFields(self):
        self.name_input.setText(self.phase.name)
        self.description_input.setPlainText(self.phase.description or "")

    def validate(self):
        name = self.name_input.text().strip()
        if not name:
            self.showError("Give the phase a name.", self.name_input)
            return False
        self.phase_data = {'name': name, 'description': self.description_input.toPlainText().strip()}
        if self.mode == "edit" and self.phase:
            self.phase_data['phase_id'] = self.phase.id
        self.phaseSaved.emit(self.phase_data)
        return True

    def onSave(self):
        self._save()
