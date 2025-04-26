# Stub PyQt5.QtWidgets for testing
class QApplication:
    _instance = None
    @classmethod
    def instance(cls):
        return cls._instance
    def __init__(self, *args, **kwargs):
        QApplication._instance = self

class QMainWindow:
    def __init__(self, *args, **kwargs):
        pass
    def statusBar(self):
        return QStatusBar()

class QTabWidget:
    def __init__(self, *args, **kwargs):
        self._widgets = []
    def addTab(self, widget, name):
        self._widgets.append(widget)
    def widget(self, index):
        return self._widgets[index]
    def count(self):
        return len(self._widgets)
    def tabText(self, index):
        return ""

class QLabel:
    def __init__(self, *args, **kwargs): pass

class QStatusBar:
    def __init__(self, *args, **kwargs): pass
    def showMessage(self, *args, **kwargs): pass

# Stub additional QtWidgets classes needed by FragmentForgeTab
class QWidget:
    def __init__(self, *args, **kwargs): pass

class QVBoxLayout:
    def __init__(self, *args, **kwargs): pass

class QHBoxLayout:
    def __init__(self, *args, **kwargs): pass

class QLineEdit:
    def __init__(self, *args, **kwargs): pass
    def setPlaceholderText(self, *args, **kwargs): pass
    def setCompleter(self, *args, **kwargs): pass

class QTextEdit:
    def __init__(self, *args, **kwargs): pass
    def setPlaceholderText(self, *args, **kwargs): pass
    def setMinimumHeight(self, *args, **kwargs): pass

class QPushButton:
    def __init__(self, *args, **kwargs): pass
    def setStyleSheet(self, *args, **kwargs): pass

class QComboBox:
    def __init__(self, *args, **kwargs): pass
    def addItems(self, items): pass
    def setToolTip(self, *args, **kwargs): pass

class QFormLayout:
    def __init__(self, *args, **kwargs): pass
    def setLabelAlignment(self, *args, **kwargs): pass
    def setSpacing(self, *args, **kwargs): pass
    def addRow(self, *args, **kwargs): pass

class QSizePolicy:
    def __init__(self, *args, **kwargs): pass

class QFileDialog:
    pass

class QCompleter:
    def __init__(self, *args, **kwargs): pass
    def setCaseSensitivity(self, *args, **kwargs): pass

class QGroupBox:
    def __init__(self, *args, **kwargs): pass
    def setLayout(self, *args, **kwargs): pass

class QSpinBox:
    def __init__(self, *args, **kwargs): pass
    def setRange(self, *args, **kwargs): pass
    def setSuffix(self, *args, **kwargs): pass
    def setToolTip(self, *args, **kwargs): pass

class QListWidget:
    def __init__(self, *args, **kwargs): pass
    def setAlternatingRowColors(self, *args, **kwargs): pass
    def setMaximumHeight(self, *args, **kwargs): pass
    def setCurrentRow(self, *args, **kwargs): pass
    def addItem(self, *args, **kwargs): pass
    def setSpacing(self, *args, **kwargs): pass
    def count(self): return 0

class QListWidgetItem:
    def __init__(self, *args, **kwargs): pass 
