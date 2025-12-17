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
# Description: Centralized data manager - loads all data once at startup and
# provides shared access throughout the application
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

# data_manager.py
import logging
from typing import Dict, Optional
from models.task import Task
from models.project import Project
from models.phase import Phase
from utils.tasks_io import load_tasks_from_json, save_task_to_json
from utils.projects_io import load_projects_from_json, save_projects_to_json, load_phases_from_json, save_phases_to_json


class DataManager:
    """
    Singleton class that manages all application data in memory.
    Loads data once at startup (now lazily) and provides shared access throughout the app.
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

        # Store AppConfig reference to avoid creating new instances
        self.app_config = app_config

        # In-memory data storage
        self._tasks: Dict[str, Task] = {}
        self._projects: Dict[str, Project] = {}
        self._phases: Dict[str, Phase] = {}

        # Load all data immediately (called from main.py only)
        # Other components will just get the singleton instance

    def _load_all_data(self):
        """Load all data from JSON files into memory - MUST be called from main.py after initialization"""
        try:
            # self.logger.info("Loading all application data...")

            # Load tasks
            self._tasks = load_tasks_from_json(self.logger)
            self.logger.info(f"Loaded {len(self._tasks)} tasks")

            # Load projects
            self._projects = load_projects_from_json(self.logger)
            self.logger.info(f"Loaded {len(self._projects)} projects")

            # Load phases
            self._phases = load_phases_from_json(self.logger)
            self.logger.info(f"Loaded {len(self._phases)} phases")

            self.logger.info("All application data loaded successfully")
        except Exception as e:
            self.logger.error(f"Error loading application data: {e}")
            raise

    def reload_all_data(self):
        """Reload all data from disk (use sparingly, only when external changes occur)"""
        self.logger.info("Reloading all application data from disk...")
        self._load_all_data()

    # ===== TASK METHODS =====

    def get_tasks(self) -> Dict[str, Task]:
        """Get all tasks (returns reference to internal dict - callers should not modify!)"""
        # NOTE: Returning reference instead of copy to avoid recursion issues
        # Callers should treat this as read-only
        return self._tasks

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a specific task by ID"""
        return self._tasks.get(task_id)

    def add_task(self, task: Task):
        """Add or update a task in memory"""
        # No need to call _ensure_data_loaded() for single updates
        self._tasks[task.id] = task
        self.logger.debug(f"Added/updated task: {task.title}")

    def remove_task(self, task_id: str):
        """Remove a task from memory"""
        if task_id in self._tasks:
            del self._tasks[task_id]
            self.logger.debug(f"Removed task: {task_id}")

    def save_task(self, task: Task):
        """Save a task to both memory and disk"""
        self._tasks[task.id] = task
        save_task_to_json(task, self.logger)
        self.logger.debug(f"Saved task: {task.title}")

    def get_tasks_by_project(self, project_id: str) -> Dict[str, Task]:
        """Get all tasks for a specific project"""
        return {tid: task for tid, task in self._tasks.items() if task.project_id == project_id}

    def get_tasks_by_phase(self, phase_id: str) -> Dict[str, Task]:
        """Get all tasks for a specific phase"""
        return {tid: task for tid, task in self._tasks.items() if task.phase_id == phase_id}

    def get_tasks_by_category(self, category: str) -> Dict[str, Task]:
        """Get all tasks for a specific category"""
        result = {}
        for tid, task in self._tasks.items():
            task_category = task.category.value if hasattr(task.category, 'value') else task.category
            if task_category == category:
                result[tid] = task
        return result

    # ===== PROJECT METHODS =====

    def get_projects(self) -> Dict[str, Project]:
        """Get all projects (returns reference to internal dict - callers should not modify!)"""
        return self._projects

    def get_project(self, project_id: str) -> Optional[Project]:
        """Get a specific project by ID"""
        return self._projects.get(project_id)

    def add_project(self, project: Project):
        """Add or update a project in memory"""
        self._projects[project.id] = project
        self.logger.debug(f"Added/updated project: {project.title}")

    def remove_project(self, project_id: str):
        """Remove a project from memory"""
        if project_id in self._projects:
            del self._projects[project_id]
            self.logger.debug(f"Removed project: {project_id}")

    def save_project(self, project: Project):
        """Save a project to both memory and disk"""
        self._projects[project.id] = project
        save_projects_to_json(self._projects, self.logger)
        self.logger.debug(f"Saved project: {project.title}")

    # ===== PHASE METHODS =====

    def get_phases(self) -> Dict[str, Phase]:
        """Get all phases (returns reference to internal dict - callers should not modify!)"""
        return self._phases

    def get_phase(self, phase_id: str) -> Optional[Phase]:
        """Get a specific phase by ID"""
        return self._phases.get(phase_id)

    def get_phases_by_project(self, project_id: str) -> Dict[str, Phase]:
        """Get all phases for a specific project"""
        return {pid: phase for pid, phase in self._phases.items() if phase.project_id == project_id}

    def add_phase(self, phase: Phase):
        """Add or update a phase in memory"""
        self._phases[phase.id] = phase
        self.logger.debug(f"Added/updated phase: {phase.name}")

    def remove_phase(self, phase_id: str):
        """Remove a phase from memory"""
        if phase_id in self._phases:
            del self._phases[phase_id]
            self.logger.debug(f"Removed phase: {phase_id}")

    def save_phase(self, phase: Phase):
        """Save a phase to both memory and disk"""
        self._phases[phase.id] = phase
        save_phases_to_json(self._phases, self.logger)
        self.logger.debug(f"Saved phase: {phase.name}")

    # ===== UTILITY METHODS =====

    def get_data_summary(self) -> dict:
        """Get a summary of all data in memory"""
        return {
            "tasks_count": len(self._tasks),
            "projects_count": len(self._projects),
            "phases_count": len(self._phases),
            "archived_tasks": sum(1 for t in self._tasks.values() if getattr(t, "archived", False)),
            "archived_projects": sum(1 for p in self._projects.values() if getattr(p, "archived", False)),
        }
