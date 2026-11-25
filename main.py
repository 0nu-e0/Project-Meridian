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
# File: main.py
# Description: Main application entry point that sets up logging, initializes the
#              main window with animated drawer menu, banner, and screen navigation
#              system. Handles UI layout, animations, event filtering, and ensures
#              required configuration files exist.
# Author: Jereme Shaver
# -----------------------------------------------------------------------------


# Standard library imports
import ctypes
import logging
import logging.handlers
import os
import sys

# Third-party imports
from PyQt5.QtCore import QEasingCurve, QEvent, QPropertyAnimation, QRect, QSize, Qt, QTimer
from PyQt5.QtGui import QCursor, QGuiApplication, QIcon, QKeySequence, QPixmap, QResizeEvent
from PyQt5.QtWidgets import (QApplication, QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QShortcut,
                             QLabel, QPushButton, QSizePolicy, QSpacerItem,
                             QStackedWidget, QVBoxLayout, QWidget)

# Local application imports
from functools import partial
from ui.custom_widgets import dialogs
from utils.constants import (BANNER_HEIGHT, DRAWER_MAX_WIDTH, DRAWER_MIN_WIDTH, DRAWER_SPACING,
                             DRAWER_WIDTH_RATIO, LAYOUT_LARGE_SPACING, LAYOUT_NO_SPACING,
                             MARGIN_LARGE, WINDOW_DEFAULT_HEIGHT_RATIO,
                             WINDOW_DEFAULT_WIDTH_RATIO, WINDOW_MIN_HEIGHT, WINDOW_MIN_WIDTH)
from utils.app_config import AppConfig
from resources.styles import AnimatedButton, AppStyles
from ui.dashboard_screen import DashboardScreen
from ui.mindmap_screen import MindMapScreen
from ui.notes_screen import NotesScreen
from ui.planning_screen import PlanningScreen
from ui.projects_screen import ProjectsScreen
from ui.project_files.project_detail_view import ProjectDetailView
from ui.settings_screen import SettingsScreen
from ui.welcome_screen import WelcomeScreen
from utils.directory_finder import resource_path
from utils.data_manager import DataManager
from utils.safe_io import get_quarantined_files, set_quarantine_handler
from utils.display_scale import apply_interface_scale
from utils.settings import STARTUP_SCREENS, Settings, apply_color_overrides
from resources.styles import AppColors

def setup_logging(log_dir):
    """Log to <app data>/logs/app.log (kept to a few MB) and to the console"""
    log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    root = logging.getLogger('')
    root.setLevel(logging.INFO)

    # The working directory isn't always writable (e.g. Program Files), so use the app's own folder
    try:
        os.makedirs(log_dir, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            os.path.join(log_dir, 'app.log'), maxBytes=2 * 1024 * 1024, backupCount=3, encoding='utf-8')
        file_handler.setFormatter(log_format)
        root.addHandler(file_handler)
    except OSError as e:
        print(f"Could not open log file in {log_dir}: {e}")

    # The packaged app has no console (sys.stderr is None), so only log there when there is one
    if sys.stderr is not None:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(log_format)
        root.addHandler(console_handler)

def get_logger(name=__name__):
    return logging.getLogger(name)

