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
# File: settings_screen.py
# Description: Settings screen, opened from the gear in the drawer: colours,
#              categories, screen behaviour, and where data is stored. Laid out
#              like the Projects screen: a toolbar strip, then cards.
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

import os
from functools import partial

from PyQt5.QtCore import Qt, QUrl, pyqtSignal
from PyQt5.QtGui import QColor, QDesktopServices
from PyQt5.QtWidgets import (QCheckBox, QColorDialog, QComboBox, QFrame, QGridLayout, QHBoxLayout,
                             QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
                             QPushButton, QScrollArea, QStackedWidget, QVBoxLayout, QWidget)

from ui.custom_widgets import dialogs
from resources.styles import AnimatedButton, AppColors, AppStyles
from utils import task_sections
from utils.app_config import AppConfig
from utils.categories_config import CategoriesConfigManager, category_usage, rename_category_everywhere
from utils.display_scale import INTERFACE_SIZES, detect_auto_scale
from utils.settings import EDITABLE_COLORS, PLANNING_VIEWS, STARTUP_SCREENS, Settings, default_color

# Built-in category that Archived tasks are grouped under; it can't be renamed or removed
PROTECTED_CATEGORY = "Archived"

SECTIONS = ["🎨  Appearance", "🏷  Categories", "⚙  Behaviour", "💾  Data"]

# Colour cards on the Appearance page: (title, subtitle, colour names)
COLOR_GROUPS = [
    ("App Frame", "The window background, banner, and drawer",
     ["main_background_color", "banner_color", "accent_background_color"]),
    ("Accent", "Buttons, borders, and highlights",
     ["accent", "accent_dark", "accent_light"]),
    ("Panels", "Cards, inputs, and lists",
     ["surface", "surface_raised", "surface_sunken"]),
    ("Text", "Headings, labels, and hints",
     ["text_primary", "text_secondary", "text_muted"]),
    ("Status", "Done, delete, warnings, and highlights",
     ["success", "danger", "warning", "highlight"]),
]
COLOR_LABELS = dict(EDITABLE_COLORS)

# On wide monitors the page stays a readable width, centred, instead of stretching
CONTENT_MAX_WIDTH = 1280       # toolbar and two-column pages
SINGLE_CARD_MAX_WIDTH = 960    # pages with one card
CARD_MIN_WIDTH = 420           # below two of these side by side, cards stack in one column
PAGE_MARGIN = 20


def centered(inner, max_width):
    """Wrap inner so it grows up to max_width and is centred in any extra space"""
    inner.setMaximumWidth(max_width)
    wrapper = QWidget()
    wrapper.setStyleSheet("background: transparent;")
    row = QHBoxLayout(wrapper)
    row.setContentsMargins(0, 0, 0, 0)
    row.addStretch(1)
    row.addWidget(inner, 100)
    row.addStretch(1)
    return wrapper


