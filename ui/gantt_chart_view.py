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
# copies or substantial portion of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# -----------------------------------------------------------------------------
# File: gantt_chart_view.py
# Description: Gantt chart view for project timeline visualization
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

from datetime import datetime, timedelta
from PyQt5.QtCore import Qt, pyqtSignal, QRect, QPoint, QDate, QRectF
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QDialog, QLineEdit, QTextEdit,
    QDateEdit, QColorDialog, QMessageBox, QSizePolicy, QSpacerItem,
    QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsTextItem,
    QGraphicsItem, QFileDialog
)
from PyQt5.QtPrintSupport import QPrinter

from models.gantt_item import GanttChart, GanttChartItem, GanttItemType
from models.phase import Phase
from utils.gantt_io import load_gantt_chart_for_project, save_gantt_chart
from utils.projects_io import load_phases_from_json
from resources.styles import AppStyles, AnimatedButton


class GanttBarItem(QGraphicsRectItem):
    """
    A draggable bar representing a Gantt chart item on the timeline
    """

    def __init__(self, gantt_item: GanttChartItem, timeline_widget, x, y, width, height):
        super().__init__(x, y, width, height)

        self.gantt_item = gantt_item
        self.timeline_widget = timeline_widget

        # Visual setup
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)

        # Set colors
        color = QColor(gantt_item.color)
        self.setBrush(QBrush(color))
        self.setPen(QPen(color.darker(120), 2))

        # Resize handles
        self.resize_handle_size = 8
        self.resizing = None  # None, 'left', or 'right'
        self.original_pos = None

    def mousePressEvent(self, event):
        """Handle mouse press for dragging or resizing"""
        self.original_pos = self.pos()

        # Check if clicking on resize handles
        rect = self.rect()
        click_pos = event.pos()

        if click_pos.x() < self.resize_handle_size:
            self.resizing = 'left'
        elif click_pos.x() > rect.width() - self.resize_handle_size:
            self.resizing = 'right'
        else:
            self.resizing = None

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle dragging or resizing"""
        if self.resizing:
            # Resize logic
            delta_x = event.scenePos().x() - event.buttonDownScenePos(Qt.LeftButton).x()
            rect = self.rect()

            if self.resizing == 'left':
                new_x = self.x() + delta_x
                new_width = rect.width() - delta_x
                if new_width > 20:  # Minimum width
                    self.setRect(0, 0, new_width, rect.height())
                    self.setPos(new_x, self.y())
            elif self.resizing == 'right':
                new_width = rect.width() + delta_x
                if new_width > 20:  # Minimum width
                    self.setRect(0, 0, new_width, rect.height())
        else:
            # Only allow horizontal movement
            super().mouseMoveEvent(event)
            self.setY(self.original_pos.y())

    def mouseReleaseEvent(self, event):
        """Update dates when dragging/resizing ends"""
        if self.resizing or self.pos() != self.original_pos:
            self.timeline_widget.updateItemDatesFromPosition(self.gantt_item, self)

        self.resizing = None
        self.original_pos = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Open edit dialog on double-click"""
        self.timeline_widget.editItem(self.gantt_item)
        # Don't call super() - the item may be deleted after editItem re-renders
        event.accept()

    def paint(self, painter, option, widget):
        """Custom paint with rounded corners"""
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw rounded rectangle
        rect = self.rect()
        path = QPainterPath()
        path.addRoundedRect(rect, 5, 5)

        painter.fillPath(path, self.brush())
        painter.strokePath(path, self.pen())

        # Draw resize handles
        handle_color = QColor(255, 255, 255, 100)
        painter.fillRect(0, 0, self.resize_handle_size, int(rect.height()), handle_color)
        painter.fillRect(int(rect.width()) - self.resize_handle_size, 0,
                        self.resize_handle_size, int(rect.height()), handle_color)


