"""
Migration script to add phase_id to existing tasks in phases
Run this once to fix tasks that were created before phase_id was properly set
"""

import json
import logging
from utils.tasks_io import load_tasks_from_json, save_task_to_json
from utils.projects_io import load_phases_from_json

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_phase_tasks():
    """Add phase_id to tasks that are in a phase's task_ids list"""

    # Load all tasks and phases
    tasks = load_tasks_from_json(logger)
    phases = load_phases_from_json(logger)

    updated_count = 0

    # For each phase, update its tasks with the phase_id
    for phase_id, phase in phases.items():
        logger.info(f"Processing phase: {phase.name} ({phase_id})")

        for task_id in phase.task_ids:
            if task_id in tasks:
                task = tasks[task_id]

                # Check if task already has phase_id set
                if not hasattr(task, 'phase_id') or task.phase_id is None:
                    logger.info(f"  Setting phase_id for task: {task.title}")
                    task.phase_id = phase_id
                    task.project_id = phase.project_id  # Also set project_id
                    updated_count += 1
                elif task.phase_id != phase_id:
                    logger.warning(f"  Task {task.title} has different phase_id: {task.phase_id} vs {phase_id}")
                    task.phase_id = phase_id
                    task.project_id = phase.project_id
                    updated_count += 1
            else:
                logger.warning(f"  Task {task_id} not found in tasks.json")

    # Save updated tasks
    if updated_count > 0:
        for task in tasks.values():
            if hasattr(task, 'phase_id') and task.phase_id is not None:
                save_task_to_json(task, logger)
        logger.info(f"\nMigration complete! Updated {updated_count} tasks.")
    else:
        logger.info("\nNo tasks needed updating.")

if __name__ == "__main__":
    migrate_phase_tasks()