class MainWindow(QWidget):

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        logging.info("Application starting")

        # IMPORTANT: Initialize AppConfig FIRST to ensure it's fully initialized
        # before DataManager tries to load data (which internally uses AppConfig)
        from utils.app_config import AppConfig
        self.app_config = AppConfig()
        self.logger.info(f"AppConfig initialized: {self.app_config.app_data_dir}")

        # Initialize DataManager once at startup
        self.data_manager = DataManager(self.logger, self.app_config)
        self.logger.info(f"DataManager initialized: {self.data_manager.get_data_summary()}")

        # One-time move of phase membership from phase files onto tasks (B24)
        from utils.projects_io import reconcile_phase_membership
        reconcile_phase_membership(self.logger)

        # Set window flags to make it act like a main window
        self.setWindowFlags(Qt.Window)

        self.banner_header_label = ""

        self.screen_mapping = {
            "Dashboard": "dashboard_screen",
            "Planning": "planning_screen",
            "Projects": "projects_screen",
            "Notes": "notes_screen",
            "Mindmaps": "mindmaps_screen"
        }

        # Open on the monitor the user is working on, sized to it and centred
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        self.screen_size = screen.availableGeometry()
        self.resize(
            int(self.screen_size.width() * WINDOW_DEFAULT_WIDTH_RATIO),
            int(self.screen_size.height() * WINDOW_DEFAULT_HEIGHT_RATIO)
        )
        # A fixed minimum (not a share of this screen) so the window still fits on a
        # smaller second monitor
        self.setMinimumSize(
            min(WINDOW_MIN_WIDTH, self.screen_size.width()),
            min(WINDOW_MIN_HEIGHT, self.screen_size.height())
        )
        self.move(self.screen_size.center() - self.rect().center())
        self.window_width = self.width()

        # Drawer navigation: the screen picked while the drawer closes, and the screen
        # a slide transition is heading to
        self._pending_screen = None
        self._transition_target = None
        self.initUI()

        QApplication.instance().installEventFilter(self)

        self.drawer.raise_()
        self.drawer.setGeometry(-self.drawer_width, 0, self.drawer_width, self.height())

        self.window_width = self.width()

    def eventFilter(self, source, event):
        # Close the drawer on a click outside it, but only for clicks in this window,
        # not in dialogs or popups that happen to sit over it
        if (event.type() == QEvent.MouseButtonPress and self.drawer_open
                and isinstance(source, QWidget) and source.window() is self):
            click_position = self.mapFromGlobal(event.globalPos())
            on_toggle_button = self.toggle_drawer_button.rect().contains(
                self.toggle_drawer_button.mapFromGlobal(event.globalPos()))
            if not self.drawer.geometry().contains(click_position) and not on_toggle_button:
                self.toggleDrawer()

        return super(MainWindow, self).eventFilter(source, event)

    def closeEvent(self, event):
        """Offer to save unsaved notes and mindmaps, then clean up"""
        for screen in (self.notes_screen, self.mindmaps_screen):
            if not screen.confirm_discard_changes():
                event.ignore()
                return
        QApplication.instance().removeEventFilter(self)
        super().closeEvent(event)

    def calculateDrawerWidth(self):
        return max(DRAWER_MIN_WIDTH, min(DRAWER_MAX_WIDTH, int(self.width() * DRAWER_WIDTH_RATIO)))

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        if hasattr(self, 'global_search'):
            self.global_search.close_results()  # it's placed for the old size
        if hasattr(self, 'toast') and self.toast.isVisible():
            self.toast.reposition()

        new_width = max(0, self.width())
        new_height = max(0, self.height())

        # Recalculate the drawer width so it tracks the window instead of the startup size
        if hasattr(self, 'drawer') and self.drawer:
            self.drawer_width = self.calculateDrawerWidth()
            self.drawer.setFixedWidth(self.drawer_width)
            drawer_x = 0 if self.drawer_open else -self.drawer_width
            self.drawer.setGeometry(drawer_x, 0, self.drawer_width, new_height)

        # The banner lives in the central widget's layout, so only the central widget needs placing
        if hasattr(self, 'central_widget') and self.central_widget:
            if self.drawer_open:
                self.central_widget.setGeometry(self.drawer_width, 0, new_width - self.drawer_width, new_height)
            else:
                self.central_widget.setGeometry(0, 0, new_width, new_height)

        self.fitOverlays()

    def fitOverlays(self):
        """Keep open overlays covering the window and their cards centred in it.

        Screens tag the widgets they float over the window with these properties:
        "coversWindow" (dimmed backgrounds) and "centeredInWindow" (task/project cards).
        """
        # Overlays sit on the window or inside a container that does, so two levels
        # is enough (and avoids walking every widget on every resize)
        direct = Qt.FindDirectChildrenOnly
        top_level = self.findChildren(QWidget, options=direct)
        candidates = top_level + [child for top in top_level if top.property("coversWindow")
                                  for child in top.findChildren(QWidget, options=direct)]
        for widget in candidates:
            parent = widget.parentWidget()
            if widget.property("coversWindow"):
                widget.setGeometry(parent.rect())
            elif widget.property("centeredInWindow"):
                width, height = widget.width(), widget.height()
                if hasattr(type(widget), 'calculate_optimal_card_size'):
                    width, height = type(widget).calculate_optimal_card_size(self)
                widget.setGeometry((parent.width() - width) // 2, (parent.height() - height) // 2, width, height)

    def initUI(self):
        self.setWindowTitle("Project Meridian")

        self.drawer_open = False
        self.initCentralWidget()
        self.initBanner()
        self.initDrawer()
        self.initStackedWidgets()

        self.drawer_animation = QPropertyAnimation(self.drawer, b"geometry")
        self.drawer_animation.finished.connect(self.onDrawerAnimationFinished)
        self.central_widget_animation = QPropertyAnimation(self.central_widget, b"geometry")

    def initCentralWidget(self):
        self.central_widget = QWidget(self)
        self.central_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(LAYOUT_NO_SPACING, LAYOUT_NO_SPACING, LAYOUT_NO_SPACING, LAYOUT_NO_SPACING)
        self.main_layout.setSpacing(LAYOUT_NO_SPACING)

    def initStackedWidgets(self):
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.main_layout.addWidget(self.stacked_widget)

        self.welcome_screen = WelcomeScreen()
        self.welcome_screen.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.dashboard_screen = DashboardScreen(logger=self.logger, width=self.window_width)
        self.dashboard_screen.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.dashboard_screen.setObjectName("Dashboard")

        self.planning_screen = PlanningScreen(logger=self.logger)
        self.planning_screen.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.projects_screen = ProjectsScreen(logger=self.logger)
        self.projects_screen.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.projects_screen.projectClicked.connect(self.showProjectDetail)

        self.notes_screen = NotesScreen(logger=self.logger)
        self.notes_screen.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.mindmaps_screen = MindMapScreen(logger=self.logger)
        self.mindmaps_screen.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.settings_screen = SettingsScreen(logger=self.logger)
        self.settings_screen.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.settings_screen.restartRequested.connect(self.restartApp)
        Settings.instance().changed.connect(self.onSettingChanged)

        self.dashboard_screen.refreshPlanningUI.connect(self.planning_screen.refreshPlanningUI)

        self.stacked_widget.addWidget(self.dashboard_screen)
        self.stacked_widget.addWidget(self.welcome_screen)
        self.stacked_widget.addWidget(self.planning_screen)
        self.stacked_widget.addWidget(self.projects_screen)
        self.stacked_widget.addWidget(self.notes_screen)
        self.stacked_widget.addWidget(self.mindmaps_screen)
        self.stacked_widget.addWidget(self.settings_screen)

        # Open on the screen chosen in Settings
        startup = Settings.instance().get("startup_screen")
        self.stacked_widget.setCurrentWidget(self.screenWidget(startup) or self.welcome_screen)
        if startup in STARTUP_SCREENS and startup != "welcome":
            self.banner_header.setText(STARTUP_SCREENS[startup])

    def initBanner(self):
        # The banner sits in the layout above the stacked screens, so every screen
        # starts at the same height without needing its own spacer
        self.banner = QWidget()
        self.banner.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.banner.setFixedHeight(BANNER_HEIGHT)
        self.banner.setStyleSheet(AppStyles.banner_color())
        self.banner_layout = QHBoxLayout(self.banner)
        self.banner_layout.setContentsMargins(MARGIN_LARGE, 0, MARGIN_LARGE, 0)
        self.banner_layout.setSpacing(LAYOUT_LARGE_SPACING)
        self.initToggleButton()
        self.initBannerHeader()
        self.main_layout.addWidget(self.banner)

    def initToggleButton(self):
        self.toggle_drawer_button = QPushButton()
        self.toggle_drawer_button.setToolTip("Menu")
        self.toggle_drawer_button.clicked.connect(self.toggleDrawer)
        self.toggle_drawer_button.setFixedSize(40, 40)
        self.toggle_drawer_button.setStyleSheet(AppStyles.button_toggle_drawer())
        self.toggle_drawer_button.setText("\u2630")  # Unicode character for hamburger icon

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(3)
        shadow.setXOffset(1)
        shadow.setYOffset(1)
        self.toggle_drawer_button.setGraphicsEffect(shadow)
        self.banner_layout.addWidget(self.toggle_drawer_button, 0, Qt.AlignVCenter)

    def initBannerHeader(self):
        self.banner_header_container = QWidget()
        banner_header_layout = QHBoxLayout(self.banner_header_container)
        banner_header_layout.setContentsMargins(0, 0, 0, 0)
        self.banner_header = QLabel(self.banner_header_label)
        self.banner_header.setStyleSheet(AppStyles.banner_header())

        self.banner_header.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        banner_header_layout.addWidget(self.banner_header)
        self.banner_layout.addWidget(self.banner_header_container, 1)

        # Search everything (Ctrl+K or Ctrl+F)
        from ui.custom_widgets.global_search import GlobalSearch
        self.global_search = GlobalSearch(self, self.logger)
        self.global_search.resultChosen.connect(self.openSearchResult)
        self.banner_layout.addWidget(self.global_search, 0, Qt.AlignVCenter)
        for keys in ("Ctrl+K", "Ctrl+F"):
            QShortcut(QKeySequence(keys), self, self.global_search.focus)

        # Undo / redo for saved changes (the mind map has its own), and the notice that offers it
        from ui.custom_widgets.toast import Toast
        from utils.data_history import history
        self.toast = Toast(self)
        history().recorded.connect(lambda label: self.toast.show_message(label, "Undo", self.undo))
        history().restored.connect(self.onDataRestored)
        # The guide (F1 or ?) and a new task from anywhere (Ctrl+N)
        help_button = QPushButton("?")
        help_button.setToolTip("Quick guide and shortcuts (F1)")
        help_button.setFixedSize(36, 36)
        help_button.setCursor(Qt.PointingHandCursor)
        help_button.setStyleSheet("""
            QPushButton { background-color: rgba(255, 255, 255, 30); color: white; border: 1px solid rgba(255, 255, 255, 60);
                          border-radius: 18px; font-size: 16px; font-weight: bold; }
            QPushButton:hover { background-color: rgba(255, 255, 255, 60); }""")
        help_button.clicked.connect(self.showGuide)
        self.banner_layout.addWidget(help_button, 0, Qt.AlignVCenter)
        QShortcut(QKeySequence("F1"), self, self.showGuide)
        QShortcut(QKeySequence("Ctrl+N"), self, self.newTask)

        QShortcut(QKeySequence("Ctrl+Z"), self, self.undo)
        for keys in ("Ctrl+Y", "Ctrl+Shift+Z"):
            QShortcut(QKeySequence(keys), self, self.redo)

    def initDrawer(self):
        self.drawer = QFrame(self)
        self.drawer.setStyleSheet(AppStyles.drawer_style())
        self.drawer_layout = QVBoxLayout()
        self.drawer.setLayout(self.drawer_layout)
        self.addDrawerButtons()

        self.drawer_width = self.calculateDrawerWidth()
        self.drawer.setFixedWidth(self.drawer_width)
        self.drawer_layout.setAlignment(Qt.AlignTop)
        self.drawer.setGeometry(-self.drawer_width, 0, self.drawer_width, self.height())

        self.drawer_shadow = QGraphicsDropShadowEffect(self)
        self.drawer_shadow.setBlurRadius(10)
        self.drawer_shadow.setXOffset(1)
        self.drawer_shadow.setYOffset(1)
        self.drawer.setGraphicsEffect(self.drawer_shadow)
        self.drawer_shadow.setEnabled(False)

    def addDrawerButtons(self):
        self.drawer_layout.setSpacing(DRAWER_SPACING)

        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)

        headerLabel = QLabel("Project Meridian")
        headerLabel.setAlignment(Qt.AlignCenter)
        headerLabel.setStyleSheet(AppStyles.label_xlgfnt_bold_dark())
        header_layout.addWidget(headerLabel)

        logo_widget = QWidget()

        header_layout.addWidget(logo_widget)

        self.drawer_layout.addWidget(header_widget)


        for name, screen in self.screen_mapping.items():

            button = AnimatedButton(text=name, blur=2, x=60, y=20, offsetX=1, offsetY=1)
            button.setToolTip(f"Go to {name}")

            button.setStyleSheet(AppStyles.button_normal())
            button.clicked.connect(partial(self.buttonClicked, screen))
            self.drawer_layout.addWidget(button)

        settings_button = QPushButton()
        settings_button.setToolTip("Settings")
        image_path = resource_path('resources/images/settings.png')
        pixmap = QPixmap(image_path)
        setting_icon = QIcon(pixmap)
        settings_button.setIcon(setting_icon)
        settings_button.setFixedSize(QSize(40, 40))
        settings_button.setIconSize(QSize(40, 40))
        settings_button.setStyleSheet(AppStyles.button_transparent())
        settings_button.clicked.connect(self.showSettingsMenu)

        spacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.drawer_layout.addSpacerItem(spacer)

        self.drawer_layout.addWidget(settings_button)
        self.drawer_layout.setAlignment(settings_button, Qt.AlignHCenter)

    def buttonClicked(self, screen):
        # The last button clicked wins, even if several are clicked while the drawer closes
        self._pending_screen = screen
        if self.drawer_open:
            self.toggleDrawer()
        elif self.drawer_animation.state() != QPropertyAnimation.Running:
            self.onDrawerAnimationFinished()

    def onDrawerAnimationFinished(self):
        if self._pending_screen and not self.drawer_open:
            screen, self._pending_screen = self._pending_screen, None
            self.initiateStackedWidgetTransition(screen)

    def showSettingsMenu(self):
        self.buttonClicked("settings_screen")

    def screenWidget(self, screen):
        """The screen widget for a name like "planning_screen", or None"""
        return {
            "dashboard_screen": self.dashboard_screen,
            "planning_screen": self.planning_screen,
            "notes_screen": self.notes_screen,
            "mindmaps_screen": self.mindmaps_screen,
            "projects_screen": self.projects_screen,
            "settings_screen": self.settings_screen,
        }.get(screen)

    def onSettingChanged(self, key):
        """Apply settings that can change while the app is running"""
        if key == "dashboard_show_archived":
            self.dashboard_screen.refreshDashboard()
        elif key == "planning_show_weekends":
            self.planning_screen.weekly_view.updateWeekView()
            self.planning_screen.refreshPlanningUI()
        elif key in ("mindmap_show_grid", "mindmap_snap_to_grid"):
            self.mindmaps_screen.applyGridSettings()

    def restartApp(self):
        """Restart so colour changes take effect (unsaved work is offered for saving first)"""
        from PyQt5.QtCore import QProcess
        if not self.close():
            return
        args = sys.argv[1:] if getattr(sys, 'frozen', False) else sys.argv
        QProcess.startDetached(sys.executable, args)
        QApplication.instance().quit()

    def _cancelTransition(self):
        """Stop a drawer slide in progress so it can't switch screens after we do"""
        if self._transition_target is None:
            return
        self.outgoingAnimation.stop()
        self.incomingAnimation.stop()
        self._transition_target = None
        for index in range(self.stacked_widget.count()):
            self.stacked_widget.widget(index).setGeometry(self.stacked_widget.rect())

    def _discardTransientViews(self, keep=()):
        """Remove Project Detail and Gantt views from the stack, except those in keep"""
        from ui.gantt_chart_view import GanttChartView

        for index in reversed(range(self.stacked_widget.count())):
            widget = self.stacked_widget.widget(index)
            if (isinstance(widget, (ProjectDetailView, GanttChartView)) and widget not in keep
                    and widget is not self.stacked_widget.currentWidget()):
                self.stacked_widget.removeWidget(widget)
                widget.deleteLater()

    def showProjectDetail(self, project_id):
        """Show the project detail view for the given project ID"""
        self._cancelTransition()

        # Create a new project detail view
        project_detail_view = ProjectDetailView(project_id, self.logger)
        project_detail_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Connect back button to return to projects screen
        project_detail_view.backClicked.connect(self.returnToProjectsScreen)

        # Connect Gantt chart button
        project_detail_view.ganttChartClicked.connect(self.showGanttChart)

        # Connect task update signal to refresh dashboard
        project_detail_view.taskUpdated.connect(self.dashboard_screen.refreshDashboard)

        # Add to stacked widget and show it
        self.stacked_widget.addWidget(project_detail_view)
        self.stacked_widget.setCurrentWidget(project_detail_view)
        self._discardTransientViews(keep=(project_detail_view,))

        # Update banner header
        self.banner_header.setText("Project Details")

    def showGanttChart(self, project_id):
        """Show the Gantt chart view for the given project ID"""
        from ui.gantt_chart_view import GanttChartView
        self._cancelTransition()

        # Create a new Gantt chart view
        gantt_view = GanttChartView(project_id, self.logger)
        gantt_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Connect back button to return to project detail
        gantt_view.backClicked.connect(lambda: self.returnFromGanttChart(project_id))

        # Keep the detail view underneath so Back can return to it
        detail_views = [self.stacked_widget.widget(i) for i in range(self.stacked_widget.count())
                        if isinstance(self.stacked_widget.widget(i), ProjectDetailView)]

        # Add to stacked widget and show it
        self.stacked_widget.addWidget(gantt_view)
        self.stacked_widget.setCurrentWidget(gantt_view)
        self._discardTransientViews(keep=(gantt_view, *detail_views))

        # Update banner header
        self.banner_header.setText("Gantt Chart")

    def returnFromGanttChart(self, project_id):
        """Return to the project detail view underneath the Gantt chart"""
        self._cancelTransition()
        detail_view = next(
            (self.stacked_widget.widget(i) for i in range(self.stacked_widget.count())
             if isinstance(self.stacked_widget.widget(i), ProjectDetailView)
             and self.stacked_widget.widget(i).project_id == project_id),
            None)

        if detail_view is None:
            self.showProjectDetail(project_id)
            return

        # Pick up anything changed on the Gantt chart, then drop the chart
        detail_view.refresh()
        self.stacked_widget.setCurrentWidget(detail_view)
        self._discardTransientViews(keep=(detail_view,))
        self.banner_header.setText("Project Details")

    def returnToProjectsScreen(self):
        """Return to the projects screen from project detail view"""
        self._cancelTransition()
        self.stacked_widget.setCurrentWidget(self.projects_screen)
        self._discardTransientViews()
        self.banner_header.setText("Projects")

        # Refresh projects to show any updates
        self.projects_screen.refreshProjects()

    def showGuide(self):
        from ui.custom_widgets.guide import show_guide
        show_guide(self)

    def newTask(self):
        """Ctrl+N: a new task card, on the Dashboard"""
        self.showScreenNow("dashboard_screen")
        self.dashboard_screen.openExpandedCardOverlay(task=None)

    def offerGuideOnce(self):
        """First run: a notice pointing at the guide"""
        from utils.settings import Settings
        if not Settings.instance().get("seen_guide"):
            Settings.instance().set("seen_guide", True)
            self.toast.show_message("New here? A quick guide to the app is one click away.", "Open guide", self.showGuide)

    def undo(self):
        """Ctrl+Z: the mind map's own undo there; elsewhere, the last saved change"""
        from utils.data_history import history
        if self.stacked_widget.currentWidget() is self.mindmaps_screen:
            self.mindmaps_screen.undo()
        elif not history().undo():
            self.toast.show_message("Nothing to undo")

    def redo(self):
        from utils.data_history import history
        if self.stacked_widget.currentWidget() is self.mindmaps_screen:
            self.mindmaps_screen.redo()
        elif not history().redo():
            self.toast.show_message("Nothing to redo")

    def onDataRestored(self, label, undone):
        """After undo or redo: reload every screen from the files, and say what happened"""
        if getattr(self.dashboard_screen, 'expanded_card', None) is not None:
            self.dashboard_screen.expanded_card._history_recorded = True  # its changes are being undone
            self.dashboard_screen.closeExpandedCard()
        self.dashboard_screen.refreshDashboard()
        self.planning_screen.refreshPlanningUI()
        self.projects_screen.refreshProjects()
        current = self.stacked_widget.currentWidget()
        if isinstance(current, ProjectDetailView):
            current.refresh()
        if undone:
            self.toast.show_message(f"Undid: {label}", "Redo", self.redo)
        else:
            self.toast.show_message(f"Redid: {label}", "Undo", self.undo)

    def showScreenNow(self, screen):
        """Switch straight to a screen (no slide), refreshing it like the drawer does"""
        target = self.screenWidget(screen)
        if target is None:
            return
        self._cancelTransition()
        if self.stacked_widget.currentWidget() is not target:
            self.stacked_widget.setCurrentWidget(target)
            if screen == "dashboard_screen":
                self.dashboard_screen.refreshDashboard()
            elif screen == "planning_screen":
                self.planning_screen.refreshPlanningUI()
            elif screen == "projects_screen":
                self.projects_screen.refreshProjects()
        self._discardTransientViews()
        name = next((key for key, value in self.screen_mapping.items() if value == screen), "Settings")
        self.banner_header.setText(name)

    def openSearchResult(self, result):
        """Go to a search result: a task's card, a project, a note, or a mind map (centred on the shape)"""
        from utils.search import MINDMAP, NOTE, PROJECT, TASK
        if result.kind == TASK:
            task = self.data_manager.get_tasks().get(result.id)
            if task is None:
                return
            self.showScreenNow("dashboard_screen")
            self.dashboard_screen.openExpandedCardOverlay(task=task, grid_id=None)
        elif result.kind == PROJECT:
            self.showProjectDetail(result.id)
        elif result.kind == NOTE:
            self.showScreenNow("notes_screen")
            notes = self.notes_screen
            notes.updateNotesList()
            for row in range(notes.notes_list.count()):
                item = notes.notes_list.item(row)
                if item.data(Qt.UserRole) == result.id:
                    notes.loadSelectedNote(item)
                    notes.updateNotesList()  # selects it, unless the switch was cancelled
                    break
        elif result.kind == MINDMAP:
            self.showScreenNow("mindmaps_screen")
            screen = self.mindmaps_screen
            if screen.current_mindmap_id != result.id:
                screen.load_mindmap_by_id(result.id)
            if screen.current_mindmap_id == result.id:
                screen.show_node(result.extra.get("node_id"))

    def initiateStackedWidgetTransition(self, screen):
        targetWidget = self.screenWidget(screen)
        # Compare with where an in-progress slide is heading, not where it started
        currentWidget = self._transition_target or self.stacked_widget.currentWidget()

        if targetWidget and currentWidget != targetWidget:
            self.animateStackedWidgetTransition(currentWidget, targetWidget)

            # Refresh screens when switching to them to sync with any changes
            if screen == "dashboard_screen":
                self.dashboard_screen.refreshDashboard()
            elif screen == "planning_screen":
                self.planning_screen.refreshPlanningUI()
            elif screen == "projects_screen":
                self.projects_screen.refreshProjects()
        elif targetWidget is None:
            self.logger.warning(f"No valid transition for screen: {screen}")

        for key, value in self.screen_mapping.items():
            if value == screen:
                self.banner_header.setText(key)
                break
        else:
            if screen == "settings_screen":
                self.banner_header.setText("Settings")

    def toggleDrawer(self):
        # Determine the end positions for the drawer and central widget
        drawer_end_x = 0 if not self.drawer_open else -self.drawer_width
        central_widget_end_x = self.drawer_width if not self.drawer_open else 0

        # Configure and start the drawer animation
        self.drawer_animation.setEndValue(QRect(drawer_end_x, 0, self.drawer_width, self.height()))
        self.drawer_animation.start()

        # Configure and start the central widget animation
        central_widget_geometry = QRect(central_widget_end_x, 0, self.width() - central_widget_end_x, self.height())
        self.central_widget_animation.setEndValue(central_widget_geometry)
        self.central_widget_animation.start()

        # Toggle the state
        self.drawer_open = not self.drawer_open

        if not self.drawer_open:
            self.drawer_shadow.setEnabled(False)
        else:
            self.drawer_shadow.setEnabled(True)

    def animateStackedWidgetTransition(self, oldWidget, newWidget, duration=500):
        # Finish any slide still running so two can't fight over the same widgets
        if self._transition_target is not None:
            self.outgoingAnimation.stop()
            self.incomingAnimation.stop()
            self._finishTransition(self._transition_target)
            oldWidget = self.stacked_widget.currentWidget()
        self._transition_target = newWidget

        # Child geometry is relative to the stacked widget, so animate within its own rect
        currentGeometry = self.stacked_widget.rect()
        width = currentGeometry.width()
        startRect = QRect(currentGeometry)
        endRect = QRect(currentGeometry)

        self.outgoingAnimation = QPropertyAnimation(oldWidget, b"geometry")
        self.incomingAnimation = QPropertyAnimation(newWidget, b"geometry")

        self.outgoingAnimation.setStartValue(startRect)
        self.outgoingAnimation.setEndValue(startRect.translated(-width, 0))
        self.incomingAnimation.setStartValue(endRect.translated(width, 0))
        self.incomingAnimation.setEndValue(endRect)

        self.outgoingAnimation.setDuration(duration)
        self.incomingAnimation.setDuration(duration)
        self.outgoingAnimation.setEasingCurve(QEasingCurve.OutCubic)
        self.incomingAnimation.setEasingCurve(QEasingCurve.OutCubic)

        self.outgoingAnimation.start()
        self.incomingAnimation.start()

        QTimer.singleShot(duration, lambda: self._finishTransition(newWidget))

    def _finishTransition(self, newWidget):
        # Ignore a timer from a slide that was already finished early by a newer one
        if self._transition_target is not newWidget:
            return
        self._transition_target = None
        self.stacked_widget.setCurrentWidget(newWidget)
        # Put every screen back in place; the slide leaves the old one off to the side
        for index in range(self.stacked_widget.count()):
            self.stacked_widget.widget(index).setGeometry(self.stacked_widget.rect())
        # Leaving Project Detail or Gantt through the drawer: they're no longer needed
        self._discardTransientViews()