class GanttTimeline(QGraphicsView):
    """
    The timeline area showing the Gantt chart bars
    """

    itemsChanged = pyqtSignal()

    def __init__(self, gantt_chart: GanttChart, parent=None):
        super().__init__(parent)

        self.gantt_chart = gantt_chart
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        # Timeline settings
        self.row_height = 50
        self.label_width = 200
        self.pixels_per_day = 3
        self.start_date = None
        self.end_date = None

        # Visual settings
        self.setStyleSheet("""
            QGraphicsView {
                background-color: #2c3e50;
                border: 1px solid #34495e;
            }
        """)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.renderChart()

    def calculateTimelineBounds(self, force_recalculate=False):
        """Calculate the start and end dates for the timeline"""
        # Only recalculate if forced or if bounds don't exist
        if not force_recalculate and self.start_date and self.end_date:
            # Expand bounds if needed to accommodate new items
            dates = []
            for item in self.gantt_chart.items:
                if item.start_date:
                    dates.append(item.start_date)
                if item.end_date:
                    dates.append(item.end_date)

            if dates:
                min_date = min(dates) - timedelta(days=7)
                max_date = max(dates) + timedelta(days=7)

                # Only expand bounds, never shrink them
                if min_date < self.start_date:
                    self.start_date = min_date
                if max_date > self.end_date:
                    self.end_date = max_date
            return

        if not self.gantt_chart.items:
            # Default to current month
            today = datetime.now()
            self.start_date = today.replace(day=1)
            self.end_date = (today.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
            return

        # Find earliest and latest dates
        dates = []
        for item in self.gantt_chart.items:
            if item.start_date:
                dates.append(item.start_date)
            if item.end_date:
                dates.append(item.end_date)

        if dates:
            self.start_date = min(dates)
            self.end_date = max(dates)

            # Add padding (1 week before and after)
            self.start_date = self.start_date - timedelta(days=7)
            self.end_date = self.end_date + timedelta(days=7)
        else:
            # Use default if no dates set
            today = datetime.now()
            self.start_date = today.replace(day=1)
            self.end_date = (today.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)

    def renderChart(self):
        """Render the entire Gantt chart"""
        self.scene.clear()
        self.calculateTimelineBounds()

        if not self.start_date or not self.end_date:
            return

        # Calculate dimensions
        total_days = (self.end_date - self.start_date).days
        chart_width = total_days * self.pixels_per_day
        chart_height = len(self.gantt_chart.items) * self.row_height

        # Draw timeline header
        self.drawTimelineHeader(chart_width)

        # Draw grid and items
        for idx, item in enumerate(self.gantt_chart.items):
            y_pos = idx * self.row_height + 60  # Offset for header

            # Draw row background (alternating colors)
            bg_color = QColor(52, 73, 94) if idx % 2 == 0 else QColor(44, 62, 80)
            bg_rect = self.scene.addRect(0, y_pos, self.label_width + chart_width,
                                        self.row_height, QPen(Qt.NoPen), QBrush(bg_color))
            bg_rect.setZValue(-1)

            # Draw label
            label = QGraphicsTextItem(item.title)
            label.setDefaultTextColor(QColor(255, 255, 255))
            label.setFont(QFont("Arial", 10, QFont.Bold))
            label.setPos(10, y_pos + 15)
            label.setTextWidth(self.label_width - 20)
            self.scene.addItem(label)

            # Draw bar if dates are set
            if item.start_date and item.end_date:
                bar_x = self.dateToX(item.start_date)
                bar_width = (item.end_date - item.start_date).days * self.pixels_per_day
                bar_y = y_pos + 10

                bar = GanttBarItem(item, self, bar_x, bar_y, bar_width, 30)
                self.scene.addItem(bar)

        # Set scene rect
        self.scene.setSceneRect(0, 0, self.label_width + chart_width, max(chart_height + 60, 400))

    def drawTimelineHeader(self, chart_width):
        """Draw the timeline header with dates"""
        header_height = 50
        header_bg = self.scene.addRect(0, 0, self.label_width + chart_width, header_height,
                                      QPen(Qt.NoPen), QBrush(QColor(41, 128, 185)))
        header_bg.setZValue(-1)

        # Draw month labels
        current_date = self.start_date
        last_month = None

        while current_date <= self.end_date:
            if current_date.month != last_month:
                x_pos = self.dateToX(current_date)
                month_label = QGraphicsTextItem(current_date.strftime("%B %Y"))
                month_label.setDefaultTextColor(QColor(255, 255, 255))
                month_label.setFont(QFont("Arial", 10, QFont.Bold))
                month_label.setPos(x_pos + 5, 5)
                self.scene.addItem(month_label)

                # Draw day markers every 7 days
                for day_offset in range(0, 31, 7):
                    day_date = current_date + timedelta(days=day_offset)
                    if day_date.month == current_date.month and day_date <= self.end_date:
                        day_x = self.dateToX(day_date)
                        day_label = QGraphicsTextItem(str(day_date.day))
                        day_label.setDefaultTextColor(QColor(255, 255, 255, 180))
                        day_label.setFont(QFont("Arial", 8))
                        day_label.setPos(day_x + 2, 30)
                        self.scene.addItem(day_label)

                        # Draw vertical grid line
                        line = self.scene.addLine(day_x, header_height, day_x,
                                                 len(self.gantt_chart.items) * self.row_height + 60,
                                                 QPen(QColor(255, 255, 255, 30)))
                        line.setZValue(-2)

                last_month = current_date.month

            current_date += timedelta(days=1)

    def dateToX(self, date: datetime) -> float:
        """Convert a date to X coordinate"""
        days_from_start = (date - self.start_date).days
        return self.label_width + (days_from_start * self.pixels_per_day)

    def xToDate(self, x: float) -> datetime:
        """Convert X coordinate to date"""
        days_from_start = (x - self.label_width) / self.pixels_per_day
        return self.start_date + timedelta(days=days_from_start)

    def updateItemDatesFromPosition(self, gantt_item: GanttChartItem, bar: GanttBarItem):
        """Update item dates based on bar position and width"""
        start_date = self.xToDate(bar.x())
        end_date = self.xToDate(bar.x() + bar.rect().width())

        gantt_item.start_date = start_date
        gantt_item.end_date = end_date

        # Don't re-render the entire chart - just update the dates
        # Re-rendering would recalculate bounds and change all bar positions
        self.itemsChanged.emit()

    def editItem(self, gantt_item: GanttChartItem):
        """Open edit dialog for an item"""
        dialog = GanttItemEditDialog(gantt_item, self)
        if dialog.exec_() == QDialog.Accepted:
            self.renderChart()
            self.itemsChanged.emit()

    def dragEnterEvent(self, event):
        """Accept phase drops"""
        if event.mimeData().hasFormat('application/x-phase-id'):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        """Accept phase drops"""
        if event.mimeData().hasFormat('application/x-phase-id'):
            event.acceptProposedAction()

    def dropEvent(self, event):
        """Handle phase drop"""
        if event.mimeData().hasFormat('application/x-phase-id'):
            phase_id = event.mimeData().data('application/x-phase-id').data().decode()
            # Signal parent to add phase
            self.parent().parent().parent().addPhaseToGantt(phase_id)
            event.acceptProposedAction()


class GanttItemEditDialog(QDialog):
    """Dialog for editing Gantt chart item properties"""

    def __init__(self, gantt_item: GanttChartItem, parent=None):
        super().__init__(parent)
        self.gantt_item = gantt_item
        self.initUI()

    def initUI(self):
        """Initialize the dialog UI"""
        self.setWindowTitle("Edit Gantt Item")
        self.setModal(True)
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Title
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel("Title:"))
        self.title_input = QLineEdit(self.gantt_item.title)
        title_layout.addWidget(self.title_input)
        layout.addLayout(title_layout)

        # Description
        layout.addWidget(QLabel("Description:"))
        self.description_input = QTextEdit()
        self.description_input.setPlainText(self.gantt_item.description)
        self.description_input.setMaximumHeight(80)
        layout.addWidget(self.description_input)

        # Dates
        dates_layout = QHBoxLayout()

        # Start date
        start_layout = QVBoxLayout()
        start_layout.addWidget(QLabel("Start Date:"))
        self.start_date_input = QDateEdit()
        self.start_date_input.setCalendarPopup(True)
        if self.gantt_item.start_date:
            self.start_date_input.setDate(QDate(self.gantt_item.start_date.year,
                                                self.gantt_item.start_date.month,
                                                self.gantt_item.start_date.day))
        else:
            self.start_date_input.setDate(QDate.currentDate())
        start_layout.addWidget(self.start_date_input)
        dates_layout.addLayout(start_layout)

        # End date
        end_layout = QVBoxLayout()
        end_layout.addWidget(QLabel("End Date:"))
        self.end_date_input = QDateEdit()
        self.end_date_input.setCalendarPopup(True)
        if self.gantt_item.end_date:
            self.end_date_input.setDate(QDate(self.gantt_item.end_date.year,
                                             self.gantt_item.end_date.month,
                                             self.gantt_item.end_date.day))
        else:
            self.end_date_input.setDate(QDate.currentDate().addDays(7))
        end_layout.addWidget(self.end_date_input)
        dates_layout.addLayout(end_layout)

        layout.addLayout(dates_layout)

        # Color picker
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("Color:"))
        self.color_button = QPushButton()
        self.color_button.setStyleSheet(f"background-color: {self.gantt_item.color};")
        self.color_button.setFixedSize(50, 30)
        self.color_button.clicked.connect(self.pickColor)
        color_layout.addWidget(self.color_button)
        color_layout.addStretch()
        layout.addLayout(color_layout)

        # Buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        self.setStyleSheet("""
            QDialog {
                background-color: #2c3e50;
                color: white;
            }
            QLabel {
                color: white;
                font-size: 12px;
            }
            QLineEdit, QTextEdit, QDateEdit {
                background-color: #34495e;
                color: white;
                border: 1px solid #7f8c8d;
                border-radius: 4px;
                padding: 5px;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)

    def pickColor(self):
        """Open color picker"""
        color = QColorDialog.getColor(QColor(self.gantt_item.color), self)
        if color.isValid():
            self.gantt_item.color = color.name()
            self.color_button.setStyleSheet(f"background-color: {color.name()};")

    def save(self):
        """Save changes"""
        self.gantt_item.title = self.title_input.text()
        self.gantt_item.description = self.description_input.toPlainText()

        # Update dates
        start_qdate = self.start_date_input.date()
        end_qdate = self.end_date_input.date()

        self.gantt_item.start_date = datetime(start_qdate.year(), start_qdate.month(), start_qdate.day())
        self.gantt_item.end_date = datetime(end_qdate.year(), end_qdate.month(), end_qdate.day())

        self.accept()


