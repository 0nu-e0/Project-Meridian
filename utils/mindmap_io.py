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
# File: mindmap_io.py
# Description: Mindmap storage and retrieval utilities
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

import logging
from pathlib import Path
from typing import Dict, Optional, List, Any
from datetime import datetime

from models.mindmap import Mindmap
from utils.app_config import AppConfig
from utils.safe_io import parse_records, read_json, with_unparsed_records, write_json


def get_mindmaps_file() -> Path:
    """
    Get the path to the mindmaps JSON file.

    Returns:
        Path to app_mindmaps.json
    """
    app_config = AppConfig()
    return Path(app_config.data_dir) / "app_mindmaps.json"


def load_mindmaps_from_json(logger: logging.Logger) -> Dict[str, Mindmap]:
    """
    Load all mindmaps from JSON storage.

    Args:
        logger: Logger instance for logging

    Returns:
        Dictionary mapping mindmap IDs to Mindmap objects
    """
    mindmaps_file = get_mindmaps_file()

    if not mindmaps_file.exists():
        logger.debug("No mindmaps file found. Starting with empty mindmaps.")
        return {}

    data = read_json(str(mindmaps_file), logger)
    mindmaps = parse_records(str(mindmaps_file), data, lambda key, raw: Mindmap.from_dict(raw), logger)

    logger.info(f"Loaded {len(mindmaps)} mindmaps from {mindmaps_file}")
    return mindmaps


def save_mindmaps_to_json(mindmaps: Dict[str, Mindmap], logger: logging.Logger) -> bool:
    """
    Save all mindmaps to JSON storage.

    Args:
        mindmaps: Dictionary of mindmap IDs to Mindmap objects
        logger: Logger instance for logging

    Returns:
        True if successful, False otherwise
    """
    mindmaps_file = str(get_mindmaps_file())

    data = {mindmap_id: mindmap.to_dict() for mindmap_id, mindmap in mindmaps.items()}
    if not write_json(mindmaps_file, with_unparsed_records(mindmaps_file, data), logger, ensure_ascii=False):
        return False

    logger.info(f"Saved {len(mindmaps)} mindmaps to {mindmaps_file}")
    return True


