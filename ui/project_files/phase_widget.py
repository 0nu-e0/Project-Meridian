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
# File: phase_widget.py
# Description: Collapsible widget for displaying a project phase
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

from PyQt5.QtCore import QMimeData, Qt, pyqtSignal
from PyQt5.QtGui import QDrag, QDragEnterEvent, QDropEvent
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QMenu, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from models.phase import Phase
from models.project import Project
from resources.styles import AppColors, AppStyles
from ui.custom_widgets import dialogs
from ui.custom_widgets.panel_styles import MENU_STYLE
from ui.project_files.draggable_task_item import TASK_MIME, DraggableTaskItem
from ui.project_files.project_look import CARD_BACKGROUND, CARD_BORDER, badge, progress_bar
from utils.data_history import history
from utils.projects_io import delete_phase, move_task_to_phase, save_phase_fields, set_current_phase
from utils.tasks_io import load_tasks_from_json, save_task_to_json

PHASE_MIME = "application/x-meridian-phase"

ADD_TASK_STYLE = f"""
    QPushButton {{ background: transparent; color: {AppColors.text_muted}; border: 1px dashed {AppColors.surface_hover_alt};
                   border-radius: 6px; padding: 7px; font-size: 12px; }}
    QPushButton:hover {{ color: {AppColors.text_primary}; border-color: {AppColors.accent}; }}"""
ICON_BUTTON_STYLE = f"""
    QPushButton {{ background: transparent; color: {AppColors.text_muted}; border: none; border-radius: 4px;
                   font-size: 15px; padding: 0px 6px; }}
    QPushButton:hover {{ color: {AppColors.text_primary}; background-color: {AppColors.surface_raised}; }}"""


