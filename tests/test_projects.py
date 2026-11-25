"""
Tests for projects and phases: saving edits without clobbering other changes,
phase ordering, the current phase, and deleting a project from its detail view.
Runs offscreen against a temporary data directory.
"""
import logging
import os
from datetime import datetime

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication, QMessageBox

from ui.custom_widgets import dialogs

logger = logging.getLogger("test_projects")


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def make_project_with_phases(names):
    from utils.projects_io import create_phase, create_project
    project = create_project("P", logger=logger)
    phases = [create_phase(project.id, name, order=i, logger=logger) for i, name in enumerate(names)]
    return project, phases


def ordered_names(project_id):
    from utils.projects_io import load_phases_from_json
    phases = [p for p in load_phases_from_json(logger).values() if p.project_id == project_id]
    return [p.name for p in sorted(phases, key=lambda p: p.order)], sorted(p.order for p in phases)


def test_creating_a_project_keeps_its_dates():
    from utils.projects_io import create_project, load_projects_from_json
    project = create_project("Dated", logger=logger, start_date=datetime(2026, 2, 1),
                             target_completion=datetime(2026, 6, 30))
    stored = load_projects_from_json(logger)[project.id]
    assert stored.start_date == datetime(2026, 2, 1)
    assert stored.target_completion == datetime(2026, 6, 30)


def test_saving_edited_fields_keeps_changes_made_elsewhere():
    from utils.projects_io import create_phase, load_projects_from_json, save_project_fields
    project, _ = make_project_with_phases(["One"])
    open_copy = load_projects_from_json(logger)[project.id]  # what a screen is holding

    create_phase(project.id, "Added elsewhere", logger=logger)
    open_copy.title = "Renamed"
    save_project_fields(open_copy, ["title"], logger)

    stored = load_projects_from_json(logger)[project.id]
    assert stored.title == "Renamed"
    assert len(stored.phases) == 2


def test_deleting_a_phase_closes_the_gap_and_clears_current():
    from utils.projects_io import delete_phase, load_projects_from_json, set_current_phase
    project, (one, two, three) = make_project_with_phases(["One", "Two", "Three"])
    set_current_phase(project.id, two.id, logger)

    delete_phase(two.id, logger)
    assert ordered_names(project.id) == (["One", "Three"], [0, 1])
    assert load_projects_from_json(logger)[project.id].current_phase_id is None


def test_only_one_phase_is_current():
    from utils.projects_io import load_phases_from_json, load_projects_from_json, set_current_phase
    project, (one, two) = make_project_with_phases(["One", "Two"])
    set_current_phase(project.id, one.id, logger)
    set_current_phase(project.id, two.id, logger)
    phases = load_phases_from_json(logger)
    assert [phases[one.id].is_current, phases[two.id].is_current] == [False, True]
    assert load_projects_from_json(logger)[project.id].current_phase_id == two.id


def test_reordering_phases_works_with_gaps_in_the_order(app):
    from ui.project_files.project_detail_view import ProjectDetailView
    from utils.projects_io import load_phases_from_json, save_phases_to_json
    project, (a, b, c) = make_project_with_phases(["A", "B", "C"])

    # Orders 0, 5, 9: what older data or a deleted phase can leave behind
    phases = load_phases_from_json(logger)
    phases[a.id].order, phases[b.id].order, phases[c.id].order = 0, 5, 9
    save_phases_to_json(phases, logger)

    view = ProjectDetailView(project.id, logger)
    view.onPhaseReordered(c.id, 0)  # drop C onto A
    assert ordered_names(project.id) == (["C", "A", "B"], [0, 1, 2])


def test_project_delete_needs_the_typed_name(app, monkeypatch):
    from ui.project_files.project_detail_view import ProjectDetailView
    from utils.projects_io import create_project, load_projects_from_json
    project = create_project("Keep Me", logger=logger)
    view = ProjectDetailView(project.id, logger)
    monkeypatch.setattr(dialogs, "warning", lambda *a, **k: QMessageBox.Yes)
    monkeypatch.setattr(dialogs, "information", lambda *a, **k: None)

    monkeypatch.setattr(dialogs, "getText", lambda *a, **k: ("Wrong name", True))
    view.onDeleteProject()
    assert project.id in load_projects_from_json(logger)

    monkeypatch.setattr(dialogs, "getText", lambda *a, **k: ("Keep Me", True))
    view.onDeleteProject()
    assert project.id not in load_projects_from_json(logger)


def test_export_then_import_keeps_phases_and_dependencies(tmp_path):
    from models.task import Task
    from utils.projects_io import (create_phase, create_project, export_project_to_json,
                                   import_project_from_json, load_phases_from_json, load_projects_from_json,
                                   move_task_to_phase)
    from utils.tasks_io import load_tasks_from_json, save_task_to_json
    project = create_project("Original", logger=logger)
    phase = create_phase(project.id, "Build", logger=logger)
    first, second = Task(title="First", project_id=project.id), Task(title="Second", project_id=project.id)
    second.dependencies = {first.id}
    for task in (first, second):
        save_task_to_json(task, logger)
    move_task_to_phase(first.id, phase.id, logger)

    export_path = str(tmp_path / "export.json")
    assert export_project_to_json(project.id, export_path, logger)
    new_id = import_project_from_json(export_path, logger)

    imported = load_projects_from_json(logger)[new_id]
    new_phase_id, = imported.phases
    tasks = {t.title: t for t in load_tasks_from_json(logger, force_reload=True).values() if t.project_id == new_id}
    assert set(tasks) == {"First", "Second"}
    assert tasks["First"].phase_id == new_phase_id
    assert tasks["Second"].dependencies == {tasks["First"].id}
    assert load_phases_from_json(logger)[new_phase_id].task_ids == [tasks["First"].id]


def test_a_broken_import_writes_nothing(tmp_path):
    import json
    from utils.projects_io import create_project, export_project_to_json, import_project_from_json, load_projects_from_json
    from utils.tasks_io import load_tasks_from_json
    project = create_project("Source", logger=logger)
    export_path = tmp_path / "export.json"
    export_project_to_json(project.id, str(export_path), logger)

    data = json.loads(export_path.read_text(encoding="utf-8"))
    data["tasks"] = [{"id": "ok", "title": "Fine"}, {"title": "No id"}]
    export_path.write_text(json.dumps(data), encoding="utf-8")

    assert import_project_from_json(str(export_path), logger) is None
    assert list(load_projects_from_json(logger)) == [project.id]
    assert load_tasks_from_json(logger, force_reload=True) == {}
