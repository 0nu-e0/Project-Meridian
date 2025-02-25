# -----------------------------------------------------------------------------
# Project Manager
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
# File: styles.py
# Description: Used to generate the setStyleSheet settings for layouts. 
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

from datetime import datetime
from typing import Optional
from models.task import TaskPriority, TaskStatus, TaskCategory, DueStatus
from PyQt5.QtWidgets import QGraphicsDropShadowEffect, QPushButton, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QSplitter
from PyQt5.QtGui import QColor
from PyQt5.QtCore import QPropertyAnimation, QEasingCurve, QObject, QEvent, QSize, pyqtSignal

class AppColors:
    # Keep all original names but update values
    none = "transparent"
    main_background_color = "#3b3b3b"  # Near-black background
    main_background_hover_color = "#333333"
    white = "#FFFFFF"
    accent_background_color = "#13151A"  # Subtle dark accent
    accent_background_color_dark = "#1C1F26"
    banner_color = "#2E2F73"  # Added back, modern purple
    label_font_color = "#000000"  # Light purple-white
    button_background_gray = "#2E2F73"  # Deep electric purple
    button_gray = "#E2E4FF"
    button_black = "#000000"
    button_hover = "#4A4BB7"
    button_toggle = "#00FFB2"
    button_toggle_hover = "#33FFC4"
    list = "#1C1F26"
    list_selected = "#2E2F73"
    scroll_bar_main = "#2B2B2B"
    slider_groove_background = "#2E2F73"
    slider_handle_background = "#00FFB2"
    
    # Original accent colors with updated values
    button_green = "#00FF9D"
    red = "#FF2D55"
    Green = "#00FF9D"
    Cyan = "#00F0FF"
    Blue = "#2E6AFF"
    Orange = "#FF6B2C"
    Purple = "#9D00FF"
    Magenta = "#FF00D6"
    Pink = "#FF66B2"
    Teal = "#00D6B2"
    Lavender = "#E6B3FF"
    Brown = "#B67537"
    Beige = "#E6D5AC"
    Mint = "#00FFB2"
    Olive = "#8B9A47"
    Apricot = "#FFB366"
    Grey = "#8B8B8B"
    black = "#000000"

    # Priority-specific colors
    priority_colors = {
        TaskPriority.CRITICAL: "#E74C3C",  # Red
        TaskPriority.HIGH: "#F39C12",      # Orange
        TaskPriority.MEDIUM: "#F1C40F",    # Yellow
        TaskPriority.LOW: "#2ECC71",       # Green
        TaskPriority.TRIVIAL: "#95A5A6"    # Gray
    }
    
    # Status colors
    status_colors = {
        TaskStatus.NOT_STARTED: "#95A5A6",  # Gray
        TaskStatus.IN_PROGRESS: "#3498DB",  # Blue
        TaskStatus.IN_REVIEW: "#9B59B6",    # Purple
        TaskStatus.BLOCKED: "#E74C3C",      # Red
        TaskStatus.COMPLETED: "#2ECC71",    # Green
        TaskStatus.ON_HOLD: "#F39C12",      # Orange
        TaskStatus.CANCELLED: "#34495E"     # Dark Gray
    }
   
   # Category colors
    category_colors = {
        TaskCategory.FEATURE: "#3498DB",    # Blue
        TaskCategory.BUG: "#E74C3C",        # Red
        TaskCategory.MAINTENANCE: "#F39C12", # Orange
        TaskCategory.DOCUMENTATION: "#9B59B6", # Purple
        TaskCategory.RESEARCH: "#2ECC71",    # Green
        TaskCategory.MEETING: "#95A5A6"      # Gray
    }

    progress_colors = {
        (75, 100): "#27AE60",  # Green
        (50, 74): "#F39C12",   # Orange
        (25, 49): "#F1C40F",   # Yellow
        (0, 24): "#E74C3C"     # Red
    }

    due_date_colors = {
       DueStatus.OVERDUE: "#E74C3C",    # Red
       DueStatus.DUE_SOON: "#F39C12",   # Orange
       DueStatus.UPCOMING: "#F1C40F",    # Yellow
       DueStatus.FAR_FUTURE: "#2ECC71",  # Green
       DueStatus.NO_DUE_DATE: "#95A5A6"  # Gray
   }

    @staticmethod
    def get_priority_color(priority: TaskPriority):
        return AppColors.priority_colors.get(priority, AppColors.accent_background_color)

    @staticmethod
    def get_status_color(status: TaskStatus):
        return AppColors.status_colors.get(status, AppColors.accent_background_color)
        
    @staticmethod
    def get_category_color(category: TaskCategory):
        return AppColors.category_colors.get(category, AppColors.accent_background_color)
    
    @staticmethod
    def get_progress_color(percentage):
        for (lower, upper), color in AppColors.progress_colors.items():
            if lower <= percentage <= upper:
                return color
        return AppColors.accent_background_color  # Default color if outside ranges

    @staticmethod
    def get_due_date_status(due_date: Optional[datetime]) -> DueStatus:
        if not due_date:
            return DueStatus.NO_DUE_DATE
            
        now = datetime.now()
        days_until_due = (due_date - now).days
        
        if days_until_due < 0:
            return DueStatus.OVERDUE
        elif days_until_due <= 2:  # 48 hours or less
            return DueStatus.DUE_SOON
        elif days_until_due <= 7:  # Within a week
            return DueStatus.UPCOMING
        else:
            return DueStatus.FAR_FUTURE

    @staticmethod
    def get_due_date_color(due_date: Optional[datetime]):
        status = AppColors.get_due_date_status(due_date)
        return AppColors.due_date_colors.get(status, AppColors.accent_background_color)