_showing_error = False

def handle_uncaught_exception(exc_type, exc_value, exc_traceback):
    """Log unexpected errors and keep the app running.

    PyQt ends the whole process the moment a signal handler raises, unless a
    sys.excepthook is installed, so without this one bug in any button handler
    closes the app with nothing saved and nothing logged.
    """
    global _showing_error
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logging.getLogger("CentralManager").error(
        "Unexpected error", exc_info=(exc_type, exc_value, exc_traceback))

    # One dialog at a time, so a repeating error can't stack them up
    if QApplication.instance() is None or _showing_error:
        return
    _showing_error = True
    message = (f"An unexpected error occurred:\n\n{exc_type.__name__}: {exc_value}\n\n"
               "Project Meridian will keep running. The details are in app.log.")
    try:
        try:
            dialogs.critical(None, "Something Went Wrong", message)
        except Exception:
            # If the app's own dialog can't be shown, the plain one still tells the user
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(None, "Something Went Wrong", message)
    finally:
        _showing_error = False

def warn_about_unreadable_file(parent, original_path, backup_path):
    """Tell the user a data file was set aside instead of being silently replaced"""
    dialogs.warning(
        parent,
        "Data file could not be read",
        f"{os.path.basename(original_path)} could not be read, so Project Meridian set it aside "
        f"and started a new one. Nothing was deleted.\n\n"
        f"The original is saved as:\n{backup_path}"
    )

