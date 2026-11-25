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
# File: projects_io.py
# Description: Storage utilities for projects and phases
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

import os
import json
import logging
from typing import Dict, Optional
from datetime import datetime
from uuid import uuid4
from utils.app_config import AppConfig
from utils.safe_io import parse_records, read_json, with_unparsed_records, write_json
from models.project import Project, ProjectStatus
from models.phase import Phase
from models.task import TaskPriority


def load_projects_from_json(logger) -> Dict[str, Project]:
    """
    Load projects from JSON file into Project objects

    Returns:
        dict: Dictionary with project IDs as keys and Project objects as values
    """
    json_file_path = AppConfig().projects_file

    if not os.path.exists(json_file_path):
        logger.debug(f"No projects file yet at: {json_file_path}")
        return {}

    projects_data = read_json(json_file_path, logger)
    return parse_records(json_file_path, projects_data, lambda key, raw: Project.from_dict(raw), logger)


def save_projects_to_json(projects: Dict[str, Project], logger) -> bool:
    """
    Save projects dictionary to JSON file

    Args:
        projects: Dictionary of Project objects
        logger: Logger instance

    Returns:
        bool: True if successful, False otherwise
    """
    json_file_path = AppConfig().projects_file
    logger.info(f"Attempting to save {len(projects)} projects to: {json_file_path}")

    projects_data = {project_id: project.to_dict() for project_id, project in projects.items()}
    if not write_json(json_file_path, with_unparsed_records(json_file_path, projects_data), logger):
        return False

    logger.info(f"Successfully saved projects to {json_file_path}")
    return True


def load_phases_from_json(logger) -> Dict[str, Phase]:
    """
    Load phases from JSON file into Phase objects

    Returns:
        dict: Dictionary with phase IDs as keys and Phase objects as values
    """
    json_file_path = AppConfig().phases_file

    if not os.path.exists(json_file_path):
        logger.debug(f"No phases file yet at: {json_file_path}")
        return {}

    phases_data = read_json(json_file_path, logger)
    return parse_records(json_file_path, phases_data, lambda key, raw: Phase.from_dict(raw), logger)


def save_phases_to_json(phases: Dict[str, Phase], logger) -> bool:
    """
    Save phases dictionary to JSON file

    Args:
        phases: Dictionary of Phase objects
        logger: Logger instance

    Returns:
        bool: True if successful, False otherwise
    """
    json_file_path = AppConfig().phases_file
    logger.info(f"Attempting to save {len(phases)} phases to: {json_file_path}")

    phases_data = {phase_id: phase.to_dict() for phase_id, phase in phases.items()}
    if not write_json(json_file_path, with_unparsed_records(json_file_path, phases_data), logger):
        return False

    logger.info(f"Successfully saved phases to {json_file_path}")
    return True


def reconcile_phase_membership(logger) -> int:
    """
    Older files recorded phase membership in both phase.task_ids and task.phase_id,
    and the two could disagree. Membership now lives only on the task. This copies
    any membership recorded only on the phase onto its tasks, then drops the old
    lists from the phases file. Safe to run on every start.

    Returns:
        int: Number of tasks updated
    """
    from utils.tasks_io import load_tasks_from_json, save_task_to_json

    phases = load_phases_from_json(logger)
    legacy_phases = [phase for phase in phases.values() if phase._legacy_task_ids]
    if not legacy_phases:
        return 0

    tasks = load_tasks_from_json(logger)
    updated = 0
    for phase in legacy_phases:
        for task_id in phase._legacy_task_ids:
            task = tasks.get(task_id)
            # A task that already points at a real phase keeps it
            if task is None or task.phase_id in phases:
                continue
            task.phase_id = phase.id
            task.project_id = phase.project_id
            save_task_to_json(task, logger)
            updated += 1
        phase._legacy_task_ids = []

    save_phases_to_json(phases, logger)
    logger.info(f"Moved phase membership onto tasks: {updated} tasks updated")
    return updated


def save_project_fields(project: Project, fields, logger) -> bool:
    """
    Save only the named fields of project onto the copy on disk.

    Screens keep their own Project object while open. Saving that whole object
    would overwrite anything changed elsewhere in the meantime (a new phase, a
    linked mindmap), so only the fields actually edited are written.
    """
    projects = load_projects_from_json(logger)
    stored = projects.get(project.id)
    if stored is None:
        logger.warning(f"Project {project.id} not found")
        return False
    for field in fields:
        setattr(stored, field, getattr(project, field))
    return save_projects_to_json(projects, logger)


