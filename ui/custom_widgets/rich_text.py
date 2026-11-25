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
# File: rich_text.py
# Description: Task descriptions with formatting. Descriptions are stored as
#              Markdown, so pasted lists, numbering, and paragraphs survive, and
#              the stored text still reads well as plain text.
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

import re

from PyQt5.QtGui import QFont, QTextCharFormat, QTextDocument, QTextListFormat
from PyQt5.QtWidgets import QHBoxLayout, QPushButton, QTextBrowser, QTextEdit, QWidget

from resources.styles import AppColors

MARKDOWN = "markdown"
PLAIN = "plain"


def load_description(editor, task):
    """Put a task's description into a QTextEdit/QTextBrowser, keeping its formatting"""
    text = task.description or ""
    if getattr(task, "description_format", PLAIN) == MARKDOWN:
        editor.setMarkdown(text)
    else:
        # Older descriptions are plain text: keep every line break as typed
        editor.setPlainText(text)


def save_description(editor, task):
    """Store the editor's content on the task as Markdown"""
    if editor.document().isEmpty():
        task.description = ""
    else:
        task.description = _escape_numbered_paragraphs(editor.document(), editor.toMarkdown()).strip()
    task.description_format = MARKDOWN


_NUMBERED = re.compile(r"^(\d+)([.)])(\s)")


def _escape_numbered_paragraphs(document, markdown):
    """Keep "1. Something" typed as a plain paragraph from turning into a list on reload.

    Qt doesn't escape these when writing Markdown, so a heading like "2. Setup" would
    come back as list item 1. Real list items are left alone.
    """
    block = document.begin()
    while block.isValid():
        if block.textList() is None:
            match = _NUMBERED.match(block.text())
            if match:
                rest = block.text()[match.end():][:30]
                pattern = r"(?m)^" + re.escape(match.group(1)) + re.escape(match.group(2)) + r"(\s+" + re.escape(rest.split(" ")[0]) + ")"
                escaped = match.group(1) + "\\" + match.group(2)  # e.g. 2\. so Markdown keeps it as text
                markdown = re.sub(pattern, lambda m, escaped=escaped: escaped + m.group(1), markdown, count=1)
        block = block.next()
    return markdown


def description_plain_text(task):
    """The description as plain text, for places that can't show formatting"""
    if getattr(task, "description_format", PLAIN) != MARKDOWN:
        return task.description or ""
    document = QTextDocument()
    document.setMarkdown(task.description or "")
    return document.toPlainText()


def text_area_style(read_only=False):
    border = AppColors.surface_raised
    return f"""
        QTextEdit, QTextBrowser {{
            background-color: {AppColors.surface};
            border: 2px solid {border};
            border-radius: 6px;
            padding: 8px;
            color: {AppColors.text_primary};
            font-size: 12px;
            selection-background-color: {AppColors.accent};
        }}
        {'' if read_only else f'QTextEdit:focus {{ border: 2px solid {AppColors.accent}; background-color: {AppColors.surface_raised}; }}'}
        QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px; }}
        QScrollBar::handle:vertical {{ background: {AppColors.surface_raised}; border-radius: 3px; min-height: 24px; }}
        QScrollBar::handle:vertical:hover {{ background: {AppColors.accent}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
    """


class DescriptionView(QTextBrowser):
    """Read-only, scrollable view of a formatted description"""

    def __init__(self, task, parent=None):
        super().__init__(parent)
        self.setOpenExternalLinks(True)
        self.setStyleSheet(text_area_style(read_only=True))
        load_description(self, task)


class FormattingToolbar(QWidget):
    """Bold, italic, and list buttons for a description editor (only what Markdown can store)"""

    def __init__(self, editor: QTextEdit, parent=None):
        super().__init__(parent)
        self.editor = editor
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        for text, tip, handler, bold, italic in (
                ("B", "Bold (Ctrl+B)", self.toggleBold, True, False),
                ("I", "Italic (Ctrl+I)", self.toggleItalic, False, True),
                ("• List", "Bulleted list", lambda: self.makeList(QTextListFormat.ListDisc), False, False),
                ("1. List", "Numbered list", lambda: self.makeList(QTextListFormat.ListDecimal), False, False)):
            button = QPushButton(text)
            button.setToolTip(tip)
            font = QFont()
            font.setBold(bold)
            font.setItalic(italic)
            button.setFont(font)
            button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {AppColors.surface_raised}; color: {AppColors.text_primary};
                    border: none; border-radius: 4px; padding: 3px 8px; font-size: 11px;
                }}
                QPushButton:hover {{ background-color: {AppColors.accent}; }}
            """)
            button.clicked.connect(handler)
            layout.addWidget(button)
        layout.addStretch(1)

    def toggleBold(self):
        fmt = QTextCharFormat()
        weight = self.editor.currentCharFormat().fontWeight()
        fmt.setFontWeight(QFont.Normal if weight > QFont.Normal else QFont.Bold)
        self.editor.mergeCurrentCharFormat(fmt)
        self.editor.setFocus()

    def toggleItalic(self):
        fmt = QTextCharFormat()
        fmt.setFontItalic(not self.editor.currentCharFormat().fontItalic())
        self.editor.mergeCurrentCharFormat(fmt)
        self.editor.setFocus()

    def makeList(self, style):
        cursor = self.editor.textCursor()
        current = cursor.currentList()
        cursor.beginEditBlock()
        if current is not None and current.format().style() == style:
            # Pressing the same list button again turns the list off
            block_format = cursor.blockFormat()
            current.remove(cursor.block())
            block_format.setIndent(0)
            cursor.setBlockFormat(block_format)
        else:
            list_format = QTextListFormat()
            list_format.setStyle(style)
            cursor.createList(list_format)
        cursor.endEditBlock()
        self.editor.setFocus()
