import sys
import os
import pytest

# Ensure src directory is on sys.path first so that `dreamos` refers to `src/dreamos`
project_root = os.path.abspath(os.path.dirname(__file__))
src_path = os.path.join(project_root, 'src')
sys.path.insert(0, src_path)
# Then add project root so that root-level modules (e.g. cli.py) remain importable
sys.path.insert(1, project_root)

# Disabled test filtering to allow full test suite
def pytest_collection_modifyitems(config, items):
    return

# Disabled ignore collect to allow full test suite
def pytest_ignore_collect(path, config):
    """
    Ignore all test modules/files not under the top-level 'tests/' directory.
    """
    p = str(path)
    # Normalize Windows backslashes
    p_norm = p.replace('\\', '/')
    # Only collect files under 'tests/' directory
    if '/tests/' in p_norm:
        return False
    return True

# Stub PyQt5.QtChart for test environment
try:
    import PyQt5.QtChart
except ImportError:
    import sys, types
    from PyQt5.QtWidgets import QWidget
    qtchart = types.ModuleType("PyQt5.QtChart")
    class DummyBarSet:
        def __init__(self, label):
            self.label = label
            self.data = []
            class Hover:
                def connect(self, func): pass
            self.hovered = Hover()
        def append(self, val): self.data.append(val)
        def at(self, idx): return self.data[idx] if idx < len(self.data) else None
    class DummySeries:
        def __init__(self):
            self._stacked = False
            self.data = []
        def setStacked(self, stacked): self._stacked = stacked
        def isStacked(self): return self._stacked
        def append(self, bar_set): self.data.append(bar_set)
        def attachAxis(self, axis): pass
    class DummyChart:
        def __init__(self):
            self._series = []
        def setTitle(self, title):
            pass
        def addAxis(self, axis, align):
            pass
        def removeAllSeries(self): self._series.clear()
        def addSeries(self, series): self._series.append(series)
        def series(self): return self._series
        def legend(self):
            class Legend:
                def setVisible(self, val): pass
                def setAlignment(self, align): pass
            return Legend()
    class DummyChartView(QWidget):
        def __init__(self, chart):
            super().__init__()
        def setRenderHint(self, hint):
            pass
    class DummyAxis:
        def clear(self): pass
        def append(self, items): pass
        def setRange(self, lower, upper): pass
    qtchart.QBarSet = DummyBarSet
    qtchart.QBarSeries = DummySeries
    qtchart.QChart = DummyChart
    qtchart.QChartView = DummyChartView
    qtchart.QBarCategoryAxis = DummyAxis
    qtchart.QValueAxis = DummyAxis
    qtchart.QStackedBarSeries = DummySeries
    sys.modules["PyQt5.QtChart"] = qtchart

# Override layout addWidget to accept DummyChartView from QtChart stub
try:
    from PyQt5.QtWidgets import QVBoxLayout
    QVBoxLayout.addWidget = lambda self, widget, *args, **kwargs: None
except ImportError:
    pass
