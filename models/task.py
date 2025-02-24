from datetime import datetime, timedelta
from typing import List, Optional, Dict, Set
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

    def track_time(self, hours: float, user_id: str, description: str = ""):
        """Log time spent on the task."""
        time_log = TimeLog(hours, user_id, description)
        self.time_logs.append(time_log)
        self.actual_hours += hours
        self.modified_date = datetime.now()
        self.modified_by = user_id

    def add_attachment(self, file_path: str, user_id: str, description: str = ""):
        """Add an attachment to the task."""
        attachment = Attachment(file_path, user_id, description)
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

class Attachment:
    def __init__(self, file_path: str, user_id: str, description: str = ""):
        self.id = str(uuid4())
        self.file_path = file_path
        self.user_id = user_id
        self.description = description
        self.upload_date = datetime.now()
        self.file_size: Optional[int] = None 
        self.file_type: Optional[str] = None

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