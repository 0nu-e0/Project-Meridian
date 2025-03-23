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
    ARCHIVED = "Archived"

class DueStatus(Enum):
   OVERDUE = "Overdue"
   DUE_SOON = "Due Soon"
   UPCOMING = "Upcoming"
   FAR_FUTURE = "Far Future"
   NO_DUE_DATE = "No Due Date"

class Task(QObject):
    removeTaskCardSignal = pyqtSignal(str)
    
    def __init__(
        self,
        title: str,
        description: str = "",
        project_id: str = None,
        category: TaskCategory = TaskCategory.FEATURE
    ):
        # Unique identifiers
        self.id = str(uuid4())
        self.project_id = project_id
        
        # Basic information
        self.title = title
        self.description = description
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

        # Comment Activities
        self.entries: List[TaskEntry] = []    
        self.time_logs: List[TimeLog] = [] 

        # Checklist items
        self.checklist: List[Dict[str, any]] = [] 

        self.check_archived()

    def check_archived(self):
        # print(f"checking for archived for {self.title}, with category: {self.status}")
        
        if self.status == TaskStatus.COMPLETED:
            self.archived = True
            self.category = TaskCategory.ARCHIVED

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
        remaining_duration = (self.due_date - datetime.now()).days
        return (remaining_duration / total_duration) * (100 - self.percentage_complete)

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