def save_phase_fields(phase: Phase, fields, logger) -> bool:
    """Save only the named fields of phase onto the copy on disk (see save_project_fields)"""
    phases = load_phases_from_json(logger)
    stored = phases.get(phase.id)
    if stored is None:
        logger.warning(f"Phase {phase.id} not found")
        return False
    for field in fields:
        setattr(stored, field, getattr(phase, field))
    return save_phases_to_json(phases, logger)


def set_current_phase(project_id: str, phase_id: str, logger) -> bool:
    """Make phase_id the project's current phase, and the only phase marked current"""
    phases = load_phases_from_json(logger)
    for phase in phases.values():
        if phase.project_id == project_id:
            phase.is_current = phase.id == phase_id
    if not save_phases_to_json(phases, logger):
        return False

    projects = load_projects_from_json(logger)
    if project_id not in projects:
        return False
    projects[project_id].current_phase_id = phase_id
    return save_projects_to_json(projects, logger)


def renumber_phases(project_id: str, phases: Dict[str, Phase]):
    """Give a project's phases the orders 0, 1, 2... keeping their current sequence"""
    project_phases = sorted((p for p in phases.values() if p.project_id == project_id), key=lambda p: p.order)
    for index, phase in enumerate(project_phases):
        phase.order = index


def create_project(
    title: str,
    description: str = "",
    status: ProjectStatus = ProjectStatus.PLANNING,
    priority: TaskPriority = TaskPriority.MEDIUM,
    color: str = "#3498db",
    logger = None,
    start_date: Optional[datetime] = None,
    target_completion: Optional[datetime] = None
) -> Project:
    """
    Create a new project and save it

    Args:
        title: Project title
        description: Project description
        status: Project status
        priority: Project priority
        color: Project color (hex)
        logger: Logger instance

    Returns:
        Project: The created project
    """
    project = Project(
        title=title,
        description=description,
        status=status,
        priority=priority,
        color=color
    )
    project.start_date = start_date
    project.target_completion = target_completion

    if logger:
        logger.info(f"Created new project: {title} (ID: {project.id})")

    # Load existing projects and add the new one
    projects = load_projects_from_json(logger) if logger else {}
    projects[project.id] = project

    # Save back to file
    if logger:
        save_projects_to_json(projects, logger)

    return project


def create_phase(
    project_id: str,
    name: str,
    description: str = "",
    order: int = 0,
    logger = None
) -> Phase:
    """
    Create a new phase and associate it with a project

    Args:
        project_id: ID of the parent project
        name: Phase name
        description: Phase description
        order: Phase order in project
        logger: Logger instance

    Returns:
        Phase: The created phase
    """
    phase = Phase(
        project_id=project_id,
        name=name,
        description=description,
        order=order
    )

    if logger:
        logger.info(f"Created new phase: {name} (ID: {phase.id}) for project {project_id}")

        # Load phases and add the new one
        phases = load_phases_from_json(logger)
        phases[phase.id] = phase
        save_phases_to_json(phases, logger)

        # Update project to include this phase
        projects = load_projects_from_json(logger)
        if project_id in projects:
            project = projects[project_id]
            if phase.id not in project.phases:
                project.phases.append(phase.id)
                save_projects_to_json(projects, logger)

    return phase


