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
# File: gantt_item.py
# Description: Model for Gantt chart swimlane items
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

from datetime import datetime
from typing import Optional
from uuid import uuid4
from PyQt5.QtCore import QObject, pyqtSignal


class GanttItemType:
    """Type enumeration for Gantt items"""
    PHASE = "phase"
    CUSTOM = "custom"


class GanttChartItem(QObject):
    """
    Represents a swimlane item in a Gantt chart.

    Can be linked to a phase or be a custom standalone item.
    """

    itemUpdated = pyqtSignal()

    def __init__(
        self,
        title: str,
        item_type: str = GanttItemType.CUSTOM,
        phase_id: Optional[str] = None
    ):
        super().__init__()

        # Identifiers
        self.id = str(uuid4())
        self.title = title
        self.item_type = item_type  # "phase" or "custom"
        self.phase_id = phase_id  # Link to phase if type is "phase"

        # Timeline data
        self.start_date: Optional[datetime] = None
        self.end_date: Optional[datetime] = None

        # Visual properties
        self.color: str = "#3498db"
        self.description: str = ""

        # Ordering
        self.order: int = 0

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON storage"""
        return {
            'id': self.id,
            'title': self.title,
            'item_type': self.item_type,
            'phase_id': self.phase_id,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'color': self.color,
            'description': self.description,
            'order': self.order
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'GanttChartItem':
        """Deserialize from dictionary"""
        item = cls(
            title=data['title'],
            item_type=data.get('item_type', GanttItemType.CUSTOM),
            phase_id=data.get('phase_id')
        )

        item.id = data['id']
        item.color = data.get('color', '#3498db')
        item.description = data.get('description', '')
        item.order = data.get('order', 0)

        # Parse dates
        if data.get('start_date'):
            item.start_date = datetime.fromisoformat(data['start_date'])
        if data.get('end_date'):
            item.end_date = datetime.fromisoformat(data['end_date'])

        return item

    @classmethod
    def from_phase(cls, phase) -> 'GanttChartItem':
        """Create a GanttChartItem from a Phase object"""
        item = cls(
            title=phase.name,
            item_type=GanttItemType.PHASE,
            phase_id=phase.id
        )

        # Copy dates from phase if available
        item.start_date = phase.start_date
        item.end_date = phase.end_date
        item.description = phase.description
        item.order = phase.order

        # Use a default color (can be customized)
        item.color = "#3498db"

        return item


class GanttChart(QObject):
    """
    Container for a project's Gantt chart data
    """

    chartUpdated = pyqtSignal()

    def __init__(self, project_id: str):
        super().__init__()

        self.id = str(uuid4())
        self.project_id = project_id
        self.items: list[GanttChartItem] = []

    def add_item(self, item: GanttChartItem):
        """Add an item to the chart"""
        self.items.append(item)
        self.chartUpdated.emit()

    def remove_item(self, item_id: str):
        """Remove an item from the chart"""
        self.items = [item for item in self.items if item.id != item_id]
        self.chartUpdated.emit()

    def reorder_items(self):
        """Sort items by their order property"""
        self.items.sort(key=lambda x: x.order)

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON storage"""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'items': [item.to_dict() for item in self.items]
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'GanttChart':
        """Deserialize from dictionary"""
        chart = cls(project_id=data['project_id'])
        chart.id = data['id']
        chart.items = [GanttChartItem.from_dict(item_data) for item_data in data.get('items', [])]
        return chart
