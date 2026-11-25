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
# File: phase.py
# Description: Phase model for project phase management
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

from datetime import datetime
from typing import Optional, List
from uuid import uuid4
from PyQt5.QtCore import QObject, pyqtSignal

from models.task import TaskStatus


class Phase(QObject):
    """
    Phase model representing a stage within a project.

    A task belongs to a phase when its phase_id is the phase's id. That is the only
    record of membership; task_ids is worked out from it so the two can't disagree.
    """

    # Signals
    phaseUpdated = pyqtSignal()

    def __init__(
        self,
        project_id: str,
        name: str,
        description: str = "",
        order: int = 0
    ):
        super().__init__()

        # Identifiers
        self.id = str(uuid4())
        self.project_id = project_id
        self.name = name
        self.description = description

        # task_ids read from an older file, used once by reconcile_phase_membership()
        self._legacy_task_ids: List[str] = []

        # Ordering & State
        self.order = order  # Sequence in project (0-based)
        self.is_current = False  # Marks the active phase
        self.collapsed = False  # UI state for expandable sections

        # Dates
        self.start_date: Optional[datetime] = None
        self.end_date: Optional[datetime] = None
        self.completion_date: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Serialize phase to dictionary for JSON storage"""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'name': self.name,
            'description': self.description,
            'order': self.order,
            'is_current': self.is_current,
            'collapsed': self.collapsed,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'completion_date': self.completion_date.isoformat() if self.completion_date else None
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Phase':
        """Deserialize phase from dictionary"""
        phase = cls(
            project_id=data['project_id'],
            name=data['name'],
            description=data.get('description', ''),
            order=data.get('order', 0)
        )

        # Restore fields
        phase.id = data['id']
        phase._legacy_task_ids = list(data.get('task_ids', []))
        phase.is_current = data.get('is_current', False)
        phase.collapsed = data.get('collapsed', False)

        # Parse dates
        if data.get('start_date'):
            phase.start_date = datetime.fromisoformat(data['start_date'])
        if data.get('end_date'):
            phase.end_date = datetime.fromisoformat(data['end_date'])
        if data.get('completion_date'):
            phase.completion_date = datetime.fromisoformat(data['completion_date'])

        return phase

    def get_tasks(self) -> list:
        """Tasks in this phase, oldest first"""
        from utils.tasks_io import load_tasks_from_json
        from logging import getLogger

        tasks = load_tasks_from_json(getLogger(__name__))
        phase_tasks = [task for task in tasks.values() if task.phase_id == self.id]
        return sorted(phase_tasks, key=lambda task: task.creation_date)

    @property
    def task_ids(self) -> List[str]:
        """IDs of the tasks in this phase, oldest first (read-only; set task.phase_id instead)"""
        return [task.id for task in self.get_tasks()]

    def get_progress_percentage(self) -> float:
        """
        Calculate phase completion percentage based on tasks.

        Returns:
            Float between 0.0 and 100.0
        """
        phase_tasks = self.get_tasks()

        if not phase_tasks:
            return 0.0

        completed_tasks = sum(1 for task in phase_tasks if task.status == TaskStatus.COMPLETED)
        return (completed_tasks / len(phase_tasks)) * 100.0

    def get_task_count(self) -> int:
        """
        Get total number of tasks in this phase.

        Returns:
            Integer count of tasks
        """
        return len(self.get_tasks())

    def get_completed_task_count(self) -> int:
        """
        Get number of completed tasks in this phase.

        Returns:
            Integer count of completed tasks
        """
        completed_tasks = sum(1 for task in self.get_tasks() if task.status == TaskStatus.COMPLETED)

        return completed_tasks
