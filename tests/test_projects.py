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

from PyQt5.QtWidgets import QApplication

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


def test_deleting_a_project_asks_and_can_be_undone(app, monkeypatch):
    from ui.project_files.project_detail_view import ProjectDetailView
    from utils.data_history import history
    from utils.projects_io import create_phase, create_project, load_phases_from_json, load_projects_from_json
    project = create_project("Keep Me", logger=logger)
    phase = create_phase(project.id, "Phase", logger=logger)
    view = ProjectDetailView(project.id, logger)
    went_back = []
    view.backClicked.connect(lambda: went_back.append(True))

    monkeypatch.setattr(dialogs, "confirm", lambda *a, **k: False)
    view.onDeleteProject()
    assert project.id in load_projects_from_json(logger) and not went_back

    monkeypatch.setattr(dialogs, "confirm", lambda *a, **k: True)
    view.onDeleteProject()
    assert project.id not in load_projects_from_json(logger) and went_back
    assert phase.id not in load_phases_from_json(logger)

    history().undo()
    assert project.id in load_projects_from_json(logger)
    assert phase.id in load_phases_from_json(logger)


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


# -- the screens ----------------------------------------------------------------

def shown_titles(screen):
    return [card.project.title for card in screen.project_cards]


def test_projects_screen_filters_and_says_why_it_is_empty(app):
    from models.project import ProjectStatus
    from ui.projects_screen import ProjectsScreen
    from utils.projects_io import create_project, load_projects_from_json, save_project_fields
    create_project("Garden", description="Plant the beds", status=ProjectStatus.ACTIVE, logger=logger)
    create_project("Kitchen", status=ProjectStatus.PLANNING, logger=logger)
    screen = ProjectsScreen(logger)
    assert sorted(shown_titles(screen)) == ["Garden", "Kitchen"]
    assert screen.empty_state_widget.isHidden()

    screen.search_box.setText("beds")  # matches the description
    assert shown_titles(screen) == ["Garden"]
    assert not screen.clear_button.isHidden()

    screen.status_filter.setCurrentIndex(screen.status_filter.findData("Planning"))
    assert shown_titles(screen) == []
    assert screen.empty_title.text() == "No projects match"

    screen.onClearFilters()
    assert sorted(shown_titles(screen)) == ["Garden", "Kitchen"]
    assert screen.clear_button.isHidden()

    # Archived projects are hidden until asked for
    for project in load_projects_from_json(logger).values():
        project.archived = True
        save_project_fields(project, ["archived"], logger)
    screen.loadProjects()
    assert shown_titles(screen) == []
    assert screen.empty_title.text() == "Every project is archived"
    screen.archived_checkbox.setChecked(True)
    assert sorted(shown_titles(screen)) == ["Garden", "Kitchen"]


def test_projects_can_be_sorted_by_due_date_and_name(app):
    from ui.projects_screen import ProjectsScreen
    from utils.projects_io import create_project
    create_project("B later", logger=logger, target_completion=datetime(2026, 12, 1))
    create_project("A no date", logger=logger)
    create_project("C sooner", logger=logger, target_completion=datetime(2026, 6, 1))
    screen = ProjectsScreen(logger)
    screen.sort_combo.setCurrentIndex(screen.sort_combo.findData("Due soonest"))
    assert shown_titles(screen) == ["C sooner", "B later", "A no date"]
    screen.sort_combo.setCurrentIndex(screen.sort_combo.findData("Name"))
    assert shown_titles(screen) == ["A no date", "B later", "C sooner"]


def test_cards_fill_as_many_columns_as_fit(app):
    from ui.projects_screen import ProjectsScreen
    from utils.projects_io import create_project
    for i in range(5):
        create_project(f"P{i}", logger=logger)
    screen = ProjectsScreen(logger)
    screen.resize(1400, 800)
    screen.show()
    app.processEvents()
    wide = screen._columns
    screen.resize(700, 800)
    app.processEvents()
    assert wide > screen._columns >= 1
    positions = {screen.grid_layout.getItemPosition(screen.grid_layout.indexOf(card))[:2]
                 for card in screen.project_cards}
    assert len(positions) == 5  # every card in its own cell, none left behind
    screen.close()


