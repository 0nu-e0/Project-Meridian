from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QFontInfo, QKeySequence, QTextCharFormat, QTextListFormat, QTextTableFormat
from PyQt5.QtWidgets import QComboBox, QFrame, QHBoxLayout, QListView, QShortcut, QToolButton, QWidget

from resources.styles import AppColors
from ui.custom_widgets import dialogs

FONT_SIZES = [8, 9, 10, 11, 12, 14, 16, 18, 20, 24, 28, 36]

TOOLBAR_STYLE = f"""
    QToolButton {{ background-color: {AppColors.surface_raised}; color: {AppColors.text_primary};
                   border: 1px solid {AppColors.surface_hover_alt}; border-radius: 6px;
                   padding: 4px 9px; font-size: 12px; min-width: 14px; }}
    QToolButton:hover {{ border-color: {AppColors.accent}; }}
    QToolButton:checked {{ background-color: {AppColors.accent}; border-color: {AppColors.accent}; color: white; }}
    QComboBox {{ background-color: {AppColors.surface_raised}; color: {AppColors.text_primary};
                 border: 1px solid {AppColors.surface_hover_alt}; border-radius: 6px; padding: 3px 6px; font-size: 12px; }}
    QComboBox:hover, QComboBox:focus {{ border-color: {AppColors.accent}; }}
    QComboBox::drop-down {{ border: none; width: 16px; }}
    QComboBox QAbstractItemView {{ background-color: {AppColors.surface_raised}; color: {AppColors.text_primary};
                                   selection-background-color: {AppColors.accent}; border: 1px solid {AppColors.surface_hover_alt}; }}
    QFrame#toolbarDivider {{ background-color: {AppColors.surface_hover_alt}; }}
"""


class TextEditToolbar(QWidget):
    """Formatting buttons for a rich-text editor. Bold, italic, underline, and the size
    follow the text at the cursor; their shortcuts work while the editor has focus."""

    def __init__(self, editor, parent=None):
        super().__init__(parent)
        self.editor = editor
        self.setStyleSheet(TOOLBAR_STYLE)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.boldButton = self._button("B", "Bold (Ctrl+B)", self.toggleBold, checkable=True, bold=True)
        self.italicButton = self._button("I", "Italic (Ctrl+I)", self.toggleItalic, checkable=True, italic=True)
        self.underlineButton = self._button("U", "Underline (Ctrl+U)", self.toggleUnderline, checkable=True,
                                            underline=True)
        for button in (self.boldButton, self.italicButton, self.underlineButton):
            layout.addWidget(button)

        self.sizeCombo = QComboBox()
        self.sizeCombo.setEditable(True)
        self.sizeCombo.setView(QListView())
        self.sizeCombo.setToolTip("Text size")
        self.sizeCombo.setFixedWidth(64)
        self.sizeCombo.addItems([str(size) for size in FONT_SIZES])
        self.sizeCombo.lineEdit().setPlaceholderText("Size")
        self.sizeCombo.activated[str].connect(self.changeFontSize)
        self.sizeCombo.lineEdit().returnPressed.connect(lambda: self.changeFontSize(self.sizeCombo.currentText()))
        layout.addWidget(self.sizeCombo)

        layout.addWidget(self._divider())
        layout.addWidget(self._button("•  List", "Bulleted list (press again to remove)",
                                      lambda: self.makeList(QTextListFormat.ListDisc)))
        layout.addWidget(self._button("1.  List", "Numbered list (press again to remove)",
                                      lambda: self.makeList(QTextListFormat.ListDecimal)))
        layout.addWidget(self._button("▦  Table", "Insert a table", self.insertTable))

        for keys, handler in (("Ctrl+B", self.toggleBold), ("Ctrl+I", self.toggleItalic),
                              ("Ctrl+U", self.toggleUnderline)):
            QShortcut(QKeySequence(keys), editor, handler, context=Qt.WidgetShortcut)

        editor.currentCharFormatChanged.connect(self.syncToCursor)
        editor.cursorPositionChanged.connect(self.syncToCursor)
        self.syncToCursor()

    def _button(self, text, tip, handler, checkable=False, bold=False, italic=False, underline=False):
        button = QToolButton()
        button.setText(text)
        button.setToolTip(tip)
        button.setCheckable(checkable)
        button.setCursor(Qt.PointingHandCursor)
        button.setFocusPolicy(Qt.NoFocus)  # keep the cursor (and selection) in the editor
        font = button.font()
        font.setBold(bold)
        font.setItalic(italic)
        font.setUnderline(underline)
        button.setFont(font)
        button.clicked.connect(lambda *_: handler())
        return button

    @staticmethod
    def _divider():
        line = QFrame()
        line.setObjectName("toolbarDivider")
        line.setFixedSize(1, 20)
        return line

    # -- formatting -----------------------------------------------------------
    def _merge(self, fmt):
        self.editor.mergeCurrentCharFormat(fmt)
        self.editor.setFocus()
        self.syncToCursor()

    def toggleBold(self):
        fmt = QTextCharFormat()
        fmt.setFontWeight(QFont.Normal if self.editor.currentCharFormat().fontWeight() > QFont.Normal else QFont.Bold)
        self._merge(fmt)

    def toggleItalic(self):
        fmt = QTextCharFormat()
        fmt.setFontItalic(not self.editor.currentCharFormat().fontItalic())
        self._merge(fmt)

    def toggleUnderline(self):
        fmt = QTextCharFormat()
        fmt.setFontUnderline(not self.editor.currentCharFormat().fontUnderline())
        self._merge(fmt)

    def changeFontSize(self, size_str):
        try:
            size = float(size_str)
        except ValueError:
            self.syncToCursor()
            return
        if not 1 <= size <= 200:
            self.syncToCursor()
            return
        fmt = QTextCharFormat()
        fmt.setFontPointSize(size)
        self._merge(fmt)

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

    def insertTable(self):
        rows, ok = dialogs.getInt(self, "Insert Table", "Number of rows:", 2, 1, 100, 1)
        if not ok:
            return
        columns, ok = dialogs.getInt(self, "Insert Table", "Number of columns:", 2, 1, 100, 1)
        if not ok:
            return
        table_format = QTextTableFormat()
        table_format.setBorder(1)
        table_format.setBorderStyle(QTextTableFormat.BorderStyle_Solid)
        table_format.setBorderBrush(Qt.gray)
        table_format.setCellPadding(4)
        table_format.setCellSpacing(0)
        self.editor.textCursor().insertTable(rows, columns, table_format)
        self.editor.setFocus()

    # -- follow the cursor ----------------------------------------------------
    def syncToCursor(self, *_):
        fmt = self.editor.currentCharFormat()
        self.boldButton.setChecked(fmt.fontWeight() > QFont.Normal)
        self.italicButton.setChecked(fmt.fontItalic())
        self.underlineButton.setChecked(fmt.fontUnderline())
        size = round(fmt.fontPointSize() or QFontInfo(fmt.font()).pointSizeF())
        if not self.sizeCombo.lineEdit().hasFocus():
            self.sizeCombo.blockSignals(True)
            self.sizeCombo.setEditText(f"{size:g}" if size > 0 else "")
            self.sizeCombo.blockSignals(False)
