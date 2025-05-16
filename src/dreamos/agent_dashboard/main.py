from PyQt5.QtWidgets import QApplication, QTabWidget, QMainWindow
from tabs.agent_management import AgentManagementTab
from tabs.project_analysis import ProjectAnalysisTab
from tabs.task_board import TaskBoardTab
import sys

class Dashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dream.OS Command Dashboard")
        self.setGeometry(100, 100, 1200, 800)
        
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Add each tab
        self.tabs.addTab(AgentManagementTab(), "Agent Management")
        self.tabs.addTab(ProjectAnalysisTab(), "Project Analysis")
        self.tabs.addTab(TaskBoardTab(), "Task Board")

def main():
    app = QApplication(sys.argv)
    window = Dashboard()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
