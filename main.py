import os, yaml, logging, sys, asyncio, json, qasync
from utils.dashboard_config import DashboardConfigManager
from ui.welcome_screen import WelcomeScreen
from ui.dashboard_screen import DashboardScreen
from resources.styles import AppStyles, AnimatedButton
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, 
                             QVBoxLayout, QWidget, QFrame, QDesktopWidget, QSpacerItem,
                             QSizePolicy, QGraphicsDropShadowEffect, QHBoxLayout,
                             QSpacerItem, QLabel, QStackedWidget, )
from PyQt5.QtCore import QPropertyAnimation, QEasingCurve, QRect, QEvent, Qt, QTimer
from PyQt5.QtGui import QResizeEvent, QPixmap
from pathlib import Path
import shutil

def setup_logging():
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(filename='app.log', filemode='a', format=log_format, level=logging.INFO)
    
    # Create console handler and set level to debug
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(log_format))
    
    # Add the handler to the root logger
    logging.getLogger('').addHandler(console_handler)

def get_logger(name=__name__):
    return logging.getLogger(name)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        logging.info("Application starting")

        self.banner_header_label = ""

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

        self.banner.raise_()
        self.drawer.raise_()
        self.toggle_drawer_button.raise_()
        self.banner_header.raise_()

        self.drawer.setGeometry(-self.drawer.width(), 0, self.drawer.width(), self.height())

    def eventFilter(self, source, event):
        if event.type() == QEvent.MouseButtonPress:
            # Get the click position relative to the window
            click_position = self.mapFromGlobal(event.globalPos())

            if self.drawer_open and not self.drawer.geometry().contains(click_position) and not self.toggle_drawer_button.rect().contains(self.toggle_drawer_button.mapFromGlobal(event.globalPos())):
                self.toggleDrawer()

        return super(MainWindow, self).eventFilter(source, event)

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
        self.initBanner()
        self.initDrawer()
        self.initStackedWidgets()

        self.drawer_animation = QPropertyAnimation(self.drawer, b"geometry")
        self.drawer_animation.setProperty("source", "Drawer")
        self.central_widget_animation = QPropertyAnimation(self.central_widget, b"geometry")


    def initCentralWidget(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

    def initStackedWidgets(self):
        self.stacked_widget = QStackedWidget()
        self.main_layout.addWidget(self.stacked_widget)

        self.welcome_screen = WelcomeScreen()
        self.dashboard_screen = DashboardScreen(
            logger=self.logger,
            saved_grid_layouts=DashboardConfigManager.get_all_grid_layouts()
        )

        self.dashboard_screen.setObjectName("Dashboard")

        self.stacked_widget.addWidget(self.dashboard_screen)
        self.stacked_widget.addWidget(self.welcome_screen)

        self.stacked_widget.setCurrentWidget(self.welcome_screen)

    def initBanner(self):
        self.banner = QWidget(self.central_widget)
        self.banner.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.banner.setStyleSheet(AppStyles.banner_color())
        banned_height = int(self.height()*0.125)
        self.banner.setGeometry(0, 0, self.width(), banned_height)
        self.banner.setContentsMargins(0, 0, 0, 0)
        self.banner_layout = QHBoxLayout()
        self.initToggleButton()
        self.initBannerHeader()
        self.banner.setLayout(self.banner_layout)

    def initToggleButton(self):
        self.toggle_drawer_button = QPushButton(self,)
        self.toggle_drawer_button.clicked.connect(self.toggleDrawer)
        self.toggle_drawer_button.setFixedSize(40, 40)
        self.toggle_drawer_button.setStyleSheet(AppStyles.button_toggle_drawer())
        self.toggle_drawer_button.setText("\u2630")  # Unicode character for hamburger icon

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(3)
        shadow.setXOffset(1)
        shadow.setYOffset(1)
        self.toggle_drawer_button.setGraphicsEffect(shadow)
        self.banner_layout.addWidget(self.toggle_drawer_button)

    def initBannerHeader(self):
        self.banner_header_container = QWidget()
        banner_header_layout = QHBoxLayout(self.banner_header_container)
        banner_header_layout.setContentsMargins(0, 0, 0, 0)
        self.banner_header = QLabel(self.banner_header_label)
        self.banner_header.setStyleSheet(AppStyles.banner_header())

        self.banner_header.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        banner_header_layout.addWidget(self.banner_header)
        self.banner_layout.addSpacerItem(QSpacerItem(int(self.width()*0.05), 20, QSizePolicy.Minimum, QSizePolicy.Minimum))
        self.banner_layout.addWidget(self.banner_header_container)

    def initDrawer(self):
        self.drawer = QFrame(self)
        self.drawer.setStyleSheet(AppStyles.drawer_style())
        self.drawer_layout = QVBoxLayout()
        self.drawer.setLayout(self.drawer_layout)
        self.addDrawerButtons()

        self.drawer_width = int(self.width() * 0.2)
        self.drawer.setFixedWidth(self.drawer_width)
        self.drawer_layout.setAlignment(Qt.AlignTop)
        self.drawer.move(-self.drawer_width, 0)
        self.drawer.setGeometry(-self.drawer_width, 0, self.drawer_width, int(self.screen_size.height() * 0.75))

        self.drawer_shadow = QGraphicsDropShadowEffect(self)
        self.drawer_shadow.setBlurRadius(10)
        self.drawer_shadow.setXOffset(1)
        self.drawer_shadow.setYOffset(1)
        self.drawer.setGraphicsEffect(self.drawer_shadow)
        self.drawer_shadow.setEnabled(False)

    def addDrawerButtons(self):
        self.drawer_layout.setSpacing(20)

        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        
        headerLabel = QLabel("Project Management Software")
        headerLabel.setAlignment(Qt.AlignCenter) 
        headerLabel.setStyleSheet(AppStyles.label_xlgfnt_bold()) 
        header_layout.addWidget(headerLabel)

        logo_widget = QWidget()
        #logo_layout = QHBoxLayout(logo_widget)
        #logo_pixmap = QPixmap("resources/images/header_logo_blue.png")
        #logo_pixmap = logo_pixmap.scaled(50, 50)
        #logo_label = QLabel()
        #logo_label.setPixmap(logo_pixmap)
        #logo_layout.addStretch(1)
        #logo_layout.addWidget(logo_label)
        #logo_layout.addStretch(1)
        header_layout.addWidget(logo_widget)

        self.drawer_layout.addWidget(header_widget)
        # usernameLabel = QLabel(self.username)
        # usernameLabel.setAlignment(Qt.AlignCenter)
        # usernameLabel.setStyleSheet(AppStyles.label_normal())
        # self.drawer_layout.addWidget(usernameLabel)
        
        for name, screen in self.screen_mapping.items():
            #button = QPushButton(name, self)

            button = AnimatedButton(text=name, blur=2, x=60, y=20, offsetX=1, offsetY=1)

            button.setStyleSheet(AppStyles.button_normal())
            button.clicked.connect(lambda checked, name=screen: self.buttonClicked(name))
            self.drawer_layout.addWidget(button)

        spacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.drawer_layout.addSpacerItem(spacer)

    def buttonClicked(self, screen):
        if self.drawer_open:
            self.toggleDrawer()
        
        self.drawer_animation.finished.connect(lambda: self.initiateStackedWidgetTransition(screen))
    
    def initiateStackedWidgetTransition(self, screen):
        sender = self.sender()
        source = sender.property("source")

        screen_to_widget_mapping = {
            "dashboard_screen": self.dashboard_screen
        }

        targetWidget = screen_to_widget_mapping.get(screen)
        currentWidget = self.stacked_widget.currentWidget()

        if targetWidget and currentWidget != targetWidget:
            self.animateStackedWidgetTransition(currentWidget, targetWidget)
        else:
            print(f"No valid transition for screen: {screen}")

        for key, value in self.screen_mapping.items():
            if value == screen:
                self.banner_header.setText(key)
                break
        if source == "Drawer":
            self.drawer_animation.finished.disconnect()

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

    def animateStackedWidgetTransition(self, oldWidget, newWidget, duration=500):
        currentGeometry = self.stacked_widget.geometry()
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

        QTimer.singleShot(duration, lambda: self.stacked_widget.setCurrentWidget(newWidget))

def ensure_required_files():
    base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'Project_Manager', 'data')
    
    # Ensure the directory exists
    os.makedirs(base_dir, exist_ok=True)

    # File paths
    saved_tasks_path = os.path.join(base_dir, 'saved_tasks.json')
    app_config_path = os.path.join(base_dir, 'app_config.yaml')

    # Check and create saved_tasks.json if it doesn't exist
    if not os.path.exists(saved_tasks_path):
        default_tasks = {"tasks": []}
        with open(saved_tasks_path, 'w') as f:
            json.dump(default_tasks, f, indent=4)
        print(f"Created missing file: {saved_tasks_path}")

    # Check and create app_config.yaml if it doesn't exist
    if not os.path.exists(app_config_path):
        default_config = {
            "app_name": "Project Manager",
            "version": "1.0",
            "settings": {}
        }
        with open(app_config_path, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False)
        print(f"Created missing file: {app_config_path}")

    print("File check completed.")


if __name__ == '__main__':
    setup_logging()
    logger = get_logger("CentralManager")
    logging.info("Logging system initialized")
    ensure_required_files()
    app = QApplication(sys.argv)
    loop = qasync.QEventLoop(app) # Need Qasync for PyQt async - QWidgets
    asyncio.set_event_loop(loop)
    
    main_window = MainWindow()
    main_window.show()

    with loop:
        loop.run_forever()
        