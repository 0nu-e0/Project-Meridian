"""
Tests for the data layer: safe file handling, model round trips, and the
cleanup done when a project is deleted.

Every test runs against a temporary data directory (see conftest.py).
"""
import json
import logging
import os
import sys
from datetime import datetime


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

logger = logging.getLogger("test_data_layer")


def write_raw(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


def read_raw(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ----------------------------------------------------------------- safe_io

def test_write_json_is_atomic_and_leaves_no_temp_files(tmp_path):
    from utils.safe_io import read_json, write_json
    path = str(tmp_path / "data.json")
    assert write_json(path, {"a": "ünïcode"})
    assert read_json(path) == {"a": "ünïcode"}
    assert os.listdir(tmp_path) == ["data.json"] or sorted(os.listdir(tmp_path)).count("data.json") == 1
    assert not [name for name in os.listdir(tmp_path) if name.endswith(".tmp")]


def test_corrupt_file_is_moved_aside_not_overwritten(tmp_path):
    from utils.safe_io import get_quarantined_files, read_json, write_json
    path = str(tmp_path / "data.json")
    with open(path, "w", encoding="utf-8") as f:
        f.write('{"truncated": ')

    seen = []
    from utils import safe_io
    safe_io.set_quarantine_handler(lambda original, backup: seen.append(backup))

    assert read_json(path) == {}
    (original, backup), = get_quarantined_files()
    assert original == path and seen == [backup]
    with open(backup, encoding="utf-8") as f:
        assert f.read() == '{"truncated": '

    # Saving afterwards starts a new file and leaves the backup alone
    assert write_json(path, {"new": 1})
    assert read_raw(path) == {"new": 1}
    with open(backup, encoding="utf-8") as f:
        assert f.read() == '{"truncated": '


def test_wrong_top_level_type_is_quarantined(tmp_path):
    from utils.safe_io import get_quarantined_files, read_json
    path = str(tmp_path / "data.json")
    write_raw(path, ["not", "a", "dict"])
    assert read_json(path) == {}
    assert len(get_quarantined_files()) == 1


def test_unreadable_file_blocks_writes(tmp_path, monkeypatch):
    from utils import safe_io
    path = str(tmp_path / "data.json")
    write_raw(path, {"keep": True})

    real_open = open
    def locked_open(file, mode="r", *args, **kwargs):
        if file == path and "r" in mode:
            raise PermissionError("locked")
        return real_open(file, mode, *args, **kwargs)
    monkeypatch.setattr("builtins.open", locked_open)

    assert safe_io.read_json(path) == {}
    assert safe_io.write_json(path, {}) is False
    monkeypatch.undo()
    assert read_raw(path) == {"keep": True}


# ----------------------------------------------------------------- tasks

def make_full_task():
    from models.task import Task, TaskPriority, TaskStatus, TimeLog, TaskEntry, Attachment
    task = Task(title="Full task", description="desc", category="My Custom Category")
    task.status = TaskStatus.IN_PROGRESS
    task.priority = TaskPriority.HIGH
    task.due_date = datetime(2026, 1, 2, 3, 4, 5)
    task.start_date = datetime(2025, 12, 1, 8, 0, 0)
    task.percentage_complete = 40
    task.estimated_hours = 3.5
    task.story_points = 5
    task.assignee = "alex"
    task.dependencies = {"other-task-id"}
    task.collaborators = {"alice", "bob"}
    task.tags = {"x"}
    task.custom_fields = {"k": "v"}
    task.checklist = [{"text": "one", "checked": True}, {"text": "two", "checked": False}]
    task.visible_sections = {"attachments": False}
    log = TimeLog(1.5, "alex", "work")
    log.timestamp = datetime(2025, 12, 2, 9, 0, 0)
    task.time_logs = [log]
    entry = TaskEntry("a comment", user_id="alex")
    entry.timestamp = datetime(2025, 12, 3, 10, 30)
    task.entries = [entry]
    attachment = Attachment("C:/docs/spec.pdf", "alex")
    attachment.upload_date = datetime(2025, 12, 4, 11, 15)
    task.attachments = [attachment]
    return task


def test_task_round_trip_keeps_every_field():
    from utils.tasks_io import load_tasks_from_json, save_task_to_json
    task = make_full_task()
    assert save_task_to_json(task, logger)

    loaded = load_tasks_from_json(logger)[task.id]
    assert loaded.title == task.title
    assert loaded.category == "My Custom Category"
    assert loaded.status == task.status and loaded.priority == task.priority
    assert loaded.due_date == task.due_date and loaded.start_date == task.start_date
    assert loaded.percentage_complete == 40 and loaded.estimated_hours == 3.5
    assert loaded.story_points == 5
    assert loaded.assignee == "alex"
    assert loaded.dependencies == {"other-task-id"}
    assert loaded.collaborators == {"alice", "bob"}
    assert loaded.tags == {"x"} and loaded.custom_fields == {"k": "v"}
    assert loaded.checklist == task.checklist
    assert loaded.visible_sections == {"attachments": False}
    assert [(l.hours, l.timestamp) for l in loaded.time_logs] == [(1.5, datetime(2025, 12, 2, 9, 0, 0))]
    assert [(e.content, e.timestamp) for e in loaded.entries] == [("a comment", datetime(2025, 12, 3, 10, 30))]
    assert [(a.path_or_url, a.upload_date) for a in loaded.attachments] == [("C:/docs/spec.pdf", datetime(2025, 12, 4, 11, 15))]


def test_completed_task_is_archived_but_keeps_its_category():
    from models.task import TaskStatus
    from utils.tasks_io import load_tasks_from_json, save_task_to_json
    task = make_full_task()
    task.status = TaskStatus.COMPLETED
    save_task_to_json(task, logger)
    loaded = load_tasks_from_json(logger)[task.id]
    assert loaded.archived and loaded.category == "My Custom Category"

    # Reopening it unarchives it, still in its own category
    loaded.status = TaskStatus.IN_PROGRESS
    save_task_to_json(loaded, logger)
    reopened = load_tasks_from_json(logger)[task.id]
    assert not reopened.archived and reopened.category == "My Custom Category"


def test_old_files_without_archived_flag(isolated_data_dir):
    from models.task import TaskCategory
    from utils.tasks_io import load_tasks_from_json
    write_raw(isolated_data_dir.tasks_file, {
        "a": {"id": "a", "title": "Old archived", "category": "Archived", "status": "COMPLETED"},
        "b": {"id": "b", "title": "Old completed", "category": "Bug", "status": "COMPLETED"},
        "c": {"id": "c", "title": "Active", "category": "Bug", "status": "IN_PROGRESS"},
    })
    tasks = load_tasks_from_json(logger)
    assert tasks["a"].archived and tasks["a"].category == TaskCategory.ARCHIVED
    assert tasks["b"].archived and tasks["b"].category == TaskCategory.BUG
    assert not tasks["c"].archived


def test_legacy_task_formats_still_load(isolated_data_dir):
    from utils.tasks_io import load_tasks_from_json
    write_raw(isolated_data_dir.tasks_file, {
        "Legacy title key": {
            "title": "Legacy title key",
            "status": "In Progress",
            "percentage_complete": "50%",
            "team_members": ["carol"],
            "checklist": [{"text": "old", "completed": True}, "plain string"],
            "category": "Bug",
        }
    })
    tasks = load_tasks_from_json(logger)
    task, = tasks.values()
    assert task.id == "Legacy title key"  # the file key, so re-saving doesn't duplicate it
    assert task.percentage_complete == 50
    assert task.collaborators == {"carol"}
    assert task.checklist == [{"text": "old", "checked": True}, {"text": "plain string", "checked": False}]


def test_one_bad_task_does_not_hide_the_rest_and_survives_saves(isolated_data_dir):
    from models.task import Task
    from utils.tasks_io import load_tasks_from_json, save_task_to_json
    good = Task(title="Good")
    write_raw(isolated_data_dir.tasks_file, {
        good.id: {**good.to_dict()},
        "bad": "this record is not a dict",
    })
    tasks = load_tasks_from_json(logger)
    assert list(tasks) == [good.id]

    save_task_to_json(Task(title="Another"), logger)
    assert read_raw(isolated_data_dir.tasks_file)["bad"] == "this record is not a dict"


def test_unknown_status_and_bad_date_do_not_drop_the_task(isolated_data_dir):
    from models.task import TaskStatus
    from utils.tasks_io import load_tasks_from_json
    write_raw(isolated_data_dir.tasks_file, {
        "t1": {"id": "t1", "title": "T", "status": "Mystery", "due_date": "not a date"}
    })
    task = load_tasks_from_json(logger)["t1"]
    assert task.status == TaskStatus.NOT_STARTED and task.due_date is None


def test_delete_task():
    from models.task import Task
    from utils.tasks_io import delete_task_from_json, load_tasks_from_json, save_task_to_json
    a, b = Task(title="A"), Task(title="B")
    save_task_to_json(a, logger)
    save_task_to_json(b, logger)
    assert delete_task_from_json(a.id, logger)
    assert list(load_tasks_from_json(logger)) == [b.id]
    assert delete_task_from_json(a.id, logger) is False


def test_delete_task_removes_references_to_it(isolated_data_dir):
    from models.task import Task
    from utils.projects_io import create_phase, create_project, load_phases_from_json, move_task_to_phase
    from utils.tasks_io import delete_task_from_json, load_tasks_from_json, save_task_to_json
    doomed, dependent = Task(title="Doomed"), Task(title="Dependent")
    save_task_to_json(doomed, logger)
    dependent.dependencies = {doomed.id, "something-else"}
    save_task_to_json(dependent, logger)

    project = create_project("P", logger=logger)
    phase = create_phase(project.id, "Phase", logger=logger)
    move_task_to_phase(doomed.id, phase.id, logger)

    schedule_path = os.path.join(isolated_data_dir.data_dir, "scheduled_tasks.json")
    write_raw(schedule_path, {"s1": {"task_id": doomed.id, "title": "Doomed", "date": "2026-01-05"},
                              "s2": {"task_id": dependent.id, "title": "Dependent", "date": "2026-01-06"}})

    assert delete_task_from_json(doomed.id, logger)
    assert load_tasks_from_json(logger)[dependent.id].dependencies == {"something-else"}
    assert load_phases_from_json(logger)[phase.id].task_ids == []
    assert list(read_raw(schedule_path)) == ["s2"]


def test_data_manager_sees_saves_made_elsewhere():
    from models.task import Task
    from utils.data_manager import DataManager
    from utils.tasks_io import save_task_to_json
    manager = DataManager(logger)
    assert manager.get_tasks() == {}

    task = Task(title="Saved by another screen")
    save_task_to_json(task, logger)
    assert task.id in manager.get_tasks()

    manager.delete_task(task.id)
    assert manager.get_tasks() == {}


# ----------------------------------------------------------------- projects and phases

def test_corrupt_projects_file_is_not_wiped_by_create_project(isolated_data_dir):
    from utils.projects_io import create_project
    with open(isolated_data_dir.projects_file, "w", encoding="utf-8") as f:
        f.write('{"half written')

    create_project("New", logger=logger)

    backups = [name for name in os.listdir(isolated_data_dir.data_dir) if ".corrupt-" in name]
    assert len(backups) == 1
    with open(os.path.join(isolated_data_dir.data_dir, backups[0]), encoding="utf-8") as f:
        assert f.read() == '{"half written'


def test_bad_project_record_survives_create_project(isolated_data_dir):
    from utils.projects_io import create_project, load_projects_from_json
    write_raw(isolated_data_dir.projects_file, {"broken": {"title": "missing id and dates"}})
    assert load_projects_from_json(logger) == {}

    project = create_project("New", logger=logger)
    raw = read_raw(isolated_data_dir.projects_file)
    assert raw["broken"] == {"title": "missing id and dates"}
    assert project.id in raw


def test_phase_membership_lives_on_the_task(isolated_data_dir):
    from models.task import Task
    from utils.projects_io import (create_phase, create_project, load_phases_from_json,
                                   move_task_to_phase, remove_task_from_phase)
    from utils.tasks_io import save_task_to_json
    project = create_project("P", logger=logger)
    first, second = create_phase(project.id, "One", logger=logger), create_phase(project.id, "Two", logger=logger)
    task = Task(title="T")
    save_task_to_json(task, logger)

    move_task_to_phase(task.id, first.id, logger)
    move_task_to_phase(task.id, second.id, logger)
    phases = load_phases_from_json(logger)
    assert phases[first.id].task_ids == [] and phases[second.id].task_ids == [task.id]
    assert "task_ids" not in read_raw(isolated_data_dir.phases_file)[second.id]

    remove_task_from_phase(second.id, task.id, logger)
    assert load_phases_from_json(logger)[second.id].task_ids == []


def test_reconcile_moves_old_phase_lists_onto_tasks(isolated_data_dir):
    from models.task import Task
    from utils.projects_io import create_project, load_phases_from_json, reconcile_phase_membership
    from utils.tasks_io import load_tasks_from_json, save_task_to_json
    project = create_project("P", logger=logger)
    only_on_phase, already_elsewhere = Task(title="Only listed on phase"), Task(title="Points at phase two")
    already_elsewhere.phase_id = "phase-two"
    for task in (only_on_phase, already_elsewhere):
        save_task_to_json(task, logger)

    write_raw(isolated_data_dir.phases_file, {
        "phase-one": {"id": "phase-one", "project_id": project.id, "name": "One",
                      "task_ids": [only_on_phase.id, already_elsewhere.id, "missing-task"]},
        "phase-two": {"id": "phase-two", "project_id": project.id, "name": "Two", "task_ids": []},
    })

    assert reconcile_phase_membership(logger) == 1
    tasks = load_tasks_from_json(logger)
    assert tasks[only_on_phase.id].phase_id == "phase-one" and tasks[only_on_phase.id].project_id == project.id
    assert tasks[already_elsewhere.id].phase_id == "phase-two"
    assert all("task_ids" not in raw for raw in read_raw(isolated_data_dir.phases_file).values())
    assert load_phases_from_json(logger)["phase-one"].task_ids == [only_on_phase.id]
    assert reconcile_phase_membership(logger) == 0


def test_category_groups_are_created_for_every_category_in_use():
    from models.task import Task, TaskStatus
    from utils.dashboard_config import DashboardConfigManager
    from utils.project_dashboard_sync import ensure_category_groups_exist
    bug, custom, done = Task(title="b", category="Bug"), Task(title="c", category="Widgets"), Task(title="d", category="Bug")
    done.status = TaskStatus.COMPLETED
    done.update_archived()

    assert ensure_category_groups_exist([bug, custom, done], logger) == 3
    categories = sorted(g.filter.category[0] for g in DashboardConfigManager.get_all_grid_layouts())
    assert categories == ["Archived", "Bug", "Widgets"]

    # Nothing new the second time, and nothing at all for an empty view
    assert ensure_category_groups_exist([bug, custom, done], logger) == 0
    assert ensure_category_groups_exist([], logger) == 0


def test_project_and_phase_round_trip():
    from models.project import ProjectStatus
    from utils.projects_io import create_phase, create_project, load_phases_from_json, load_projects_from_json
    project = create_project("P", description="d", status=ProjectStatus.ACTIVE, logger=logger)
    phase = create_phase(project.id, "Phase 1", logger=logger)

    loaded = load_projects_from_json(logger)[project.id]
    assert loaded.title == "P" and loaded.status == ProjectStatus.ACTIVE
    assert loaded.phases == [phase.id]
    assert load_phases_from_json(logger)[phase.id].name == "Phase 1"


def test_delete_project_cleans_up_everything_it_owns():
    from models.task import Task
    from models.gantt_item import GanttChart
    from utils.dashboard_config import DashboardConfigManager
    from utils.gantt_io import load_gantt_chart_for_project, save_gantt_chart
    from utils.mindmap_io import create_mindmap, load_mindmaps_from_json
    from utils.project_dashboard_sync import ensure_project_groups_exist
    from utils.projects_io import (create_phase, create_project, delete_project, load_phases_from_json,
                                   load_scheduled_projects, move_task_to_phase, schedule_project)
    from utils.tasks_io import load_tasks_from_json, save_task_to_json

    project = create_project("Doomed", logger=logger)
    keeper = create_project("Keeper", logger=logger)
    phase = create_phase(project.id, "Phase", logger=logger)

    in_phase, loose, unrelated = Task(title="In phase"), Task(title="Loose", project_id=project.id), Task(title="Other")
    for task in (in_phase, loose, unrelated):
        save_task_to_json(task, logger)
    move_task_to_phase(in_phase.id, phase.id, logger)

    schedule_project(project.id, "2026-01-05", logger)
    kept_schedule = schedule_project(keeper.id, "2026-01-06", logger)
    save_gantt_chart(GanttChart(project.id), logger)
    mindmap = create_mindmap("Map", project_id=project.id, logger=logger)
    ensure_project_groups_exist(logger)
    assert any(getattr(g.filter, "project_id", None) == project.id for g in DashboardConfigManager.get_all_grid_layouts())

    assert delete_project(project.id, logger)

    tasks = load_tasks_from_json(logger)
    assert tasks[in_phase.id].project_id is None and tasks[in_phase.id].phase_id is None
    assert tasks[loose.id].project_id is None
    assert unrelated.id in tasks
    assert phase.id not in load_phases_from_json(logger)
    assert list(load_scheduled_projects(logger)) == [kept_schedule]
    assert load_gantt_chart_for_project(project.id, logger) is None
    assert load_mindmaps_from_json(logger)[mindmap.id].project_id is None
    grids = DashboardConfigManager.get_all_grid_layouts()
    assert not any(getattr(g.filter, "project_id", None) == project.id for g in grids)
    assert any(getattr(g.filter, "project_id", None) == keeper.id for g in grids)


# ----------------------------------------------------------------- other stores

def test_gantt_round_trip_and_bad_chart_is_kept():
    from models.gantt_item import GanttChart
    from utils.gantt_io import _get_gantt_file_path, load_gantt_charts_from_json, save_gantt_chart
    write_raw(_get_gantt_file_path(), {"charts": [{"project_id": "broken", "items": "not a list"}]})

    save_gantt_chart(GanttChart("p1"), logger)
    assert "p1" in load_gantt_charts_from_json(logger)
    project_ids = [chart.get("project_id") for chart in read_raw(_get_gantt_file_path())["charts"]]
    assert sorted(project_ids) == ["broken", "p1"]


def test_mindmap_round_trip_and_bad_mindmap_is_kept():
    from utils.mindmap_io import create_mindmap, get_mindmaps_file, load_mindmaps_from_json
    write_raw(str(get_mindmaps_file()), {"broken": "not a dict"})

    mindmap = create_mindmap("Map", nodes=[{"id": "n1"}], connections=[{"from": "n1", "to": "n2"}], logger=logger)
    loaded = load_mindmaps_from_json(logger)[mindmap.id]
    assert loaded.nodes == [{"id": "n1"}] and loaded.connections == [{"from": "n1", "to": "n2"}]
    assert read_raw(str(get_mindmaps_file()))["broken"] == "not a dict"


def test_notes_round_trip_and_delete():
    from models.note import Note
    from utils.notes_io import delete_note_from_json, load_notes_from_json, save_note_to_json
    note = Note(title="N", content="body ✓")
    assert save_note_to_json(note, logger)
    assert load_notes_from_json(logger)[note.id]["content"] == "body ✓"
    assert delete_note_from_json(note.id, logger)
    assert load_notes_from_json(logger) == {}


def test_corrupt_dashboard_config_is_not_wiped(isolated_data_dir):
    from utils.dashboard_config import DashboardConfigManager
    from utils.project_dashboard_sync import ensure_project_groups_exist
    from utils.projects_io import create_project
    config_dir = os.path.join(isolated_data_dir.app_data_dir, "config")
    os.makedirs(config_dir)
    config_path = os.path.join(config_dir, "app_config.yaml")
    with open(config_path, "w", encoding="utf-8") as f:
        f.write("dashboard: [unclosed")

    create_project("P", logger=logger)
    ensure_project_groups_exist(logger)

    backups = [name for name in os.listdir(config_dir) if ".corrupt-" in name]
    assert len(backups) == 1
    assert len(DashboardConfigManager.get_all_grid_layouts()) == 1
