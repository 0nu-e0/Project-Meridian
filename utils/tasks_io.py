# -----------------------------------------------------------------------------
# Project Maridian
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
# File: task.io.py
# Description: Used to load and save tasks to the saved_task.json file.
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

import os, json
from uuid import uuid4
from datetime import datetime
from utils.app_config import AppConfig
from utils.directory_finder import resource_path
from models.task import Task, TaskStatus, TaskPriority, TaskCategory, Attachment, TaskEntry, TimeLog

def load_tasks_from_json(logger):
    """
    Load tasks from JSON file into Task objects

    Returns:
        dict: Dictionary with task titles as keys and Task objects as values, sorted by priority
    """
    from utils.app_config import AppConfig

    task_objects = {}

    # Get the file path from AppConfig
    app_config = AppConfig()
    json_file_path = app_config.tasks_file

    # logger.info(f"Attempting to load tasks from: {json_file_path}")

    # Check if file exists
    if not os.path.exists(json_file_path):
        logger.warning(f"Task file not found at: {json_file_path}")
        return {}

    try:
        # Read the JSON file
        with open(json_file_path, 'r') as file:
            tasks_data = json.load(file)

        # logger.info(f"Successfully loaded {len(tasks_data)} tasks from {json_file_path}")

        # Convert each task data to Task object
        for task_key, task_info in tasks_data.items():
            # Get the title from the task info or use the key as fallback
            task_name = task_info.get('title', task_key)

            # Create base Task object
            task = Task(
                title=task_name,
                description=task_info.get('description', ''),
                project_id=task_info.get('project_id', None)
            )

            # Set ID if available, otherwise use the generated one
            if 'id' in task_info:
                task.id = task_info['id']

            # Set enum values
            if 'status' in task_info:
                status_value = task_info['status'].replace(" ", "_").upper()
                task.status = TaskStatus[status_value]

            if 'priority' in task_info:
                priority_value = task_info['priority'].upper()
                task.priority = TaskPriority[priority_value]

            if 'category' in task_info:
                category_value = task_info['category'].replace(" ", "_").upper()
                task.category = TaskCategory[category_value]

            # Set numeric values
            if 'percentage_complete' in task_info:
                percentage = task_info['percentage_complete']
                if isinstance(percentage, str):
                    task.percentage_complete = int(percentage.rstrip('%'))
                else:
                    task.percentage_complete = percentage

            if 'estimated_hours' in task_info:
                task.estimated_hours = float(task_info['estimated_hours'])

            if 'actual_hours' in task_info:
                task.actual_hours = float(task_info['actual_hours'])

            if 'cost_estimate' in task_info:
                task.cost_estimate = float(task_info['cost_estimate'])

            if 'actual_cost' in task_info:
                task.actual_cost = float(task_info['actual_cost'])

            # Set date values
            date_fields = {
                'creation_date': '%Y-%m-%d, %H:%M:%S',
                'start_date': '%Y-%m-%d, %H:%M:%S',
                'due_date': '%Y-%m-%d, %H:%M:%S',
                'completion_date': '%Y-%m-%d, %H:%M:%S',
                'reminder_date': '%Y-%m-%d, %H:%M:%S',
                'modified_date': '%Y-%m-%d, %H:%M:%S'
            }

            for field, format_str in date_fields.items():
                if field in task_info and task_info[field]:
                    try:
                        setattr(task, field, datetime.strptime(task_info[field], format_str))
                    except ValueError:
                        # Handle potential format issues
                        logger.warning(f"Could not parse date for {field} in task {task_name}")

            # Set string values
            string_fields = ['assignee', 'creator', 'modified_by', 'sprint_id', 'milestone_id', 'parent_task_id']
            for field in string_fields:
                if field in task_info:
                    setattr(task, field, task_info[field])

            # Set collection values
            if 'dependencies' in task_info:
                task.dependencies = set(task_info['dependencies'])

            if 'blocked_by' in task_info:
                task.blocked_by = set(task_info['blocked_by'])

            if 'watchers' in task_info:
                task.watchers = set(task_info['watchers'])

            if 'collaborators' in task_info:
                task.collaborators = set(task_info['collaborators'])

            if 'team_members' in task_info:
                task.collaborators = set(task_info['team_members'])

            if 'tags' in task_info:
                task.tags = set(task_info['tags'])

            # Set custom fields
            if 'custom_fields' in task_info:
                task.custom_fields = task_info['custom_fields']

            # Add attachments
            if 'attachments' in task_info:
                for attachment_data in task_info['attachments']:
                    attachment = Attachment(
                        file_path=attachment_data['file_path'],
                        user_id=attachment_data.get('added_by', 'System'),
                        description=attachment_data.get('file_name', '')
                    )

                    if 'added_date' in attachment_data:
                        try:
                            attachment.upload_date = datetime.strptime(attachment_data['added_date'], '%m/%d/%Y %H:%M')
                        except ValueError:
                            attachment.upload_date = datetime.now()

                    if 'file_size' in attachment_data:
                        attachment.file_size = attachment_data['file_size']

                    if 'file_type' in attachment_data:
                        attachment.file_type = attachment_data['file_type']

                    task.attachments.append(attachment)

            if 'checklist' in task_info:
                task.checklist = task_info['checklist']
            else:
                task.checklist = []

            # Add the task to our dictionary
            task_objects[task_name] = task

        # Return tasks sorted by priority
        return dict(sorted(task_objects.items(), key=lambda item: item[1].priority.value, reverse=True))

    except Exception as e:
        logger.error(f"Error loading tasks from JSON: {e}")
        return {}