def create_mindmap(
    title: str,
    description: str = "",
    nodes: Optional[List[Dict[str, Any]]] = None,
    connections: Optional[List[Dict[str, Any]]] = None,
    project_id: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> Mindmap:
    """
    Create a new mindmap and save it to storage.

    Args:
        title: Mindmap title
        description: Optional description
        nodes: Optional list of node data
        connections: Optional list of connection data
        project_id: Optional project ID to link to
        logger: Logger instance

    Returns:
        New Mindmap instance
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    # Create mindmap
    mindmap = Mindmap(
        title=title,
        description=description,
        nodes=nodes,
        connections=connections,
        project_id=project_id
    )

    # Load existing mindmaps
    mindmaps = load_mindmaps_from_json(logger)

    # Add new mindmap
    mindmaps[mindmap.id] = mindmap

    # Save
    save_mindmaps_to_json(mindmaps, logger)

    logger.info(f"Created mindmap: {mindmap.title} (ID: {mindmap.id})")
    return mindmap


def update_mindmap(
    mindmap_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    nodes: Optional[List[Dict[str, Any]]] = None,
    connections: Optional[List[Dict[str, Any]]] = None,
    project_id: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> bool:
    """
    Update an existing mindmap.

    Args:
        mindmap_id: ID of mindmap to update
        title: Optional new title
        description: Optional new description
        nodes: Optional new nodes
        connections: Optional new connections
        project_id: Optional new project_id (use "" to unlink)
        logger: Logger instance

    Returns:
        True if successful, False otherwise
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    mindmaps = load_mindmaps_from_json(logger)

    if mindmap_id not in mindmaps:
        logger.error(f"Mindmap {mindmap_id} not found")
        return False

    mindmap = mindmaps[mindmap_id]

    # Update fields
    if title is not None:
        mindmap.title = title
    if description is not None:
        mindmap.description = description
    if nodes is not None:
        mindmap.nodes = nodes
    if connections is not None:
        mindmap.connections = connections
    if project_id is not None:
        if project_id == "":
            mindmap.project_id = None
        else:
            mindmap.project_id = project_id

    mindmap.modified_date = datetime.now()

    # Save
    success = save_mindmaps_to_json(mindmaps, logger)

    if success:
        logger.info(f"Updated mindmap: {mindmap.title} (ID: {mindmap_id})")

    return success


def delete_mindmap(mindmap_id: str, logger: logging.Logger) -> bool:
    """
    Delete a mindmap from storage.

    Args:
        mindmap_id: ID of mindmap to delete
        logger: Logger instance

    Returns:
        True if successful, False otherwise
    """
    mindmaps = load_mindmaps_from_json(logger)

    if mindmap_id not in mindmaps:
        logger.error(f"Mindmap {mindmap_id} not found")
        return False

    mindmap = mindmaps[mindmap_id]

    # If linked to a project, unlink it first
    if mindmap.project_id:
        try:
            from utils.projects_io import load_projects_from_json, save_projects_to_json

            projects = load_projects_from_json(logger)
            if mindmap.project_id in projects:
                project = projects[mindmap.project_id]
                project.mindmap_id = None
                save_projects_to_json(projects, logger)
                logger.info(f"Unlinked mindmap from project {project.title}")
        except Exception as e:
            logger.error(f"Error unlinking project: {e}")

    # Remove and save only after any pre-save work is done
    mindmaps.pop(mindmap_id)
    success = save_mindmaps_to_json(mindmaps, logger)

    if success:
        logger.info(f"Deleted mindmap: {mindmap.title} (ID: {mindmap_id})")
    else:
        logger.error(f"Failed to save after deleting mindmap {mindmap_id}")

    return success


def link_mindmap_to_project(
    mindmap_id: str,
    project_id: str,
    logger: logging.Logger
) -> bool:
    """
    Link a mindmap to a project (bi-directional).

    Args:
        mindmap_id: ID of mindmap to link
        project_id: ID of project to link to
        logger: Logger instance

    Returns:
        True if successful, False otherwise
    """
    from utils.projects_io import load_projects_from_json, save_projects_to_json

    # Load mindmaps and projects
    mindmaps = load_mindmaps_from_json(logger)
    projects = load_projects_from_json(logger)

    if mindmap_id not in mindmaps:
        logger.error(f"Mindmap {mindmap_id} not found")
        return False

    if project_id not in projects:
        logger.error(f"Project {project_id} not found")
        return False

    mindmap = mindmaps[mindmap_id]
    project = projects[project_id]

    # Unlink previous connections if any
    if mindmap.project_id and mindmap.project_id != project_id:
        old_project = projects.get(mindmap.project_id)
        if old_project:
            old_project.mindmap_id = None

    if project.mindmap_id and project.mindmap_id != mindmap_id:
        old_mindmap = mindmaps.get(project.mindmap_id)
        if old_mindmap:
            old_mindmap.project_id = None

    # Create bi-directional link
    mindmap.link_to_project(project_id)
    project.mindmap_id = mindmap_id
    project.modified_date = datetime.now()

    # Save both
    save_mindmaps_to_json(mindmaps, logger)
    save_projects_to_json(projects, logger)

    logger.info(f"Linked mindmap '{mindmap.title}' to project '{project.title}'")
    return True


def unlink_mindmap_from_project(
    mindmap_id: str,
    logger: logging.Logger
) -> bool:
    """
    Unlink a mindmap from its project (bi-directional).

    Args:
        mindmap_id: ID of mindmap to unlink
        logger: Logger instance

    Returns:
        True if successful, False otherwise
    """
    from utils.projects_io import load_projects_from_json, save_projects_to_json

    # Load mindmaps and projects
    mindmaps = load_mindmaps_from_json(logger)

    if mindmap_id not in mindmaps:
        logger.error(f"Mindmap {mindmap_id} not found")
        return False

    mindmap = mindmaps[mindmap_id]

    if not mindmap.project_id:
        logger.info(f"Mindmap '{mindmap.title}' is not linked to any project")
        return True

    # Load project and unlink
    projects = load_projects_from_json(logger)
    project_id = mindmap.project_id

    if project_id in projects:
        project = projects[project_id]
        project.mindmap_id = None
        project.modified_date = datetime.now()
        save_projects_to_json(projects, logger)

    # Unlink mindmap
    mindmap.unlink_from_project()
    save_mindmaps_to_json(mindmaps, logger)

    logger.info(f"Unlinked mindmap '{mindmap.title}' from project")
    return True


def get_mindmaps_for_project(project_id: str, logger: logging.Logger) -> List[Mindmap]:
    """
    Get all mindmaps linked to a specific project.

    Args:
        project_id: ID of the project
        logger: Logger instance

    Returns:
        List of Mindmap instances
    """
    mindmaps = load_mindmaps_from_json(logger)
    return [m for m in mindmaps.values() if m.project_id == project_id]


def get_unlinked_mindmaps(logger: logging.Logger) -> List[Mindmap]:
    """
    Get all mindmaps that are not linked to any project.

    Args:
        logger: Logger instance

    Returns:
        List of Mindmap instances
    """
    mindmaps = load_mindmaps_from_json(logger)
    return [m for m in mindmaps.values() if not m.project_id]
