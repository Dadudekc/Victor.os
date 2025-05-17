from PyQt5.QtWidgets import QApplication, QTabWidget, QMainWindow, QStatusBar, QShortcut
from PyQt5.QtGui import QKeySequence
from tabs.agent_management import AgentManagementTab
from tabs.project_analysis import ProjectAnalysisTab
from tabs.task_board import TaskBoardTab
from tabs.discord_commander import DiscordCommanderTab
import sys

class Dashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dream.OS Command Dashboard")
        self.setGeometry(100, 100, 1200, 800)
        
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Initialize each tab
        self.agent_tab = AgentManagementTab()
        self.analysis_tab = ProjectAnalysisTab()
        self.task_tab = TaskBoardTab()
        self.discord_tab = DiscordCommanderTab()

        # Add each tab
        self.tabs.addTab(self.agent_tab, "Agent Management")
        self.tabs.addTab(self.analysis_tab, "Project Analysis")
        self.tabs.addTab(self.task_tab, "Task Board")
        self.tabs.addTab(self.discord_tab, "Discord Commander")

        # Add status bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Ready")

        # Global shortcut: Ctrl+R to run Project Scanner
        self.shortcut = QShortcut(QKeySequence("Ctrl+R"), self)
        self.shortcut.activated.connect(self.run_project_scan)

    def run_project_scan(self):
        if hasattr(self.analysis_tab, "run_project_scanner"):
            self.analysis_tab.run_project_scanner()
            self.status.showMessage("Project scanner executed (Ctrl+R)")

def main():
    app = QApplication(sys.argv)
    window = Dashboard()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
