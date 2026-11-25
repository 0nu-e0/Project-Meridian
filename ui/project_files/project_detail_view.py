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
# File: project_detail_view.py
# Description: Detailed view for a single project with phases
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMenu,
                             QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget)

from models.project import ProjectStatus
from resources.styles import AppColors
from ui.custom_widgets import dialogs
from ui.custom_widgets.panel_styles import (CARD_LIST_STYLE, LINK_BUTTON_STYLE, MENU_STYLE, PANEL_BUTTON_STYLE,
                                            PRIMARY_BUTTON_STYLE, SECTION_HEADER_STYLE)
from ui.project_files import project_actions
from ui.project_files.phase_widget import PhaseWidget
from ui.project_files.project_look import badge, priority_badge, progress_bar, short_date, status_badge
from utils.data_history import history
from utils.mindmap_io import get_unlinked_mindmaps, link_mindmap_to_project, unlink_mindmap_from_project
from utils.projects_io import (create_phase, load_phases_from_json, load_projects_from_json, save_phases_to_json,
                               save_project_fields)

TWO_COLUMNS_FROM = 900  # narrower than this, phases stack in one column

SCROLL_STYLE = f"""
    QScrollArea {{ background: transparent; border: none; }}
    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: {AppColors.surface_raised}; border-radius: 4px; min-height: 30px; }}
    QScrollBar::handle:vertical:hover {{ background: {AppColors.accent}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}"""


