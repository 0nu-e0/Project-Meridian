from resources.styles import AppStyles
from PyQt5.QtWidgets import QWidget, QToolBar, QAction, QComboBox, QHBoxLayout, QInputDialog, QListView
from PyQt5.QtCore import QSize
from PyQt5.QtGui import QTextListFormat, QFont, QTextTableFormat

class TextEditToolbar(QWidget):

    def __init__(self, editor, parent=None):
        super().__init__(parent)
        # Store a reference to the text editor
        self.editor = editor
        # Create a horizontal layout for the toolbar widget
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        # Create the QToolBar using our helper method and add it to the layout
        toolbar = self.initEditorToolbar()
        layout.addWidget(toolbar)
        self.setLayout(layout)

    def toggleBold(self, checked):
        fmt = self.editor.currentCharFormat()
        fmt.setFontWeight(QFont.Bold if checked else QFont.Normal)
        self.editor.setCurrentCharFormat(fmt)

    def toggleItalic(self, checked):
        fmt = self.editor.currentCharFormat()
        fmt.setFontItalic(checked)
        self.editor.setCurrentCharFormat(fmt)

    def toggleUnderline(self, checked):
        fmt = self.editor.currentCharFormat()
        fmt.setFontUnderline(checked)
        self.editor.setCurrentCharFormat(fmt)

    def changeFontSize(self, size_str):
        try:
            size = int(size_str)
        except ValueError:
            return
        fmt = self.editor.currentCharFormat()
        fmt.setFontPointSize(size)
        self.editor.setCurrentCharFormat(fmt)

    def insertBulletList(self):
        cursor = self.editor.textCursor()
        list_format = QTextListFormat()
        list_format.setStyle(QTextListFormat.ListDisc)
        cursor.beginEditBlock()
        cursor.createList(list_format)
        cursor.endEditBlock()

    def insertNumberedList(self):
        cursor = self.editor.textCursor()
        list_format = QTextListFormat()
        list_format.setStyle(QTextListFormat.ListDecimal)
        cursor.beginEditBlock()
        cursor.createList(list_format)
        cursor.endEditBlock()

    def initEditorToolbar(self):
        """
        Creates and returns a QToolBar with actions for text formatting.
        """

        self.setStyleSheet(AppStyles.toolbar_action_norm())

        toolbar = QToolBar("Editor Toolbar", self)
        toolbar.setIconSize(QSize(16, 16))
        
        # Bold action
        bold_action = QAction("B", self)
        bold_action.setShortcut("Ctrl+B")
        bold_action.setCheckable(True)
        bold_action.triggered.connect(self.toggleBold)
        bold_font = QFont()
        bold_font.setPointSize(14)  # Increase size
        bold_action.setFont(bold_font)
        toolbar.addAction(bold_action)
        
        # Italic action
        italic_action = QAction("I", self)
        
        italic_action.setShortcut("Ctrl+I")
        italic_action.setCheckable(True)
        italic_action.triggered.connect(self.toggleItalic)
        italic_font = QFont()
        italic_font.setPointSize(14)
        italic_action.setFont(italic_font)
        toolbar.addAction(italic_action)
        
        # Underline action
        underline_action = QAction("U", self)
        underline_action.setShortcut("Ctrl+U")
        underline_action.setCheckable(True)
        underline_action.triggered.connect(self.toggleUnderline)
        underline_font = QFont()
        underline_font.setPointSize(14)
        underline_action.setFont(underline_font)
        toolbar.addAction(underline_action)
        
        # Font size combo box
        font_size_combo = QComboBox(self)
        font_size_combo.setEditable(True)
        font_size_combo.setStyleSheet(AppStyles.combo_box_text_size())
        for size in range(8, 30, 2):
            font_size_combo.addItem(str(size))
        font_size_combo.currentTextChanged.connect(self.changeFontSize)
        font_size_combo.setView(QListView())
        toolbar.addWidget(font_size_combo)
        
        # Bullet list action (using robust rich-text formatting)
        bullet_action = QAction("Bullet", self)
        bullet_action.triggered.connect(self.insertBulletList)
        bullet_font = QFont()
        bullet_font.setPointSize(14)
        bullet_action.setFont(bullet_font)
        toolbar.addAction(bullet_action)
        
        # Numbered list action (using robust rich-text formatting)
        numbered_action = QAction("Numbered", self)
        numbered_action.triggered.connect(self.insertNumberedList)
        numbered_font = QFont()
        numbered_font.setPointSize(14)
        numbered_action.setFont(numbered_font)
        toolbar.addAction(numbered_action)
        
        # Insert Table action
        table_action = QAction("Table", self)
        table_action.triggered.connect(self.insertTable)
        table_font = QFont()
        table_font.setPointSize(14)
        table_action.setFont(table_font)
        toolbar.addAction(table_action)
        
        return toolbar

    def insertTable(self):
        # Prompt for the number of rows
        rows, ok = QInputDialog.getInt(self, "Insert Table", "Number of rows:", 2, 1, 100, 1)
        if not ok:
            return
        
        # Prompt for the number of columns
        columns, ok = QInputDialog.getInt(self, "Insert Table", "Number of columns:", 2, 1, 100, 1)
        if not ok:
            return
        
        # Get the current text cursor from the editor
        cursor = self.editor.textCursor()
        
        # Optionally set up a table format with borders, padding, etc.
        table_format = QTextTableFormat()
        table_format.setBorder(1)
        table_format.setBorderStyle(QTextTableFormat.BorderStyle_Solid)
        table_format.setCellPadding(4)
        table_format.setCellSpacing(2)
        
        # Insert the table at the current cursor position
        cursor.insertTable(rows, columns, table_format)