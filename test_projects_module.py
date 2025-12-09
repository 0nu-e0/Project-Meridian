#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Project Meridian - Projects Module Test Script
# Description: Manual test script for Phase 1 data models and storage utilities
# -----------------------------------------------------------------------------

import logging
import sys
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ProjectsModuleTest")

# Import the modules to test
from models.project import Project, ProjectStatus
from models.phase import Phase
from models.task import Task, TaskStatus, TaskPriority, TaskCategory
from utils.projects_io import (
    load_projects_from_json,
    save_projects_to_json,
    load_phases_from_json,
    save_phases_to_json,
    create_project,
    create_phase,
    delete_project,
    delete_phase,
    move_task_to_phase,
    add_task_to_phase,
    remove_task_from_phase
)
from utils.tasks_io import load_tasks_from_json, save_task_to_json


def test_project_creation():
    """Test creating a project programmatically"""
    logger.info("\n=== TEST 1: Project Creation ===")

    project = Project(
        title="Test Project Alpha",
        description="A comprehensive test project for the Projects module",
        status=ProjectStatus.PLANNING,
        priority=TaskPriority.HIGH,
        color="#e74c3c"
    )

    logger.info(f"Created project: {project.title} (ID: {project.id})")
    logger.info(f"Status: {project.status.value}")
    logger.info(f"Priority: {project.priority.value}")
    logger.info(f"Color: {project.color}")

    return project


def test_phase_creation(project_id):
    """Test creating phases for a project"""
    logger.info("\n=== TEST 2: Phase Creation ===")

    phases = []
    phase_names = ["Planning & Design", "Development", "Testing & QA"]

    for i, name in enumerate(phase_names):
        phase = Phase(
            project_id=project_id,
            name=name,
            description=f"Phase {i+1} of the project",
            order=i
        )
        phases.append(phase)
        logger.info(f"Created phase: {phase.name} (ID: {phase.id}, Order: {phase.order})")

    # Mark first phase as current
    phases[0].is_current = True
    logger.info(f"Set '{phases[0].name}' as current phase")

    return phases


def test_task_creation_with_phases(project_id, phase_ids):
    """Test creating tasks and assigning them to phases"""
    logger.info("\n=== TEST 3: Task Creation with Phase Assignment ===")

    tasks = []

    # Create tasks for Planning phase
    task1 = Task(
        title="Define project requirements",
        description="Gather and document all project requirements",
        project_id=project_id,
        category=TaskCategory.DOCUMENTATION
    )
    task1.phase_id = phase_ids[0]
    task1.priority = TaskPriority.HIGH
    task1.status = TaskStatus.COMPLETED
    tasks.append(task1)

    task2 = Task(
        title="Create wireframes",
        description="Design UI wireframes for all screens",
        project_id=project_id,
        category=TaskCategory.FEATURE
    )
    task2.phase_id = phase_ids[0]
    task2.priority = TaskPriority.MEDIUM
    task2.status = TaskStatus.IN_PROGRESS
    tasks.append(task2)

    # Create tasks for Development phase
    task3 = Task(
        title="Implement core functionality",
        description="Build the main features of the application",
        project_id=project_id,
        category=TaskCategory.FEATURE
    )
    task3.phase_id = phase_ids[1]
    task3.priority = TaskPriority.CRITICAL
    task3.status = TaskStatus.NOT_STARTED
    tasks.append(task3)

    task4 = Task(
        title="Set up database schema",
        description="Create database tables and relationships",
        project_id=project_id,
        category=TaskCategory.FEATURE
    )
    task4.phase_id = phase_ids[1]
    task4.priority = TaskPriority.HIGH
    task4.status = TaskStatus.NOT_STARTED
    tasks.append(task4)

    # Create tasks for Testing phase
    task5 = Task(
        title="Write unit tests",
        description="Create comprehensive unit tests for all modules",
        project_id=project_id,
        category=TaskCategory.FEATURE
    )
    task5.phase_id = phase_ids[2]
    task5.priority = TaskPriority.MEDIUM
    task5.status = TaskStatus.NOT_STARTED
    tasks.append(task5)

    for task in tasks:
        logger.info(f"Created task: '{task.title}' (Phase: {task.phase_id[:8]}..., Status: {task.status.value})")

    return tasks


