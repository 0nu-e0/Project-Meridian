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
# File: task.py
# Description: Object used to define the functionality of tasks. 
# Author: Jereme Shaver
# -----------------------------------------------------------------------------
import os, mimetypes, re
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Set, Tuple
from enum import Enum
from uuid import uuid4
from PyQt5.QtCore import QObject, pyqtSignal

class TaskPriority(Enum):
    CRITICAL = 5
    HIGH = 4
    MEDIUM = 3
    LOW = 2
    TRIVIAL = 1

class TaskStatus(Enum):
    NOT_STARTED = "Not Started"
    IN_PROGRESS = "In Progress"
    IN_REVIEW = "In Review"
    BLOCKED = "Blocked"
    COMPLETED = "Completed"
    ON_HOLD = "On Hold"
    CANCELLED = "Cancelled"

class TaskCategory(Enum):
    FEATURE = "Feature"
    BUG = "Bug"
    MAINTENANCE = "Maintenance"
    DOCUMENTATION = "Documentation"
    RESEARCH = "Research"
    MEETING = "Meeting"
    ECO = "ECO"
    ERP_CHANGE = "ERP Change"
    BORIDE_SHAPING = "Boride Shaping"
    DRAWING_UPDATE = "Drawing Update"
    CAPA = "CAPA"
    BUILD_FIXTURE = "Build Fixture"
    WORK_INSTRUCTION = "Work Instruction"
    LAB_TESTING = "Lab Testing"
    PROJECTS = "Projects"
    ARCHIVED = "Archived"

class DueStatus(Enum):
   OVERDUE = "Overdue"
   DUE_SOON = "Due Soon"
   UPCOMING = "Upcoming"
   FAR_FUTURE = "Far Future"
   NO_DUE_DATE = "No Due Date"