class GanttChartView(QWidget):
    """
    Main Gantt chart view widget
    """

    backClicked = pyqtSignal()

    def __init__(self, project_id: str, logger, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.logger = logger
        self.gantt_chart = None
        self.phases = []

        self.loadData()
        self.initUI()

    def loadData(self):
        """Load Gantt chart data or create new"""
        self.gantt_chart = load_gantt_chart_for_project(self.project_id, self.logger)

        if not self.gantt_chart:
            # Create new chart
            self.gantt_chart = GanttChart(self.project_id)
            self.logger.info(f"Created new Gantt chart for project {self.project_id}")

        # Load project phases
        all_phases = load_phases_from_json(self.logger)
        self.phases = [p for p in all_phases.values() if p.project_id == self.project_id]
        self.phases.sort(key=lambda p: p.order)

    def initUI(self):
        """Initialize the UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Banner spacer
        banner_widget = QWidget()
        banner_layout = QVBoxLayout(banner_widget)
        banner_height = int(self.height() * 0.10)
        banner_spacer = QSpacerItem(1, banner_height, QSizePolicy.Expanding, QSizePolicy.Fixed)
        banner_layout.addSpacerItem(banner_spacer)
        main_layout.addWidget(banner_widget)

        # Content area
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(15)

        # Header
        header_layout = self.createHeader()
        content_layout.addLayout(header_layout)

        # Toolbar
        toolbar_layout = self.createToolbar()
        content_layout.addLayout(toolbar_layout)

        # Timeline
        self.timeline = GanttTimeline(self.gantt_chart, self)
        self.timeline.itemsChanged.connect(self.onItemsChanged)
        self.timeline.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.timeline.setMinimumHeight(400)
        content_layout.addWidget(self.timeline, 1)  # Stretch factor of 1 to fill space

        main_layout.addWidget(content_widget)

        self.setStyleSheet("""
            QWidget {
                background-color: #2c3e50;
                color: white;
            }
        """)

    def createHeader(self):
        """Create header with back button and title"""
        header_layout = QHBoxLayout()

        # Back button
        back_btn = QPushButton("← Back")
        back_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #3498db;
                font-size: 14px;
                font-weight: bold;
                padding: 5px 10px;
            }
            QPushButton:hover {
                color: #2980b9;
            }
        """)
        back_btn.clicked.connect(self.backClicked.emit)
        header_layout.addWidget(back_btn)

        # Title
        title = QLabel("Gantt Chart")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        return header_layout

    def createToolbar(self):
        """Create toolbar with action buttons"""
        toolbar_layout = QHBoxLayout()

        # Add custom item button
        add_btn = AnimatedButton("+ Add Custom Item")
        add_btn.setStyleSheet(AppStyles.add_button())
        add_btn.setFixedHeight(35)
        add_btn.clicked.connect(self.addCustomItem)
        toolbar_layout.addWidget(add_btn)

        # Add all phases button
        add_phases_btn = AnimatedButton("📋 Add All Phases")
        add_phases_btn.setStyleSheet(AppStyles.button_normal())
        add_phases_btn.setFixedHeight(35)
        add_phases_btn.clicked.connect(self.addAllPhases)
        toolbar_layout.addWidget(add_phases_btn)

        # Reset View button (recalculate timeline bounds)
        reset_btn = AnimatedButton("🔄 Reset View")
        reset_btn.setStyleSheet(AppStyles.button_normal())
        reset_btn.setFixedHeight(35)
        reset_btn.clicked.connect(self.resetView)
        toolbar_layout.addWidget(reset_btn)

        toolbar_layout.addStretch()

        # Export PDF button
        export_btn = AnimatedButton("📄 Export PDF")
        export_btn.setStyleSheet(AppStyles.button_normal())
        export_btn.setFixedHeight(35)
        export_btn.clicked.connect(self.exportToPDF)
        toolbar_layout.addWidget(export_btn)

        # Save button
        save_btn = AnimatedButton("💾 Save")
        save_btn.setStyleSheet(AppStyles.button_normal())
        save_btn.setFixedHeight(35)
        save_btn.clicked.connect(self.saveChart)
        toolbar_layout.addWidget(save_btn)

        return toolbar_layout

    def addCustomItem(self):
        """Add a custom Gantt item"""
        item = GanttChartItem("New Item", item_type=GanttItemType.CUSTOM)
        item.order = len(self.gantt_chart.items)

        # Open edit dialog
        dialog = GanttItemEditDialog(item, self)
        if dialog.exec_() == QDialog.Accepted:
            self.gantt_chart.add_item(item)
            self.timeline.renderChart()

    def addAllPhases(self):
        """Add all project phases to Gantt chart"""
        for phase in self.phases:
            # Check if already added
            already_added = any(item.phase_id == phase.id for item in self.gantt_chart.items)
            if not already_added:
                item = GanttChartItem.from_phase(phase)
                item.order = len(self.gantt_chart.items)
                self.gantt_chart.add_item(item)

        self.timeline.renderChart()

    def addPhaseToGantt(self, phase_id: str):
        """Add a specific phase to the Gantt chart"""
        phase = next((p for p in self.phases if p.id == phase_id), None)
        if not phase:
            return

        # Check if already added
        already_added = any(item.phase_id == phase_id for item in self.gantt_chart.items)
        if already_added:
            QMessageBox.information(self, "Already Added", "This phase is already in the Gantt chart.")
            return

        item = GanttChartItem.from_phase(phase)
        item.order = len(self.gantt_chart.items)
        self.gantt_chart.add_item(item)
        self.timeline.renderChart()

    def onItemsChanged(self):
        """Handle timeline item changes"""
        # Auto-save could be triggered here
        pass

    def resetView(self):
        """Reset the timeline view by recalculating bounds"""
        self.timeline.start_date = None
        self.timeline.end_date = None
        self.timeline.calculateTimelineBounds(force_recalculate=True)
        self.timeline.renderChart()

    def saveChart(self):
        """Save the Gantt chart"""
        if save_gantt_chart(self.gantt_chart, self.logger):
            QMessageBox.information(self, "Success", "Gantt chart saved successfully!")
        else:
            QMessageBox.warning(self, "Error", "Failed to save Gantt chart.")

    def exportToPDF(self):
        """Export the Gantt chart to PDF"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Gantt Chart",
            f"gantt_chart_{self.project_id}.pdf",
            "PDF Files (*.pdf)"
        )

        if not file_path:
            return

        try:
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(file_path)
            printer.setPageSize(QPrinter.A3)
            printer.setOrientation(QPrinter.Landscape)

            painter = QPainter()
            painter.begin(printer)

            # Render the scene to the PDF
            self.timeline.scene.render(painter)

            painter.end()

            QMessageBox.information(self, "Success", f"Gantt chart exported to {file_path}")

        except Exception as e:
            self.logger.error(f"Failed to export PDF: {e}")
            QMessageBox.warning(self, "Error", f"Failed to export PDF: {str(e)}")
