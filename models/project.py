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
# File: project.py
# Description: Project model for hierarchical project management
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

from datetime import datetime
from typing import Optional, List, Dict
from enum import Enum
from uuid import uuid4
from PyQt5.QtCore import QObject, pyqtSignal

from models.task import TaskPriority, TaskStatus


class ProjectStatus(Enum):
    """Status enumeration for projects"""
    PLANNING = "Planning"
    ACTIVE = "Active"
    ON_HOLD = "On Hold"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"


class Project(QObject):
    """
    Project model representing a hierarchical container for phases and tasks.

    Hierarchy: Project → Phases → Tasks
    """

    # Signals
    projectUpdated = pyqtSignal()

    def __init__(
        self,
        title: str,
        description: str = "",
        status: ProjectStatus = ProjectStatus.PLANNING,
        priority: TaskPriority = TaskPriority.MEDIUM,
        color: str = "#3498db"
    ):
        super().__init__()

        # Identifiers
        self.id = str(uuid4())
        self.title = title
        self.description = description

        # Relationships
        self.phases: List[str] = []  # Ordered list of phase IDs
        self.mindmap_id: Optional[str] = None
        self.current_phase_id: Optional[str] = None

        # Metadata
        self.creation_date = datetime.now()
        self.start_date: Optional[datetime] = None
        self.target_completion: Optional[datetime] = None
        self.completion_date: Optional[datetime] = None
        self.status = status
        self.priority = priority
        self.color = color
        self.archived = False

        # Cache for loaded tasks to avoid redundant file I/O
        self._cached_tasks = None

    def to_dict(self) -> dict:
        """Serialize project to dictionary for JSON storage"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'phases': self.phases,
            'mindmap_id': self.mindmap_id,
            'current_phase_id': self.current_phase_id,
            'creation_date': self.creation_date.isoformat(),
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'target_completion': self.target_completion.isoformat() if self.target_completion else None,
            'completion_date': self.completion_date.isoformat() if self.completion_date else None,
            'status': self.status.value,
            'priority': self.priority.value,
            'color': self.color,
            'archived': self.archived
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Project':
        """Deserialize project from dictionary"""
        project = cls(
            title=data['title'],
            description=data.get('description', ''),
            status=ProjectStatus(data.get('status', ProjectStatus.PLANNING.value)),
            priority=TaskPriority(data.get('priority', TaskPriority.MEDIUM.value)),
            color=data.get('color', '#3498db')
        )

        # Restore fields
        project.id = data['id']
        project.phases = data.get('phases', [])
        project.mindmap_id = data.get('mindmap_id')
        project.current_phase_id = data.get('current_phase_id')
        project.archived = data.get('archived', False)

        # Parse dates
        project.creation_date = datetime.fromisoformat(data['creation_date'])
        if data.get('start_date'):
            project.start_date = datetime.fromisoformat(data['start_date'])
        if data.get('target_completion'):
            project.target_completion = datetime.fromisoformat(data['target_completion'])
        if data.get('completion_date'):
            project.completion_date = datetime.fromisoformat(data['completion_date'])

        return project

    def _get_project_tasks(self, logger=None):
        """
        Get all tasks belonging to this project with caching.

        Args:
            logger: Optional logger instance

        Returns:
            List of Task objects belonging to this project
        """
        if self._cached_tasks is None:
            from utils.tasks_io import load_tasks_from_json
            from logging import getLogger

            if logger is None:
                logger = getLogger(__name__)

            all_tasks = load_tasks_from_json(logger)
            self._cached_tasks = [task for task in all_tasks.values() if task.project_id == self.id]

        return self._cached_tasks

    def invalidate_task_cache(self):
        """
        Invalidate the cached tasks, forcing a reload on next access.
        Call this when tasks are added, modified, or deleted.
        """
        self._cached_tasks = None
        # Also invalidate the global cache
        from utils.tasks_io import invalidate_tasks_cache
        invalidate_tasks_cache()

    def get_progress_percentage(self) -> float:
        """
        Calculate overall project completion percentage based on tasks.

        Returns:
            Float between 0.0 and 100.0
        """
        project_tasks = self._get_project_tasks()

        if not project_tasks:
            return 0.0

        completed_tasks = sum(1 for task in project_tasks if task.status == TaskStatus.COMPLETED)
        return (completed_tasks / len(project_tasks)) * 100.0

    def get_total_tasks(self) -> int:
        """
        Get total number of tasks in this project.

        Returns:
            Integer count of tasks
        """
        project_tasks = self._get_project_tasks()
        return len(project_tasks)

    def get_completed_tasks(self) -> int:
        """
        Get number of completed tasks in this project.

        Returns:
            Integer count of completed tasks
        """
        project_tasks = self._get_project_tasks()
        completed_tasks = sum(1 for task in project_tasks if task.status == TaskStatus.COMPLETED)
        return completed_tasks

    def get_current_phase(self):
        """
        Get the current active phase of this project.

        Returns:
            Phase object if current_phase_id is set, None otherwise
        """
        if not self.current_phase_id:
            return None

        from utils.projects_io import load_phases_from_json
        from logging import getLogger

        logger = getLogger(__name__)
        phases = load_phases_from_json(logger)

        return phases.get(self.current_phase_id)

    def get_tasks_by_status(self) -> Dict[TaskStatus, int]:
        """
        Get task count breakdown by status.

        Returns:
            Dictionary mapping TaskStatus to count
        """
        project_tasks = self._get_project_tasks()

        status_counts = {status: 0 for status in TaskStatus}
        for task in project_tasks:
            status_counts[task.status] += 1

        return status_counts