class PhaseWidget(QWidget):
    """A phase of a project: its name, progress, and tasks. Collapse it with the arrow, drag it
    by its handle to reorder, drop tasks on it to move them here; ⋯ (or right-click) for more."""

    phaseUpdated = pyqtSignal(str)  # phase id
    phaseDeleted = pyqtSignal(str)  # phase id
    phaseReordered = pyqtSignal(str, int)  # dragged phase id, the drop target's order
    taskUpdated = pyqtSignal()  # a task in this phase was changed or deleted

    def __init__(self, phase: Phase, project: Project, logger):
        super().__init__()
        self.phase = phase
        self.project = project
        self.logger = logger
        self.is_expanded = not phase.collapsed
        self.tasks = []
        self.drag_start_position = None
        self.setAcceptDrops(True)
        self.loadTasks()
        self.initUI()

    def loadTasks(self):
        """This phase's tasks, unfinished first, then by priority"""
        from models.task import TaskStatus
        done = (TaskStatus.COMPLETED, TaskStatus.CANCELLED)
        self.tasks = sorted((task for task in load_tasks_from_json(self.logger).values()
                             if task.phase_id == self.phase.id),
                            key=lambda t: (t.status in done, -t.priority.value, t.title.lower()))

    # -- layout -----------------------------------------------------------------
    def initUI(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.container = QFrame()
        self.container.setObjectName("phaseCard")
        self.updateContainerStyle()
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(14, 12, 14, 14)
        container_layout.setSpacing(8)

        self.header_widget = QWidget()
        self.header_widget.setStyleSheet("background: transparent;")
        self.header_layout = QVBoxLayout(self.header_widget)
        self.header_layout.setContentsMargins(0, 0, 0, 0)
        self.header_layout.setSpacing(6)
        self.buildHeader()
        container_layout.addWidget(self.header_widget)

        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: transparent;")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 6, 0, 0)
        self.content_layout.setSpacing(6)
        self.tasks_layout = QVBoxLayout()
        self.tasks_layout.setSpacing(6)
        self.content_layout.addLayout(self.tasks_layout)
        self.fillTasks()

        add_task_btn = QPushButton("+  Add task")
        add_task_btn.setToolTip("Add a task to this phase")
        add_task_btn.setCursor(Qt.PointingHandCursor)
        add_task_btn.setStyleSheet(ADD_TASK_STYLE)
        add_task_btn.clicked.connect(self.onAddTask)
        self.content_layout.addWidget(add_task_btn)
        container_layout.addWidget(self.content_widget)
        self.content_widget.setVisible(self.is_expanded)

        main_layout.addWidget(self.container)

    def buildHeader(self):
        while self.header_layout.count():
            item = self.header_layout.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    child = item.layout().takeAt(0)
                    if child.widget():
                        child.widget().hide()
                        child.widget().deleteLater()

        row = QHBoxLayout()
        row.setSpacing(6)
        handle = QLabel("⋮⋮")
        handle.setToolTip("Drag to reorder phases")
        handle.setCursor(Qt.OpenHandCursor)
        handle.setStyleSheet(f"color: {AppColors.text_faint}; font-size: 13px; background: transparent;")
        row.addWidget(handle)

        self.expand_btn = QPushButton("▾" if self.is_expanded else "▸")
        self.expand_btn.setToolTip("Show or hide this phase's tasks")
        self.expand_btn.setCursor(Qt.PointingHandCursor)
        self.expand_btn.setStyleSheet(ICON_BUTTON_STYLE)
        self.expand_btn.setFixedWidth(24)
        self.expand_btn.clicked.connect(self.toggleExpand)
        row.addWidget(self.expand_btn)

        number = QLabel(f"PHASE {self.phase.order + 1}")
        number.setStyleSheet(f"color: {AppColors.text_muted}; font-size: 10px; font-weight: bold; "
                             f"letter-spacing: 1px; background: transparent;")
        row.addWidget(number)
        self.name_label = QLabel(self.phase.name)
        self.name_label.setToolTip(self.phase.name)
        self.name_label.setStyleSheet(f"color: {AppColors.text_primary}; font-size: 15px; font-weight: bold; "
                                      f"background: transparent;")
        self.name_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.name_label.setMinimumWidth(40)
        row.addWidget(self.name_label, 1)
        if self.phase.is_current:
            current = badge("Current", self.project.color)
            current.setToolTip("The phase the project is in now")
            row.addWidget(current)

        self.menu_button = QPushButton("⋯")
        self.menu_button.setToolTip("Edit, make current, delete")
        self.menu_button.setCursor(Qt.PointingHandCursor)
        self.menu_button.setStyleSheet(ICON_BUTTON_STYLE)
        self.menu_button.clicked.connect(
            lambda: self.showMenu(self.menu_button.mapToGlobal(self.menu_button.rect().bottomLeft())))
        row.addWidget(self.menu_button)
        self.header_layout.addLayout(row)

        if self.phase.description:
            description = QLabel(self.phase.description)
            description.setWordWrap(True)
            description.setStyleSheet(f"color: {AppColors.text_muted}; font-size: 12px; background: transparent; "
                                      f"padding-left: 36px;")
            self.header_layout.addWidget(description)

        total = len(self.tasks)
        from models.task import TaskStatus
        done = sum(1 for task in self.tasks if task.status == TaskStatus.COMPLETED)
        progress_row = QHBoxLayout()
        progress_row.setContentsMargins(36, 0, 0, 0)
        progress_row.setSpacing(8)
        progress_row.addWidget(progress_bar(self.project.color, 100 * done / total if total else 0, height=5), 1)
        self.progress_label = QLabel(f"{done}/{total} done" if total else "No tasks")
        self.progress_label.setStyleSheet(f"color: {AppColors.text_muted}; font-size: 11px; background: transparent;")
        progress_row.addWidget(self.progress_label)
        self.header_layout.addLayout(progress_row)

    def fillTasks(self):
        while self.tasks_layout.count():
            item = self.tasks_layout.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().deleteLater()
        if self.tasks:
            for task in self.tasks:
                self.tasks_layout.addWidget(self.createTaskItem(task))
        else:
            empty = QLabel("No tasks yet. Add one, or drag one here from another phase.")
            empty.setWordWrap(True)
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(f"color: {AppColors.text_faint}; font-size: 12px; padding: 8px; background: transparent;")
            self.tasks_layout.addWidget(empty)

    def createTaskItem(self, task):
        item = DraggableTaskItem(task)
        item.clicked.connect(self.onTaskClicked)
        return item

    def updateContainerStyle(self, highlight=None):
        """The box: the project's colour down the side for the current phase; highlight is the
        colour of a dashed border while something is dragged over it"""
        side = self.project.color if self.phase.is_current else CARD_BORDER
        border = f"2px dashed {highlight}" if highlight else f"1px solid {CARD_BORDER}"
        self.container.setStyleSheet(f"""
            QFrame#phaseCard {{ background-color: {CARD_BACKGROUND}; border: {border};
                                border-left: 4px solid {side}; border-radius: 8px; }}""")

    def toggleExpand(self):
        self.is_expanded = not self.is_expanded
        self.expand_btn.setText("▾" if self.is_expanded else "▸")
        self.content_widget.setVisible(self.is_expanded)
        self.phase.collapsed = not self.is_expanded
        save_phase_fields(self.phase, ['collapsed'], self.logger)

    def contextMenuEvent(self, event):
        self.showMenu(event.globalPos())

    def showMenu(self, global_pos):
        menu = QMenu(self)
        menu.setStyleSheet(MENU_STYLE)
        menu.addAction("Edit phase…", self.onEditPhase)
        menu.addAction("Add task…", self.onAddTask)
        if not self.phase.is_current:
            menu.addAction("Make this the current phase", self.onMarkAsCurrent)
        menu.addAction("Collapse" if self.is_expanded else "Expand", self.toggleExpand)
        menu.addSeparator()
        menu.addAction("Delete phase…", self.onDeletePhase)
        menu.exec_(global_pos)

    # -- tasks ----------------------------------------------------------------------
    def onTaskClicked(self, task):
        """Handle task item click - opens task detail view"""
        from ui.task_files.task_card_expanded import TaskCardExpanded
        from PyQt5.QtCore import Qt

        self.logger.info(f"Task clicked: {task.title}")

        # Create overlay to dim background
        self.overlay = QWidget(self.window())
        self.overlay.setStyleSheet("background-color: rgba(0, 0, 0, 128);")
        self.overlay.setGeometry(self.window().rect())
        self.overlay.setProperty("coversWindow", True)
        self.overlay.show()
        self.overlay.raise_()

        # Create dialog container
        self.dialog_container = QWidget(self.window())
        self.dialog_container.setStyleSheet("background-color: transparent;")
        self.dialog_container.setGeometry(self.window().rect())
        self.dialog_container.setProperty("coversWindow", True)
        # Clicking outside cancels, like the Cancel button, so unsaved edits are undone (see B38)
        self.dialog_container.mousePressEvent = lambda event: self._cancelTaskDetail() if event.button() == Qt.LeftButton else None
        self.dialog_container.show()
        self.dialog_container.raise_()

        # Create the expanded card
        self.expanded_card = TaskCardExpanded(
            logger=self.logger,
            task=task,
            grid_id=None,
            parent_view=None,
            parent=self.dialog_container
        )
        # Connect both save signals (saveCompleted for new tasks, newTaskUpdate for existing tasks)
        self.expanded_card.saveCompleted.connect(self.onTaskSaveCompleted)
        self.expanded_card.newTaskUpdate.connect(self.onTaskSaveCompleted)
        self.expanded_card.cancelTask.connect(self.onTaskCanceled)
        self.expanded_card.taskDeleted.connect(self.onTaskDeleted)
        self.expanded_card.setObjectName("card_container")
        self.expanded_card.setAttribute(Qt.WA_StyledBackground, True)
        self.expanded_card.setStyleSheet(AppStyles.expanded_task_card())

        # Prevent clicks on the card from closing the dialog
        self.expanded_card.mousePressEvent = lambda event: event.accept()

        # Center and show the card
        window = self.window()
        card_width, card_height = TaskCardExpanded.calculate_optimal_card_size(window)
        window_rect = window.rect()
        x = (window_rect.width() - card_width) // 2
        y = (window_rect.height() - card_height) // 2
        self.expanded_card.setGeometry(x, y, card_width, card_height)
        self.expanded_card.setProperty("centeredInWindow", True)
        self.expanded_card.show()
        self.expanded_card.raise_()

    def onTaskSaveCompleted(self, task, grid_id):
        """Handle task save completion"""
        # Invalidate project task cache since a task was modified
        if self.project:
            self.project.invalidate_task_cache()
        self.closeTaskDetail()
        self.refreshTasks()
        # Emit signal to notify that a task was updated
        self.taskUpdated.emit()

    def _cancelTaskDetail(self):
        if getattr(self, 'expanded_card', None) is not None:
            self.expanded_card.cancelTaskChanges()  # emits cancelTask, which closes it
        else:
            self.closeTaskDetail()

    def onTaskCanceled(self):
        """Handle task dialog cancel"""
        self.closeTaskDetail()

    def onTaskDeleted(self, task_title):
        """Handle task deletion"""
        # Invalidate project task cache since a task was deleted
        if self.project:
            self.project.invalidate_task_cache()
        self.closeTaskDetail()
        self.refreshTasks()
        # Emit signal to notify that a task was deleted
        self.taskUpdated.emit()

    def closeTaskDetail(self):
        """Close the task detail overlay"""
        if hasattr(self, 'expanded_card') and self.expanded_card:
            self.expanded_card.close()
            self.expanded_card.deleteLater()
            self.expanded_card = None

        if hasattr(self, 'dialog_container') and self.dialog_container:
            self.dialog_container.close()
            self.dialog_container.deleteLater()
            self.dialog_container = None

        if hasattr(self, 'overlay') and self.overlay:
            self.overlay.close()
            self.overlay.deleteLater()
            self.overlay = None

    def onAddTask(self):
        from ui.project_files.task_dialog import TaskDialog
        dialog = TaskDialog(project_id=self.project.id, phase_id=self.phase.id, logger=self.logger, parent=self,
                            phase_name=self.phase.name)
        dialog.taskSaved.connect(self.onTaskSaved)
        dialog.exec_()

    def onTaskSaved(self, task_data):
        from datetime import datetime

        from models.task import Task
        task = Task(title=task_data['title'], description=task_data['description'])
        task.priority = task_data['priority']
        task.status = task_data['status']
        task.project_id = task_data['project_id']
        task.phase_id = task_data['phase_id']  # this is what puts it in the phase
        task.creation_date = datetime.now()
        with history().action(f"Added task “{task.title}”"):
            save_task_to_json(task, self.logger)
        if self.project:
            self.project.invalidate_task_cache()
        self.refreshTasks()
        self.taskUpdated.emit()

    def refreshTasks(self):
        """Reload this phase's tasks and redraw them (and the progress in the header)"""
        self.loadTasks()
        self.fillTasks()
        self.buildHeader()

    # -- the phase ------------------------------------------------------------------
    def onEditPhase(self):
        from ui.project_files.phase_dialog import PhaseDialog
        dialog = PhaseDialog(mode="edit", project_id=self.project.id, phase=self.phase, logger=self.logger,
                             parent=self)
        dialog.phaseSaved.connect(self.onPhaseEdited)
        dialog.exec_()

    def onPhaseEdited(self, phase_data):
        old_name = self.phase.name
        self.phase.name = phase_data['name']
        self.phase.description = phase_data['description']
        # Save just the edited fields, so changes made elsewhere aren't overwritten
        with history().action(f"Edited phase “{old_name}”"):
            save_phase_fields(self.phase, ['name', 'description'], self.logger)
        self.phaseUpdated.emit(self.phase.id)

    def onDeletePhase(self):
        if not dialogs.confirm(self, f"Delete the phase “{self.phase.name}”?",
                               "Its tasks are kept in the project, just not in a phase. "
                               "You can bring the phase back with Undo.", "Delete"):
            return
        with history().action(f"Deleted phase “{self.phase.name}”"):
            deleted = delete_phase(self.phase.id, self.logger)
        if deleted:
            self.phaseDeleted.emit(self.phase.id)
        else:
            dialogs.warning(self, "Couldn't delete the phase", "See app.log for details.")

    def onMarkAsCurrent(self):
        with history().action(f"Made “{self.phase.name}” the current phase"):
            set_current_phase(self.project.id, self.phase.id, self.logger)
        self.phase.is_current = True
        self.project.current_phase_id = self.phase.id
        self.phaseUpdated.emit(self.phase.id)

    # -- dragging the phase, and dropping tasks or phases on it ---------------------
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.pos()

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton) or self.drag_start_position is None:
            return
        if (event.pos() - self.drag_start_position).manhattanLength() < 10:
            return
        from PyQt5 import sip
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setData(PHASE_MIME, self.phase.id.encode())
        drag.setMimeData(mime_data)
        drag.setPixmap(self.container.grab().scaledToWidth(min(320, self.container.width()), Qt.SmoothTransformation))
        drag.exec_(Qt.MoveAction)
        self.drag_start_position = None
        if not sip.isdeleted(self):  # the drop may have rebuilt the page
            self.updateContainerStyle()

    def dragEnterEvent(self, event: QDragEnterEvent):
        mime_data = event.mimeData()
        if mime_data.hasFormat(TASK_MIME):
            event.acceptProposedAction()
            self.updateContainerStyle(AppColors.accent)
        elif mime_data.hasFormat(PHASE_MIME) and bytes(mime_data.data(PHASE_MIME)).decode() != self.phase.id:
            event.acceptProposedAction()
            self.updateContainerStyle(AppColors.success)
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.updateContainerStyle()

    def dropEvent(self, event: QDropEvent):
        mime_data = event.mimeData()
        self.updateContainerStyle()
        if mime_data.hasFormat(TASK_MIME):
            task_id = bytes(mime_data.data(TASK_MIME)).decode()
            task = load_tasks_from_json(self.logger).get(task_id)
            if task is None:
                event.ignore()
                return
            if task.phase_id == self.phase.id:
                return
            old_phase_id = task.phase_id
            with history().action(f"Moved “{task.title}” to “{self.phase.name}”"):
                moved = move_task_to_phase(task_id, self.phase.id, self.logger)
            if not moved:
                dialogs.warning(self, "Couldn't move the task", "See app.log for details.")
                event.ignore()
                return
            self.logger.info(f"Moved task {task.title} to phase {self.phase.name}")
            event.acceptProposedAction()
            self.refreshTasks()
            self.phaseUpdated.emit(self.phase.id)
            if old_phase_id:
                self.phaseUpdated.emit(old_phase_id)
        elif mime_data.hasFormat(PHASE_MIME):
            dragged_phase_id = bytes(mime_data.data(PHASE_MIME)).decode()
            if dragged_phase_id != self.phase.id:
                event.acceptProposedAction()
                self.phaseReordered.emit(dragged_phase_id, self.phase.order)
