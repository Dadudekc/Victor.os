"""
Dream.OS ‑ Main GUI shell (PyQt6).

* Injects the loaded AppConfig for runtime settings.
* Provides stubs for future tabs (Strategy, Execution, Logs, Settings).
* Emits `closeRequested` signal so boot_gui() can handle graceful shutdowns.
"""

from __future__ import annotations
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QTabWidget,
    QVBoxLayout,
    QLabel,
    QStatusBar,
    QMessageBox,
)
# Removed sys.path modification and conditional import logic

# Changed to absolute import relative to project root (added to sys.path in main.py)
from dreamos.config import AppConfig

class MainWindow(QMainWindow):
    closeRequested = pyqtSignal()

    def __init__(self, config: AppConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.cfg = config
        # Accessing config.gui might fail if GuiConfig was removed and not re-added
        # Using a default title for now, requires AppConfig update if GUI config is needed
        self.setWindowTitle(getattr(self.cfg, 'gui', {}).get('window_title', "Dream.OS"))
        self.resize(1200, 800)

        # ——— central tab widget —————————————————
        self.tabs = QTabWidget()
        self.tabs.addTab(self._make_placeholder("Strategy"), "Strategy")
        self.tabs.addTab(self._make_placeholder("Execution"), "Execution")
        self.tabs.addTab(self._make_placeholder("Logs"), "Logs")
        self.tabs.addTab(self._make_placeholder("Settings"), "Settings")
        self.setCentralWidget(self.tabs)

        # ——— status bar ——————————————————
        status = QStatusBar()
        status.showMessage("Dream.OS ready", 5000)
        self.setStatusBar(status)

    # ——————————————————————————
    def _make_placeholder(self, name: str) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addStretch()
        lab = QLabel(f"{name} tab – coming soon.")
        lab.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(lab)
        lay.addStretch()
        return w

    def closeEvent(self, event):  # noqa: N802  (qt override)
        reply = QMessageBox.question(
            self,
            "Quit Dream.OS",
            "Are you sure you want to exit?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No # Default button
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.closeRequested.emit()
            event.accept()
        else:
            event.ignore() 
