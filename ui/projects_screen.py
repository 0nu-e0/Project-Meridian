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
# File: projects_screen.py
# Description: Main screen for displaying and managing projects
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

from datetime import datetime

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import (QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMenu, QPushButton,
                             QScrollArea, QVBoxLayout, QWidget)

from models.project import ProjectStatus
from models.task import TaskPriority
from resources.styles import AppColors
from ui.custom_widgets.panel_styles import (COMBO_STYLE, EMPTY_HINT_STYLE, LINK_BUTTON_STYLE, MENU_STYLE,
                                            PANEL_BUTTON_STYLE, PRIMARY_BUTTON_STYLE, SEARCH_BOX_STYLE)
from ui.project_files import project_actions
from ui.project_files.project_card import MIN_CARD_WIDTH, ProjectCard
from utils.projects_io import load_phases_from_json, load_projects_from_json

GRID_SPACING = 16
GRID_MARGIN = 20

SORTS = {
    "Newest first": lambda p: (-p.creation_date.timestamp(),),
    "Due soonest": lambda p: (p.target_completion is None, p.target_completion or datetime.max),
    "Name": lambda p: (p.title.lower(),),
}

SCROLL_STYLE = f"""
    QScrollArea {{ background: transparent; border: none; }}
    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: {AppColors.surface_raised}; border-radius: 4px; min-height: 30px; }}
    QScrollBar::handle:vertical:hover {{ background: {AppColors.accent}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}"""