def delete_project(project_id: str, logger) -> bool:
    """
    Delete a project and everything that belongs only to it: its phases, its
    schedule entries, its Gantt chart, and its dashboard group. Its tasks are
    kept but unlinked from the project, and a linked mindmap is unlinked.

    Args:
        project_id: ID of project to delete
        logger: Logger instance

    Returns:
        bool: True if successful, False otherwise
    """
    from utils.tasks_io import load_tasks_from_json, save_task_to_json

    try:
        projects = load_projects_from_json(logger)

        if project_id not in projects:
            logger.warning(f"Project {project_id} not found")
            return False

        project = projects[project_id]

        # Unlink every task in the project, including any not listed in a phase
        phases = load_phases_from_json(logger)
        project_phase_ids = set(project.phases) | {
            phase_id for phase_id, phase in phases.items() if phase.project_id == project_id
        }
        phase_task_ids = {task_id for phase_id in project_phase_ids if phase_id in phases
                          for task_id in phases[phase_id].task_ids}

        for task in list(load_tasks_from_json(logger).values()):
            if task.project_id == project_id or task.id in phase_task_ids:
                task.phase_id = None
                task.project_id = None
                save_task_to_json(task, logger)

        for phase_id in project_phase_ids:
            phases.pop(phase_id, None)
        save_phases_to_json(phases, logger)

        del projects[project_id]
        if not save_projects_to_json(projects, logger):
            return False

        # Remove what only made sense for this project. A failure here leaves a
        # harmless orphan, so log it rather than reporting the delete as failed.
        try:
            scheduled = load_scheduled_projects(logger)
            remaining = {sid: entry for sid, entry in scheduled.items() if entry.get('project_id') != project_id}
            if len(remaining) != len(scheduled):
                save_scheduled_projects(remaining, logger)
        except Exception as e:
            logger.error(f"Error removing schedule entries for project {project_id}: {e}")

        try:
            from utils.gantt_io import delete_gantt_chart, load_gantt_chart_for_project
            if load_gantt_chart_for_project(project_id, logger):
                delete_gantt_chart(project_id, logger)
        except Exception as e:
            logger.error(f"Error removing Gantt chart for project {project_id}: {e}")

        try:
            from utils.mindmap_io import load_mindmaps_from_json, save_mindmaps_to_json
            mindmaps = load_mindmaps_from_json(logger)
            linked = [mindmap for mindmap in mindmaps.values() if mindmap.project_id == project_id]
            for mindmap in linked:
                mindmap.project_id = None
            if linked:
                save_mindmaps_to_json(mindmaps, logger)
        except Exception as e:
            logger.error(f"Error unlinking mindmaps from project {project_id}: {e}")

        try:
            from utils.project_dashboard_sync import remove_project_grid_layout
            remove_project_grid_layout(project_id, logger)
        except Exception as e:
            logger.error(f"Error removing dashboard group for project {project_id}: {e}")

        logger.info(f"Deleted project {project_id}")
        return True

    except Exception as e:
        logger.error(f"Error deleting project: {e}")
        return False


def delete_phase(phase_id: str, logger) -> bool:
    """
    Delete a phase and update associated tasks and project

    Args:
        phase_id: ID of phase to delete
        logger: Logger instance

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Load phases
        phases = load_phases_from_json(logger)

        if phase_id not in phases:
            logger.warning(f"Phase {phase_id} not found")
            return False

        phase = phases[phase_id]

        # Update tasks to remove phase_id
        from utils.tasks_io import load_tasks_from_json, save_task_to_json
        tasks = load_tasks_from_json(logger)

        for task_id in phase.task_ids:
            if task_id in tasks:
                task = tasks[task_id]
                task.phase_id = None
                save_task_to_json(task, logger)

        # Update project to remove phase reference
        projects = load_projects_from_json(logger)
        if phase.project_id in projects:
            project = projects[phase.project_id]
            if phase_id in project.phases:
                project.phases.remove(phase_id)
            if project.current_phase_id == phase_id:
                project.current_phase_id = None
            save_projects_to_json(projects, logger)

        # Delete the phase, then close the gap it leaves in the ordering
        del phases[phase_id]
        renumber_phases(phase.project_id, phases)
        save_phases_to_json(phases, logger)

        logger.info(f"Deleted phase {phase_id}")
        return True

    except Exception as e:
        logger.error(f"Error deleting phase: {e}")
        return False


def move_task_to_phase(task_id: str, phase_id: Optional[str], logger) -> bool:
    """
    Move a task to a different phase (or remove from phase if phase_id is None)

    Args:
        task_id: ID of task to move
        phase_id: ID of target phase (None to remove from phase)
        logger: Logger instance

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        from utils.tasks_io import load_tasks_from_json, save_task_to_json

        tasks = load_tasks_from_json(logger)

        if task_id not in tasks:
            logger.warning(f"Task {task_id} not found")
            return False

        task = tasks[task_id]

        # Membership lives on the task, so only the task needs saving
        if phase_id:
            phases = load_phases_from_json(logger)
            if phase_id not in phases:
                logger.warning(f"Phase {phase_id} not found")
                return False

            task.phase_id = phase_id
            task.project_id = phases[phase_id].project_id
        else:
            task.phase_id = None

        if not save_task_to_json(task, logger):
            return False

        logger.info(f"Moved task {task_id} to phase {phase_id}")
        return True

    except Exception as e:
        logger.error(f"Error moving task to phase: {e}")
        return False


def add_task_to_phase(phase_id: str, task_id: str, logger) -> bool:
    """
    Add an existing task to a phase

    Args:
        phase_id: ID of the phase
        task_id: ID of the task
        logger: Logger instance

    Returns:
        bool: True if successful, False otherwise
    """
    return move_task_to_phase(task_id, phase_id, logger)