class Task(QObject):

    def __init__(
        self,
        title: str,
        description: str = "",
        project_id: str = None,
        category = TaskCategory.FEATURE  # Can be TaskCategory enum or string
    ):
        # Initialize QObject parent class
        super().__init__()

        # Unique identifiers
        self.id = str(uuid4())
        self.project_id = project_id
        self.phase_id: Optional[str] = None  # Phase within project

        # Basic information
        self.title = title
        self.description = description
        # Support both enum and string categories for dynamic categories
        if isinstance(category, str):
            # Try to convert string to enum for backward compatibility
            category_enum = None
            for cat in TaskCategory:
                if cat.value == category:
                    category_enum = cat
                    break
            self.category = category_enum if category_enum else category
        else:
            self.category = category
        
        # Dates and timing
        self.creation_date = datetime.now()
        self.due_date: Optional[datetime] = None
        self.start_date: Optional[datetime] = None
        self.completion_date: Optional[datetime] = None
        self.estimated_hours: float = 0.0
        self.actual_hours: float = 0.0
        self.reminder_date: Optional[datetime] = None
        
        # Status and priority
        self.status = TaskStatus.NOT_STARTED
        self.priority = TaskPriority.MEDIUM
        self.percentage_complete: int = 0
        self.archived: bool = False
        
        # Dependencies and relationships
        self.parent_task_id: Optional[str] = None
        self.subtasks: List['Task'] = []
        self.dependencies: Set[str] = set()  # IDs of tasks that must be completed first
        self.blocked_by: Set[str] = set()    # IDs of tasks blocking this one
        
        # Assignment and collaboration
        self.assignee: Optional[str] = None
        self.creator: Optional[str] = None
        self.watchers: Set[str] = set()      # Users following this task
        self.collaborators: Set[str] = set()  # Users working on this task
        
        # Tracking and history
        self.entries: List[TaskEntry] = []    # Comments and updates
        self.time_logs: List[TimeLog] = []    # Time tracking entries
        self.attachments: List[Attachment] = []
        self.tags: Set[str] = set()
        self.modified_date = datetime.now()
        self.modified_by: Optional[str] = None
        
        # Custom fields for flexibility
        self.custom_fields: Dict[str, any] = {}
        
        # Metrics and planning
        self.story_points: Optional[int] = None
        self.cost_estimate: float = 0.0
        self.actual_cost: float = 0.0
        self.sprint_id: Optional[str] = None
        self.milestone_id: Optional[str] = None

        # Checklist items
        self.checklist: List[Dict[str, any]] = []

        # Per-task section visibility settings (key → bool, default True/visible)
        self.visible_sections: Dict[str, bool] = {}

        self.check_archived()

    def to_dict(self) -> dict:
        """Serialize Task to a dictionary matching the tasks JSON file format."""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'project_id': self.project_id,
            'phase_id': self.phase_id,
            'category': self.category.value if isinstance(self.category, TaskCategory) else (self.category if isinstance(self.category, str) else TaskCategory.FEATURE.value),
            'creation_date': self.creation_date.strftime('%Y-%m-%d, %H:%M:%S') if self.creation_date else None,
            'start_date': self.start_date.strftime('%Y-%m-%d, %H:%M:%S') if self.start_date else None,
            'due_date': self.due_date.strftime('%Y-%m-%d, %H:%M:%S') if self.due_date else None,
            'completion_date': self.completion_date.strftime('%Y-%m-%d, %H:%M:%S') if self.completion_date else None,
            'reminder_date': self.reminder_date.strftime('%Y-%m-%d, %H:%M:%S') if self.reminder_date else None,
            'modified_date': self.modified_date.strftime('%Y-%m-%d, %H:%M:%S') if self.modified_date else None,
            'status': self.status.name if self.status else TaskStatus.NOT_STARTED.name,
            'priority': self.priority.name if self.priority else TaskPriority.MEDIUM.name,
            'percentage_complete': self.percentage_complete,
            'estimated_hours': self.estimated_hours,
            'actual_hours': self.actual_hours,
            'cost_estimate': self.cost_estimate,
            'actual_cost': self.actual_cost,
            'assignee': self.assignee,
            'creator': self.creator,
            'modified_by': self.modified_by,
            'parent_task_id': self.parent_task_id,
            'sprint_id': self.sprint_id,
            'milestone_id': self.milestone_id,
            'story_points': self.story_points,
            'dependencies': list(self.dependencies),
            'blocked_by': list(self.blocked_by),
            'watchers': list(self.watchers),
            'collaborators': list(self.collaborators),
            'tags': list(self.tags),
            'custom_fields': self.custom_fields,
            'attachments': [
                {
                    'path_or_url': a.path_or_url,
                    'file_name': os.path.basename(a.path_or_url),
                    'added_date': a.upload_date.strftime('%m/%d/%Y %H:%M'),
                    'added_by': a.user_id,
                    'file_type': a.file_type,
                }
                for a in self.attachments
            ],
            'checklist': [
                {'text': item['text'], 'checked': item.get('checked', False)}
                if isinstance(item, dict) else {'text': item, 'checked': False}
                for item in self.checklist
            ],
            'visible_sections': self.visible_sections,
            'time_logs': [
                {
                    'id': log.id,
                    'hours': log.hours,
                    'user_id': log.user_id,
                    'description': log.description,
                    'timestamp': log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                }
                for log in self.time_logs
            ],
            'activities': [
                {
                    'text': entry.content,
                    'timestamp': entry.timestamp.strftime('%m/%d/%Y %H:%M'),
                    'type': entry.entry_type,
                    'edited': entry.edited,
                    'edit_timestamp': entry.edit_timestamp.strftime('%m/%d/%Y %H:%M') if entry.edit_timestamp else None,
                    'user_id': entry.user_id,
                }
                for entry in self.entries
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Task':
        """Deserialize a Task from a dictionary (inverse of to_dict)."""
        task = cls(
            title=data.get('title', 'Untitled'),
            description=data.get('description', ''),
            project_id=data.get('project_id'),
        )

        if 'id' in data:
            task.id = data['id']
        task.phase_id = data.get('phase_id')

        if 'status' in data:
            status_value = data['status'].replace(' ', '_').upper()
            try:
                task.status = TaskStatus[status_value]
            except KeyError:
                task.status = TaskStatus.NOT_STARTED

        if 'priority' in data:
            try:
                task.priority = TaskPriority[data['priority'].upper()]
            except KeyError:
                task.priority = TaskPriority.MEDIUM

        if 'category' in data:
            category_value = data['category']
            try:
                task.category = TaskCategory[category_value.replace(' ', '_').upper()]
            except KeyError:
                task.category = category_value

        date_fields = ['creation_date', 'start_date', 'due_date', 'completion_date', 'reminder_date', 'modified_date']
        for field in date_fields:
            raw = data.get(field)
            if raw:
                for fmt in ('%Y-%m-%d, %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S'):
                    try:
                        setattr(task, field, datetime.strptime(raw, fmt))
                        break
                    except ValueError:
                        continue

        for field in ['assignee', 'creator', 'modified_by', 'parent_task_id', 'sprint_id', 'milestone_id']:
            if field in data:
                setattr(task, field, data[field])

        task.percentage_complete = data.get('percentage_complete', 0)
        task.estimated_hours = float(data.get('estimated_hours', 0.0))
        task.actual_hours = float(data.get('actual_hours', 0.0))
        task.cost_estimate = float(data.get('cost_estimate', 0.0))
        task.actual_cost = float(data.get('actual_cost', 0.0))
        task.story_points = data.get('story_points')

        task.dependencies = set(data.get('dependencies', []))
        task.blocked_by = set(data.get('blocked_by', []))
        task.watchers = set(data.get('watchers', []))
        task.collaborators = set(data.get('collaborators', []))
        task.tags = set(data.get('tags', []))
        task.custom_fields = data.get('custom_fields', {})

        task.attachments = []
        for a in data.get('attachments', []):
            attachment = Attachment(
                path_or_url=a['path_or_url'],
                user_id=a.get('added_by', 'System'),
                description=a.get('file_name', ''),
            )
            if 'added_date' in a:
                try:
                    attachment.upload_date = datetime.strptime(a['added_date'], '%m/%d/%Y %H:%M')
                except ValueError:
                    pass
            attachment.file_type = a.get('file_type')
            task.attachments.append(attachment)

        task.visible_sections = data.get('visible_sections', {})

        task.checklist = []
        for item in data.get('checklist', []):
            if isinstance(item, dict) and 'text' in item:
                task.checklist.append({'text': item['text'], 'checked': item.get('checked', False)})
            elif isinstance(item, str):
                task.checklist.append({'text': item, 'checked': False})

        task.time_logs = []
        for log_data in data.get('time_logs', []):
            log = TimeLog(
                hours=log_data.get('hours', 0),
                user_id=log_data.get('user_id', 'System'),
                description=log_data.get('description', ''),
            )
            if 'id' in log_data:
                log.id = log_data['id']
            if 'timestamp' in log_data:
                try:
                    log.timestamp = datetime.strptime(log_data['timestamp'], '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    pass
            task.time_logs.append(log)

        task.entries = []
        for entry_data in data.get('activities', []):
            entry = TaskEntry(
                content=entry_data.get('text', ''),
                entry_type=entry_data.get('type', 'comment'),
                user_id=entry_data.get('user_id', 'System'),
            )
            if 'timestamp' in entry_data:
                try:
                    entry.timestamp = datetime.strptime(entry_data['timestamp'], '%m/%d/%Y %H:%M')
                except ValueError:
                    pass
            entry.edited = entry_data.get('edited', False)
            if entry.edited and entry_data.get('edit_timestamp'):
                try:
                    entry.edit_timestamp = datetime.strptime(entry_data['edit_timestamp'], '%m/%d/%Y %H:%M')
                except ValueError:
                    pass
            task.entries.append(entry)

        return task

    def check_archived(self):
        # print(f"checking for archived for {self.title}, with category: {self.status}")

        # Don't automatically archive completed tasks - they should stay in their phase
        # Users can manually archive tasks if needed
        pass

    def add_checklist_item(self, text: str, checked: bool = False):
        self.checklist.append({
            'text': text,
            'checked': checked
        })
            
    def update_checklist_item(self, index: int, text: str = None, checked: bool = None):
        """Update an existing checklist item."""
        if 0 <= index < len(self.checklist):
            if text is not None:
                self.checklist[index]['text'] = text
            if checked is not None:
                self.checklist[index]['checked'] = checked
            self.modified_date = datetime.now()
            
    def remove_checklist_item(self, index: int):
        """Remove a checklist item by index."""
        if 0 <= index < len(self.checklist):
            self.checklist.pop(index)
            self.modified_date = datetime.now()
            
    def get_checklist_progress(self) -> Tuple[int, int]:
        """Get the number of completed items and total items."""
        total = len(self.checklist)
        completed = sum(1 for item in self.checklist if item.get('checked', False))
        return completed, total

    def track_time(self, hours: float, user_id: str, description: str = ""):
        """Log time spent on the task."""
        time_log = TimeLog(hours, user_id, description)
        self.time_logs.append(time_log)
        self.actual_hours += hours
        self.modified_date = datetime.now()
        self.modified_by = user_id

    def add_attachment(self, path_or_url: str, user_id: str, description: str = ""):
        """Add an attachment to the task."""
        attachment = Attachment(path_or_url, user_id, description)
        self.attachments.append(attachment)
        self.modified_date = datetime.now()
        self.modified_by = user_id

    def calculate_burndown(self) -> float:
        """Calculate remaining work vs time left."""
        if not self.due_date:
            return 0.0
        total_duration = (self.due_date - self.creation_date).days
        if total_duration == 0:
            return 0.0
        remaining_duration = (self.due_date - datetime.now()).days
        return (remaining_duration / total_duration) * (100 - self.percentage_complete)

    def get_project(self):
        """
        Get the project this task belongs to.

        Returns:
            Project object if project_id is set, None otherwise
        """
        if not self.project_id:
            return None

        from utils.projects_io import load_projects_from_json
        from logging import getLogger

        logger = getLogger(__name__)
        projects = load_projects_from_json(logger)

        return projects.get(self.project_id)

    def get_phase(self):
        """
        Get the phase this task belongs to.

        Returns:
            Phase object if phase_id is set, None otherwise
        """
        if not self.phase_id:
            return None

        from utils.projects_io import load_phases_from_json
        from logging import getLogger

        logger = getLogger(__name__)
        phases = load_phases_from_json(logger)

        return phases.get(self.phase_id)

class TimeLog:
    def __init__(self, hours: float, user_id: str, description: str = ""):
        self.id = str(uuid4())
        self.hours = hours
        self.user_id = user_id
        self.description = description
        self.timestamp = datetime.now()

class AttachmentType:
    FILE = "file"
    DIRECTORY = "directory"
    HYPERLINK = "hyperlink"

class Attachment:
    def __init__(self, path_or_url: str, user_id: str, description: str = ""):
        self.id = str(uuid4())
        self.path_or_url = path_or_url  
        self.user_id = user_id
        self.description = description
        self.upload_date = datetime.now()

        # Determine attachment type
        self.attachment_type = self._detect_type(path_or_url)

        # File-specific attributes
        # self.file_size: Optional[int] = None
        self.file_type: Optional[str] = None
        
        # if self.attachment_type == AttachmentType.FILE:
        #     self._process_file()
        # elif self.attachment_type == AttachmentType.DIRECTORY:
        #     self._process_directory()
        # elif self.attachment_type == AttachmentType.HYPERLINK:
        #     self._process_hyperlink()

    def _detect_type(self, path_or_url: str) -> str:
        """Classifies the attachment without checking validity."""

        normalized_path = os.path.normpath(path_or_url)

        # Assume hyperlinks if they start with "http" or "www"
        if path_or_url.startswith(("http", "www")):
            return AttachmentType.HYPERLINK

        # If the path has a file extension, classify it as a file
        if os.path.splitext(normalized_path)[1]:
            return AttachmentType.FILE

        # Otherwise, assume it's a directory
        return AttachmentType.DIRECTORY

    def _process_file(self):
        """Retrieves file size and type for file attachments."""
        # self.file_size = os.path.getsize(self.path_or_url)  # File size in bytes
        self.file_type = mimetypes.guess_type(self.path_or_url)[0]  # Detect MIME type

    def _process_directory(self):
        """Counts files in the directory and sets a relevant description."""
        file_count = len([f for f in os.listdir(self.path_or_url) if os.path.isfile(os.path.join(self.path_or_url, f))])
        self.description = f"Directory containing {file_count} files."

    def _process_hyperlink(self):
        """No file properties for hyperlinks, but can sanitize input."""
        self.path_or_url = self.path_or_url.strip()  # Clean whitespace if needed

    @staticmethod
    def _is_valid_url(url: str) -> bool:
        """Checks if a string is a valid URL."""
        url_regex = re.compile(
            r"^(https?|ftp)://"  # Protocol
            r"([a-zA-Z0-9.-]+)"  # Domain
            r"(:[0-9]+)?"  # Port (optional)
            r"(/.*)?$",  # Path (optional)
            re.IGNORECASE
        )
        return re.match(url_regex, url) is not None

class Project:
    def __init__(self, name: str):
        self.id = str(uuid4())
        self.name = name
        self.tasks: List[Task] = []
        self.sprints: List[Sprint] = []
        self.milestones: List[Milestone] = []
        self.team_members: Set[str] = set()

class Sprint:
    def __init__(self, name: str, start_date: datetime, end_date: datetime):
        self.id = str(uuid4())
        self.name = name
        self.start_date = start_date
        self.end_date = end_date
        self.tasks: List[str] = []  # Task IDs

class Milestone:
    def __init__(self, name: str, due_date: datetime):
        self.id = str(uuid4())
        self.name = name
        self.due_date = due_date
        self.tasks: List[str] = []  # Task IDs

class TaskEntry:
    def __init__(self, content: str, entry_type: str = "comment", user_id: str = None):
        self.id = str(uuid4())
        self.content = content
        self.entry_type = entry_type  # comment, status_change, assignment_change, etc.
        self.user_id = user_id
        self.timestamp = datetime.now()
        self.edited = False
        self.edit_timestamp: Optional[datetime] = None
        self.attachments: List[Attachment] = []
        self.mentions: Set[str] = set()  # User IDs mentioned in the entry
        
    def edit(self, new_content: str, user_id: str):
        """Edit the entry content."""
        self.content = new_content
        self.edited = True
        self.edit_timestamp = datetime.now()
    
    def add_attachment(self, attachment: Attachment):
        """Add an attachment to the entry."""
        self.attachments.append(attachment)
    
    def __str__(self):
        edited_str = " (edited)" if self.edited else ""
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M')}] {self.content}{edited_str}"