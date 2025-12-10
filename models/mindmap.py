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
# File: mindmap.py
# Description: Mindmap data model
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from PyQt5.QtCore import QObject, pyqtSignal


class Mindmap(QObject):
    """
    Represents a mindmap with nodes and connections.
    Can be linked to a project for bi-directional navigation.
    """

    # Signals
    mindmapChanged = pyqtSignal()

    def __init__(
        self,
        id: Optional[str] = None,
        title: str = "Untitled Mindmap",
        description: str = "",
        nodes: Optional[List[Dict[str, Any]]] = None,
        connections: Optional[List[Dict[str, Any]]] = None,
        project_id: Optional[str] = None,
        creation_date: Optional[datetime] = None,
        modified_date: Optional[datetime] = None,
        parent=None
    ):
        super().__init__(parent)

        # Identifiers
        self.id = id if id else str(uuid.uuid4())
        self.title = title
        self.description = description

        # Mindmap content
        self.nodes = nodes if nodes is not None else []
        self.connections = connections if connections is not None else []

        # Project linking
        self.project_id = project_id

        # Metadata
        self.creation_date = creation_date if creation_date else datetime.now()
        self.modified_date = modified_date if modified_date else datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize the mindmap to a dictionary for JSON storage.

        Returns:
            Dictionary representation of the mindmap
        """
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'nodes': self.nodes,
            'connections': self.connections,
            'project_id': self.project_id,
            'creation_date': self.creation_date.isoformat() if self.creation_date else None,
            'modified_date': self.modified_date.isoformat() if self.modified_date else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Mindmap':
        """
        Deserialize a mindmap from a dictionary.

        Args:
            data: Dictionary containing mindmap data

        Returns:
            Mindmap instance
        """
        # Parse dates
        creation_date = None
        if data.get('creation_date'):
            try:
                creation_date = datetime.fromisoformat(data['creation_date'])
            except (ValueError, TypeError):
                creation_date = datetime.now()

        modified_date = None
        if data.get('modified_date'):
            try:
                modified_date = datetime.fromisoformat(data['modified_date'])
            except (ValueError, TypeError):
                modified_date = datetime.now()

        return cls(
            id=data.get('id'),
            title=data.get('title', 'Untitled Mindmap'),
            description=data.get('description', ''),
            nodes=data.get('nodes', []),
            connections=data.get('connections', []),
            project_id=data.get('project_id'),
            creation_date=creation_date,
            modified_date=modified_date
        )

    def get_node_count(self) -> int:
        """
        Get the number of nodes in this mindmap.

        Returns:
            Number of nodes
        """
        return len(self.nodes) if self.nodes else 0

    def get_connection_count(self) -> int:
        """
        Get the number of connections in this mindmap.

        Returns:
            Number of connections
        """
        return len(self.connections) if self.connections else 0

    def update_content(self, nodes: List[Dict[str, Any]], connections: List[Dict[str, Any]]):
        """
        Update the mindmap content (nodes and connections).

        Args:
            nodes: List of node data dictionaries
            connections: List of connection data dictionaries
        """
        self.nodes = nodes
        self.connections = connections
        self.modified_date = datetime.now()
        self.mindmapChanged.emit()

    def link_to_project(self, project_id: str):
        """
        Link this mindmap to a project.

        Args:
            project_id: The ID of the project to link to
        """
        self.project_id = project_id
        self.modified_date = datetime.now()
        self.mindmapChanged.emit()

    def unlink_from_project(self):
        """
        Remove the link to a project.
        """
        self.project_id = None
        self.modified_date = datetime.now()
        self.mindmapChanged.emit()

    def get_project(self):
        """
        Get the linked project (lazy loading to avoid circular imports).

        Returns:
            Project instance or None if not linked
        """
        if not self.project_id:
            return None

        try:
            from utils.projects_io import load_projects_from_json
            import logging
            logger = logging.getLogger(__name__)

            projects = load_projects_from_json(logger)
            return projects.get(self.project_id)
        except Exception as e:
            print(f"Error loading project: {e}")
            return None
