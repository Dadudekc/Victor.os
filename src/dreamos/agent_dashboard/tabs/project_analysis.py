from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget, QPushButton
import json
from pathlib import Path
import subprocess

class ProjectAnalysisTab(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Run Scanner Button
        run_button = QPushButton("Run Project Scanner")
        run_button.clicked.connect(self.run_project_scanner)
        self.layout.addWidget(run_button)

        # Load Data
        self.reload_data()

    def run_project_scanner(self):
        try:
            result = subprocess.run(
                ["python", "src/dreamos/tools/project_scanner.py"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                self.layout.addWidget(QLabel("Scan complete. Reloading results..."))
                self.reload_data()
            else:
                self.layout.addWidget(QLabel(f"Scan failed: {result.stderr}"))
        except Exception as e:
            self.layout.addWidget(QLabel(f"Error running project scanner: {e}"))

    def reload_data(self):
        self.load_file_info("chatgpt_project_context.json", "Project Context", show_issues=False)
        self.load_file_info("project_analysis.json", "File Stats", show_issues=True)
        self.load_file_info("dependency_cache.json", "Dependency Map", show_issues=False)

    def load_file_info(self, file_name, label, show_issues=False):
        path = Path(file_name)
        if not path.exists():
            self.layout.addWidget(QLabel(f"{label}: Not found"))
            return

        try:
            with open(path, "r") as f:
                data = json.load(f)
        except Exception as e:
            self.layout.addWidget(QLabel(f"{label}: Error loading JSON - {e}"))
            return

        count = len(data) if isinstance(data, (list, dict)) else "?"
        self.layout.addWidget(QLabel(f"{label}: Loaded ({count} items)"))

        if show_issues and isinstance(data, list):
            issue_list = QListWidget()
            issue_count = 0
            for item in data:
                if isinstance(item, dict) and (
                    item.get("is_orphaned") or item.get("missing_docs") or not item.get("runnable_hook")
                ):
                    file_path = item.get("path", "Unknown file")
                    issues = ", ".join(filter(None, [
                        "Orphaned" if item.get("is_orphaned") else "",
                        "Missing Docs" if item.get("missing_docs") else "",
                        "No Runnable Hook" if not item.get("runnable_hook") else ""
                    ]))
                    issue_list.addItem(f"{file_path} | {issues}")
                    issue_count += 1
            if issue_count > 0:
                self.layout.addWidget(QLabel(f"{issue_count} file(s) need attention:"))
                self.layout.addWidget(issue_list)
