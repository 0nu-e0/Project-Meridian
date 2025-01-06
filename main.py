import logging, sys, asyncio, json
from ui.dashboard_screen import DashboardScreen
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, 
                             QVBoxLayout, QWidget, QFrame, QDesktopWidget, QSpacerItem,
                             QSizePolicy, QGraphicsDropShadowEffect, QHBoxLayout,
                             QSpacerItem, QLabel, QStackedWidget, )
from PyQt5.QtCore import QPropertyAnimation, QEasingCurve, QRect, QEvent, Qt, QTimer
from PyQt5.QtGui import QResizeEvent, QPixmap
from pathlib import Path
import shutil

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        logging.info("Application starting")

        self.screen_mapping = {
            "Dashboard": "dashboard_screen"
        }

        self.screen_size = QDesktopWidget().screenGeometry(-1)
        self.resize(int(self.screen_size.width() * 0.90), int(self.screen_size.height() * 0.90))
        self.setMinimumSize(int(self.screen_size.width() * 0.5), int(self.screen_size.height() * 0.5))
        
        self.initUI()

        self.drawer_open = False
        self.pendingTransistion = None
        QApplication.instance().installEventFilter(self)

        self.toggle_drawer_button.raise_()

        self.drawer.setGeometry(-self.drawer.width(), 0, self.drawer.width(), self.height())

    def eventFilter(self, source, event):
        if event.type() == QEvent.MouseButtonPress:
            # Get the click position relative to the window
            click_position = self.mapFromGlobal(event.globalPos())

            if self.drawer_open and not self.drawer.geometry().contains(click_position) and not self.toggle_drawer_button.rect().contains(self.toggle_drawer_button.mapFromGlobal(event.globalPos())):
                self.toggleDrawer()

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)

        new_width = max(0, self.width()) 
        new_height = max(0, self.height()) 
        drawer_width = self.drawer_width

        # Update drawer geometry
        if hasattr(self, 'drawer') and self.drawer and self.drawer.isVisible():
            try:
                if self.drawer_open:
                    self.drawer.setGeometry(0, 0, drawer_width, new_height)
                else:
                    self.drawer.setGeometry(-drawer_width, 0, drawer_width, new_height)
                    
            except Exception as e:
                print(f"Error setting drawer geometry: {e}")

        # Adjust banner and central widget taking the drawer into account
        if hasattr(self, 'banner') and self.banner:
            try:
                if self.drawer_open:
                    self.banner.setGeometry(0, 0, new_width, 75)
                else:
                    self.banner.setGeometry(0, 0, new_width, 75)
            except Exception as e:
                print(f"Error setting banner geometry: {e}")

        # Adjust central widget and other components accordingly
        if hasattr(self, 'central_widget') and self.central_widget:
            try:
                if self.drawer_open:
                    self.central_widget.setGeometry(drawer_width, 0, new_width - drawer_width , new_height)
                else:
                    self.central_widget.setGeometry(0, 0, new_width, new_height)
            except Exception as e:
                print(f"Error setting central widget geometry: {e}")

        # Adjust toggle button position
        if hasattr(self, 'toggle_drawer_button') and self.toggle_drawer_button and self.toggle_drawer_button.isVisible():
            try:
                button_center_y = int(75 / 2 - self.toggle_drawer_button.height() / 2)
                self.toggle_drawer_button.move(10, button_center_y)
            except Exception as e:
                print(f"Error moving toggle drawer button: {e}")
    
    def initUI(self):
        self.setWindowTitle("Project Manager Software")
        
        self.initCentralWidget()
        self.initDrawer()
        self.initStackedWidgets()

    def initCentralWidget(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargin(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

    def initStackedWidgets(self):
        self.stacked_widget = QStackedWidget()
        self.main_layout.addWidget(self.stacked_widget)

        self.wdashboard_screen = DashboardScreen()

    
    def toggleDrawer(self):
        # Determine the end positions for the drawer and central widget

        drawer_end_x = 0 if not self.drawer_open else -self.drawer_width
        central_widget_end_x = self.drawer_width if not self.drawer_open else 0

        # Configure and start the drawer animation
        self.drawer_animation.setEndValue(QRect(drawer_end_x, 0, self.drawer_width, self.drawer.height()))
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