def remove_task_from_phase(phase_id: str, task_id: str, logger) -> bool:
    """
    Remove a task from a phase (task still exists, just not in phase)

    Args:
        phase_id: ID of the phase
        task_id: ID of the task
        logger: Logger instance

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        from utils.tasks_io import load_tasks_from_json, save_task_to_json

        tasks = load_tasks_from_json(logger)

        if task_id not in tasks:
            logger.warning(f"Task {task_id} not found")
            return False

        task = tasks[task_id]

        # Only proceed if task is actually in this phase
        if task.phase_id != phase_id:
            logger.warning(f"Task {task_id} is not in phase {phase_id}")
            return False

        task.phase_id = None
        if not save_task_to_json(task, logger):
            return False

        logger.info(f"Removed task {task_id} from phase {phase_id}")
        return True

    except Exception as e:
        logger.error(f"Error removing task from phase: {e}")
        return False


# ============================================================================
# Scheduled Projects Storage
# ============================================================================

def load_scheduled_projects(logger):
    """
    Load scheduled projects from JSON file

    Returns:
        dict: Dictionary with schedule_id as keys and scheduled project data as values
    """
    json_file_path = os.path.join(AppConfig().data_dir, "scheduled_projects.json")
    return read_json(json_file_path, logger)


def save_scheduled_projects(scheduled_projects, logger):
    """
    Save scheduled projects to JSON file

    Args:
        scheduled_projects: Dictionary of scheduled projects
        logger: Logger instance

    Returns:
        bool: True if successful, False otherwise
    """
    json_file_path = os.path.join(AppConfig().data_dir, "scheduled_projects.json")

    if not write_json(json_file_path, scheduled_projects, logger, indent=4, default=str):
        return False

    logger.info(f"Successfully saved {len(scheduled_projects)} scheduled projects to {json_file_path}")
    return True


def schedule_project(project_id: str, scheduled_date: str, logger):
    """
    Schedule a project for a specific date

    Args:
        project_id: ID of project to schedule
        scheduled_date: Date string in format YYYY-MM-DD
        logger: Logger instance

    Returns:
        str: schedule_id if successful, None otherwise
    """
    try:
        # Load existing scheduled projects
        scheduled_projects = load_scheduled_projects(logger)

        # Load project to get title
        projects = load_projects_from_json(logger)
        if project_id not in projects:
            logger.error(f"Project {project_id} not found")
            return None

        project = projects[project_id]

        # Scheduling the same project twice on one day would just show it twice
        for existing_id, entry in scheduled_projects.items():
            if entry.get('project_id') == project_id and entry.get('scheduled_date') == scheduled_date:
                logger.info(f"Project {project_id} is already scheduled for {scheduled_date}")
                return existing_id

        # Create schedule entry
        schedule_id = str(uuid4())
        scheduled_projects[schedule_id] = {
            'project_id': project_id,
            'title': project.title,
            'scheduled_date': scheduled_date,
            'schedule_id': schedule_id
        }

        # Save
        save_scheduled_projects(scheduled_projects, logger)

        logger.info(f"Scheduled project {project_id} for {scheduled_date}")
        return schedule_id

    except Exception as e:
        logger.error(f"Error scheduling project: {e}")
        return None


def move_scheduled_project(schedule_id: str, scheduled_date: str, logger) -> bool:
    """
    Move a scheduled project to another date (YYYY-MM-DD). If the project is
    already scheduled on that date, the moved entry is merged into it.

    Returns:
        bool: True if successful, False otherwise
    """
    scheduled_projects = load_scheduled_projects(logger)
    entry = scheduled_projects.get(schedule_id)
    if entry is None:
        logger.warning(f"Schedule {schedule_id} not found")
        return False

    duplicate = any(other_id != schedule_id and other.get('project_id') == entry.get('project_id')
                    and other.get('scheduled_date') == scheduled_date
                    for other_id, other in scheduled_projects.items())
    if duplicate:
        del scheduled_projects[schedule_id]
    else:
        entry['scheduled_date'] = scheduled_date

    return save_scheduled_projects(scheduled_projects, logger)


def unschedule_project(schedule_id: str, logger):
    """
    Remove a scheduled project

    Args:
        schedule_id: ID of schedule entry to remove
        logger: Logger instance

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        scheduled_projects = load_scheduled_projects(logger)

        if schedule_id in scheduled_projects:
            del scheduled_projects[schedule_id]
            save_scheduled_projects(scheduled_projects, logger)
            logger.info(f"Unscheduled project {schedule_id}")
            return True
        else:
            logger.warning(f"Schedule {schedule_id} not found")
            return False

    except Exception as e:
        logger.error(f"Error unscheduling project: {e}")
        return False


