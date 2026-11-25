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
# File: project_actions.py
# Description: What can be done to a whole project (new, edit, archive, export,
#              delete, import), shared by the Projects screen and a project's page.
#              Each change is one undoable step, announced by the notice at the bottom.
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

from PyQt5.QtWidgets import QFileDialog

from ui.custom_widgets import dialogs
from ui.custom_widgets.toast import show_toast
from utils.data_history import history
from utils import projects_io

EDITABLE_FIELDS = ['title', 'description', 'status', 'priority', 'color', 'start_date', 'target_completion']


def _quoted(project):
    return f"“{project.title}”"


def new_project(parent, logger):
    """Ask for a new project's details and create it. Returns the project, or None."""
    from ui.project_files.project_dialog import ProjectDialog
    dialog = ProjectDialog(mode="create", logger=logger, parent=parent)
    if not dialog.exec_() or not dialog.project_data:
        return None
    data = dialog.project_data
    with history().action(f"Created project “{data['title']}”"):
        project = projects_io.create_project(
            title=data['title'], description=data['description'], status=data['status'],
            priority=data['priority'], color=data['color'], logger=logger,
            start_date=data.get('start_date'), target_completion=data.get('target_completion'))
    return project


def edit_project(parent, project, logger):
    """Edit a project's details. Returns True if anything was saved."""
    from ui.project_files.project_dialog import ProjectDialog
    dialog = ProjectDialog(mode="edit", project=project, logger=logger, parent=parent)
    if not dialog.exec_() or not dialog.project_data:
        return False
    apply_edit(project, dialog.project_data, logger)
    return True


def apply_edit(project, data, logger):
    """Save edited details onto project (and the file), as one undoable step"""
    title = project.title
    for field in EDITABLE_FIELDS:
        if field in data:
            setattr(project, field, data[field])
    # Save just these fields, so changes made elsewhere aren't overwritten
    with history().action(f"Edited project “{title}”"):
        projects_io.save_project_fields(project, EDITABLE_FIELDS, logger)


def set_archived(parent, project, archived, logger):
    """Archive (hide from the Projects screen) or restore a project"""
    project.archived = archived
    with history().action(("Archived" if archived else "Restored") + f" project {_quoted(project)}"):
        projects_io.save_project_fields(project, ['archived'], logger)
    return True


def delete_project(parent, project, logger):
    """Delete a project after asking. Undo brings it back. Returns True if deleted."""
    if not dialogs.confirm(parent, f"Delete {_quoted(project)}?",
                           "Its phases, Gantt chart, and schedule are removed. Its tasks are kept, "
                           "just no longer in a project. You can bring it all back with Undo.", "Delete"):
        return False
    with history().action(f"Deleted project {_quoted(project)}"):
        deleted = projects_io.delete_project(project.id, logger)
    if not deleted:
        dialogs.critical(parent, "Couldn't delete the project", "See app.log for details.")
    return deleted


def export_project(parent, project, logger):
    """Save a copy of the project (phases, tasks, Gantt chart) to a file someone else can import"""
    default_name = f"{project.title.replace(' ', '_')}_export.json"
    path, _ = QFileDialog.getSaveFileName(parent, "Export Project", default_name, "JSON Files (*.json)")
    if not path:
        return False
    if projects_io.export_project_to_json(project.id, path, logger):
        show_toast(parent, f"Exported {_quoted(project)}")
        return True
    dialogs.critical(parent, "Couldn't export the project", "See app.log for details.")
    return False


def import_project(parent, logger):
    """Bring in a project exported from Project Meridian. Returns its new id, or None."""
    path, _ = QFileDialog.getOpenFileName(parent, "Import Project", "", "JSON Files (*.json)")
    if not path:
        return None
    try:
        with history().action("Imported a project"):
            new_id = projects_io.import_project_from_json(path, logger)
    except Exception as e:
        logger.error(f"Error importing project: {e}")
        new_id = None
    if not new_id:
        dialogs.warning(parent, "Couldn't import the project",
                        "The file may not be a Project Meridian export. See app.log for details.")
    return new_id