class AppPixelSizes:
    none = "0px"
    font_xsml = "4px"
    font_sml = "8px"
    font_norm = "12px"
    font_lrg = "16px"
    font_xlrg = "20px"
    font_xxlrg = "26px"
    border_radius_norm = "10px"
    border_radius_sml = "8px"
    border_radius_xsml = "5px"
    border_radius_xxsml = "2px"
    padding_norm = "10px"
    padding_sml = "5px"
    padding_xsml = "2px"
    splitter_padding_norm = "2px"
    splitter_height = "10px"
    margin_norm = "10px"
    margin_sml = "5px"
    margin_xsml = "2px"
    scroll_bar_width = "10px"
    scroll_bar_min_height = "10px"
    slider_groove__height = "10px"
    slider_handle__height = "20px"
    slider_handle__width = "8px"
    

class AppBorders:
    none = "none"
    line_edit_norm = "1px solid #b6b6b6"
    line_edit_focus = "2px solid #64A8C8"
    line_edit_warn = "1px solid #ff0000"
    solid_border = "solid"
    text_edit_norm = "1px solid #b6b6b6"
    text_edit_focus = "2px solid #64A8C8"
    combo_box_norm = "1px solid #b6b6b6"

class AppFontFamily:
    helvetica = "Helvetica"
    
class AppFontWeight:
    norm = "normal"
    bold = "bold"
    light = "300"
    
class AppFontStyle:
    norm = "normal"
    italic = "italic"
    oblique = "oblique" 

class AppMargins:
    none = "0px"
    margin_norm = "10px"
    margin_sml = "5px"
    margin_xsml = "2px"
    margin_xxsml = "1px"
    slider_groove = "2px 0"
    slider_handle = "-6px 0"

