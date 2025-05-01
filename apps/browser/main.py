import sys

from PySide6.QtCore import QUrl
from PySide6.QtGui import QAction
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QLineEdit, QMainWindow, QToolBar


class BrowserMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dream.OS Browser")
        self.resize(1024, 768)

        # Web view
        self.web_view = QWebEngineView(self)
        self.setCentralWidget(self.web_view)
        self.web_view.load("https://www.python.org")

        # --- Navigation Toolbar ---
        nav_toolbar = QToolBar("Navigation", self)
        self.addToolBar(nav_toolbar)
        # Back
        back_action = QAction("Back", self)
        back_action.triggered.connect(self.web_view.back)
        nav_toolbar.addAction(back_action)
        # Forward
        forward_action = QAction("Forward", self)
        forward_action.triggered.connect(self.web_view.forward)
        nav_toolbar.addAction(forward_action)
        # Reload
        reload_action = QAction("Reload", self)
        reload_action.triggered.connect(self.web_view.reload)
        nav_toolbar.addAction(reload_action)
        # Address bar
        self.address_bar = QLineEdit(self)
        self.address_bar.returnPressed.connect(self.navigate_to_url)
        nav_toolbar.addWidget(self.address_bar)

    def navigate_to_url(self):
        url = self.address_bar.text()
        if not url.startswith("http"):
            url = "http://" + url
        self.web_view.load(QUrl(url))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BrowserMainWindow()
    window.show()
    sys.exit(app.exec())