def test_editing_a_project_updates_its_page(app, monkeypatch):
    from ui.project_files import project_actions
    from ui.project_files.project_detail_view import ProjectDetailView
    from utils.projects_io import create_project, load_projects_from_json
    project = create_project("Old name", logger=logger, target_completion=datetime(2026, 6, 1))
    view = ProjectDetailView(project.id, logger)
    data = {"title": "New name", "description": "Now described", "status": project.status,
            "priority": project.priority, "color": "#e74c3c", "start_date": None, "target_completion": None}
    project_actions.apply_edit(view.project, data, logger)
    view.refresh()
    assert view.title_label.text() == "New name"
    stored = load_projects_from_json(logger)[project.id]
    assert stored.title == "New name" and stored.color == "#e74c3c"
    assert stored.target_completion is None  # a date can now be cleared


def test_project_dialog_checks_the_form(app):
    from ui.project_files.project_dialog import ProjectDialog
    dialog = ProjectDialog(mode="create", logger=logger)
    dialog._save()
    assert dialog.project_data is None and not dialog.errorLabel.isHidden()

    dialog.title_input.setText("Named")
    dialog.start_date_edit.setValue(datetime(2026, 5, 1))
    dialog.target_date_edit.setValue(datetime(2026, 4, 1))
    dialog._save()
    assert dialog.project_data is None and "before the start" in dialog.errorLabel.text()

    dialog.target_date_edit.check.setChecked(False)
    dialog.color_choice.setColor("#123456")  # a custom colour
    dialog._save()
    assert dialog.project_data["title"] == "Named"
    assert dialog.project_data["target_completion"] is None
    assert dialog.project_data["start_date"] == datetime(2026, 5, 1)
    assert dialog.project_data["color"] == "#123456"


def test_deleting_a_phase_can_be_undone(app):
    from ui.project_files.project_detail_view import ProjectDetailView
    from utils.data_history import history
    project, (one, two) = make_project_with_phases(["One", "Two"])
    view = ProjectDetailView(project.id, logger)
    view.phase_widgets[0].onDeletePhase()  # conftest answers Yes
    view.refresh()
    assert [w.phase.name for w in view.phase_widgets] == ["Two"]

    history().undo()
    view.refresh()
    assert [w.phase.name for w in view.phase_widgets] == ["One", "Two"]


def test_adding_a_task_to_a_phase(app):
    from models.task import TaskPriority, TaskStatus
    from ui.project_files.project_detail_view import ProjectDetailView
    from utils.tasks_io import load_tasks_from_json
    project, (phase,) = make_project_with_phases(["Build"])
    view = ProjectDetailView(project.id, logger)
    widget = view.phase_widgets[0]
    widget.onTaskSaved({"title": "Pour concrete", "description": "", "priority": TaskPriority.HIGH,
                        "status": TaskStatus.NOT_STARTED, "project_id": project.id, "phase_id": phase.id})
    assert [t.title for t in widget.tasks] == ["Pour concrete"]
    task = next(t for t in load_tasks_from_json(logger, force_reload=True).values() if t.title == "Pour concrete")
    assert task.phase_id == phase.id and task.project_id == project.id
    assert widget.progress_label.text() == "0/1 done"


def test_a_dragged_over_phase_goes_back_to_the_dark_style(app):
    from ui.project_files.project_detail_view import ProjectDetailView
    from ui.project_files.project_look import CARD_BACKGROUND
    project, _ = make_project_with_phases(["One"])
    view = ProjectDetailView(project.id, logger)
    widget = view.phase_widgets[0]
    widget.updateContainerStyle("#ffffff")
    widget.dragLeaveEvent(None)
    assert CARD_BACKGROUND in widget.container.styleSheet() and "dashed" not in widget.container.styleSheet()


def test_mind_map_buttons_go_both_ways(app):
    from ui.mindmap_screen import MindMapScreen
    from ui.project_files.project_detail_view import ProjectDetailView
    from utils.mindmap_io import create_mindmap
    from utils.projects_io import create_project, save_project_fields
    project = create_project("Linked", logger=logger)
    mindmap = create_mindmap("Map", project_id=project.id, logger=logger)
    project.mindmap_id = mindmap.id
    save_project_fields(project, ["mindmap_id"], logger)

    view = ProjectDetailView(project.id, logger)
    opened = []
    view.mindmapClicked.connect(opened.append)
    view.onViewMindmap()
    assert opened == [mindmap.id]

    screen = MindMapScreen(logger)
    screen.load_mindmap_by_id(mindmap.id)
    requested = []
    screen.projectRequested.connect(requested.append)
    screen.view_linked_project()
    assert requested == [project.id]
