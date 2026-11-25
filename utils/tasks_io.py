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
# File: tasks_io.py
# Description: Used to load and save tasks to the saved_task.json file.
# Author: Jereme Shaver
# -----------------------------------------------------------------------------


import os
from datetime import datetime
from utils.app_config import AppConfig
from utils.safe_io import parse_records, read_json, write_json
from models.task import Task, TaskCategory

# Global cache for tasks to avoid redundant file I/O
_tasks_cache = None
_tasks_cache_mtime = None

def invalidate_tasks_cache():
    """Invalidate the global tasks cache, forcing a reload on next access"""
    global _tasks_cache, _tasks_cache_mtime
    _tasks_cache = None
    _tasks_cache_mtime = None

def _parse_task(key, raw):
    # Very old files had no 'id' field; the file key is the only stable identifier
    if isinstance(raw, dict) and 'id' not in raw:
        raw = {**raw, 'id': key}
    return Task.from_dict(raw)

def load_tasks_from_json(logger, force_reload=False):
    """
    Load tasks from JSON file into Task objects with caching

    Args:
        logger: Logger instance
        force_reload: If True, bypass cache and reload from disk

    Returns:
        dict: Dictionary with task IDs as keys and Task objects as values, sorted by priority
    """
    global _tasks_cache, _tasks_cache_mtime

    json_file_path = AppConfig().tasks_file

    if not os.path.exists(json_file_path):
        logger.debug(f"No task file yet at: {json_file_path}")
        return {}

    current_mtime = os.path.getmtime(json_file_path)

    # Return cached data if available and file hasn't changed
    if not force_reload and _tasks_cache is not None and _tasks_cache_mtime == current_mtime:
        logger.debug("Using cached tasks (file unchanged)")
        return _tasks_cache

    logger.info(f"Attempting to load tasks from: {json_file_path}")
    tasks_data = read_json(json_file_path, logger)

    # One bad record is skipped and kept on disk, rather than hiding every task
    parsed = parse_records(json_file_path, tasks_data, _parse_task, logger)
    task_objects = {task.id: task for task in parsed.values()}
    logger.info(f"Loaded {len(task_objects)} of {len(tasks_data)} tasks from {json_file_path}")

    # Sort tasks by priority
    sorted_tasks = dict(sorted(task_objects.items(), key=lambda item: item[1].priority.value, reverse=True))

    # The file may have been moved aside as unreadable, so re-check before caching
    if os.path.exists(json_file_path):
        _tasks_cache = sorted_tasks
        _tasks_cache_mtime = os.path.getmtime(json_file_path)

    return sorted_tasks

def save_task_to_json(task, logger):
    """
    Save a Task object to the JSON file in the user's app data directory

    Args:
        task: The Task object to save (can be new or existing)
    """
    if task is None:
        task = Task(title="New Task", description="", category=TaskCategory.FEATURE)

    json_file_path = AppConfig().tasks_file
    logger.info(f"Attempting to save task to: {json_file_path}")

    # Completed tasks are archived; their category is left alone
    task.update_archived()

    task.modified_date = datetime.now()

    # Clean up None values for cleaner JSON
    task_data = {k: v for k, v in task.to_dict().items() if v is not None}

    # Read the raw file so records this version can't parse are written back untouched
    tasks_data = read_json(json_file_path, logger)
    tasks_data[task.id] = task_data

    if not write_json(json_file_path, tasks_data, logger):
        return False

    invalidate_tasks_cache()
    logger.info(f"Task saved to {json_file_path}")
    return True

def save_tasks_to_json(tasks, logger):
    """Save several tasks in one write (all or nothing). Returns True on success."""
    json_file_path = AppConfig().tasks_file
    tasks_data = read_json(json_file_path, logger)
    for task in tasks:
        task.update_archived()
        tasks_data[task.id] = {k: v for k, v in task.to_dict().items() if v is not None}
    if not write_json(json_file_path, tasks_data, logger):
        return False
    invalidate_tasks_cache()
    return True

def update_task_fields(task_id, fields, logger):
    """
    Save just some fields of an already-saved task, leaving everything else on disk
    as it was. Used for changes that apply immediately (like ticking a checklist
    item) while other edits to the task are still unsaved.

    Returns:
        True if saved, False if the task isn't on disk yet or the save failed
    """
    json_file_path = AppConfig().tasks_file
    tasks_data = read_json(json_file_path, logger)
    if not isinstance(tasks_data.get(task_id), dict):
        return False

    tasks_data[task_id].update(fields)
    if not write_json(json_file_path, tasks_data, logger):
        return False

    invalidate_tasks_cache()
    return True

def delete_task_from_json(task_id, logger):
    """
    Delete a task by ID.

    Returns:
        True if the task was deleted, False if it wasn't found or the save failed
    """
    json_file_path = AppConfig().tasks_file
    tasks_data = read_json(json_file_path, logger)

    if task_id not in tasks_data:
        logger.warning(f"Task {task_id} not found in {json_file_path}")
        return False

    del tasks_data[task_id]

    # Drop references from other tasks in the same write
    for raw in tasks_data.values():
        if isinstance(raw, dict):
            for field in ('dependencies', 'blocked_by'):
                if isinstance(raw.get(field), list) and task_id in raw[field]:
                    raw[field] = [ref for ref in raw[field] if ref != task_id]

    if not write_json(json_file_path, tasks_data, logger):
        return False

    invalidate_tasks_cache()
    _remove_task_references(task_id, logger)
    logger.info(f"Deleted task {task_id}")
    return True

def _remove_task_references(task_id, logger):
    """Remove a deleted task from the planning schedule"""
    schedule_path = os.path.join(AppConfig().data_dir, "scheduled_tasks.json")
    if os.path.exists(schedule_path):
        schedule = read_json(schedule_path, logger)
        remaining = {sid: entry for sid, entry in schedule.items()
                     if not (isinstance(entry, dict) and entry.get('task_id') == task_id)}
        if len(remaining) != len(schedule):
            write_json(schedule_path, remaining, logger)