class AppStyles:

    ### Label Styles ###
    
    @staticmethod
    def label_lgfnt_bold():
        return f"color: {AppColors.label_font_color}; font-size: {AppPixelSizes.font_lrg}; font-weight: {AppFontWeight.bold}; font-family: {AppFontFamily.helvetica}; border: none;"
    
    @staticmethod
    def label_xlgfnt_bold():
        return f"color: {AppColors.label_font_color}; font-size: {AppPixelSizes.font_xlrg}; font-weight: {AppFontWeight.bold}; font-family: {AppFontFamily.helvetica};"
    
    @staticmethod
    def label_lgfnt():
        return f"color: {AppColors.label_font_color}; font-size: {AppPixelSizes.font_lrg}; font-family: {AppFontFamily.helvetica};"
    
    @staticmethod
    def label_xlgfnt():
        return f"color: {AppColors.label_font_color}; font-size: {AppPixelSizes.font_xlrg}; font-family: {AppFontFamily.helvetica};"
    
    @staticmethod
    def label_normal():
        return f"color: {AppColors.label_font_color}; font-size: {AppPixelSizes.font_norm}; font-style: {AppFontWeight.norm}; font-family: {AppFontFamily.helvetica};"
    
    @staticmethod
    def list_label_normal():
        return f"color: {AppColors.label_font_color}; background-color: {AppColors.list}; font-size: {AppPixelSizes.font_norm}; font-style: {AppFontWeight.norm}; font-family: {AppFontFamily.helvetica};"
    
    @staticmethod
    def label_small():
        return f"color: {AppColors.label_font_color}; font-size: {AppPixelSizes.font_sml}; font-weight: {AppFontWeight.norm}; font-family: {AppFontFamily.helvetica};"
    
    @staticmethod
    def label_bold():
        return f"color: {AppColors.label_font_color}; font-size: {AppPixelSizes.font_norm}; font-weight: {AppFontWeight.bold}; font-family: {AppFontFamily.helvetica}; border: none;"
    
    @staticmethod
    def label_bold_wht():
        return f"color: {AppColors.label_font_color}; font-size: {AppPixelSizes.font_norm}; font-weight: {AppFontWeight.bold}; background-color: {AppColors.white}; font-family: {AppFontFamily.helvetica};"
    
    @staticmethod
    def label_normal_warn():
        return f"color: {AppColors.red}; font-size: {AppPixelSizes.font_norm}; font-style: {AppFontWeight.norm}; font-family: {AppFontFamily.helvetica};"
    
    ### Container Styles ###
            
    @staticmethod
    def background_color():
        return f"background-color: {AppColors.main_background_color};"
    
    @staticmethod
    def banner_color():
        return f"background-color: {AppColors.banner_color};"
    
    @staticmethod
    def card_color():
        return f"background-color: {AppColors.white};"
    
    @staticmethod
    def banner_header():
        return f"color: {AppColors.label_font_color}; font-size: {AppPixelSizes.font_xxlrg}; font-weight: {AppFontWeight.bold};"
    
    @staticmethod
    def drawer_style():
        return f"background-color: {AppColors.accent_background_color}; border-radius: {AppPixelSizes.border_radius_norm};"
    
    ### Button Styles ###
    
    @staticmethod
    def button_normal():
        return f"""
            QPushButton {{
                background-color: {AppColors.Blue};
                color: {AppColors.white};
                border-radius: 4px;
                padding: 6px 10px;
                border: none;
                font-weight: bold;
                letter-spacing: 0.5px;
            }}
            QPushButton:hover {{
                background-color: {AppColors.Purple};
            }}
            QPushButton:pressed {{
                background-color: {AppColors.Magenta};
            }}
        """
    
    @staticmethod
    def button_normal_lg_font():
        return f"""
            QPushButton {{
                background-color: {AppColors.Blue};
                color: {AppColors.white};
                border-radius: 4px;
                padding: 15px 25px;
                font-size: 16px;
                text-align: center;
                border: none;
                font-weight: bold;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{
                background-color: {AppColors.Purple};
            }}
            QPushButton:pressed {{
                background-color: {AppColors.Magenta};
            }}
        """
    
    @staticmethod
    def button_norm_pad5():
        return f"""
            QPushButton {{
                background-color: {AppColors.Blue};
                color: {AppColors.white};
                border-radius: 4px;
                padding: 8px 16px;
                border: none;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {AppColors.Purple};
            }}
        """

    @staticmethod
    def button_bold():
        return f"""
            QPushButton {{
                background: linear-gradient(135deg, {AppColors.Blue}, {AppColors.Purple});
                color: {AppColors.white};
                border-radius: 4px;
                padding: 12px 24px;
                font-weight: 800;
                font-size: 16px;
                border: none;
            }}
            QPushButton:hover {{
                background: linear-gradient(135deg, {AppColors.Purple}, {AppColors.Magenta});
            }}
        """

    @staticmethod
    def button_normal_delete():
        return f"""
            QPushButton {{ background-color: {AppColors.black}; color: {AppColors.red}; border-radius: 4px; padding: 10px 20px; font-weight: bold; font-size: 14px; border: 2px solid {AppColors.red}; }}
            QPushButton:hover {{ background-color: {AppColors.red}; color: {AppColors.white}; }}
        """
    
    @staticmethod
    def add_button_normal():
        return f"""
            QPushButton {{ background-color: {AppColors.button_background_gray}; color: {AppColors.button_gray}; text-align: center; padding-left: {AppPixelSizes.padding_sml};
                padding-right: {AppPixelSizes.padding_sml}; border-radius: {AppPixelSizes.border_radius_sml}; font-weight: {AppFontWeight.bold}; font-size: {AppPixelSizes.font_norm};  }}
            QPushButton:hover {{ background-color: {AppColors.button_hover}; }}
        """

    @staticmethod
    def button_toggle_drawer():
        return f"""
            QPushButton {{ background-color: {AppColors.button_toggle}; border-radius: {AppPixelSizes.border_radius_norm};
                color: {AppColors.white}; border-style: {AppBorders.solid_border}; font-size: {AppPixelSizes.font_xlrg}; }}
            QPushButton:hover {{background-color: {AppColors.button_toggle_hover}; }}
        """
    
    @staticmethod
    def button_transparent():
        return f"""
            QPushButton {{ border: none; background: transparent; }}
        """
    
    @staticmethod
    def button_calendar_horizontal():
        return f"""
            QToolButton {{ font-size: 16px; font-weigh: bold; }}
        """
    
    @staticmethod
    def button_calendar_vertical():
        return f"""
            QToolButton {{ color: white; background-color: #36454F; border: none; outline; border-radius: 4px; }}
        """

    ### Scroll Bar Styles ###
    
    @staticmethod
    def scroll_area():
        return f"""
            QScrollArea {{ border: {AppBorders.none}; background: transparent;}}

            QScrollBar:vertical {{ border: {AppBorders.none}; background: transparent; width: {AppPixelSizes.scroll_bar_width}; }}
            QScrollBar:horizontal {{ border: {AppBorders.none}; background: transparent; height: {AppPixelSizes.scroll_bar_width};}}

            QScrollBar::handle:vertical {{ background: {AppColors.scroll_bar_main}; min-height: {AppPixelSizes.scroll_bar_min_height}; border-radius: {AppPixelSizes.border_radius_xsml}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ border: {AppBorders.none}; background: {AppColors.none}; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: {AppColors.none}; }}

            QScrollBar::handle:horizontal {{ background: transparent; min-width: {AppPixelSizes.scroll_bar_min_height}; border-radius: {AppPixelSizes.border_radius_xxsml}; }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ border: {AppBorders.none}; background: {AppColors.none}; }}
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: {AppColors.none}; }}
        """

        
    ### List Style ###
    @staticmethod
    def list_widget():
        return f"background-color: {AppColors.list}; border-radius: {AppPixelSizes.border_radius_sml}; "
    
    @staticmethod
    def list_hover_style():
        return f"""
        QListWidget {{ border: {AppBorders.none}; outline: {AppBorders.none}; color: {AppColors.list}; }}
        QListWidget::item:hover {{background-color: {AppColors.list}; border-radius: {AppPixelSizes.border_radius_sml}; }}
        """
    
    @staticmethod
    def list_select_style():
        return f"background-color: {AppColors.list};" f"border-radius: {AppPixelSizes.border_radius_sml};"
    
    @staticmethod
    def list_style():
        return f"""
            QListWidget {{ border: {AppBorders.none}; outline: {AppBorders.none}; background-color: {AppColors.main_background_color}; color: {AppColors.list}; border-radius: {AppPixelSizes.border_radius_sml}; margin-right: 10px; margin-left: 10px;  }}
            QListWidget::item {{ border: {AppBorders.none}; outline: {AppBorders.none}; color: {AppColors.list}; border-radius: {AppPixelSizes.border_radius_sml}; }}
            QListWidget::item:selected {{ border: 2px solid {AppColors.list_selected}; background-color: {AppColors.list}; border-radius: {AppPixelSizes.border_radius_norm};  margin-right: 10px; margin-left: 10px;  margin-top: 5px; margin-bottom: 5px; }}
            QListWidget::item:hover {{ background-color: {AppColors.list_selected}; color: {AppColors.list_selected}; border-radius: {AppPixelSizes.border_radius_norm}; margin-right: 10px; margin-left: 10px; margin-top: 5px; margin-bottom: 5px;  }}
            QScrollArea {AppStyles.scroll_area()}
        """
    
    @staticmethod
    def list_style_step_running():
        return f"""
            QListWidget {{ border: {AppBorders.none}; outline: {AppBorders.none}; background-color: {AppColors.main_background_color}; color: {AppColors.list}; border-radius: {AppPixelSizes.border_radius_sml}; margin-right: 10px; margin-left: 10px;  }}
            QListWidget::item {{ border: {AppBorders.none}; outline: {AppBorders.none}; color: {AppColors.list}; border-radius: {AppPixelSizes.border_radius_sml}; }}
            QListWidget::item:selected {{ border: 2px solid {AppColors.list_selected}; background-color: {AppColors.button_toggle}; border-radius: {AppPixelSizes.border_radius_norm};  margin-right: 10px; margin-left: 10px;  margin-top: 5px; margin-bottom: 5px; }}
            QScrollArea {{ border: {AppBorders.none}; }}

            QScrollBar:vertical {{ border: {AppBorders.none}; background: {AppColors.accent_background_color}; width: {AppPixelSizes.scroll_bar_width}; }}
            QScrollBar:horizontal {{ border: {AppBorders.none}; background: {AppColors.accent_background_color}; }}

            QScrollBar::handle:vertical {{ background: {AppColors.scroll_bar_main}; min-height: {AppPixelSizes.scroll_bar_min_height}; border-radius: {AppPixelSizes.border_radius_xsml}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ border: {AppBorders.none}; background: {AppColors.none}; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: {AppColors.none}; }}

            QScrollBar::handle:horizontal {{ background: {AppColors.scroll_bar_main}; min-width: {AppPixelSizes.scroll_bar_min_height}; border-radius: {AppPixelSizes.border_radius_xsml}; }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ border: {AppBorders.none}; background: {AppColors.none}; }}
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: {AppColors.none}; }}
        """
    @staticmethod
    def list_style_step_waiting():
        return f"""
            QListWidget {{ border: {AppBorders.none}; outline: {AppBorders.none}; background-color: {AppColors.main_background_color}; color: {AppColors.list}; border-radius: {AppPixelSizes.border_radius_sml}; margin-right: 10px; margin-left: 10px;  }}
            QListWidget::item {{ border: {AppBorders.none}; outline: {AppBorders.none}; color: {AppColors.list}; border-radius: {AppPixelSizes.border_radius_sml}; }}
            QScrollArea {{ border: {AppBorders.none}; }}
            
            QScrollBar:vertical {{ border: {AppBorders.none}; background: {AppColors.accent_background_color}; width: {AppPixelSizes.scroll_bar_width}; }}
            QScrollBar:horizontal {{ border: {AppBorders.none}; background: {AppColors.accent_background_color}; }}

            QScrollBar::handle:vertical {{ background: {AppColors.scroll_bar_main}; min-height: {AppPixelSizes.scroll_bar_min_height}; border-radius: {AppPixelSizes.border_radius_xsml}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ border: {AppBorders.none}; background: {AppColors.none}; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: {AppColors.none}; }}

            QScrollBar::handle:horizontal {{ background: {AppColors.scroll_bar_main}; min-width: {AppPixelSizes.scroll_bar_min_height}; border-radius: {AppPixelSizes.border_radius_xsml}; }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ border: {AppBorders.none}; background: {AppColors.none}; }}
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: {AppColors.none}; }}
        """
    
    @staticmethod
    def list_style_graph():
        return f"""
            QListWidget {{ border: {AppBorders.none}; outline: {AppBorders.none}; background-color: {AppColors.main_background_color}; color: {AppColors.accent_background_color_dark}; border-radius: {AppPixelSizes.border_radius_sml}; }}
            QListWidget::item {{ border: {AppBorders.none}; outline: {AppBorders.none}; color: {AppColors.black}; border-radius: {AppPixelSizes.border_radius_sml}; }}
            QScrollArea {{ border: {AppBorders.none}; }}

            QScrollBar:vertical {{ border: {AppBorders.none}; background: {AppColors.accent_background_color_dark}; width: {AppPixelSizes.scroll_bar_width}; }}
            QScrollBar:horizontal {{ border: {AppBorders.none}; background: {AppColors.accent_background_color_dark}; height: {AppPixelSizes.scroll_bar_width};}}

            QScrollBar::handle:vertical {{ background: {AppColors.scroll_bar_main}; min-height: {AppPixelSizes.scroll_bar_min_height}; border-radius: {AppPixelSizes.border_radius_xsml}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ border: {AppBorders.none}; background: {AppColors.none}; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: {AppColors.none}; }}

            QScrollBar::handle:horizontal {{ background: {AppColors.scroll_bar_main}; min-width: {AppPixelSizes.scroll_bar_min_height}; border-radius: {AppPixelSizes.border_radius_xsml}; }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ border: {AppBorders.none}; background: {AppColors.none}; }}
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: {AppColors.none}; }}
        """
    
    @staticmethod
    def list_style_graph_item():
        return f"""
            QListWidget {{ border: {AppBorders.none}; outline: {AppBorders.none}; background-color: {AppColors.accent_background_color_dark}; color: {AppColors.accent_background_color_dark}; border-radius: {AppPixelSizes.border_radius_sml}; }}
            QListWidget::item {{ border: {AppBorders.none}; outline: {AppBorders.none}; color: {AppColors.black}; border-radius: {AppPixelSizes.border_radius_sml};}}
            QScrollArea {{ border: {AppBorders.none}; }}

            QScrollBar:vertical {{ border: {AppBorders.none}; background: {AppColors.accent_background_color_dark}; width: {AppPixelSizes.scroll_bar_width}; }}
            QScrollBar:horizontal {{ border: {AppBorders.none}; background: {AppColors.accent_background_color_dark}; height: {AppPixelSizes.scroll_bar_width};}}

            QScrollBar::handle:vertical {{ background: {AppColors.scroll_bar_main}; min-height: {AppPixelSizes.scroll_bar_min_height}; border-radius: {AppPixelSizes.border_radius_xsml}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ border: {AppBorders.none}; background: {AppColors.none}; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: {AppColors.none}; }}

            QScrollBar::handle:horizontal {{ background: {AppColors.scroll_bar_main}; min-width: {AppPixelSizes.scroll_bar_min_height}; border-radius: {AppPixelSizes.border_radius_xsml}; }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ border: {AppBorders.none}; background: {AppColors.none}; }}
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: {AppColors.none}; }}
        """
    
    @staticmethod
    def list_style_inner_list_item():
        return f"""
            QListWidget {{ border: {AppBorders.none}; outline: {AppBorders.none}; background-color: {AppColors.accent_background_color_dark}; color: {AppColors.accent_background_color_dark};}}
            QListWidget::item {{ outline: {AppBorders.none}; color: {AppColors.black};}}
            QScrollArea {{ border: {AppBorders.none}; }}

            QScrollBar:vertical {{ border: {AppBorders.none}; background: {AppColors.accent_background_color_dark}; width: {AppPixelSizes.scroll_bar_width}; }}
            QScrollBar:horizontal {{ border: {AppBorders.none}; background: {AppColors.accent_background_color_dark}; height: {AppPixelSizes.scroll_bar_width};}}

            QScrollBar::handle:vertical {{ background: {AppColors.scroll_bar_main}; min-height: {AppPixelSizes.scroll_bar_min_height}; border-radius: {AppPixelSizes.border_radius_xsml}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ border: {AppBorders.none}; background: {AppColors.none}; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: {AppColors.none}; }}

            QScrollBar::handle:horizontal {{ background: {AppColors.scroll_bar_main}; min-width: {AppPixelSizes.scroll_bar_min_height}; border-radius: {AppPixelSizes.border_radius_xsml}; }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ border: {AppBorders.none}; background: {AppColors.none}; }}
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: {AppColors.none}; }}
        """
    
    @staticmethod
    def log_list():
        return f"""
            QListWidget {{ background-color: transparent; border: 0px solid #ccc; border-radius: 8px; padding: 5px; }}
            QListWidget::item {{ background-color: transparent; border: none; padding: 5px; border-radius: 5px; }}
        """

    ### Slider Styles ###
    
    @staticmethod
    def slider_norm():
        return f"""
            QSlider::groove:horizontal {{ background: {AppColors.slider_groove_background}; border: {AppBorders.none}; border-radius: {AppPixelSizes.border_radius_xsml}; 
                    margin:{AppMargins.slider_groove}; height: {AppPixelSizes.slider_groove__height}; }}
            QSlider::handle:horizontal {{ background: {AppColors.slider_handle_background}; border: {AppBorders.none}; border-radius: {AppPixelSizes.border_radius_xsml};
                    margin: {AppMargins.slider_handle}; height: {AppPixelSizes.slider_handle__height}; width: {AppPixelSizes.slider_handle__width}; }}
        """
        
    ### Line Edit Styles ###
    
    @staticmethod
    def line_edit_norm():
        return f"""
            QLineEdit {{border: {AppBorders.line_edit_norm}; border-radius: {AppPixelSizes.border_radius_xsml}; padding: {AppPixelSizes.border_radius_xsml}; 
                background-color: {AppColors.black}; color: {AppColors.white}; font-size: {AppPixelSizes.font_norm}; font-style: {AppFontStyle.norm}; }}
            QLineEdit:focus {{ border: {AppBorders.line_edit_focus}; }}
        """
    
    @staticmethod
    def line_edit_small():
        return f"""
            QLineEdit {{border: {AppBorders.line_edit_norm}; border-radius: {AppPixelSizes.border_radius_xsml}; padding: {AppPixelSizes.border_radius_xxsml};
                background-color: {AppColors.white}; color: {AppColors.label_font_color}; font-size: {AppPixelSizes.font_norm}; font-style: {AppFontStyle.norm}; }}
            QLineEdit:focus {{ border: {AppBorders.line_edit_focus}; }}
        """
    
    @staticmethod
    def line_edit_warn():
        return f"""
            QLineEdit {{border: {AppBorders.line_edit_warn}; border-radius: {AppPixelSizes.border_radius_xsml}; padding: {AppPixelSizes.border_radius_xsml}; 
                background-color: {AppColors.white}; color: {AppColors.label_font_color}; font-size: {AppPixelSizes.font_norm}; font-style: {AppFontStyle.norm}; }}
            QLineEdit:focus {{ border: {AppBorders.line_edit_warn}; }}
        """
    
    @staticmethod
    def log_line_edit():
        return f"""
            QLineEdit {{ border: 1px solid #ccc; border-radius: 8px; padding: 5px; }}
        """
    
    ### Text Edit Styles ##

    @staticmethod
    def text_edit_norm():
        return f"""
            QTextEdit {{border: {AppBorders.text_edit_norm}; border-radius: {AppPixelSizes.border_radius_xsml}; padding: {AppPixelSizes.border_radius_xsml}; 
                background-color: {AppColors.black}; color: {AppColors.white}; font-size: {AppPixelSizes.font_norm}; font-style: {AppFontStyle.norm}; }}
            QTextEdit:focus {{ border: {AppBorders.text_edit_focus}; }}
        """
    
    @staticmethod
    def text_edit_small():
        return f"""
            QTextEdit {{border: {AppBorders.text_edit_norm}; border-radius: {AppPixelSizes.border_radius_xsml}; padding: {AppPixelSizes.border_radius_xxsml};
                background-color: {AppColors.white}; color: {AppColors.label_font_color}; font-size: {AppPixelSizes.font_norm}; font-style: {AppFontStyle.norm}; }}
            QTextEdit:focus {{ border: {AppBorders.text_edit_focus}; }}
        """
    
    @staticmethod
    def combo_box_norm():
        return f"""
            QComboBox {{
                border: {AppBorders.combo_box_norm}; 
                border-radius: {AppPixelSizes.border_radius_xsml}; 
                padding: {AppPixelSizes.border_radius_xsml};
                background-color: transparent; 
                color: {AppColors.label_font_color}; 
                font-size: {AppPixelSizes.font_norm}; 
                font-style: {AppFontStyle.norm}; 
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding; 
                subcontrol-position: top right; 
                width: 10px; 
                border-left-width: 1px; 
                border-left-style: solid; 
                border-top-right-radius: 1px; 
                border-bottom-right-radius: 1px; 
            }}
            QComboBox::down-arrow {{
                image: url(down_arrow.png);  /* If you have an image */
                width: 8px;
                height: 8px;
            }}
            /* Or use a Unicode character if you don't want to use an image */
            QComboBox::down-arrow {{
                color: {AppColors.label_font_color};
                width: 8px;
                height: 8px;
            }}
    """
    
    @staticmethod
    def combo_box_norm_warn():
        return f"""
            QComboBox {{border: {AppBorders.line_edit_warn}; border-radius: {AppPixelSizes.border_radius_xsml}; padding: {AppPixelSizes.border_radius_xsml}; 
                background-color: {AppColors.white}; color: {AppColors.label_font_color}; font-size: {AppPixelSizes.font_norm}; font-style: {AppFontStyle.norm}; }}
            QComboBox::drop-down {{subcontrol-origin: padding; subcontrol-position: top right; width: 10px; border-left-width: 1px; border-left-style: solid; border-top-right-radius: 1px; border-bottom-right-radius: 1px; }}
        """
    
    @staticmethod
    def combo_box_wide():
        return f"""
            QComboBox {{border: {AppBorders.combo_box_norm}; border-radius: {AppPixelSizes.border_radius_xsml}; padding: {AppPixelSizes.border_radius_xsml}; 
                background-color: {AppColors.white}; color: {AppColors.label_font_color}; font-size: {AppPixelSizes.font_norm}; font-style: {AppFontStyle.norm}; }}
            QComboBox::drop-down {{subcontrol-origin: padding; subcontrol-position: top right; width: 30px; border-left-width: 1px; border-left-style: solid; border-top-right-radius: 1px; border-bottom-right-radius: 1px; }}
        """
    
    @staticmethod
    def combo_box_x_wide():
        return f"""
            QComboBox {{border: {AppBorders.combo_box_norm}; border-radius: {AppPixelSizes.border_radius_xsml}; padding: {AppPixelSizes.border_radius_xsml}; 
                background-color: {AppColors.white}; color: {AppColors.label_font_color}; font-size: {AppPixelSizes.font_norm}; font-style: {AppFontStyle.norm}; }}
            QComboBox::drop-down {{subcontrol-origin: padding; subcontrol-position: top right; width: 80px; border-left-width: 1px; border-left-style: solid; border-top-right-radius: 1px; border-bottom-right-radius: 1px; }}
        """
    
    ### Splitter Styles ##
    @staticmethod
    def splitter_hor_norm():
        return f"""

            QSplitter::handle:horizontal {{width: {AppPixelSizes.splitter_height}; }}
        """
    
    @staticmethod
    def splitter_ver_norm():
        return f"""
            QSplitter::handle:vertical {{height: {AppPixelSizes.splitter_height}; }}
        """
    
    ### Widget Styles ###

    @staticmethod
    def widget():
        return f"""
            QWidget {{background-color: {AppColors.accent_background_color_dark}; border-radius: {AppPixelSizes.border_radius_sml}; }}
        """
    
    @staticmethod
    def border_widget():
        return """
            QWidget { border: 1px solid #ccc; border-radius: 4px; }
        """
    
    ### Test Widget Border ###

    @staticmethod
    def widget_border(color):
        return f"border: 1px solid {color}; "
    

    ### Calendar Styles
    @staticmethod
    def calendar_norm():
        return f"""
            /* Main calendar widget styling */
            QCalendarWidget {{
                background-color: #000000;  /* Pure Black - main background */
                border: 1px solid #e0e0e0;  /* Light Gray - border */
                border-radius: 8px;         /* Rounded corners */
            }}
            QCalendarWidget QHeaderView::section {{
                background-color: #36454F;  /* Charcoal Gray - header background */
                color: #f0f0f0;            /* Off White - header text */
                padding: 4px;
                border: 1px solid #e0e0e0;  /* Light Gray - header border */
                border-radius: 4px;
            }}
            QCalendarWidget QAbstractItemView {{
                background-color: #f0f0f0;  /* Off White - cell background */
                color: #000000;            /* Black - cell text */
                border: 1px solid #e0e0e0;  /* Light Gray - cell border */
                border-radius: 4px;
            }}
            QCalendarWidget QAbstractItemView:selected {{
                background-color: #2980b9;  /* Blue - selected day background */
                color: #ffffff;            /* White - selected day text */
                border-radius: 4px;
            }}
            QCalendarWidget QAbstractItemView:disabled {{
                color: #808080;            /* Gray - other month's days */
            }}
            QCalendarWidget QToolButton {{
                color: #000000;            /* Black - button text */
                background-color: transparent;
                border: none;
                padding: 4px;
                border-radius: 4px;
            }}
            QCalendarWidget QToolButton::menu-indicator {{
                image: none;
            }}
            QCalendarWidget QWidget {{
                alternate-background-color: #f5f5f5;  /* Very Light Gray - alternate rows */
            }}
            QCalendarWidget QToolButton {{
                color: #000000;            /* Black - button text */
                background-color: transparent;
                border: none;
                padding: 4px;
                qproperty-autoRaise: true;
            }}
            QCalendarWidget QToolButton:hover {{
                background-color: #e8f0fe;  /* Light Blue - button hover */
            }}
        """
    
    ### Tab Section Styles
    @staticmethod
    def tab_norm():
        return f"""
            QTabWidget::pane {{
                border-top: 2px solid #C2C7CB; 
                position: absolute;
                top: -2px; 
            }}
            QTabWidget::tab-bar {{
                left: 5px; 
            }}
            QTabBar::tab {{
                background: {AppColors.main_background_color}; 
                border: 1px solid #C4C4C3;
                border-bottom-color: #C2C7CB; 
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                min-width: 8ex;
                padding: 2px;
            }}
            QTabBar::tab:selected, QTabBar::tab:hover {{
                background: {AppColors.main_background_color};  
                border-color: #9B9B9B; 
                border-bottom-color: {AppColors.main_background_color};  
            }}
            QTabBar::tab:selected {{
                border-color: #9B9B9B;
                border-bottom-color: {AppColors.main_background_color}; 
            }}
            QTabBar::tab:!selected {{
                margin-top: 2px; 
            }}
        """
    
    ### Shadow Styles ###

    @staticmethod
    def shadow_rad_2():

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(2)
        shadow.setXOffset(1)
        shadow.setYOffset(1)
        return shadow
    
    @staticmethod
    def shadow_rad_3():
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(3)
        shadow.setXOffset(1)
        shadow.setYOffset(1)
        return shadow
    
    @staticmethod
    def shadow_rad_10():
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setXOffset(1)
        shadow.setYOffset(1)
        return shadow
    
    @staticmethod
    def shadow_rad_100_alpha60():
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(100)
        shadow.setXOffset(1)
        shadow.setYOffset(1)
        shadow.setColor(QColor(0, 0, 0, 60))
        return shadow
    

    @staticmethod
    def divider():
        return f"""
            QFrame {{
                background-color: {AppColors.accent_background_color_dark};
                border: none;
            }}
        """

    @staticmethod
    def section_container():
        return f"""
            QWidget {{
                background-color: {AppColors.accent_background_color};
                border-radius: 8px;
                margin: 8px;
            }}
        """
    
    @staticmethod
    def task_card():
        return f"""
            QWidget#card_container {{  
                background-color: {AppColors.accent_background_color};
                border-radius: 8px;
                padding: 10px;
                border: 1px solid {AppColors.accent_background_color_dark};
            }}
            QWidget#card_container:hover {{
                background-color: {AppColors.accent_background_color_dark};
                border: 1px solid {AppColors.Blue};
                border-radius: 8px; /* Ensure border radius remains on hover */
            }}
            QLabel {{
                border: none; 
                border-radius: 0px; /* Remove border radius from labels */
            }}
            QLabel:hover {{
                border: none;  
                border-radius: 0px; /* Remove border radius from labels on hover */
            }}
        """
    

    @staticmethod
    def expanded_task_card():
        return f"""
            QWidget#card_container {{
                background-color: {AppColors.main_background_color};
                border-radius: 8px;
                padding: 15px;
                border: 1px solid {AppColors.accent_background_color_dark};
            }}
        """