if __name__ == '__main__':
    app_config = AppConfig()  # This will trigger directory creation
    setup_logging(app_config.logs_dir)
    logger = get_logger("CentralManager")
    sys.excepthook = handle_uncaught_exception

    # Interface size from Settings ("auto" enlarges it on big, low-density monitors).
    # Has to be set before the QApplication exists.
    apply_interface_scale(Settings.instance().get("interface_scale"))

    # Scale the UI with Windows display scaling (125%, 150%, ...). Without this, fixed
    # pixel sizes stay the same while text grows, so text gets cut off.
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)

    # Saved colours must be in place before any screen builds its stylesheets
    apply_color_overrides()

    app.setStyle("Fusion")
    app.setStyleSheet(f"""
        QWidget {{
            background-color: {AppColors.main_background_color};
            color: white
        }}
    """)

    # app_icon.ico holds the icon at 16-256 px, so Windows picks a sharp size everywhere
    app_icon = QIcon(resource_path('resources/images/app_icon.ico'))
    if app_icon.isNull():
        app_icon = QIcon(resource_path('resources/images/Untitled2.png'))
    app.setWindowIcon(app_icon)

    if sys.platform == 'win32':
        # Lets Windows group the taskbar icon under this app instead of python.exe
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('ProjectMeridian.v0.1')

    main_window = MainWindow()
    main_window.show()

    # After sleep or a monitor change, put the window back at the right scale (Qt 5 can get
    # stuck at another monitor's scale, leaving everything huge)
    from utils.display_watch import DisplayWatcher
    main_window.display_watcher = DisplayWatcher(main_window)
    main_window.offerGuideOnce()

    # Report files set aside during startup, then any set aside later
    for original_path, backup_path in get_quarantined_files():
        warn_about_unreadable_file(main_window, original_path, backup_path)
    set_quarantine_handler(partial(warn_about_unreadable_file, main_window))
    sys.exit(app.exec_())