def test_project_serialization(project, phases):
    """Test serializing and saving project data"""
    logger.info("\n=== TEST 4: Project Serialization ===")

    # Update project with phase IDs
    project.phases = [phase.id for phase in phases]
    project.current_phase_id = phases[0].id

    # Save to JSON
    projects_dict = {project.id: project}
    success = save_projects_to_json(projects_dict, logger)

    if success:
        logger.info(f"✓ Successfully saved project to JSON")
    else:
        logger.error(f"✗ Failed to save project to JSON")

    return success


def test_phase_serialization(phases, tasks):
    """Test serializing and saving phase data"""
    logger.info("\n=== TEST 5: Phase Serialization ===")

    # Update phases with task IDs
    phase_tasks = {phase.id: [] for phase in phases}
    for task in tasks:
        if task.phase_id:
            phase_tasks[task.phase_id].append(task.id)

    for phase in phases:
        phase.task_ids = phase_tasks.get(phase.id, [])

    # Save to JSON
    phases_dict = {phase.id: phase for phase in phases}
    success = save_phases_to_json(phases_dict, logger)

    if success:
        logger.info(f"✓ Successfully saved {len(phases)} phases to JSON")
    else:
        logger.error(f"✗ Failed to save phases to JSON")

    return success


def test_task_serialization(tasks):
    """Test serializing and saving task data with phase_id"""
    logger.info("\n=== TEST 6: Task Serialization with Phase IDs ===")

    success_count = 0
    for task in tasks:
        if save_task_to_json(task, logger):
            success_count += 1

    if success_count == len(tasks):
        logger.info(f"✓ Successfully saved all {len(tasks)} tasks to JSON")
        return True
    else:
        logger.error(f"✗ Only saved {success_count}/{len(tasks)} tasks")
        return False


def test_data_loading():
    """Test loading all data back from JSON"""
    logger.info("\n=== TEST 7: Data Loading from JSON ===")

    # Load projects
    projects = load_projects_from_json(logger)
    logger.info(f"Loaded {len(projects)} projects")

    # Load phases
    phases = load_phases_from_json(logger)
    logger.info(f"Loaded {len(phases)} phases")

    # Load tasks
    tasks = load_tasks_from_json(logger)
    logger.info(f"Loaded {len(tasks)} tasks")

    # Verify data integrity
    if projects:
        project = list(projects.values())[0]
        logger.info(f"\nProject: {project.title}")
        logger.info(f"  - Status: {project.status.value}")
        logger.info(f"  - Phases: {len(project.phases)}")
        logger.info(f"  - Current Phase: {project.current_phase_id[:8] if project.current_phase_id else 'None'}...")

    if phases:
        for phase_id, phase in phases.items():
            logger.info(f"\nPhase: {phase.name}")
            logger.info(f"  - Order: {phase.order}")
            logger.info(f"  - Tasks: {len(phase.task_ids)}")
            logger.info(f"  - Is Current: {phase.is_current}")

    tasks_with_phases = [task for task in tasks.values() if task.phase_id]
    logger.info(f"\nTasks with phase assignments: {len(tasks_with_phases)}/{len(tasks)}")

    return len(projects) > 0 and len(phases) > 0 and len(tasks) > 0


def test_project_progress_calculation():
    """Test calculating project progress from tasks"""
    logger.info("\n=== TEST 8: Project Progress Calculation ===")

    projects = load_projects_from_json(logger)

    if not projects:
        logger.error("No projects found to test")
        return False

    project = list(projects.values())[0]
    progress = project.get_progress_percentage()
    total_tasks = project.get_total_tasks()
    completed_tasks = project.get_completed_tasks()

    logger.info(f"Project: {project.title}")
    logger.info(f"  - Total Tasks: {total_tasks}")
    logger.info(f"  - Completed Tasks: {completed_tasks}")
    logger.info(f"  - Progress: {progress:.1f}%")

    return True


def test_phase_progress_calculation():
    """Test calculating phase progress from tasks"""
    logger.info("\n=== TEST 9: Phase Progress Calculation ===")

    phases = load_phases_from_json(logger)

    if not phases:
        logger.error("No phases found to test")
        return False

    for phase in phases.values():
        progress = phase.get_progress_percentage()
        total_tasks = phase.get_task_count()
        completed_tasks = phase.get_completed_task_count()

        logger.info(f"Phase: {phase.name}")
        logger.info(f"  - Total Tasks: {total_tasks}")
        logger.info(f"  - Completed Tasks: {completed_tasks}")
        logger.info(f"  - Progress: {progress:.1f}%")

    return True