class AnimatedDrawerButton(QPushButton):
    def __init__(self, text=None, parent=None):
        super().__init__(text, parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        text_label = QLabel("\u2630", self)
        text_label.setStyleSheet(AppStyles.button_toggle_drawer())
        layout.addWidget(text_label)
        #self.setText = "\u2630"
        self.setFixedSize(40, 40)
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(2)
        self.shadow.setXOffset(1)
        self.shadow.setYOffset(1)
        self.setGraphicsEffect(self.shadow)
        self.installEventFilter(self)
        
    def eventFilter(self, obj, event):
        if obj == self:
            if event.type() == QEvent.MouseButtonPress:

                self.shadow.setEnabled(False)
            elif event.type() == QEvent.MouseButtonRelease:
                self.shadow.setEnabled(True)

        return super().eventFilter(obj, event)

class AnimatedButton(QPushButton):
    def __init__(self, text, parent=None, x=None, y=None, set_max_width:bool=None, 
                 is_fixed_size=False, blur=None, offsetX=None, offsetY=None):
        super().__init__(text, parent)
        self.setContentsMargins(0, 0, 0, 0)
        
        # Handle size settings
        if x and y:
            if is_fixed_size:
                self.setFixedSize(x, y)
            else:
                self.setMinimumSize(x, y)
            if set_max_width:
                self.setMaximumWidth(x)
        
        # Setup shadow effect
        if blur is not None:
            self.original_blur = blur
            self.shadow = QGraphicsDropShadowEffect(self)
            self.shadow.setBlurRadius(self.original_blur)
            if offsetX is not None:
                self.shadow.setXOffset(offsetX)
            if offsetY is not None:
                self.shadow.setYOffset(offsetY)
            self.setGraphicsEffect(self.shadow)
        
        self.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj == self:
            if event.type() == QEvent.MouseButtonPress:
                if hasattr(self, 'shadow'):
                    self.shadow.setEnabled(False)
            elif event.type() == QEvent.MouseButtonRelease:
                if hasattr(self, 'shadow'):
                    self.shadow.setEnabled(True)
        return super().eventFilter(obj, event)
    

class AnimatedButtonMultiText(QPushButton):
    clickedButton = pyqtSignal(QPushButton)

    def __init__(self, name_text, rssi_text,  parent=None, x=None, y=None, blur=None, offsetX=None, offsetY=None):
        super().__init__(parent)
        self.enlarge = False
        self.x = x
        self.y = y
        self.originalSize = QSize(self.x, self.y)
        self.enlargedSize = QSize(self.x+20, self.y+10)
        self.clicked.connect(self.onClick)
        self.initUI(name_text, rssi_text, x, y, blur, offsetX, offsetY)

    def initUI(self, name_text, rssi_text, x, y, blur, offsetX, offsetY):
        self.x = x
        self.y = y
    
        container_layout = QHBoxLayout(self)

        name_label = QLabel(name_text)
        name_label.setStyleSheet(AppStyles.label_normal())

        rssi_label = QLabel(f"RSSI:  {str(rssi_text)}")
        rssi_label.setStyleSheet(AppStyles.label_normal())

        container_layout.addWidget(name_label)
        container_layout.addWidget(rssi_label)

        if x and y:
            self.setFixedSize(x, y)
            self.x_larg = self.x + 20
            self.y_larg = self.y + 10

        self.original_blur = blur

        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(self.original_blur)
        if offsetX: 
            self.shadow.setXOffset(offsetX)
        if offsetY:
            self.shadow.setYOffset(offsetY)
        self.setGraphicsEffect(self.shadow)

    def onClick(self):
        self.clickedButton.emit(self)

class ButtonContainer(QWidget):
    def __init__(self, name_text, rssi_text,  parent=None, x=None, y=None, blur=None, offsetX=None, offsetY=None):
        super().__init()
        self.name_text = name_text
        self.rssi_text = rssi_text
        self.x = x
        self.y = y
        self.blur = blur
        self.offsetX = offsetX
        self.offsetY = offsetY

        self.initUI()
        self.currentlyEnlargedButton = None

    def initUI(self):
        layout = QVBoxLayout(self)

        button = AnimatedButtonMultiText(name_text=self.name_text, rssi_text=self.rssi_text, x=self.x, y=self.y, blur=self.blur, offsetX=self.offsetX, offsetY=self.offsetY)
        button.clickedButton.connect(self.handleButtonClick)
        layout.addWidget(button)

    def handleButtonClick(self, clickedButton):
        if self.currentlyEnlargedButton and self.currentlyEnlargedButton != clickedButton:
            self.currentlyEnlargedButton.setFixedSize(self.currentlyEnlargedButton.originaSize)

        clickedButton.setFixedSize(clickedButton.enlargedSize)
        self.currentlyEnlargedButton = clickedButton

        self.installEventFilter(self)
        
    def eventFilter(self, obj, event):
        if obj == self:
            if event.type() == QEvent.MouseButtonPress:
                self.shadow.setEnabled(False)
            elif event.type() == QEvent.MouseButtonRelease:
                self.shadow.setEnabled(True)

        return super().eventFilter(obj, event)
    
    def enterEvent(self, event):
        if self.enlarge:
            self.setFixedSize(self.x_larg, self.y_larg)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.enlarge == False:
            self.setFixedSize(self.x, self.y)
        super().leaveEvent(event)

