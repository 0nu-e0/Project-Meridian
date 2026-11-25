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
# File: guide.py
# Description: A short guide to the app (F1, or ? in the banner): what each
#              screen is for, the handy tricks, and every keyboard shortcut.
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

from PyQt5.QtWidgets import QTextBrowser

from resources.styles import AppColors
from ui.custom_widgets.dialogs import PRIMARY, StyledDialog

SECTIONS = [
    ("Dashboard", [
        "Your tasks, grouped by category. Hover a card for its details; click it to open.",
        "Right-click a card to <b>archive</b> it without completing it (completed tasks archive themselves).",
        "Collapse a group with its ▼ arrow; a collapsed group shows ▶ and how many tasks it holds.",
        "In an open task, drag the bars between sections to resize them; the layout is remembered.",
    ]),
    ("Planning", [
        "Drag tasks or projects from the left onto a day. Drag between days to move them, "
        "or back to the left to unschedule.",
        "Daily, Weekly, and Monthly views are at the top.",
    ]),
    ("Projects", [
        "Projects hold phases, and phases hold tasks. Open a project for its phases, Gantt chart, and mind map.",
        "The Gantt chart: drag bars to change dates, drag their ends to change length. "
        "Right-click a row (or select a bar and press Delete) to remove it.",
    ]),
    ("Mind maps", [
        "Drag shapes from the <b>Design</b> tab onto the canvas. Double-click a shape to type in it.",
        "Drag from a dot on a shape's edge to another shape to connect them. "
        "Drag a dot that has lines to move them; Ctrl+drag starts another line.",
        "Drag anywhere on a line to bend it; click a bend's diamond and press Delete to remove it.",
        "Select shapes or lines and pick a colour. Right-click for more. Export as PNG or PDF.",
        "Double-click a line to label it. Group shapes (Ctrl+G) to move them as one, or put them "
        "in a frame (right-click › Frame these) to box them under a title.",
        "Your saved mind maps are in the <b>Mind maps</b> tab.",
    ]),
    ("Anywhere", [
        "Search everything (tasks, projects, notes, mind maps) from the box in the banner.",
        "Made a mistake? Ctrl+Z undoes it, and the notice at the bottom has an Undo button too.",
        "Settings (the gear in the menu): colours, categories, interface size, and more.",
    ]),
]

SHORTCUTS = [
    ("Ctrl+K or Ctrl+F", "Search everything"),
    ("Ctrl+N", "New task"),
    ("Ctrl+Z", "Undo (on a mind map, undoes the map)"),
    ("Ctrl+Y or Ctrl+Shift+Z", "Redo"),
    ("Ctrl+S", "Save the mind map"),
    ("Ctrl+G / Ctrl+Shift+G", "Group / ungroup the selected shapes"),
    ("Delete", "Delete the selected shapes, lines, bend, or Gantt bar"),
    ("Ctrl+B / Ctrl+I", "Bold / italic in a task description"),
    ("Ctrl + / Ctrl − / Ctrl 0", "Zoom the mind map in / out / to actual size"),
    ("Enter / Shift+Enter", "Finish typing in a shape / new line"),
    ("Esc", "Close search results; stop typing in a shape"),
    ("F1", "This guide"),
]


def guide_html():
    accent, muted, text = AppColors.accent, AppColors.text_muted, AppColors.text_primary
    parts = [f"<style>h3 {{ color: {accent}; margin: 14px 0 4px 0; }} li {{ margin: 3px 0; }} "
             f"td {{ padding: 3px 14px 3px 0; color: {text}; }} .key {{ color: {accent}; font-weight: bold; }}</style>"]
    for title, points in SECTIONS:
        parts.append(f"<h3>{title}</h3><ul>" + "".join(f"<li>{point}</li>" for point in points) + "</ul>")
    parts.append("<h3>Keyboard shortcuts</h3><table>")
    parts += [f"<tr><td class='key'>{keys}</td><td>{what}</td></tr>" for keys, what in SHORTCUTS]
    parts.append(f"</table><p style='color:{muted}'>Hover over a button to see what it does.</p>")
    return "".join(parts)


def make_guide(parent):
    dialog = StyledDialog(parent, "Project Meridian, quickly", "What each part of the app is for, and the shortcuts.",
                          icon="?")
    browser = QTextBrowser()
    browser.setOpenExternalLinks(True)
    browser.setHtml(guide_html())
    browser.setMinimumSize(620, 460)
    browser.setStyleSheet(f"""
        QTextBrowser {{ background-color: {AppColors.surface_raised}; color: {AppColors.text_primary};
                        border: none; border-radius: 8px; padding: 10px 14px; font-size: 13px; }}
        QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px; }}
        QScrollBar::handle:vertical {{ background: {AppColors.surface_hover_alt}; border-radius: 3px; min-height: 30px; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}""")
    dialog.content.addWidget(browser)
    dialog.addButton("Got it", True, PRIMARY, default=True)
    return dialog


def show_guide(parent):
    make_guide(parent).ask()