def test_task_phase_relationships():
    """Test task methods for getting project and phase"""
    logger.info("\n=== TEST 10: Task-Phase-Project Relationships ===")

    tasks = load_tasks_from_json(logger)

    if not tasks:
        logger.error("No tasks found to test")
        return False

    # Get first task with a phase
    test_task = None
    for task in tasks.values():
        if task.phase_id:
            test_task = task
            break

    if not test_task:
        logger.error("No tasks with phase assignments found")
        return False

    logger.info(f"Task: {test_task.title}")

    # Test get_phase()
    phase = test_task.get_phase()
    if phase:
        logger.info(f"  ✓ get_phase() returned: {phase.name}")
    else:
        logger.error(f"  ✗ get_phase() failed")
        return False

    # Test get_project()
    project = test_task.get_project()
    if project:
        logger.info(f"  ✓ get_project() returned: {project.title}")
    else:
        logger.error(f"  ✗ get_project() failed")
        return False

    return True


def test_move_task_between_phases():
    """Test moving a task from one phase to another"""
    logger.info("\n=== TEST 11: Moving Task Between Phases ===")

    phases = load_phases_from_json(logger)
    tasks = load_tasks_from_json(logger)

    if len(phases) < 2 or not tasks:
        logger.error("Need at least 2 phases and 1 task for this test")
        return False

    # Get a task from the first phase
    phase_list = sorted(phases.values(), key=lambda p: p.order)
    source_phase = phase_list[0]
    target_phase = phase_list[1]

    if not source_phase.task_ids:
        logger.error(f"Source phase '{source_phase.name}' has no tasks")
        return False

    task_id = source_phase.task_ids[0]
    task = tasks.get(task_id)

    if not task:
        logger.error(f"Task {task_id} not found")
        return False

    logger.info(f"Moving task '{task.title}' from '{source_phase.name}' to '{target_phase.name}'")

    # Move the task
    success = move_task_to_phase(task_id, target_phase.id, logger)

    if success:
        logger.info(f"✓ Task moved successfully")

        # Verify the move
        updated_phases = load_phases_from_json(logger)
        updated_tasks = load_tasks_from_json(logger)
        updated_task = updated_tasks.get(task_id)

        if updated_task.phase_id == target_phase.id:
            logger.info(f"✓ Verified: task.phase_id updated correctly")
        else:
            logger.error(f"✗ Verification failed: task.phase_id not updated")
            return False

        if task_id in updated_phases[target_phase.id].task_ids:
            logger.info(f"✓ Verified: task added to target phase")
        else:
            logger.error(f"✗ Verification failed: task not in target phase")
            return False

        if task_id not in updated_phases[source_phase.id].task_ids:
            logger.info(f"✓ Verified: task removed from source phase")
        else:
            logger.error(f"✗ Verification failed: task still in source phase")
            return False

        return True
    else:
        logger.error(f"✗ Failed to move task")
        return False


def run_all_tests():
    """Run all test functions"""
    logger.info("=" * 70)
    logger.info("PROJECTS MODULE - PHASE 1 TEST SUITE")
    logger.info("=" * 70)

    try:
        # Create test data
        project = test_project_creation()
        phases = test_phase_creation(project.id)
        tasks = test_task_creation_with_phases(project.id, [p.id for p in phases])

        # Save data
        test_project_serialization(project, phases)
        test_phase_serialization(phases, tasks)
        test_task_serialization(tasks)

        # Load and verify data
        test_data_loading()

        # Test calculations
        test_project_progress_calculation()
        test_phase_progress_calculation()

        # Test relationships
        test_task_phase_relationships()

        # Test operations
        test_move_task_between_phases()

        logger.info("\n" + "=" * 70)
        logger.info("✓ ALL TESTS COMPLETED SUCCESSFULLY")
        logger.info("=" * 70)

        return True

    except Exception as e:
        logger.error(f"\n✗ TEST SUITE FAILED: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