class ProjectDetailView(QWidget):
    """One project: its details at the top, then its phases (each with its tasks)"""

    backClicked = pyqtSignal()
    ganttChartClicked = pyqtSignal(str)  # project id
    mindmapClicked = pyqtSignal(str)  # mind map id
    taskUpdated = pyqtSignal()  # a task in this project changed

    def __init__(self, project_id: str, logger, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.logger = logger
        self.project = None
        self.phases = []
        self.phase_widgets = []
        self._columns = 0

        self.loadProjectData()
        self.initUI()

    def loadProjectData(self):
        self.project = load_projects_from_json(self.logger).get(self.project_id)
        if not self.project:
            self.logger.error(f"Project {self.project_id} not found")
            self.phases = []
            return
        all_phases = load_phases_from_json(self.logger)
        self.phases = sorted((all_phases[pid] for pid in self.project.phases if pid in all_phases),
                             key=lambda phase: phase.order)

    # -- layout -----------------------------------------------------------------
    def initUI(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(24, 16, 24, 0)
        self.main_layout.setSpacing(12)

        if not self.project:
            missing = QLabel("This project no longer exists.")
            missing.setStyleSheet(f"color: {AppColors.text_muted}; font-size: 15px;")
            back = self._linkButton("←  All projects", self.onBackClicked)
            self.main_layout.addWidget(back, 0, Qt.AlignLeft)
            self.main_layout.addWidget(missing, 1, Qt.AlignCenter)
            return

        self.header_widget = QWidget()
        self.header_layout = QVBoxLayout(self.header_widget)
        self.header_layout.setContentsMargins(0, 0, 0, 0)
        self.header_layout.setSpacing(10)
        self.main_layout.addWidget(self.header_widget)
        self.buildHeader()

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet(SCROLL_STYLE)
        self.scroll_area = scroll_area

        self.phases_container = QWidget()
        container_layout = QVBoxLayout(self.phases_container)
        container_layout.setContentsMargins(0, 0, 4, 20)
        container_layout.setSpacing(14)
        self.phases_layout = QGridLayout()
        self.phases_layout.setSpacing(14)
        self.phases_layout.setAlignment(Qt.AlignTop)
        container_layout.addLayout(self.phases_layout)
        container_layout.addStretch(1)
        scroll_area.setWidget(self.phases_container)
        self.main_layout.addWidget(scroll_area, 1)

        self.populatePhases()

    @staticmethod
    def _linkButton(text, handler):
        button = QPushButton(text)
        button.setCursor(Qt.PointingHandCursor)
        button.setStyleSheet(LINK_BUTTON_STYLE + "QPushButton { font-size: 13px; }")
        button.clicked.connect(handler)
        return button

    @staticmethod
    def _panelButton(text, tip, handler, primary=False):
        button = QPushButton(text)
        button.setToolTip(tip)
        button.setCursor(Qt.PointingHandCursor)
        button.setStyleSheet(PANEL_BUTTON_STYLE + (PRIMARY_BUTTON_STYLE if primary else ""))
        button.clicked.connect(handler)
        return button

    def buildHeader(self):
        """The top of the page, rebuilt whenever the project changes"""
        while self.header_layout.count():
            item = self.header_layout.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().deleteLater()
            elif item.layout():
                self._deleteLayout(item.layout())
        project = self.project

        # Back, and what can be done with the project
        top = QHBoxLayout()
        top.setSpacing(8)
        top.addWidget(self._linkButton("←  All projects", self.onBackClicked))
        top.addStretch(1)
        top.addWidget(self._panelButton("📊  Gantt chart", "Open the project's timeline", self.onViewGanttChart))
        if project.mindmap_id:
            top.addWidget(self._panelButton("🧠  Mind map", "Open the mind map linked to this project",
                                            self.onViewMindmap))
        else:
            top.addWidget(self._panelButton("🧠  Link mind map…", "Link one of your mind maps, or start one",
                                            self.onLinkMindmap))
        top.addWidget(self._panelButton("Edit", "Change the name, status, dates, or colour", self.onEditProject))
        self.menu_button = self._panelButton("⋯", "More: export, archive, delete", self.onMenuClicked)
        self.menu_button.setFixedWidth(40)
        top.addWidget(self.menu_button)
        self.header_layout.addLayout(top)

        if project.archived:
            banner = QFrame()
            banner.setObjectName("archivedBanner")
            banner.setStyleSheet(f"QFrame#archivedBanner {{ background-color: {AppColors.surface_raised}; "
                                 f"border-radius: 6px; }} QLabel {{ background: transparent; }}")
            row = QHBoxLayout(banner)
            row.setContentsMargins(12, 6, 8, 6)
            note = QLabel("This project is archived, so it's hidden on the Projects screen.")
            note.setStyleSheet(f"color: {AppColors.text_secondary}; font-size: 12px;")
            row.addWidget(note)
            row.addStretch(1)
            row.addWidget(self._linkButton("Restore", self.onRestoreProject))
            self.header_layout.addWidget(banner)

        # Name, status, and priority
        title_row = QHBoxLayout()
        title_row.setSpacing(10)
        dot = QLabel()
        dot.setFixedSize(14, 14)
        dot.setStyleSheet(f"background-color: {project.color}; border-radius: 7px;")
        title_row.addWidget(dot)
        self.title_label = QLabel(project.title)
        self.title_label.setStyleSheet(f"color: {AppColors.text_primary}; font-size: 24px; font-weight: bold; "
                                       f"background: transparent;")
        self.title_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        title_row.addWidget(self.title_label)
        title_row.addSpacing(4)
        title_row.addWidget(status_badge(project.status))
        title_row.addWidget(priority_badge(project.priority))
        if project.archived:
            title_row.addWidget(badge("Archived", AppColors.text_faint))
        title_row.addStretch(1)
        self.header_layout.addLayout(title_row)

        if project.description:
            description = QLabel(project.description)
            description.setWordWrap(True)
            description.setTextInteractionFlags(Qt.TextSelectableByMouse)
            description.setStyleSheet(f"color: {AppColors.text_secondary}; font-size: 13px; background: transparent;")
            description.setMaximumHeight(60)
            self.header_layout.addWidget(description)

        # Dates and progress
        meta = QHBoxLayout()
        meta.setSpacing(14)
        dates = self._datesText()
        if dates:
            dates_label = QLabel(dates)
            dates_label.setStyleSheet(f"color: {AppColors.text_muted}; font-size: 12px; background: transparent;")
            meta.addWidget(dates_label)
        due, color = self._dueStatus()
        if due:
            due_label = QLabel(due)
            due_label.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold; background: transparent;")
            meta.addWidget(due_label)
        meta.addStretch(1)
        progress = project.get_progress_percentage()
        self.info_progress_bar = progress_bar(project.color, progress, height=8)
        self.info_progress_bar.setFixedWidth(220)
        meta.addWidget(self.info_progress_bar)
        total, done = project.get_total_tasks(), project.get_completed_tasks()
        self.info_task_count_label = QLabel(f"{progress:.0f}%  ·  {done} of {total} task{'s' if total != 1 else ''} done"
                                            if total else "No tasks yet")
        self.info_task_count_label.setStyleSheet(f"color: {AppColors.text_secondary}; font-size: 12px; "
                                                 f"background: transparent;")
        meta.addWidget(self.info_task_count_label)
        self.header_layout.addLayout(meta)

        # The phases' heading
        section = QHBoxLayout()
        section.setContentsMargins(0, 8, 0, 0)
        count = len(self.phases)
        heading = QLabel(f"PHASES  ·  {count}" if count else "PHASES")
        heading.setStyleSheet(SECTION_HEADER_STYLE)
        section.addWidget(heading)
        hint = QLabel("Drag a phase by its ⋮⋮ to reorder; drag a task onto another phase to move it.")
        hint.setStyleSheet(f"color: {AppColors.text_faint}; font-size: 11px; background: transparent;")
        hint.setVisible(count > 0)
        section.addSpacing(10)
        section.addWidget(hint)
        section.addStretch(1)
        section.addWidget(self._panelButton("+  Add phase", "Add a phase after the others", self.onAddPhase,
                                            primary=True))
        self.header_layout.addLayout(section)

    def _deleteLayout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().deleteLater()
            elif item.layout():
                self._deleteLayout(item.layout())

    def _datesText(self):
        start, due = self.project.start_date, self.project.target_completion
        if start and due:
            same_year = start.year == due.year
            return f"{short_date(start, with_year=not same_year)} – {short_date(due, with_year=True)}"
        if start:
            return f"Started {short_date(start, with_year=True)}"
        if due:
            return f"Due {short_date(due, with_year=True)}"
        return ""

    def _dueStatus(self):
        """("Due in 3 days", colour) while the project is under way"""
        from datetime import datetime
        due = self.project.target_completion
        if due is None or self.project.status in (ProjectStatus.COMPLETED, ProjectStatus.CANCELLED):
            return "", None
        days = (due.date() - datetime.now().date()).days
        if days < 0:
            text = f"{-days} day{'s' if days != -1 else ''} overdue"
        elif days == 0:
            text = "Due today"
        else:
            text = f"Due in {days} day{'s' if days != 1 else ''}"
        return text, AppColors.get_due_date_color(due)

    def populatePhases(self):
        """Fill the grid with a box per phase (or a hint when there are none)"""
        while self.phases_layout.count():
            item = self.phases_layout.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().deleteLater()
        self.phase_widgets.clear()
        self._columns = 0

        if not self.phases:
            empty = QLabel("No phases yet.\nPhases are the stages of a project, such as Design, Build, and Test.\n"
                           "Press + Add phase to make the first one.")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(f"color: {AppColors.text_muted}; font-size: 13px; padding: 40px;")
            self.phases_layout.addWidget(empty, 0, 0)
            return

        for phase in self.phases:
            phase_widget = PhaseWidget(phase, self.project, self.logger)
            phase_widget.phaseUpdated.connect(self.onPhaseUpdated)
            phase_widget.phaseDeleted.connect(self.onPhaseDeleted)
            phase_widget.phaseReordered.connect(self.onPhaseReordered)
            phase_widget.taskUpdated.connect(self.onTaskUpdated)
            phase_widget.setMinimumWidth(300)
            phase_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
            self.phase_widgets.append(phase_widget)
        self._placePhases()

    def _placePhases(self):
        if not self.phase_widgets:
            return
        columns = 2 if self.scroll_area.viewport().width() >= TWO_COLUMNS_FROM else 1
        if columns == self._columns:
            return
        self._columns = columns
        for column in range(2):
            self.phases_layout.setColumnStretch(column, 1 if column < columns else 0)
        for widget in self.phase_widgets:
            self.phases_layout.removeWidget(widget)
        for index, widget in enumerate(self.phase_widgets):
            self.phases_layout.addWidget(widget, index // columns, index % columns, Qt.AlignTop)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.project:
            self._placePhases()

    def showEvent(self, event):
        super().showEvent(event)
        if self.project:
            QTimer.singleShot(0, self._placePhases)

    # -- navigation ---------------------------------------------------------------
    def onBackClicked(self):
        self.backClicked.emit()

    def onViewGanttChart(self):
        self.ganttChartClicked.emit(self.project_id)

    def onViewMindmap(self):
        if self.project.mindmap_id:
            self.mindmapClicked.emit(self.project.mindmap_id)

    # -- the project ----------------------------------------------------------------
    def onEditProject(self):
        if project_actions.edit_project(self, self.project, self.logger):
            self.refresh()

    def onProjectEdited(self, project_data):
        """Kept for callers: save edited details and show them"""
        project_actions.apply_edit(self.project, project_data, self.logger)
        self.refresh()

    def onMenuClicked(self):
        menu = QMenu(self)
        menu.setStyleSheet(MENU_STYLE)
        menu.addAction("Export…", self.onExportProject)
        if self.project.mindmap_id:
            menu.addAction("Unlink mind map…", self.onUnlinkMindmap)
        menu.addSeparator()
        if self.project.archived:
            menu.addAction("Restore from archive", self.onRestoreProject)
        else:
            menu.addAction("Archive", self.onArchiveProject)
        menu.addAction("Delete project…", self.onDeleteProject)
        button = getattr(self, "menu_button", None)
        menu.exec_(button.mapToGlobal(button.rect().bottomLeft()) if button else self.cursor().pos())

    def onArchiveProject(self):
        """Archive it (hidden on the Projects screen; Undo or Restore brings it back) and go back"""
        project_actions.set_archived(self, self.project, True, self.logger)
        self.backClicked.emit()

    def onRestoreProject(self):
        project_actions.set_archived(self, self.project, False, self.logger)
        self.refresh()

    def onDeleteProject(self):
        if project_actions.delete_project(self, self.project, self.logger):
            self.backClicked.emit()

    def onExportProject(self):
        project_actions.export_project(self, self.project, self.logger)

    # -- mind map -----------------------------------------------------------------
    def onLinkMindmap(self):
        """Link one of the mind maps not yet in a project, or start a new one for this project"""
        unlinked = get_unlinked_mindmaps(self.logger)
        dialog = dialogs.StyledDialog(
            self, "Link a mind map",
            "Pick one of your mind maps for this project, or start a new one." if unlinked
            else "All your mind maps belong to other projects. Start a new one for this project?",
            icon="🧠", cancel_value=None)
        mindmap_list = None
        if unlinked:
            mindmap_list = QListWidget()
            mindmap_list.setStyleSheet(CARD_LIST_STYLE + "QListWidget::item { padding: 8px 10px; color: white; }")
            mindmap_list.setSpacing(2)
            mindmap_list.setMinimumHeight(min(260, 44 * len(unlinked) + 10))
            for mindmap in unlinked:
                item = QListWidgetItem(mindmap.title)
                item.setData(Qt.UserRole, mindmap.id)
                item.setToolTip(mindmap.description or mindmap.title)
                mindmap_list.addItem(item)
            mindmap_list.setCurrentRow(0)
            mindmap_list.itemDoubleClicked.connect(lambda *_: dialog._finish("link"))
            dialog.content.addWidget(mindmap_list)
        dialog.addButton("Start a new one", "new", left=True)
        dialog.addButton("Cancel", None)
        if unlinked:
            dialog.addButton("Link", "link", dialogs.PRIMARY, default=True)
        choice = dialog.ask()

        title = f"“{self.project.title}”"
        if choice == "link" and mindmap_list is not None and mindmap_list.currentItem() is not None:
            with history().action(f"Linked a mind map to {title}"):
                linked = link_mindmap_to_project(mindmap_list.currentItem().data(Qt.UserRole), self.project_id,
                                                 self.logger)
            if not linked:
                dialogs.warning(self, "Couldn't link the mind map", "See app.log for details.")
        elif choice == "new":
            from utils.mindmap_io import create_mindmap
            with history().action(f"Started a mind map for {title}"):
                mindmap = create_mindmap(title=f"{self.project.title} mind map",
                                         description=f"Mind map for the project {self.project.title}",
                                         project_id=self.project_id, logger=self.logger)
                self.project.mindmap_id = mindmap.id
                save_project_fields(self.project, ['mindmap_id'], self.logger)
        else:
            return
        self.refresh()

    def onUnlinkMindmap(self):
        if not dialogs.confirm(self, "Unlink the mind map?",
                               "It stays in your mind maps; it just won't belong to this project.", "Unlink",
                               danger=False):
            return
        with history().action(f"Unlinked the mind map from “{self.project.title}”"):
            unlinked = unlink_mindmap_from_project(self.project.mindmap_id, self.logger)
        if not unlinked:
            dialogs.warning(self, "Couldn't unlink the mind map", "See app.log for details.")
        self.refresh()

    # -- phases ---------------------------------------------------------------------
    def onAddPhase(self):
        from ui.project_files.phase_dialog import PhaseDialog
        dialog = PhaseDialog(mode="create", project_id=self.project_id, logger=self.logger, parent=self)
        dialog.phaseSaved.connect(self.onPhaseSaved)
        dialog.exec_()

    def onPhaseSaved(self, phase_data):
        with history().action(f"Added phase “{phase_data['name']}”"):
            create_phase(project_id=self.project_id, name=phase_data['name'],
                         description=phase_data['description'], order=len(self.project.phases), logger=self.logger)
        self.refresh()

    def onPhaseUpdated(self, phase_id):
        self.refresh()

    def onPhaseDeleted(self, phase_id):
        self.refresh()

    def onTaskUpdated(self):
        self.refreshHeader()
        self.taskUpdated.emit()

    def onPhaseReordered(self, dragged_phase_id, target_position):
        """Drop a phase onto another: it takes that phase's place, and the rest move along"""
        all_phases = load_phases_from_json(self.logger)
        project_phases = sorted((p for p in all_phases.values() if p.project_id == self.project.id),
                                key=lambda p: p.order)
        dragged = next((p for p in project_phases if p.id == dragged_phase_id), None)
        if not dragged:
            self.logger.warning(f"Dragged phase {dragged_phase_id} not found")
            return

        # Work in list positions: stored orders can have gaps or repeats, so they
        # can't be used as indexes. target_position is the drop target's order.
        current_position = project_phases.index(dragged)
        target_index = next((i for i, p in enumerate(project_phases) if p.order == target_position),
                            len(project_phases) - 1)
        project_phases.pop(current_position)
        project_phases.insert(target_index, dragged)
        for index, phase in enumerate(project_phases):
            phase.order = index
            all_phases[phase.id] = phase

        with history().action(f"Moved phase “{dragged.name}”"):
            save_phases_to_json(all_phases, self.logger)
        self.logger.info(f"Reordered phase {dragged.name} from position {current_position} to {target_index}")
        self.refresh()

    # -- refreshing -------------------------------------------------------------------
    def refreshHeader(self):
        """Reload the project and redraw the top (after a task changed: progress, counts)"""
        self.loadProjectData()
        if self.project:
            self.project.invalidate_task_cache()
            self.buildHeader()

    def updateInfoSection(self):
        """Kept for callers"""
        self.refreshHeader()

    def refresh(self):
        """Reload everything from the files and redraw the page"""
        if self.project:
            self.project.invalidate_task_cache()
        self.loadProjectData()
        if not self.project:
            # Deleted (e.g. its creation was undone): nothing to show here any more
            QTimer.singleShot(0, self.backClicked.emit)
            return
        self.project.invalidate_task_cache()
        if not hasattr(self, "header_layout"):
            return
        self.buildHeader()
        self.populatePhases()
