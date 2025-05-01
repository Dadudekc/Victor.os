import os
import sys

from PyQt5.QtCore import QUrl

# Import WebEngine for embedding HTML
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWidgets import QAction, QApplication, QMainWindow


class SkyViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sky Map Viewer")
        self.resize(1024, 768)

        # Menu bar for full-screen and multi-window
        menubar = self.menuBar()
        view_menu = menubar.addMenu("View")
        fs_action = QAction("Toggle Full Screen", self)
        fs_action.setShortcut("F11")
        fs_action.triggered.connect(self.toggle_fullscreen)
        view_menu.addAction(fs_action)
        window_menu = menubar.addMenu("Window")
        splash_action = QAction("Open Splash Window", self)
        splash_action.triggered.connect(self.open_splash)
        window_menu.addAction(splash_action)

        # Create web view widget
        self.web_view = QWebEngineView(self)
        self.setCentralWidget(self.web_view)

        # Construct local file URL to sky.html
        base_dir = os.path.dirname(os.path.abspath(__file__))
        html_file = os.path.join(base_dir, "templates", "planets.html")
        url = QUrl.fromLocalFile(html_file)

        # Load the HTML
        self.web_view.load(url)

    def send_fullscreen_toggle(self):
        # helper stub, not used
        pass

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def open_splash(self):
        # Open a second window showing splash.html
        if not hasattr(self, "splash_window"):
            self.splash_window = QMainWindow()
            splash_web = QWebEngineView()
            self.splash_window.setCentralWidget(splash_web)
            base_dir = os.path.dirname(os.path.abspath(__file__))
            splash_path = os.path.join(base_dir, "splash.html")
            splash_web.load(QUrl.fromLocalFile(splash_path))
            self.splash_window.setWindowTitle("Splash Page")
        self.splash_window.show()


if __name__ == "__main__":
    # Ensure PyQtWebEngine is installed: pip install PyQtWebEngine
    app = QApplication(sys.argv)
    viewer = SkyViewer()
    viewer.show()
    sys.exit(app.exec_())
