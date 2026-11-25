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
# File: panel_styles.py
# Description: Button, menu, list, and search-box styles shared by the side
#              panels (mind maps, notes).
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

from resources.styles import AppColors

PANEL_BUTTON_STYLE = f"""
    QPushButton {{ background-color: {AppColors.surface_raised}; color: {AppColors.text_primary};
                   border: 1px solid {AppColors.surface_hover_alt}; border-radius: 6px;
                   padding: 6px 10px; font-size: 12px; }}
    QPushButton:hover {{ border-color: {AppColors.accent}; }}
    QPushButton:checked {{ background-color: {AppColors.accent}; border-color: {AppColors.accent}; color: white;
                           font-weight: bold; }}
    QPushButton:disabled {{ background-color: transparent; color: {AppColors.text_faint};
                            border-color: {AppColors.surface_raised}; }}
"""
PRIMARY_BUTTON_STYLE = f"""
    QPushButton {{ background-color: {AppColors.accent}; border-color: {AppColors.accent}; color: white; font-weight: bold; }}
    QPushButton:hover {{ background-color: {AppColors.accent_dark}; }}
"""
MENU_STYLE = f"""
    QMenu {{ background-color: {AppColors.surface_raised}; color: {AppColors.text_primary};
             border: 1px solid {AppColors.surface_hover_alt}; padding: 4px; }}
    QMenu::item {{ padding: 6px 22px 6px 10px; border-radius: 3px; }}
    QMenu::item:selected {{ background-color: {AppColors.accent}; }}
    QMenu::separator {{ height: 1px; background: {AppColors.surface_hover_alt}; margin: 4px 6px; }}
"""
SEARCH_BOX_STYLE = f"""
    QLineEdit {{ background-color: {AppColors.surface_raised}; color: {AppColors.text_primary};
                 border: 1px solid {AppColors.surface_hover_alt}; border-radius: 6px; padding: 6px 8px; }}
    QLineEdit:focus {{ border-color: {AppColors.accent}; }}"""
CARD_LIST_STYLE = f"""
    QListWidget {{ background: transparent; border: none; outline: none; }}
    QListWidget::item {{ background-color: {AppColors.surface_raised}; border: 1px solid {AppColors.surface_hover_alt};
                         border-radius: 8px; }}
    QListWidget::item:hover {{ border-color: {AppColors.accent}; }}
    QListWidget::item:selected {{ background-color: {AppColors.accent_background_color_dark};
                                  border: 1px solid {AppColors.accent}; }}
    QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: {AppColors.surface_raised}; border-radius: 3px; min-height: 30px; }}
    QScrollBar::handle:vertical:hover {{ background: {AppColors.accent}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}"""
EMPTY_HINT_STYLE = f"color: {AppColors.text_muted}; font-size: 12px; padding: 20px;"
def _arrow_image(color):
    """A small down arrow as a PNG (style sheets can only show arrows from image files)"""
    import os
    import tempfile
    from PyQt5.QtCore import QPointF, Qt
    from PyQt5.QtGui import QColor, QImage, QPainter, QPolygonF
    path = os.path.join(tempfile.gettempdir(), f"meridian_arrow_{color.lstrip('#')}.png")
    if not os.path.exists(path):
        image = QImage(20, 12, QImage.Format_ARGB32)
        image.fill(Qt.transparent)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(color))
        painter.drawPolygon(QPolygonF([QPointF(2, 2), QPointF(18, 2), QPointF(10, 11)]))
        painter.end()
        image.save(path)
    return path.replace("\\", "/")


ARROW_IMAGE = _arrow_image(AppColors.text_secondary)
COMBO_STYLE = f"""
    QComboBox {{ background-color: {AppColors.surface_raised}; color: {AppColors.text_primary};
                 border: 1px solid {AppColors.surface_hover_alt}; border-radius: 6px; padding: 5px 8px; font-size: 12px; }}
    QComboBox:hover, QComboBox:focus {{ border-color: {AppColors.accent}; }}
    QComboBox::drop-down {{ border: none; width: 22px; }}
    QComboBox::down-arrow {{ image: url({ARROW_IMAGE}); width: 10px; height: 6px; }}
    QComboBox QAbstractItemView {{ background-color: {AppColors.surface_raised}; color: {AppColors.text_primary};
                                   selection-background-color: {AppColors.accent};
                                   border: 1px solid {AppColors.surface_hover_alt}; outline: none; }}"""
# Text fields, lists, dates, and checkboxes in a form (dialogs)
FORM_INPUT_STYLE = COMBO_STYLE + f"""
    QWidget#formWidget, QWidget#optionalDate, QWidget#colorChoice {{ background: transparent; }}
    QLineEdit, QTextEdit, QDateEdit {{ background-color: {AppColors.surface_raised}; color: {AppColors.text_primary};
                                       border: 1px solid {AppColors.surface_hover_alt}; border-radius: 6px;
                                       padding: 6px 8px; font-size: 13px; selection-background-color: {AppColors.accent}; }}
    QLineEdit:focus, QTextEdit:focus, QDateEdit:focus {{ border-color: {AppColors.accent}; }}
    QLineEdit[invalid="true"] {{ border-color: {AppColors.danger}; }}
    QDateEdit:disabled {{ color: {AppColors.text_faint}; background-color: transparent; }}
    QDateEdit::drop-down {{ border: none; width: 22px; }}
    QDateEdit::down-arrow {{ image: url({ARROW_IMAGE}); width: 10px; height: 6px; }}
    QCheckBox {{ color: {AppColors.text_secondary}; font-size: 12px; background: transparent; spacing: 6px; }}
    QCheckBox::indicator {{ width: 14px; height: 14px; border: 1px solid {AppColors.surface_hover_alt};
                            border-radius: 3px; background-color: {AppColors.surface_raised}; }}
    QCheckBox::indicator:checked {{ background-color: {AppColors.accent}; border-color: {AppColors.accent}; }}
    QLabel {{ color: {AppColors.text_secondary}; font-size: 12px; background: transparent; }}"""
# A text-only button, like a link ("Clear filters", "← Projects")
LINK_BUTTON_STYLE = f"""
    QPushButton {{ background: transparent; color: {AppColors.accent}; border: none; padding: 4px 2px; font-size: 12px; }}
    QPushButton:hover {{ color: {AppColors.accent_light}; text-decoration: underline; }}"""
SECTION_HEADER_STYLE = (f"color: {AppColors.text_muted}; font-size: 11px; font-weight: bold; "
                        f"letter-spacing: 1px; background: transparent;")
