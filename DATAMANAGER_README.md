# DataManager - Centralized Data Management

## Overview

The DataManager is a singleton class that centralizes all data management for the Project Meridian application. It loads all data once at application startup and provides shared access throughout the app, eliminating redundant file I/O and preventing recursion errors.

## Problem Solved

### Before DataManager:
- Each screen/component loaded data independently by calling `load_tasks_from_json()`, `load_projects_from_json()`, etc.
- This caused:
  - **Recursion errors** when AppConfig was initialized multiple times during data loading
  - **Performance issues** from repeated JSON file reads
  - **Potential data inconsistency** from multiple independent loads

### After DataManager:
- Data is loaded **once** at application startup
- All components share the **same in-memory data**
- Changes are saved immediately to both memory and disk
- No more recursion errors

## Architecture

```
┌─────────────┐
│   main.py   │
│             │
│  MainWindow │
└──────┬──────┘
       │
       │ Creates once at startup
       ▼
┌──────────────────┐
│  DataManager     │  ◄─────── Singleton
│  (Singleton)     │
│                  │
│  ┌────────────┐  │
│  │  _tasks    │  │  In-memory storage
│  │  _projects │  │
│  │  _phases   │  │
│  └────────────┘  │
└────────┬─────────┘
         │
         │ Shared by all components
         ▼
┌────────────────────────────────┐
│  Dashboard  │  Planning  │ ... │
└────────────────────────────────┘
```

## Usage

### Initialization (in main.py)
```python
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)

        # Initialize DataManager once at startup
        self.data_manager = DataManager(self.logger)
        self.logger.info(f"DataManager initialized: {self.data_manager.get_data_summary()}")
```

### In Components (e.g., DashboardScreen)
```python
class DashboardScreen(QWidget):
    def __init__(self, logger, width):
        super().__init__()
        self.logger = logger

        # Get DataManager instance (singleton)
        self.data_manager = DataManager(self.logger)

        # Get data from memory (no file I/O)
        self.tasks = self.data_manager.get_tasks()
        self.projects = self.data_manager.get_projects()
```

### Saving Data
```python
# Save a task (updates both memory and disk)
self.data_manager.save_task(task)

# Save a project
self.data_manager.save_project(project)

# Save a phase
self.data_manager.save_phase(phase)
```

## API Reference

### Task Methods
- `get_tasks() -> Dict[str, Task]` - Get all tasks (returns a **copy**)
- `get_task(task_id: str) -> Optional[Task]` - Get specific task
- `add_task(task: Task)` - Add/update task in memory only
- `save_task(task: Task)` - Save task to memory AND disk
- `remove_task(task_id: str)` - Remove task from memory
- `get_tasks_by_project(project_id: str) -> Dict[str, Task]`
- `get_tasks_by_phase(phase_id: str) -> Dict[str, Task]`
- `get_tasks_by_category(category: str) -> Dict[str, Task]`

### Project Methods
- `get_projects() -> Dict[str, Project]` - Get all projects (returns a **copy**)
- `get_project(project_id: str) -> Optional[Project]` - Get specific project
- `add_project(project: Project)` - Add/update project in memory only
- `save_project(project: Project)` - Save project to memory AND disk
- `remove_project(project_id: str)` - Remove project from memory

### Phase Methods
- `get_phases() -> Dict[str, Phase]` - Get all phases (returns a **copy**)
- `get_phase(phase_id: str) -> Optional[Phase]` - Get specific phase
- `get_phases_by_project(project_id: str) -> Dict[str, Phase]`
- `add_phase(phase: Phase)` - Add/update phase in memory only
- `save_phase(phase: Phase)` - Save phase to memory AND disk
- `remove_phase(phase_id: str)` - Remove phase from memory

### Utility Methods
- `reload_all_data()` - Reload all data from disk (use sparingly)
- `get_data_summary() -> dict` - Get summary of all data in memory

## Files Modified

### New File
- `utils/data_manager.py` - The centralized data manager

### Modified Files
1. **main.py**
   - Added DataManager initialization in MainWindow.__init__()

2. **ui/dashboard_screen.py**
   - Replaced `load_tasks_from_json()` calls with `DataManager.get_tasks()`
   - Replaced `load_projects_from_json()` with `DataManager.get_projects()`
   - Uses DataManager instance throughout

3. **ui/task_files/task_card_expanded.py**
   - Replaced `save_task_to_json()` with `DataManager.save_task()`
   - Replaced `load_tasks_from_json()` with `DataManager.get_tasks()`
   - Replaced `load_projects_from_json()` with `DataManager.get_projects()`
   - Replaced `load_phases_from_json()` with `DataManager.get_phases()`

4. **utils/categories_config.py**
   - Removed dependency on AppConfig
   - Now calculates app data directory path directly
   - Eliminates recursion potential

## Benefits

1. **Performance**: Data loaded once, not on every screen switch
2. **Consistency**: All components see the same data
3. **Simplicity**: Single source of truth for all data
4. **No Recursion**: AppConfig only initialized once
5. **Memory Efficient**: Shared data, not duplicated
6. **Maintainability**: Centralized data access logic

## Migration Notes

When adding new features:
- Always use DataManager instead of direct file I/O
- Call `save_*()` methods to persist changes
- Use `get_*()` methods to retrieve data
- Never call `load_*_from_json()` directly in components

## Example: Adding a New Screen

```python
class NewScreen(QWidget):
    def __init__(self, logger):
        super().__init__()
        self.logger = logger

        # Get DataManager instance
        self.data_manager = DataManager(logger)

        # Access data
        tasks = self.data_manager.get_tasks()
        projects = self.data_manager.get_projects()

    def save_something(self, task):
        # Save changes
        self.data_manager.save_task(task)
```

## Troubleshooting

### Data not updating across screens?
- Make sure you're using `save_*()` methods, not just `add_*()`
- Verify all screens use the same DataManager instance (singleton)

### Performance issues?
- Check if you're calling `reload_all_data()` too frequently
- Consider using `get_*()` methods which return references (no copying)

### Data lost after restart?
- Ensure `save_*()` methods are being called
- Check file permissions in AppData directory
