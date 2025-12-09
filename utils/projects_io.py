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
from typing import Dict, Optional
from datetime import datetime
from utils.app_config import AppConfig
from models.project import Project, ProjectStatus
from models.phase import Phase
from models.task import TaskPriority


def load_projects_from_json(logger) -> Dict[str, Project]:
    """
    Load projects from JSON file into Project objects

    Returns:
        dict: Dictionary with project IDs as keys and Project objects as values
    """
    app_config = AppConfig()
    json_file_path = app_config.projects_file

    if not os.path.exists(json_file_path):
        logger.warning(f"Projects file not found at: {json_file_path}")
        return {}

    try:
        with open(json_file_path, 'r') as file:
            projects_data = json.load(file)

        logger.info(f"Successfully loaded {len(projects_data)} projects from {json_file_path}")

        # Convert each project data to Project object
        projects = {}
        for project_id, project_info in projects_data.items():
            project = Project.from_dict(project_info)
            projects[project_id] = project

        return projects

    except Exception as e:
        logger.error(f"Error loading projects from JSON: {e}")
        return {}


def save_projects_to_json(projects: Dict[str, Project], logger) -> bool:
    """
    Save projects dictionary to JSON file

    Args:
        projects: Dictionary of Project objects
        logger: Logger instance

    Returns:
        bool: True if successful, False otherwise
    """
    app_config = AppConfig()
    json_file_path = app_config.projects_file

    logger.info(f"Attempting to save {len(projects)} projects to: {json_file_path}")

    try:
        # Ensure the directory exists
        data_dir = os.path.dirname(json_file_path)
        if not os.path.exists(data_dir):
            logger.info(f"Creating directory: {data_dir}")
            os.makedirs(data_dir, exist_ok=True)

        # Convert projects to dictionary format
        projects_data = {}
        for project_id, project in projects.items():
            projects_data[project_id] = project.to_dict()

        # Write to file
        with open(json_file_path, 'w') as file:
            json.dump(projects_data, file, indent=2)

        logger.info(f"Successfully saved projects to {json_file_path}")
        return True

    except Exception as e:
        logger.error(f"Error saving projects to JSON: {e}")
        return False


def load_phases_from_json(logger) -> Dict[str, Phase]:
    """
    Load phases from JSON file into Phase objects

    Returns:
        dict: Dictionary with phase IDs as keys and Phase objects as values
    """
    app_config = AppConfig()
    json_file_path = app_config.phases_file

    if not os.path.exists(json_file_path):
        logger.warning(f"Phases file not found at: {json_file_path}")
        return {}

    try:
        with open(json_file_path, 'r') as file:
            phases_data = json.load(file)

        logger.info(f"Successfully loaded {len(phases_data)} phases from {json_file_path}")

        # Convert each phase data to Phase object
        phases = {}
        for phase_id, phase_info in phases_data.items():
            phase = Phase.from_dict(phase_info)
            phases[phase_id] = phase

        return phases

    except Exception as e:
        logger.error(f"Error loading phases from JSON: {e}")
        return {}


def save_phases_to_json(phases: Dict[str, Phase], logger) -> bool:
    """
    Save phases dictionary to JSON file

    Args:
        phases: Dictionary of Phase objects
        logger: Logger instance

    Returns:
        bool: True if successful, False otherwise
    """
    app_config = AppConfig()
    json_file_path = app_config.phases_file

    logger.info(f"Attempting to save {len(phases)} phases to: {json_file_path}")

    try:
        # Ensure the directory exists
        data_dir = os.path.dirname(json_file_path)
        if not os.path.exists(data_dir):
            logger.info(f"Creating directory: {data_dir}")
            os.makedirs(data_dir, exist_ok=True)

        # Convert phases to dictionary format
        phases_data = {}
        for phase_id, phase in phases.items():
            phases_data[phase_id] = phase.to_dict()

        # Write to file
        with open(json_file_path, 'w') as file:
            json.dump(phases_data, file, indent=2)

        logger.info(f"Successfully saved phases to {json_file_path}")
        return True

    except Exception as e:
        logger.error(f"Error saving phases to JSON: {e}")
        return False


