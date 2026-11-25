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
# File: data_manager.py
# Description: Centralized data access. Reads go through the *_io modules, which
#              cache by file modification time, so every screen sees the same
#              data as soon as any screen saves it.
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

import logging
from typing import Dict, Optional
from models.task import Task
from models.project import Project
from models.phase import Phase
from utils.tasks_io import delete_task_from_json, load_tasks_from_json, save_task_to_json
from utils.projects_io import load_projects_from_json, save_projects_to_json, load_phases_from_json, save_phases_to_json

class DataManager:
    """
    Singleton giving shared access to tasks, projects, and phases.

    It deliberately keeps no copy of its own: an earlier version loaded everything
    once at startup, so changes saved by other screens never showed up here.
    """
    _instance = None
    _initialized = False

    def __new__(cls, logger=None, app_config=None):
        if cls._instance is None:
            cls._instance = super(DataManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, logger=None, app_config=None):
        # Only run initialization once for singleton
        if DataManager._initialized:
            return

        DataManager._initialized = True
        self.logger = logger if logger else logging.getLogger("DataManager")
        self.app_config = app_config

    def _load_all_data(self):
        """Warm the task cache at startup and log what was found"""
        self.logger.info(f"Data available: {self.get_data_summary()}")

    def reload_all_data(self):
        """Force the next read to come from disk"""
        load_tasks_from_json(self.logger, force_reload=True)

    # ===== TASK METHODS =====

    def get_tasks(self) -> Dict[str, Task]:
        """Get all tasks (a shared, cached dict - callers should not modify it!)"""
        return load_tasks_from_json(self.logger)

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a specific task by ID"""
        return self.get_tasks().get(task_id)

    def save_task(self, task: Task) -> bool:
        """Save a task to disk"""
        return save_task_to_json(task, self.logger)

    def delete_task(self, task_id: str) -> bool:
        """Delete a task from disk"""
        return delete_task_from_json(task_id, self.logger)

    def get_tasks_by_project(self, project_id: str) -> Dict[str, Task]:
        """Get all tasks for a specific project"""
        return {tid: task for tid, task in self.get_tasks().items() if task.project_id == project_id}

    def get_tasks_by_phase(self, phase_id: str) -> Dict[str, Task]:
        """Get all tasks for a specific phase"""
        return {tid: task for tid, task in self.get_tasks().items() if task.phase_id == phase_id}

    def get_tasks_by_category(self, category: str) -> Dict[str, Task]:
        """Get all tasks for a specific category"""
        return {tid: task for tid, task in self.get_tasks().items() if task.category_name == category}

    # ===== PROJECT METHODS =====

    def get_projects(self) -> Dict[str, Project]:
        """Get all projects"""
        return load_projects_from_json(self.logger)

    def get_project(self, project_id: str) -> Optional[Project]:
        """Get a specific project by ID"""
        return self.get_projects().get(project_id)

    def save_project(self, project: Project) -> bool:
        """Save a project to disk"""
        projects = self.get_projects()
        projects[project.id] = project
        return save_projects_to_json(projects, self.logger)

    # ===== PHASE METHODS =====

    def get_phases(self) -> Dict[str, Phase]:
        """Get all phases"""
        return load_phases_from_json(self.logger)

    def get_phase(self, phase_id: str) -> Optional[Phase]:
        """Get a specific phase by ID"""
        return self.get_phases().get(phase_id)

    def get_phases_by_project(self, project_id: str) -> Dict[str, Phase]:
        """Get all phases for a specific project"""
        return {pid: phase for pid, phase in self.get_phases().items() if phase.project_id == project_id}

    def save_phase(self, phase: Phase) -> bool:
        """Save a phase to disk"""
        phases = self.get_phases()
        phases[phase.id] = phase
        return save_phases_to_json(phases, self.logger)

    # ===== UTILITY METHODS =====

    def get_data_summary(self) -> dict:
        """Get a summary of the stored data"""
        tasks = self.get_tasks()
        projects = self.get_projects()
        return {
            "tasks_count": len(tasks),
            "projects_count": len(projects),
            "phases_count": len(self.get_phases()),
            "archived_tasks": sum(1 for t in tasks.values() if getattr(t, "archived", False)),
            "archived_projects": sum(1 for p in projects.values() if getattr(p, "archived", False)),
        }