class ProjectsScreen(QWidget):
    """Every project as a card: search, filter, and sort them; click one to open it"""

    projectClicked = pyqtSignal(str)  # project id

    def __init__(self, logger):
        super().__init__()
        self.logger = logger
        self.projects = {}
        self.project_cards = []
        self._columns = 0
        self.search_text = ""
        self.filter_status = "All"
        self.filter_priority = "All"
        self.show_archived = False

        self.initUI()
        self.loadProjects()

    # -- layout -----------------------------------------------------------------
    def initUI(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.main_layout.addWidget(self.initToolbar())
        self.main_layout.addWidget(self.initContentArea(), 1)

    def initToolbar(self):
        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(GRID_MARGIN, 16, GRID_MARGIN, 6)
        layout.setSpacing(8)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search projects")
        self.search_box.setClearButtonEnabled(True)
        self.search_box.setStyleSheet(SEARCH_BOX_STYLE)
        self.search_box.setMinimumWidth(130)
        self.search_box.setMaximumWidth(260)
        self.search_box.textChanged.connect(self.onSearchTextChanged)
        layout.addWidget(self.search_box)

        self.status_filter = self._combo([("All statuses", "All")] + [(s.value, s.value) for s in ProjectStatus])
        self.status_filter.setToolTip("Show only projects with this status")
        self.status_filter.currentIndexChanged.connect(
            lambda: self.onStatusFilterChanged(self.status_filter.currentData()))
        layout.addWidget(self.status_filter)

        self.priority_filter = self._combo([("All priorities", "All")] + [(p.name.title(), p.name) for p in TaskPriority])
        self.priority_filter.setToolTip("Show only projects with this priority")
        self.priority_filter.currentIndexChanged.connect(
            lambda: self.onPriorityFilterChanged(self.priority_filter.currentData()))
        layout.addWidget(self.priority_filter)

        self.sort_combo = self._combo([(name, name) for name in SORTS])
        self.sort_combo.setToolTip("Order of the projects")
        self.sort_combo.currentIndexChanged.connect(self.displayProjects)
        layout.addWidget(self.sort_combo)

        self.archived_checkbox = QPushButton("Show archived")
        self.archived_checkbox.setCheckable(True)
        self.archived_checkbox.setToolTip("Also show projects you've archived")
        self.archived_checkbox.setStyleSheet(PANEL_BUTTON_STYLE)
        self.archived_checkbox.toggled.connect(self.onArchivedToggled)
        layout.addWidget(self.archived_checkbox)

        self.clear_button = QPushButton("Clear filters")
        self.clear_button.setStyleSheet(LINK_BUTTON_STYLE)
        self.clear_button.clicked.connect(self.onClearFilters)
        layout.addWidget(self.clear_button)

        layout.addStretch(1)

        self.count_label = QLabel()
        self.count_label.setStyleSheet(f"color: {AppColors.text_muted}; font-size: 12px;")
        layout.addWidget(self.count_label)

        self.import_project_btn = QPushButton("Import…")
        self.import_project_btn.setToolTip("Bring in a project exported from Project Meridian")
        self.import_project_btn.setStyleSheet(PANEL_BUTTON_STYLE)
        self.import_project_btn.clicked.connect(self.onImportProject)
        layout.addWidget(self.import_project_btn)

        self.add_project_btn = QPushButton("+  New project")
        self.add_project_btn.setToolTip("Start a new project")
        self.add_project_btn.setStyleSheet(PANEL_BUTTON_STYLE + PRIMARY_BUTTON_STYLE)
        self.add_project_btn.clicked.connect(self.onAddProject)
        layout.addWidget(self.add_project_btn)

        for button in (self.archived_checkbox, self.clear_button, self.import_project_btn, self.add_project_btn):
            button.setCursor(Qt.PointingHandCursor)
        return bar

    @staticmethod
    def _combo(items):
        box = QComboBox()
        box.setStyleSheet(COMBO_STYLE)
        box.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        box.setMinimumContentsLength(9)
        box.setCursor(Qt.PointingHandCursor)
        for text, value in items:
            box.addItem(text, value)
        return box

    def initContentArea(self):
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet(SCROLL_STYLE)

        self.container_widget = QWidget()
        self.container_layout = QVBoxLayout(self.container_widget)
        self.container_layout.setContentsMargins(GRID_MARGIN, 10, GRID_MARGIN, GRID_MARGIN)
        self.container_layout.setSpacing(GRID_SPACING)

        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(GRID_SPACING)
        self.grid_layout.setAlignment(Qt.AlignTop)
        self.container_layout.addLayout(self.grid_layout)

        self.empty_state_widget = self.createEmptyState()
        self.container_layout.addWidget(self.empty_state_widget)
        self.container_layout.addStretch(1)

        self.scroll_area.setWidget(self.container_widget)
        return self.scroll_area

    def createEmptyState(self):
        """Shown when no cards are: either there are no projects, or none match the filters"""
        empty = QWidget()
        layout = QVBoxLayout(empty)
        layout.setContentsMargins(0, 60, 0, 0)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignHCenter)
        self.empty_title = QLabel()
        self.empty_title.setAlignment(Qt.AlignCenter)
        self.empty_title.setStyleSheet(f"color: {AppColors.text_primary}; font-size: 17px; font-weight: bold;")
        layout.addWidget(self.empty_title)
        self.empty_text = QLabel()
        self.empty_text.setAlignment(Qt.AlignCenter)
        self.empty_text.setWordWrap(True)
        self.empty_text.setFixedWidth(460)
        self.empty_text.setStyleSheet(EMPTY_HINT_STYLE + "padding: 0;")
        layout.addWidget(self.empty_text)
        self.empty_button = QPushButton()
        self.empty_button.setCursor(Qt.PointingHandCursor)
        self.empty_button.setStyleSheet(PANEL_BUTTON_STYLE + PRIMARY_BUTTON_STYLE)
        self.empty_button.clicked.connect(lambda: self.onClearFilters() if self._filtersActive() else self.onAddProject())
        layout.addWidget(self.empty_button, 0, Qt.AlignHCenter)
        empty.hide()
        return empty

    # -- showing the cards ----------------------------------------------------------
    def loadProjects(self):
        self.projects = load_projects_from_json(self.logger)
        self.displayProjects()

    def refreshProjects(self):
        self.loadProjects()

    def displayProjects(self):
        for card in self.project_cards:
            self.grid_layout.removeWidget(card)
            card.hide()
            card.deleteLater()
        self.project_cards.clear()

        shown = self.applyFilters()
        phases = load_phases_from_json(self.logger) if shown else {}
        for project in shown:
            card = ProjectCard(project, self.logger, phases=phases)
            card.clicked.connect(self.onProjectClicked)
            card.menuRequested.connect(self.showProjectMenu)
            self.project_cards.append(card)
        self._columns = 0
        self._placeCards()
        self._updateStatusLine(len(shown))

    def _columnCount(self):
        available = self.scroll_area.viewport().width() - 2 * GRID_MARGIN
        return max(1, (available + GRID_SPACING) // (MIN_CARD_WIDTH + GRID_SPACING))

    def _placeCards(self):
        """Put the cards in as many columns as fit, each column the same width"""
        columns = self._columnCount()
        if columns == self._columns:
            return
        for column in range(max(columns, self._columns)):
            self.grid_layout.setColumnStretch(column, 1 if column < columns else 0)
        self._columns = columns
        for card in self.project_cards:
            self.grid_layout.removeWidget(card)
        for index, card in enumerate(self.project_cards):
            self.grid_layout.addWidget(card, index // columns, index % columns)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.count_label.setVisible(self.width() >= 1150)  # room for the filters first
        self._placeCards()

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self._placeCards)  # the real width is known once shown

    def _filtersActive(self):
        return bool(self.search_text.strip()) or self.filter_status != "All" or self.filter_priority != "All"

    def _updateStatusLine(self, shown):
        visible = [p for p in self.projects.values() if self.show_archived or not p.archived]
        total = len(visible)
        self.count_label.setText(f"{shown} of {total} projects" if shown != total
                                 else f"{total} project{'s' if total != 1 else ''}")
        self.clear_button.setVisible(self._filtersActive())

        self.empty_state_widget.setVisible(shown == 0)
        if shown:
            return
        if self._filtersActive():
            self.empty_title.setText("No projects match")
            self.empty_text.setText("Try other filters, or clear them to see every project.")
            self.empty_button.setText("Clear filters")
        elif self.projects and not self.show_archived:
            self.empty_title.setText("Every project is archived")
            self.empty_text.setText("Press Show archived to see them, or start a new one.")
            self.empty_button.setText("+  New project")
        else:
            self.empty_title.setText("No projects yet")
            self.empty_text.setText("A project holds phases, and phases hold tasks.\n"
                                    "It gets a Gantt chart, and can have a mind map.")
            self.empty_button.setText("+  New project")

    def applyFilters(self):
        """The projects to show, in the chosen order"""
        search = self.search_text.strip().lower()
        shown = []
        for project in self.projects.values():
            if project.archived and not self.show_archived:
                continue
            if search and search not in project.title.lower() and search not in (project.description or "").lower():
                continue
            if self.filter_status != "All" and project.status.value != self.filter_status:
                continue
            if self.filter_priority != "All" and project.priority.name != self.filter_priority:
                continue
            shown.append(project)
        shown.sort(key=SORTS.get(self.sort_combo.currentData(), SORTS["Newest first"]))
        return shown

    # -- filters ------------------------------------------------------------------
    def onSearchTextChanged(self, text):
        self.search_text = text
        self.displayProjects()

    def onStatusFilterChanged(self, status):
        self.filter_status = status or "All"
        self.displayProjects()

    def onPriorityFilterChanged(self, priority):
        self.filter_priority = priority or "All"
        self.displayProjects()

    def onArchivedToggled(self, checked):
        self.show_archived = checked
        self.displayProjects()

    def onClearFilters(self):
        for widget in (self.search_box, self.status_filter, self.priority_filter):
            widget.blockSignals(True)
        self.search_box.clear()
        self.status_filter.setCurrentIndex(0)
        self.priority_filter.setCurrentIndex(0)
        for widget in (self.search_box, self.status_filter, self.priority_filter):
            widget.blockSignals(False)
        self.search_text, self.filter_status, self.filter_priority = "", "All", "All"
        self.displayProjects()

    # -- actions ------------------------------------------------------------------
    def onAddProject(self):
        project = project_actions.new_project(self, self.logger)
        if project:
            self.loadProjects()
            self.projectClicked.emit(project.id)  # straight into it, to add phases

    def onImportProject(self):
        if project_actions.import_project(self, self.logger):
            self.loadProjects()

    def onProjectClicked(self, project_id):
        self.projectClicked.emit(project_id)

    def showProjectMenu(self, project_id, global_pos):
        project = self.projects.get(project_id)
        if project is None:
            return
        menu = QMenu(self)
        menu.setStyleSheet(MENU_STYLE)
        menu.addAction("Open", lambda: self.onProjectClicked(project_id))
        menu.addAction("Edit details…", lambda: self._afterAction(project_actions.edit_project(self, project, self.logger)))
        menu.addAction("Export…", lambda: project_actions.export_project(self, project, self.logger))
        menu.addSeparator()
        if project.archived:
            menu.addAction("Restore from archive",
                           lambda: self._afterAction(project_actions.set_archived(self, project, False, self.logger)))
        else:
            menu.addAction("Archive",
                           lambda: self._afterAction(project_actions.set_archived(self, project, True, self.logger)))
        menu.addAction("Delete…", lambda: self._afterAction(project_actions.delete_project(self, project, self.logger)))
        menu.exec_(global_pos)

    def _afterAction(self, changed):
        if changed:
            self.loadProjects()