def create_project(
    title: str,
    description: str = "",
    status: ProjectStatus = ProjectStatus.PLANNING,
    priority: TaskPriority = TaskPriority.MEDIUM,
    color: str = "#3498db",
    logger = None
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
    Delete a project and all its phases

    Args:
        project_id: ID of project to delete
        logger: Logger instance

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Load projects
        projects = load_projects_from_json(logger)

        if project_id not in projects:
            logger.warning(f"Project {project_id} not found")
            return False

        project = projects[project_id]

        # Delete all phases in this project
        phases = load_phases_from_json(logger)
        for phase_id in project.phases:
            if phase_id in phases:
                # Update tasks to remove phase_id
                from utils.tasks_io import load_tasks_from_json, save_task_to_json
                tasks = load_tasks_from_json(logger)
                phase = phases[phase_id]

                for task_id in phase.task_ids:
                    if task_id in tasks:
                        task = tasks[task_id]
                        task.phase_id = None
                        task.project_id = None
                        save_task_to_json(task, logger)

                # Remove phase
                del phases[phase_id]

        save_phases_to_json(phases, logger)

        # Delete the project
        del projects[project_id]
        save_projects_to_json(projects, logger)

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
                save_projects_to_json(projects, logger)

        # Delete the phase
        del phases[phase_id]
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
        old_phase_id = task.phase_id

        # Load phases
        phases = load_phases_from_json(logger)

        # Remove from old phase
        if old_phase_id and old_phase_id in phases:
            old_phase = phases[old_phase_id]
            if task_id in old_phase.task_ids:
                old_phase.task_ids.remove(task_id)

        # Add to new phase
        if phase_id:
            if phase_id not in phases:
                logger.warning(f"Phase {phase_id} not found")
                return False

            new_phase = phases[phase_id]
            if task_id not in new_phase.task_ids:
                new_phase.task_ids.append(task_id)

            # Update task's phase_id and project_id
            task.phase_id = phase_id
            task.project_id = new_phase.project_id
        else:
            # Remove from phase
            task.phase_id = None

        # Save everything
        save_phases_to_json(phases, logger)
        save_task_to_json(task, logger)

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

        # Load phases
        phases = load_phases_from_json(logger)

        if phase_id not in phases:
            logger.warning(f"Phase {phase_id} not found")
            return False

        phase = phases[phase_id]

        # Remove from phase's task list
        if task_id in phase.task_ids:
            phase.task_ids.remove(task_id)

        # Update task
        task.phase_id = None

        # Save everything
        save_phases_to_json(phases, logger)
        save_task_to_json(task, logger)

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
    from utils.app_config import AppConfig

    scheduled_projects = {}

    # Get the file path
    app_config = AppConfig()
    json_file_path = os.path.join(app_config.data_dir, "scheduled_projects.json")

    if not os.path.exists(json_file_path):
        logger.info(f"No scheduled projects file found at {json_file_path}, returning empty dict")
        return scheduled_projects

    try:
        with open(json_file_path, 'r') as file:
            data = json.load(file)

            for schedule_id, project_data in data.items():
                scheduled_projects[schedule_id] = project_data

        logger.info(f"Successfully loaded {len(scheduled_projects)} scheduled projects from {json_file_path}")
        return scheduled_projects

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error loading scheduled projects: {e}")
        return scheduled_projects
    except Exception as e:
        logger.error(f"Error loading scheduled projects: {e}")
        return scheduled_projects


def save_scheduled_projects(scheduled_projects, logger):
    """
    Save scheduled projects to JSON file

    Args:
        scheduled_projects: Dictionary of scheduled projects
        logger: Logger instance
    """
    from utils.app_config import AppConfig

    app_config = AppConfig()
    json_file_path = os.path.join(app_config.data_dir, "scheduled_projects.json")

    try:
        with open(json_file_path, 'w') as file:
            json.dump(scheduled_projects, file, indent=4, default=str)

        logger.info(f"Successfully saved {len(scheduled_projects)} scheduled projects to {json_file_path}")

    except Exception as e:
        logger.error(f"Error saving scheduled projects: {e}")


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