def export_project_to_json(project_id: str, export_path: str, logger: logging.Logger) -> bool:
    """
    Export a project with all its phases and tasks to a JSON file.

    Args:
        project_id: ID of the project to export
        export_path: Path to save the export file
        logger: Logger instance

    Returns:
        True if successful, False otherwise
    """
    try:
        # Load project
        projects = load_projects_from_json(logger)
        if project_id not in projects:
            logger.error(f"Project {project_id} not found")
            return False

        project = projects[project_id]

        # Load phases
        all_phases = load_phases_from_json(logger)
        project_phases = []
        for phase_id in project.phases:
            if phase_id in all_phases:
                project_phases.append(all_phases[phase_id].to_dict())

        # Load tasks
        from utils.tasks_io import load_tasks_from_json
        all_tasks = load_tasks_from_json(logger)
        project_tasks = []
        for task in all_tasks.values():
            if task.project_id == project_id:
                project_tasks.append(task.to_dict())

        # Create export data structure
        export_data = {
            "project": project.to_dict(),
            "phases": project_phases,
            "tasks": project_tasks,
            "export_date": datetime.now().isoformat(),
            "version": "1.0"
        }

        # Write to file
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Exported project '{project.title}' to {export_path}")
        return True

    except Exception as e:
        logger.error(f"Error exporting project: {e}")
        return False


def import_project_from_json(import_path: str, logger: logging.Logger) -> Optional[str]:
    """
    Import a project from a JSON file.

    Args:
        import_path: Path to the import file
        logger: Logger instance

    Returns:
        New project ID if successful, None otherwise
    """
    try:
        # Read import file
        with open(import_path, 'r', encoding='utf-8') as f:
            import_data = json.load(f)
        if not isinstance(import_data, dict):
            logger.error("Invalid import file format")
            return None

        # Validate format
        if "project" not in import_data or "phases" not in import_data:
            logger.error("Invalid import file format")
            return None

        # Generate new IDs to avoid conflicts
        old_to_new_project_id = {}
        old_to_new_phase_id = {}
        old_to_new_task_id = {}

        # Import project with new ID
        from models.project import Project
        project_data = import_data["project"]
        old_project_id = project_data["id"]
        new_project_id = str(uuid4())
        old_to_new_project_id[old_project_id] = new_project_id

        # Update project data
        project_data["id"] = new_project_id
        project_data["creation_date"] = datetime.now().isoformat()
        project_data["title"] = project_data["title"] + " (Imported)"
        project_data["phases"] = []  # Will update with new phase IDs

        project = Project.from_dict(project_data)

        # Import phases with new IDs
        phases = {}
        for phase_data in import_data["phases"]:
            old_phase_id = phase_data["id"]
            new_phase_id = str(uuid4())
            old_to_new_phase_id[old_phase_id] = new_phase_id

            phase_data["id"] = new_phase_id
            phase_data["project_id"] = new_project_id

            from models.phase import Phase
            phase = Phase.from_dict(phase_data)
            phase._legacy_task_ids = []  # Membership comes from each task's phase_id
            phases[new_phase_id] = phase
            project.phases.append(new_phase_id)

        # Import tasks with new IDs. Everything is read and checked before anything
        # is written, so a bad file can't leave half a project behind.
        from models.task import Task
        from utils.tasks_io import save_tasks_to_json
        tasks_data = import_data.get("tasks", [])
        for task_data in tasks_data:
            old_to_new_task_id[task_data["id"]] = str(uuid4())

        tasks = []
        for task_data in tasks_data:
            task_data["id"] = old_to_new_task_id[task_data["id"]]
            task_data["project_id"] = new_project_id

            # Point the task at its phase's new ID
            if task_data.get("phase_id") in old_to_new_phase_id:
                task_data["phase_id"] = old_to_new_phase_id[task_data["phase_id"]]
            else:
                task_data["phase_id"] = None

            # Dependencies between imported tasks follow them to their new IDs
            for field in ("dependencies", "blocked_by"):
                task_data[field] = [old_to_new_task_id.get(ref, ref) for ref in task_data.get(field, [])]

            tasks.append(Task.from_dict(task_data))

        # Save project and phases, then the tasks
        all_projects = load_projects_from_json(logger)
        all_projects[new_project_id] = project
        if not save_projects_to_json(all_projects, logger):
            return None

        all_phases = load_phases_from_json(logger)
        all_phases.update(phases)
        save_phases_to_json(all_phases, logger)

        if not save_tasks_to_json(tasks, logger):
            return None

        logger.info(f"Imported project '{project.title}' with ID {new_project_id}")
        return new_project_id

    except Exception as e:
        logger.error(f"Error importing project: {e}")
        return None
