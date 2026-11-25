# -----------------------------------------------------------------------------
# Project Meridian
# Copyright (c) 2025 Jereme Shaver
#
# Utility to synchronize projects with dashboard grid layouts
# -----------------------------------------------------------------------------

from utils.dashboard_config import DashboardConfigManager
from utils.projects_io import load_projects_from_json


def ensure_project_groups_exist(logger):
    """
    Ensure that all active projects have corresponding grid layouts in the dashboard.
    Creates missing project groups automatically.

    Args:
        logger: Logger instance
    """
    # Load all projects
    projects = load_projects_from_json(logger)
    active_projects = {
        proj_id: proj for proj_id, proj in projects.items()
        if not getattr(proj, 'archived', False)
    }

    # Load existing grid layouts
    grid_layouts = DashboardConfigManager.get_all_grid_layouts()

    # Find which projects already have grid layouts
    existing_project_grids = set()
    for grid in grid_layouts:
        # Check if this grid has a project_id filter
        if hasattr(grid.filter, 'project_id') and grid.filter.project_id:
            existing_project_grids.add(grid.filter.project_id)

    # Create missing project groups
    new_grids_created = 0
    for project_id, project in active_projects.items():
        if project_id not in existing_project_grids:
            logger.info(f"Creating dashboard group for project: {project.title}")
            create_project_grid_layout(project, grid_layouts, logger)
            new_grids_created += 1

    if new_grids_created > 0:
        logger.info(f"Created {new_grids_created} new project dashboard groups")
        DashboardConfigManager.save_grid_layouts(grid_layouts)

    return new_grids_created


def create_project_grid_layout(project, existing_grids, logger):
    """
    Create a grid layout configuration for a project.

    Args:
        project: Project object
        existing_grids: List of existing grid layouts (will be modified)
        logger: Logger instance
    """
    # Create a new grid layout object
    grid = type('', (), {})()

    # Set basic properties
    grid.id = f"project_{project.id}"
    grid.name = f"📦 {project.title}"
    grid.position = len(existing_grids)
    grid.columns = 3
    grid.minimize = 'false'

    # Create filter object with project_id
    grid.filter = type('', (), {})()
    grid.filter.status = []  # All statuses
    grid.filter.category = []  # All categories
    grid.filter.due = []  # All due dates
    grid.filter.project_id = project.id  # Special filter for project tasks

    existing_grids.append(grid)

    logger.debug(f"Created grid layout for project: {project.title} (ID: {project.id})")


def remove_project_grid_layout(project_id, logger):
    """
    Remove the grid layout for a deleted/archived project.

    Args:
        project_id: Project ID
        logger: Logger instance
    """
    grid_layouts = DashboardConfigManager.get_all_grid_layouts()

    # Find and remove the project grid
    original_count = len(grid_layouts)
    grid_layouts = [
        grid for grid in grid_layouts
        if not (hasattr(grid.filter, 'project_id') and grid.filter.project_id == project_id)
    ]

    if len(grid_layouts) < original_count:
        logger.info(f"Removed dashboard group for project: {project_id}")
        DashboardConfigManager.save_grid_layouts(grid_layouts)
        return True

    return False


def update_project_grid_name(project_id, new_name, logger):
    """
    Update the name of a project's grid layout.

    Args:
        project_id: Project ID
        new_name: New project name
        logger: Logger instance
    """
    grid_layouts = DashboardConfigManager.get_all_grid_layouts()

    for grid in grid_layouts:
        if hasattr(grid.filter, 'project_id') and grid.filter.project_id == project_id:
            grid.name = f"📦 {new_name}"
            logger.info(f"Updated dashboard group name for project: {new_name}")
            DashboardConfigManager.save_grid_layouts(grid_layouts)
            return True

    return False


def ensure_category_groups_exist(tasks, logger):
    """
    Make sure every category used by the given tasks has a dashboard group, so no
    task is hidden. Archived tasks need the Archived group instead of their own
    category's group.

    Args:
        tasks: Iterable of Task objects shown on the dashboard
        logger: Logger instance

    Returns:
        int: Number of groups created
    """
    from uuid import uuid4
    from models.task import TaskCategory, TaskStatus

    archived_name = TaskCategory.ARCHIVED.value
    needed = {archived_name if task.archived else task.category_name for task in tasks}
    if not needed:
        return 0

    grid_layouts = DashboardConfigManager.get_all_grid_layouts()

    covered = set()
    for grid in grid_layouts:
        if getattr(grid.filter, 'project_id', None):
            continue
        categories = list(getattr(grid.filter, 'category', []) or [])
        statuses = list(getattr(grid.filter, 'status', []) or [])
        covered.update(categories)
        if TaskStatus.COMPLETED.value in statuses:
            covered.add(archived_name)
        if not categories and not statuses:
            # A group with no category or status filter shows every active task
            covered.update(needed - {archived_name})

    missing = sorted(needed - covered)
    for category in missing:
        grid = type('', (), {})()
        grid.id = str(uuid4())
        grid.name = category
        grid.position = len(grid_layouts)
        grid.columns = 3
        grid.minimize = 'false'
        grid.filter = type('', (), {})()
        grid.filter.status = []
        grid.filter.category = [category]
        grid.filter.due = []
        grid.filter.project_id = None
        grid_layouts.append(grid)
        logger.info(f"Creating dashboard group for category: {category}")

    if missing:
        DashboardConfigManager.save_grid_layouts(grid_layouts)

    return len(missing)
