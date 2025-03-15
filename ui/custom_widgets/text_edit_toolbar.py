from PyQt5.QtWidgets import QWidget, QToolBar, QAction, QComboBox, QHBoxLayout
from PyQt5.QtCore import QSize
from PyQt5.QtGui import QTextListFormat, QFont

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
        toolbar = QToolBar("Editor Toolbar", self)
        toolbar.setIconSize(QSize(16, 16))
        
        # Bold action
        bold_action = QAction("B", self)
        bold_action.setShortcut("Ctrl+B")
        bold_action.setCheckable(True)
        bold_action.triggered.connect(self.toggleBold)
        toolbar.addAction(bold_action)
        
        # Italic action
        italic_action = QAction("I", self)
        italic_action.setShortcut("Ctrl+I")
        italic_action.setCheckable(True)
        italic_action.triggered.connect(self.toggleItalic)
        toolbar.addAction(italic_action)
        
        # Underline action
        underline_action = QAction("U", self)
        underline_action.setShortcut("Ctrl+U")
        underline_action.setCheckable(True)
        underline_action.triggered.connect(self.toggleUnderline)
        toolbar.addAction(underline_action)
        
        # Font size combo box
        font_size_combo = QComboBox(self)
        font_size_combo.setEditable(True)
        for size in range(8, 30, 2):
            font_size_combo.addItem(str(size))
        font_size_combo.currentTextChanged.connect(self.changeFontSize)
        toolbar.addWidget(font_size_combo)
        
        # Bullet list action (using robust rich-text formatting)
        bullet_action = QAction("Bullet", self)
        bullet_action.triggered.connect(self.insertBulletList)
        toolbar.addAction(bullet_action)
        
        # Numbered list action (using robust rich-text formatting)
        numbered_action = QAction("Numbered", self)
        numbered_action.triggered.connect(self.insertNumberedList)
        toolbar.addAction(numbered_action)
        
        return toolbar

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