class ResponsiveCardGrid(QWidget):
    """Cards in two columns when there's room, otherwise one"""

    def __init__(self, cards, parent=None):
        super().__init__(parent)
        self.cards = cards
        self.columns = 0
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(PAGE_MARGIN)
        self._arrange(2)

    def _arrange(self, columns):
        if columns == self.columns:
            return
        self.columns = columns
        for card in self.cards:
            self.grid.removeWidget(card)
        for index, card in enumerate(self.cards):
            self.grid.addWidget(card, index // columns, index % columns, Qt.AlignTop)
        for column in range(2):
            self.grid.setColumnStretch(column, 1 if column < columns else 0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._arrange(2 if event.size().width() >= 2 * CARD_MIN_WIDTH + PAGE_MARGIN else 1)


def _section_button_style(active):
    if active:
        return AppStyles.button_normal()
    return f"""
        QPushButton {{
            background-color: transparent;
            color: {AppColors.text_secondary};
            border: none;
            border-radius: 4px;
            padding: 6px 10px;
            font-weight: bold;
        }}
        QPushButton:hover {{ background-color: {AppColors.surface_raised}; color: {AppColors.text_primary}; }}
    """


def _swatch_style(hex_value):
    return f"""
        QPushButton {{
            background-color: {hex_value};
            border: 2px solid {AppColors.surface_raised};
            border-radius: 6px;
        }}
        QPushButton:hover {{ border: 2px solid {AppColors.accent_light}; }}
    """


class SettingsCard(QFrame):
    """A titled, rounded panel in the style of a project card"""

    def __init__(self, title, subtitle=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet(AppStyles.card_panel("SettingsCard"))
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(18, 15, 18, 18)
        self.layout.setSpacing(10)

        title_label = QLabel(title)
        title_label.setStyleSheet(
            f"font-size: 16px; font-weight: bold; color: {AppColors.text_primary}; background: transparent; border: none;")
        self.layout.addWidget(title_label)
        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setWordWrap(True)
            subtitle_label.setStyleSheet(
                f"font-size: 12px; color: {AppColors.text_secondary}; background: transparent; border: none;")
            self.layout.addWidget(subtitle_label)

    def addField(self, label_text, widget):
        """A small bold label above a control, as in the task card"""
        label = QLabel(label_text)
        label.setStyleSheet(AppStyles.field_label())
        self.layout.addWidget(label)
        self.layout.addWidget(widget)


class SettingsScreen(QWidget):
    """Settings, one section at a time. Changes save as they're made."""

    # Ask the main window to restart the app (for colour changes)
    restartRequested = pyqtSignal()

    def __init__(self, logger, parent=None):
        super().__init__(parent)
        self.logger = logger
        self.settings = Settings.instance()
        self.color_buttons = {}
        self.color_hex_labels = {}
        self.color_reset_buttons = {}
        self.section_buttons = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFixedHeight(2)
        layout.addWidget(separator)
        layout.addWidget(self._buildToolbar())
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFixedHeight(2)
        layout.addWidget(separator)

        self.pages = QStackedWidget()
        for build in (self._buildAppearancePage, self._buildCategoriesPage,
                      self._buildBehaviourPage, self._buildDataPage):
            self.pages.addWidget(self._scrollable(build()))
        layout.addWidget(self.pages, 1)

        self.showSection(0)

    # ------------------------------------------------------------------ layout helpers

    def _buildToolbar(self):
        # The dark strip runs edge to edge; its buttons line up with the page content
        strip = QWidget()
        strip.setStyleSheet(AppStyles.toolbar_strip())
        strip_layout = QHBoxLayout(strip)
        strip_layout.setContentsMargins(0, 0, 0, 0)
        bar_widget = QWidget()
        bar = QHBoxLayout(bar_widget)
        bar.setContentsMargins(PAGE_MARGIN, 15, PAGE_MARGIN, 15)
        bar.setSpacing(10)
        strip_layout.addWidget(centered(bar_widget, CONTENT_MAX_WIDTH + 2 * PAGE_MARGIN))

        for index, text in enumerate(SECTIONS):
            button = AnimatedButton(text)
            button.setFixedHeight(36)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(partial(self.showSection, index))
            self.section_buttons.append(button)
            bar.addWidget(button)
        bar.addStretch(1)

        self.reset_all_button = AnimatedButton("Reset All Colours")
        self.reset_all_button.setToolTip("Put every colour back to the original")
        self.reset_all_button.setStyleSheet(AppStyles.add_button())
        self.reset_all_button.setFixedHeight(40)
        self.reset_all_button.clicked.connect(self.resetAllColors)
        self.restart_button = AnimatedButton("🔄 Restart to Apply")
        self.restart_button.setStyleSheet(AppStyles.button_normal())
        self.restart_button.setFixedHeight(40)
        self.restart_button.setToolTip("Colour changes apply after a restart")
        self.restart_button.clicked.connect(self.restartRequested.emit)
        self.appearance_actions = [self.reset_all_button, self.restart_button]
        for widget in self.appearance_actions:
            # Keep their space when hidden, so the toolbar is the same height on every section
            policy = widget.sizePolicy()
            policy.setRetainSizeWhenHidden(True)
            widget.setSizePolicy(policy)
            bar.addWidget(widget)

        # Never squeeze a button below its label; narrow windows get a shorter gap instead
        for button in self.section_buttons + self.appearance_actions:
            button.setMinimumWidth(button.sizeHint().width())
        return strip

    def showSection(self, index):
        self.pages.setCurrentIndex(index)
        for i, button in enumerate(self.section_buttons):
            button.setStyleSheet(_section_button_style(i == index))
        for widget in self.appearance_actions:
            widget.setVisible(index == 0)

    def _scrollable(self, widget):
        area = QScrollArea()
        area.setStyleSheet(AppStyles.scroll_area())
        area.setWidgetResizable(True)
        area.setFrameShape(QFrame.NoFrame)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        area.setWidget(widget)
        return area

    def _page(self):
        """A page whose content column is capped and centred (left edge lines up with the toolbar)"""
        page = QWidget()
        page.setStyleSheet(AppStyles.background_color())
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)

        column = QWidget()
        column.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(column)
        layout.setContentsMargins(PAGE_MARGIN, PAGE_MARGIN, PAGE_MARGIN, PAGE_MARGIN)
        layout.setSpacing(PAGE_MARGIN)
        page_layout.addWidget(centered(column, CONTENT_MAX_WIDTH + 2 * PAGE_MARGIN))
        page_layout.addStretch(1)
        return page, layout

    def _cardGrid(self, cards):
        return ResponsiveCardGrid(cards)

    def _singleCard(self, layout, card):
        """One card per page reads better narrower; keep it on the content's left edge"""
        card.setMaximumWidth(SINGLE_CARD_MAX_WIDTH)
        row = QHBoxLayout()
        row.addWidget(card, 100)  # fills up to its maximum width...
        row.addStretch(1)         # ...then the rest is empty space on the right
        layout.addLayout(row)

    def _blueButton(self, text):
        button = AnimatedButton(text)
        button.setStyleSheet(AppStyles.button_normal())
        button.setFixedHeight(36)
        return button

    # ------------------------------------------------------------------ appearance

    def _buildAppearancePage(self):
        page, layout = self._page()

        note = QLabel("Click a swatch to change a colour. Colour and size changes apply after a restart; "
                      "use Restart to Apply when you're done.")
        note.setWordWrap(True)
        note.setStyleSheet(f"color: {AppColors.text_muted}; font-size: 12px; background: transparent;")
        layout.addWidget(note)

        cards = [self._buildInterfaceSizeCard()]
        for title, subtitle, names in COLOR_GROUPS:
            card = SettingsCard(title, subtitle)
            for name in names:
                card.layout.addLayout(self._colorRow(name))
            cards.append(card)
        layout.addWidget(self._cardGrid(cards))
        layout.addStretch(1)

        self._refreshSwatches()
        return page

    def _buildInterfaceSizeCard(self):
        card = SettingsCard("Interface Size", "How big text and controls are, across the whole app")
        combo = QComboBox()
        combo.setStyleSheet(AppStyles.combo_box_accent())
        combo.setFixedHeight(36)
        combo.addItem(f"Auto: {round(detect_auto_scale() * 100)}% for this monitor", "auto")
        for percent in INTERFACE_SIZES:
            combo.addItem(f"{percent}%", percent)
        combo.setCurrentIndex(max(0, combo.findData(self.settings.get("interface_scale"))))
        combo.currentIndexChanged.connect(lambda _i: self.settings.set("interface_scale", combo.currentData()))
        self.interface_size_combo = combo
        card.addField("Size", combo)
        note = QLabel("Auto enlarges everything on large monitors with low pixel density. "
                      "Changes apply after a restart.")
        note.setWordWrap(True)
        note.setStyleSheet(f"color: {AppColors.text_muted}; font-size: 11px; background: transparent; border: none;")
        card.layout.addWidget(note)
        return card

    def _colorRow(self, name):
        row = QHBoxLayout()
        row.setSpacing(12)

        swatch = QPushButton()
        swatch.setToolTip("Click to pick a colour")
        swatch.setFixedSize(44, 28)
        swatch.setCursor(Qt.PointingHandCursor)
        swatch.clicked.connect(partial(self.pickColor, name))
        self.color_buttons[name] = swatch
        row.addWidget(swatch)

        label = QLabel(COLOR_LABELS.get(name, name))
        label.setStyleSheet(f"font-size: 13px; color: {AppColors.text_primary}; background: transparent; border: none;")
        row.addWidget(label, 1)

        hex_label = QLabel()
        hex_label.setStyleSheet(f"font-size: 11px; color: {AppColors.text_muted}; background: transparent; border: none;")
        self.color_hex_labels[name] = hex_label
        row.addWidget(hex_label)

        reset = QPushButton("↺")
        reset.setToolTip("Back to the default colour")
        reset.setFixedSize(24, 24)
        reset.setCursor(Qt.PointingHandCursor)
        reset.setStyleSheet(f"""
            QPushButton {{ color: {AppColors.accent}; background: transparent; border: none; font-size: 16px; }}
            QPushButton:hover {{ color: {AppColors.accent_light}; }}
        """)
        reset.clicked.connect(partial(self.resetColor, name))
        self.color_reset_buttons[name] = reset
        row.addWidget(reset)
        return row

    def _currentColor(self, name):
        return self.settings.color_overrides().get(name, default_color(name))

    def _refreshSwatches(self):
        overrides = self.settings.color_overrides()
        for name, button in self.color_buttons.items():
            value = self._currentColor(name)
            button.setStyleSheet(_swatch_style(value))
            button.setToolTip(f"Change {COLOR_LABELS.get(name, name).lower()}")
            self.color_hex_labels[name].setText(value.upper())
            # Keep the space so rows don't shift, but only show reset when changed
            self.color_reset_buttons[name].setEnabled(name in overrides)
            self.color_reset_buttons[name].setText("↺" if name in overrides else "")

    def pickColor(self, name):
        color = QColorDialog.getColor(QColor(self._currentColor(name)), self, "Choose a colour")
        if color.isValid():
            self.settings.set_color(name, color.name())
            self._refreshSwatches()

    def resetColor(self, name):
        self.settings.set_color(name, None)
        self._refreshSwatches()

    def resetAllColors(self):
        self.settings.reset_colors()
        self._refreshSwatches()

    # ------------------------------------------------------------------ categories

    def _buildCategoriesPage(self):
        page, layout = self._page()

        card = SettingsCard(
            "Task Categories",
            "These are offered when editing a task. Renaming a category also renames it on its tasks and "
            "Dashboard groups. Removing one keeps its tasks as they are; it just isn't offered for new tasks.")

        self.category_list = QListWidget()
        self.category_list.setStyleSheet(AppStyles.list_widget_accent())
        self.category_list.setMinimumHeight(320)
        card.layout.addWidget(self.category_list)

        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        add = AnimatedButton("+ New Category")
        add.setStyleSheet(AppStyles.add_button())
        add.setFixedHeight(36)
        add.clicked.connect(self.addCategory)
        buttons.addWidget(add)
        for text, handler in (("Rename", self.renameCategory), ("Remove", self.removeCategory)):
            button = self._blueButton(text)
            button.clicked.connect(handler)
            buttons.addWidget(button)
        buttons.addStretch(1)
        for text, step in (("▲ Up", -1), ("▼ Down", 1)):
            button = self._blueButton(text)
            button.clicked.connect(partial(self.moveCategory, step))
            buttons.addWidget(button)
        card.layout.addLayout(buttons)

        self._singleCard(layout, card)
        layout.addStretch(1)
        self.refreshCategories()
        return page

    def _categoryRow(self, name, count):
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(10, 6, 10, 6)

        title = QLabel(f"🔒 {name}" if name == PROTECTED_CATEGORY else name)
        title.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {AppColors.text_primary};")
        row_layout.addWidget(title, 1)

        # A badge like the status badge on a project card
        badge = QLabel(f"{count} task{'s' if count != 1 else ''}")
        badge.setStyleSheet(f"""
            background-color: {AppColors.accent if count else AppColors.surface_raised};
            color: {AppColors.text_primary};
            border-radius: 4px; padding: 3px 8px; font-size: 10px; font-weight: bold;
        """)
        row_layout.addWidget(badge)
        return row

    def refreshCategories(self, select=None):
        usage = category_usage()
        self.category_list.clear()
        for name in CategoriesConfigManager.load_categories():
            item = QListWidgetItem()
            item.setData(Qt.UserRole, name)
            row = self._categoryRow(name, usage.get(name, 0))
            item.setSizeHint(row.sizeHint())
            self.category_list.addItem(item)
            self.category_list.setItemWidget(item, row)
            if name == select:
                self.category_list.setCurrentItem(item)
        if hasattr(self, 'new_task_category_combo'):
            self._fillCategoryCombo()

    def _selectedCategory(self):
        item = self.category_list.currentItem()
        return item.data(Qt.UserRole) if item else None

    def addCategory(self):
        name, ok = dialogs.getText(self, "Add Category", "Category name:")
        name = name.strip()
        if not ok or not name:
            return
        if CategoriesConfigManager.category_exists(name):
            dialogs.information(self, "Already Exists", f"There's already a category called '{name}'.")
            return
        CategoriesConfigManager.add_category(name)
        self.refreshCategories(select=name)

    def renameCategory(self):
        old = self._selectedCategory()
        if old is None:
            return
        if old == PROTECTED_CATEGORY:
            dialogs.information(self, "Can't Rename", "Archived is where completed tasks go, so it keeps its name.")
            return
        new, ok = dialogs.getText(self, "Rename Category", "New name:", text=old)
        new = new.strip()
        if not ok or not new or new == old:
            return
        if CategoriesConfigManager.category_exists(new):
            dialogs.information(self, "Already Exists", f"There's already a category called '{new}'.")
            return
        if not rename_category_everywhere(old, new, self.logger):
            dialogs.warning(self, "Rename Failed", "The category could not be renamed. See app.log for details.")
        self.refreshCategories(select=new)

    def removeCategory(self):
        name = self._selectedCategory()
        if name is None:
            return
        if name == PROTECTED_CATEGORY:
            dialogs.information(self, "Can't Remove", "Archived is where completed tasks go, so it can't be removed.")
            return
        count = category_usage().get(name, 0)
        detail = (f"{count} task{'s' if count != 1 else ''} use it and will keep it." if count
                  else "No tasks use it.")
        reply = dialogs.question(self, "Remove Category", f"Remove '{name}' from the list?\n\n{detail}",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            CategoriesConfigManager.remove_category(name)
            self.refreshCategories()

    def moveCategory(self, step):
        name = self._selectedCategory()
        categories = CategoriesConfigManager.load_categories()
        if name not in categories:
            return
        index = categories.index(name)
        target = index + step
        if 0 <= target < len(categories):
            categories[index], categories[target] = categories[target], categories[index]
            CategoriesConfigManager.save_categories(categories)
            self.refreshCategories(select=name)

    # ------------------------------------------------------------------ behaviour

    def _buildBehaviourPage(self):
        page, layout = self._page()

        general = SettingsCard("General", "How the app starts and what new tasks look like")
        general.addField("Open on startup", self._choiceCombo(STARTUP_SCREENS, "startup_screen"))
        self.new_task_category_combo = QComboBox()
        self.new_task_category_combo.setStyleSheet(AppStyles.combo_box_accent())
        self.new_task_category_combo.setFixedHeight(36)
        self._fillCategoryCombo()
        self.new_task_category_combo.currentIndexChanged.connect(
            lambda _i: self.settings.set("new_task_category", self.new_task_category_combo.currentData()))
        general.addField("Category for new tasks", self.new_task_category_combo)

        dashboard = SettingsCard("Dashboard", "Groups shown on the Dashboard")
        dashboard.layout.addWidget(self._checkbox("Show the Archived group (completed tasks)", "dashboard_show_archived"))

        planning = SettingsCard("Planning", "The calendar on the Planning screen")
        planning.addField("Default view", self._choiceCombo(PLANNING_VIEWS, "planning_default_view"))
        planning.layout.addWidget(self._checkbox("Show Saturday and Sunday in the weekly view", "planning_show_weekends"))

        mindmaps = SettingsCard("Mindmaps", "Defaults for the mindmap canvas")
        mindmaps.layout.addWidget(self._checkbox("Show the grid", "mindmap_show_grid"))
        mindmaps.layout.addWidget(self._checkbox("Snap nodes to the grid", "mindmap_snap_to_grid"))

        task_cards = SettingsCard("Task card sections",
                                  "What an open task shows. Any task can still change its own with ☰ Sections; "
                                  "tasks you haven't changed follow these.")
        self.section_checkboxes = {}
        for key, label, _where in task_sections.SECTIONS:
            box = QCheckBox(label)
            box.setStyleSheet(AppStyles.checkbox_accent() + "QCheckBox { background: transparent; }")
            box.setChecked(task_sections.defaults()[key])
            box.toggled.connect(lambda shown, key=key: task_sections.set_default(key, shown))
            task_cards.layout.addWidget(box)
            self.section_checkboxes[key] = box

        layout.addWidget(self._cardGrid([general, dashboard, planning, mindmaps, task_cards]))
        layout.addStretch(1)
        return page

    def refreshSectionDefaults(self):
        """Tick the boxes to match the saved defaults (they can change from a task card)"""
        for key, box in getattr(self, "section_checkboxes", {}).items():
            box.blockSignals(True)
            box.setChecked(task_sections.defaults()[key])
            box.blockSignals(False)

    def showEvent(self, event):
        super().showEvent(event)
        self.refreshSectionDefaults()

    def _choiceCombo(self, choices, key):
        combo = QComboBox()
        combo.setStyleSheet(AppStyles.combo_box_accent())
        combo.setFixedHeight(36)
        for value, label in choices.items():
            combo.addItem(label, value)
        combo.setCurrentIndex(max(0, combo.findData(self.settings.get(key))))
        combo.currentIndexChanged.connect(lambda _i: self.settings.set(key, combo.currentData()))
        return combo

    def _checkbox(self, text, key):
        box = QCheckBox(text)
        box.setStyleSheet(AppStyles.checkbox_accent() + "QCheckBox { background: transparent; }")
        box.setChecked(bool(self.settings.get(key)))
        box.toggled.connect(lambda checked: self.settings.set(key, checked))
        return box

    def _fillCategoryCombo(self):
        combo = self.new_task_category_combo
        combo.blockSignals(True)
        combo.clear()
        categories = [c for c in CategoriesConfigManager.load_categories() if c != PROTECTED_CATEGORY]
        for name in categories:
            combo.addItem(name, name)
        current = self.settings.get("new_task_category")
        if current not in categories and categories:
            current = categories[0]
            self.settings.set("new_task_category", current)
        combo.setCurrentIndex(max(0, combo.findData(current)))
        combo.blockSignals(False)

    # ------------------------------------------------------------------ data

    def _buildDataPage(self):
        page, layout = self._page()
        config = AppConfig()

        storage = SettingsCard(
            "Where Your Data Is Stored",
            "Tasks, projects, notes, mindmaps, and settings are saved here. "
            "Back up this folder to keep a copy of everything.")
        path = QLineEdit(config.app_data_dir)
        path.setReadOnly(True)
        path.setStyleSheet(AppStyles.line_edit_accent())
        path.setFixedHeight(36)
        storage.addField("Data folder", path)

        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        open_data = self._blueButton("📂 Open Data Folder")
        open_data.clicked.connect(lambda: self._openFolder(config.app_data_dir))
        open_logs = self._blueButton("📄 Open Log Folder")
        open_logs.clicked.connect(lambda: self._openFolder(config.logs_dir))
        buttons.addWidget(open_data)
        buttons.addWidget(open_logs)
        buttons.addStretch(1)
        storage.layout.addLayout(buttons)

        self._singleCard(layout, storage)
        layout.addStretch(1)
        return page

    def _openFolder(self, path):
        os.makedirs(path, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))