def save_task_to_json(task, logger):
    """
    Save a Task object to the JSON file in the user's app data directory
    
    Args:
        task: The Task object to save (can be new or existing)
    """
    from utils.app_config import AppConfig
    
    # Initialize new task if None
    if task is None:
        task = Task(
            title="New Task",
            description="",
            category=TaskCategory.FEATURE
        )

    # Get the path from AppConfig
    app_config = AppConfig()
    json_file_path = app_config.tasks_file
    
    # Add debug logging
    logger.info(f"Attempting to save task to: {json_file_path}")

    try:
        # Ensure the directory exists
        data_dir = os.path.dirname(json_file_path)
        if not os.path.exists(data_dir):
            logger.info(f"Creating directory: {data_dir}")
            os.makedirs(data_dir, exist_ok=True)
        
        # Read existing data first
        tasks_data = {}
        if os.path.exists(json_file_path):
            with open(json_file_path, 'r') as file:
                tasks_data = json.load(file)
        
        # Convert Task object to dictionary, handling potential None values
        task_data = {
            'id': getattr(task, 'id', str(uuid4())),  # Generate new ID if none exists
            'title': getattr(task, 'title', "New Task"),
            'description': getattr(task, 'description', ""),
            'project_id': getattr(task, 'project_id', None),
            'category': task.category.name if hasattr(task, 'category') and task.category else TaskCategory.FEATURE.name,
            'creation_date': getattr(task, 'creation_date', datetime.now()).strftime('%Y-%m-%d, %H:%M:%S'),
            'start_date': task.start_date.strftime('%Y-%m-%d, %H:%M:%S') if getattr(task, 'start_date', None) else None,
            'due_date': task.due_date.strftime('%Y-%m-%d, %H:%M:%S') if getattr(task, 'due_date', None) else None,
            'completion_date': task.completion_date.strftime('%Y-%m-%d, %H:%M:%S') if getattr(task, 'completion_date', None) else None,
            'reminder_date': task.reminder_date.strftime('%Y-%m-%d, %H:%M:%S') if getattr(task, 'reminder_date', None) else None,
            'status': task.status.name if hasattr(task, 'status') and task.status else TaskStatus.NOT_STARTED.name,
            'priority': task.priority.name if hasattr(task, 'priority') and task.priority else TaskPriority.MEDIUM.name,
            'percentage_complete': getattr(task, 'percentage_complete', 0),
            'estimated_hours': getattr(task, 'estimated_hours', 0.0),
            'actual_hours': getattr(task, 'actual_hours', 0.0),
            'cost_estimate': getattr(task, 'cost_estimate', 0.0),
            'actual_cost': getattr(task, 'actual_cost', 0.0),
            'assignee': getattr(task, 'assignee', None),
            'creator': getattr(task, 'creator', None),
            'parent_task_id': getattr(task, 'parent_task_id', None),
            'sprint_id': getattr(task, 'sprint_id', None),
            'milestone_id': getattr(task, 'milestone_id', None),
            'story_points': getattr(task, 'story_points', None),
            'modified_date': datetime.now().strftime('%Y-%m-%d, %H:%M:%S'),
            'modified_by': getattr(task, 'modified_by', None),
            'dependencies': list(task.dependencies) if hasattr(task, 'dependencies') and task.dependencies else [],
            'blocked_by': list(task.blocked_by) if hasattr(task, 'blocked_by') and task.blocked_by else [],
            'watchers': list(task.watchers) if hasattr(task, 'watchers') and task.watchers else [],
            'collaborators': list(task.collaborators) if hasattr(task, 'collaborators') and task.collaborators else [],
            'team_members': list(task.collaborators) if hasattr(task, 'collaborators') and task.collaborators else [],
            'tags': list(task.tags) if hasattr(task, 'tags') and task.tags else [],
            'custom_fields': getattr(task, 'custom_fields', {}),
            'attachments': [
                {
                    'file_path': attachment.file_path,
                    'file_name': os.path.basename(attachment.file_path),
                    'added_date': attachment.upload_date.strftime('%m/%d/%Y %H:%M'),
                    'added_by': attachment.user_id,
                    'file_size': attachment.file_size,
                    'file_type': attachment.file_type
                }
                for attachment in getattr(task, 'attachments', [])
            ],
            'checklist': getattr(task, 'checklist', []),
            'time_logs': [
                {
                    'id': log.id,
                    'hours': log.hours,
                    'user_id': log.user_id,
                    'description': log.description,
                    'timestamp': log.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                }
                for log in getattr(task, 'time_logs', [])
            ],
            'activities': [
                {
                    'text': entry.content,
                    'timestamp': entry.timestamp.strftime('%m/%d/%Y %H:%M'),
                    'type': entry.entry_type,
                    'edited': entry.edited,
                    'edit_timestamp': entry.edit_timestamp.strftime('%m/%d/%Y %H:%M') if entry.edit_timestamp else None,
                    'user_id': entry.user_id
                }
                for entry in getattr(task, 'entries', [])
            ]
        }
        
        # Clean up None values for cleaner JSON
        task_data = {k: v for k, v in task_data.items() if v is not None}
        
        # Use ID as the key instead of title to avoid duplicates
        task_id = task_data['id']
        
        # Update the task in the dictionary
        tasks_data[task_id] = task_data
        
        # Write back to file
        with open(json_file_path, 'w') as file:
            json.dump(tasks_data, file, indent=2)
            
        logger.info(f"Task saved to {json_file_path}")
        return True
            
    except Exception as e:
        logger.error(f"Error saving task to JSON: {e}")
        return False