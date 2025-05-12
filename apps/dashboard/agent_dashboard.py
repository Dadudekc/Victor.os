import json
import sys
import time
import asyncio
import os
from pathlib import Path
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QTabWidget, QLabel, QHBoxLayout, QTextEdit, QTableWidgetSelectionRange,
    QSplitter, QListWidget, QListWidgetItem, QMainWindow, QMenu, QAction,
    QStyle, QStyleFactory, QComboBox, QGroupBox, QGridLayout, QTreeWidget, QTreeWidgetItem,
    QCheckBox, QMessageBox
)
from PyQt5.QtGui import QColor, QPalette, QIcon, QFont

# Add the apps directory to Python path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT)
ROOT_PATH = Path(ROOT)

from dashboard.modules.thea_handler import THEAHandler
from dashboard.modules.task_manager import load_inbox, load_status
from dashboard.modules.ui_components import (
    AgentTab, THEME, VoiceCommandWidget, EpisodeMetricsTab,
    TaskActionMenu
)
from dashboard.modules.notifier import Notifier

DEVLOG_BASE = ROOT_PATH / "runtime" / "devlog" / "agents"
ONBOARDING_TEMPLATE = ROOT_PATH / "templates" / "onboarding" / "initial_packet.json"
CONTEXT_FILE = ROOT_PATH / "chatgpt_project_context.json"
DEPENDENCY_FILE = ROOT_PATH / "dependency_cache.json"
ANALYSIS_FILE = ROOT_PATH / "project_analysis.json"
INBOX_BASE = ROOT_PATH / "runtime" / "agent_comms" / "agent_mailboxes"

# ------------------- THEME COLORS -------------------

THEME = {
    "light": {
        "background": "#ffffff",
        "text": "#000000",
        "accent": "#007acc",
        "success": "#28a745",
        "warning": "#ffc107",
        "error": "#dc3545",
        "agent_colors": {
            "brain": "#28a745",  # Green
            "shield": "#dc3545",  # Red
            "bridge": "#007acc",  # Blue
            "default": "#6c757d"  # Gray
        }
    },
    "dark": {
        "background": "#1e1e1e",
        "text": "#ffffff",
        "accent": "#007acc",
        "success": "#28a745",
        "warning": "#ffc107",
        "error": "#dc3545",
        "agent_colors": {
            "brain": "#28a745",
            "shield": "#dc3545",
            "bridge": "#007acc",
            "default": "#6c757d"
        }
    }
}

# ------------------- UTILITY FUNCTIONS -------------------

def load_devlog(agent_id: str) -> str:
    """Load agent's devlog content"""
    log_path = DEVLOG_BASE / f"{agent_id}.md"
    if log_path.exists():
        try:
            return log_path.read_text()
        except Exception:
            return "Error loading devlog"
    return "No devlog available"

def last_devlog_ts(agent_id: str) -> str | None:
    """Get timestamp of last devlog entry"""
    log_file = DEVLOG_BASE / f"{agent_id}.md"
    return time.ctime(log_file.stat().st_mtime) if log_file.exists() else None

def enqueue(agent_id: str, payload: dict) -> None:
    """Add a new message to agent's inbox"""
    inbox_path = INBOX_BASE / agent_id / "inbox.json"
    inbox_path.parent.mkdir(parents=True, exist_ok=True)
    messages = load_inbox(agent_id)
    if isinstance(messages, list):
        messages.append(payload)
        inbox_path.write_text(json.dumps(messages, indent=2))
    else:
        print(f"Warning: Invalid inbox format for {agent_id}")

def update_task_status(agent_id: str, task_id: str, new_status: str) -> None:
    """Update the status of a task in the agent's inbox"""
    inbox_path = INBOX_BASE / agent_id / "inbox.json"
    if inbox_path.exists():
        try:
            messages = json.loads(inbox_path.read_text())
            if isinstance(messages, list):
                for msg in messages:
                    if isinstance(msg, dict) and msg.get("id") == task_id:
                        msg["status"] = new_status
                inbox_path.write_text(json.dumps(messages, indent=2))
        except Exception as e:
            print(f"Error updating task status: {e}")

def requeue_task(agent_id: str, task_id: str, target_agent: str) -> None:
    """Requeue a task to another agent"""
    inbox_path = INBOX_BASE / agent_id / "inbox.json"
    target_inbox = INBOX_BASE / target_agent / "inbox.json"
    
    if inbox_path.exists() and target_inbox.exists():
        try:
            # Load source inbox
            messages = json.loads(inbox_path.read_text())
            if isinstance(messages, list):
                # Find and move the task
                task_to_move = None
                messages = [msg for msg in messages if msg.get("id") != task_id or not (task_to_move := msg)]
                
                if task_to_move:
                    # Update task metadata
                    task_to_move["requeued_from"] = agent_id
                    task_to_move["requeued_at"] = time.time()
                    
                    # Save updated source inbox
                    inbox_path.write_text(json.dumps(messages, indent=2))
                    
                    # Add to target inbox
                    target_messages = json.loads(target_inbox.read_text())
                    if isinstance(target_messages, list):
                        target_messages.append(task_to_move)
                        target_inbox.write_text(json.dumps(target_messages, indent=2))
        except Exception as e:
            print(f"Error requeuing task: {e}")

def escalate_to_thea(agent_id: str, task_id: str) -> None:
    """Escalate a task to THEA with ChatGPT integration"""
    thea_inbox = INBOX_BASE / "THEA" / "inbox.json"
    if thea_inbox.exists():
        try:
            # Load source task
            inbox_path = INBOX_BASE / agent_id / "inbox.json"
            messages = json.loads(inbox_path.read_text())
            if isinstance(messages, list):
                task = next((msg for msg in messages if msg.get("id") == task_id), None)
                if task:
                    # Create escalation message with context
                    escalation = {
                        "type": "escalation",
                        "source_agent": agent_id,
                        "source_task": task_id,
                        "content": task.get("content", "No content"),
                        "timestamp": time.time(),
                        "priority": "high",
                        "context": {
                            "original_task": task,
                            "agent_status": load_status(agent_id),
                            "agent_inbox": messages
                        }
                    }
                    
                    # Add to THEA's inbox
                    thea_messages = json.loads(thea_inbox.read_text())
                    if isinstance(thea_messages, list):
                        thea_messages.append(escalation)
                        thea_inbox.write_text(json.dumps(thea_messages, indent=2))
                        
                        # Start async THEA response handler
                        asyncio.create_task(handle_thea_escalation(agent_id, task_id, escalation))
        except Exception as e:
            print(f"Error escalating task: {e}")

async def handle_thea_escalation(agent_id: str, task_id: str, escalation: dict) -> None:
    """Handle THEA's response to an escalation using ChatGPT"""
    try:
        # Format the prompt for THEA
        prompt = f"""As THEA (Task Handling and Execution Assistant), you are receiving an escalated task from {agent_id}.

Task ID: {task_id}
Content: {escalation['content']}

Agent Status: {json.dumps(escalation['context']['agent_status'], indent=2)}
Task Context: {json.dumps(escalation['context']['original_task'], indent=2)}

Please provide a response that:
1. Acknowledges the escalation
2. Provides clear next steps or resolution
3. Includes any necessary instructions for the agent

Format your response as a JSON object with the following structure:
{{
    "type": "thea_response",
    "task_id": "{task_id}",
    "status": "resolved|in_progress|needs_info",
    "response": "Your detailed response here",
    "next_steps": ["Step 1", "Step 2", ...],
    "timestamp": {time.time()}
}}"""

        # Initialize ChatGPT web agent for THEA
        from archive.orphans.agents.chatgpt_web_agent import ChatGPTWebAgent
        from dreamos.core.config import AppConfig
        
        config = AppConfig()
        thea_agent = ChatGPTWebAgent(
            config=config,
            agent_id="THEA",
            conversation_url=config.get("agents.chatgpt_web.THEA.conversation_url", ""),
            task_nexus=None,  # We'll handle the response directly
            simulate=False
        )
        
        # Get THEA's response
        response = await thea_agent.process_external_prompt(prompt)
        if response:
            try:
                # Parse THEA's response
                thea_response = json.loads(response)
                
                # Add response to agent's inbox
                inbox_path = INBOX_BASE / agent_id / "inbox.json"
                if inbox_path.exists():
                    messages = json.loads(inbox_path.read_text())
                    if isinstance(messages, list):
                        # Add THEA's response
                        messages.append({
                            "type": "thea_response",
                            "task_id": task_id,
                            "content": thea_response,
                            "timestamp": time.time()
                        })
                        inbox_path.write_text(json.dumps(messages, indent=2))
                        
                        # Update task status if provided
                        if thea_response.get("status"):
                            update_task_status(agent_id, task_id, thea_response["status"])
            except json.JSONDecodeError:
                print(f"Error parsing THEA's response: {response}")
        else:
            print("No response received from THEA")
            
    except Exception as e:
        print(f"Error handling THEA escalation: {e}")
    finally:
        # Clean up THEA agent
        await thea_agent.close()

# ------------------- AGENT STATUS PANEL -------------------

class TaskActionMenu(QMenu):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QMenu {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
            }
            QMenu::item {
                padding: 5px 20px;
            }
            QMenu::item:selected {
                background-color: #3d3d3d;
            }
        """)

# ------------------- PROJECT ANALYSIS PANEL -------------------

class ProjectTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        # Load data sources
        self.context = self._load_json(CONTEXT_FILE)
        self.dependencies = self._load_json(DEPENDENCY_FILE)
        self.analysis = self._load_json(ANALYSIS_FILE)
        self.agent_logs = self._load_agent_logs()
        self.test_coverage = self._load_test_coverage()

        # Create main layout with metrics sidebar
        main_layout = QHBoxLayout()
        layout.addLayout(main_layout)

        # Left side - main content
        content_layout = QVBoxLayout()
        main_layout.addLayout(content_layout)

        # Create tab widget for different sections
        self.tab_widget = QTabWidget()
        content_layout.addWidget(self.tab_widget)

        # Add Overview tab
        self.overview_tab = QWidget()
        overview_layout = QVBoxLayout(self.overview_tab)
        
        # Add refresh button and overlay controls
        controls_layout = QHBoxLayout()
        self.refresh_button = QPushButton("🔄 Refresh Analysis")
        self.refresh_button.clicked.connect(self.refresh_data)
        controls_layout.addWidget(self.refresh_button)
        
        # Overlay controls
        self.ownership_check = QCheckBox("Show Agent Ownership")
        self.ownership_check.stateChanged.connect(self.update_module_tree)
        controls_layout.addWidget(self.ownership_check)
        
        self.coverage_check = QCheckBox("Show Test Coverage")
        self.coverage_check.stateChanged.connect(self.update_module_tree)
        controls_layout.addWidget(self.coverage_check)

        # Export button
        self.export_button = QPushButton("📤 Export to Markdown")
        self.export_button.clicked.connect(self.export_to_markdown)
        controls_layout.addWidget(self.export_button)
        
        controls_layout.addStretch()
        overview_layout.addLayout(controls_layout)
        
        # Project summary section
        summary_group = QGroupBox("Project Summary")
        summary_layout = QVBoxLayout()
        self.summary = QTextEdit()
        self.summary.setReadOnly(True)
        summary_layout.addWidget(self.summary)
        summary_group.setLayout(summary_layout)
        overview_layout.addWidget(summary_group)

        # File statistics section
        stats_group = QGroupBox("File Statistics")
        stats_layout = QGridLayout()
        self.total_files_label = QLabel("Total Files: 0")
        self.orphaned_files_label = QLabel("Orphaned Files: 0")
        self.missing_docs_label = QLabel("Missing Docs: 0")
        self.modules_label = QLabel("Modules: 0")
        stats_layout.addWidget(self.total_files_label, 0, 0)
        stats_layout.addWidget(self.orphaned_files_label, 0, 1)
        stats_layout.addWidget(self.missing_docs_label, 1, 0)
        stats_layout.addWidget(self.modules_label, 1, 1)
        stats_group.setLayout(stats_layout)
        overview_layout.addWidget(stats_group)

        # Add Dependencies tab
        self.deps_tab = QWidget()
        deps_layout = QVBoxLayout(self.deps_tab)
        self.deps_table = QTableWidget()
        self.deps_table.setColumnCount(3)
        self.deps_table.setHorizontalHeaderLabels(["Package", "Version", "Status"])
        deps_layout.addWidget(self.deps_table)

        # Add Module Analysis tab
        self.modules_tab = QWidget()
        modules_layout = QVBoxLayout(self.modules_tab)
        
        # Split view for modules
        modules_splitter = QSplitter(Qt.Horizontal)
        
        # Module tree with enhanced columns
        self.modules_tree = QTreeWidget()
        self.modules_tree.setHeaderLabels(["Module", "Files", "Status", "Owner", "Coverage"])
        self.modules_tree.setColumnWidth(0, 200)  # Module name
        self.modules_tree.setColumnWidth(1, 80)   # Files
        self.modules_tree.setColumnWidth(2, 100)  # Status
        self.modules_tree.setColumnWidth(3, 100)  # Owner
        self.modules_tree.setColumnWidth(4, 100)  # Coverage
        self.modules_tree.itemClicked.connect(self.show_module_details)
        modules_splitter.addWidget(self.modules_tree)
        
        # Module details panel
        self.module_details = QWidget()
        details_layout = QVBoxLayout(self.module_details)
        
        # Module info with enhanced sections
        self.module_info = QTextEdit()
        self.module_info.setReadOnly(True)
        details_layout.addWidget(QLabel("Module Details"))
        details_layout.addWidget(self.module_info)
        
        # File list with status
        self.module_files = QTextEdit()
        self.module_files.setReadOnly(True)
        details_layout.addWidget(QLabel("Files"))
        details_layout.addWidget(self.module_files)
        
        # Test coverage details
        self.coverage_info = QTextEdit()
        self.coverage_info.setReadOnly(True)
        details_layout.addWidget(QLabel("Test Coverage"))
        details_layout.addWidget(self.coverage_info)
        
        modules_splitter.addWidget(self.module_details)
        modules_layout.addWidget(modules_splitter)

        # Add tabs to widget
        self.tab_widget.addTab(self.overview_tab, "Overview")
        self.tab_widget.addTab(self.deps_tab, "Dependencies")
        self.tab_widget.addTab(self.modules_tab, "Modules")

        # Populate data
        self._populate_summary()
        self._populate_dependencies()
        self._populate_modules()

        # Right side - metrics sidebar
        metrics_panel = QWidget()
        metrics_panel.setFixedWidth(250)
        metrics_layout = QVBoxLayout(metrics_panel)
        
        # Metrics header
        metrics_header = QLabel("Project Metrics")
        metrics_header.setStyleSheet("font-weight: bold; font-size: 14px;")
        metrics_layout.addWidget(metrics_header)
        
        # Metrics group
        metrics_group = QGroupBox("Live Statistics")
        metrics_group_layout = QVBoxLayout()
        
        # Create metric labels
        self.total_modules_label = QLabel("Total Modules: 0")
        self.total_files_label = QLabel("Total Files: 0")
        self.coverage_label = QLabel("Test Coverage: 0%")
        self.orphaned_label = QLabel("Orphaned Files: 0")
        self.unowned_label = QLabel("Unowned Code: 0%")
        self.active_agents_label = QLabel("Active Agents: 0")
        
        # Add labels to group
        metrics_group_layout.addWidget(self.total_modules_label)
        metrics_group_layout.addWidget(self.total_files_label)
        metrics_group_layout.addWidget(self.coverage_label)
        metrics_group_layout.addWidget(self.orphaned_label)
        metrics_group_layout.addWidget(self.unowned_label)
        metrics_group_layout.addWidget(self.active_agents_label)
        
        metrics_group.setLayout(metrics_group_layout)
        metrics_layout.addWidget(metrics_group)
        
        # THEA insights
        thea_group = QGroupBox("THEA Insights")
        thea_layout = QVBoxLayout()
        self.thea_insight = QLabel("🧠 Analyzing project health...")
        self.thea_insight.setWordWrap(True)
        thea_layout.addWidget(self.thea_insight)
        thea_group.setLayout(thea_layout)
        metrics_layout.addWidget(thea_group)
        
        metrics_layout.addStretch()
        main_layout.addWidget(metrics_panel)

        # Update metrics
        self.update_metrics()

    def _load_json(self, path: Path):
        return json.loads(path.read_text()) if path.exists() else {}

    def _load_agent_logs(self) -> dict:
        """Load agent activity logs to determine module ownership"""
        agent_logs = {}
        log_dir = ROOT_PATH / "runtime" / "agent_logs"
        if log_dir.exists():
            for log_file in log_dir.glob("*.json"):
                try:
                    with open(log_file, 'r') as f:
                        logs = json.load(f)
                        agent_id = log_file.stem
                        agent_logs[agent_id] = logs
                except Exception as e:
                    print(f"Error loading agent log {log_file}: {e}")
        return agent_logs

    def _load_test_coverage(self) -> dict:
        """Load test coverage data"""
        coverage_data = {}
        coverage_file = ROOT_PATH / "coverage.xml"
        if coverage_file.exists():
            try:
                import xml.etree.ElementTree as ET
                tree = ET.parse(coverage_file)
                root = tree.getroot()
                for package in root.findall(".//package"):
                    name = package.get("name", "")
                    coverage_data[name] = {
                        "coverage": float(package.get("line-rate", 0)) * 100,
                        "lines": int(package.get("lines-valid", 0)),
                        "covered": int(package.get("lines-covered", 0))
                    }
            except Exception as e:
                print(f"Error loading coverage data: {e}")
        return coverage_data

    def _get_module_owner(self, module_name: str) -> tuple[str, float]:
        """Determine module ownership based on agent activity"""
        if not self.agent_logs:
            return "Unknown", 0.0
            
        module_activity = {}
        total_activity = 0
        
        for agent_id, logs in self.agent_logs.items():
            activity = 0
            for log in logs:
                if isinstance(log, dict):
                    # Count tasks and changes related to this module
                    if log.get("module") == module_name:
                        activity += 1
                    elif log.get("files"):
                        for file in log["files"]:
                            if file.startswith(module_name):
                                activity += 1
            module_activity[agent_id] = activity
            total_activity += activity
            
        if total_activity == 0:
            return "Unknown", 0.0
            
        # Find agent with highest activity
        owner = max(module_activity.items(), key=lambda x: x[1])
        ownership_percent = (owner[1] / total_activity) * 100
        return owner[0], ownership_percent

    def _get_module_coverage(self, module_name: str) -> dict:
        """Get test coverage data for a module"""
        return self.test_coverage.get(module_name, {
            "coverage": 0.0,
            "lines": 0,
            "covered": 0
        })

    def _populate_summary(self):
        ctx = self.context.get("project_summary", {})
        ana = self.analysis.get("file_counts", {})

        # Update summary text
        lines = []
        if ctx:
            lines.append(f"Project: {ctx.get('name', 'N/A')}")
            lines.append(f"Description: {ctx.get('summary', 'No summary')}")
            lines.append(f"Root folders: {', '.join(ctx.get('root_dirs', []))}")
            lines.append("")
        self.summary.setText("\n".join(lines))

        # Update statistics
        if ana:
            self.total_files_label.setText(f"Total Files: {ana.get('total_files', 0)}")
            self.orphaned_files_label.setText(f"Orphaned Files: {ana.get('orphaned_files', 0)}")
            self.missing_docs_label.setText(f"Missing Docs: {ana.get('missing_docs', 0)}")
            self.modules_label.setText(f"Modules: {len(ana.get('modules', {}))}")

    def _populate_dependencies(self):
        deps = self.dependencies.get("dependencies", {})
        self.deps_table.setRowCount(len(deps))
        
        for row, (pkg, meta) in enumerate(deps.items()):
            self.deps_table.setItem(row, 0, QTableWidgetItem(pkg))
            self.deps_table.setItem(row, 1, QTableWidgetItem(meta.get("version", "?")))
            
            # Determine status
            status = "OK"
            if meta.get("outdated"):
                status = "Outdated"
            elif meta.get("missing"):
                status = "Missing"
            status_item = QTableWidgetItem(status)
            status_item.setForeground(QColor(THEME["light"]["success"] if status == "OK" else THEME["light"]["warning"]))
            self.deps_table.setItem(row, 2, status_item)

    def _populate_modules(self):
        modules = self.analysis.get("modules", {})
        self.modules_tree.clear()
        
        show_ownership = self.ownership_check.isChecked()
        show_coverage = self.coverage_check.isChecked()
        
        for module_name, module_data in modules.items():
            # Get ownership data
            owner, ownership_percent = self._get_module_owner(module_name)
            owner_text = f"{owner} ({ownership_percent:.0f}%)" if show_ownership else ""
            
            # Get coverage data
            coverage = self._get_module_coverage(module_name)
            coverage_text = f"{coverage['coverage']:.0f}%" if show_coverage else ""
            
            # Create tree item
            module_item = QTreeWidgetItem([
                module_name,
                str(module_data.get("file_count", 0)),
                "OK" if not module_data.get("issues") else "Issues",
                owner_text,
                coverage_text
            ])
            
            # Set colors based on ownership and coverage
            if show_ownership:
                agent_color = THEME["light"]["agent_colors"].get(owner, THEME["light"]["default"])
                module_item.setForeground(3, QColor(agent_color))
            
            if show_coverage:
                coverage_color = (
                    THEME["light"]["success"] if coverage["coverage"] >= 80
                    else THEME["light"]["warning"] if coverage["coverage"] >= 50
                    else THEME["light"]["error"]
                )
                module_item.setForeground(4, QColor(coverage_color))
            
            # Add submodules
            for submodule, submodule_data in module_data.get("submodules", {}).items():
                sub_owner, sub_ownership = self._get_module_owner(f"{module_name}.{submodule}")
                sub_owner_text = f"{sub_owner} ({sub_ownership:.0f}%)" if show_ownership else ""
                
                sub_coverage = self._get_module_coverage(f"{module_name}.{submodule}")
                sub_coverage_text = f"{sub_coverage['coverage']:.0f}%" if show_coverage else ""
                
                submodule_item = QTreeWidgetItem([
                    submodule,
                    str(submodule_data.get("file_count", 0)),
                    "OK" if not submodule_data.get("issues") else "Issues",
                    sub_owner_text,
                    sub_coverage_text
                ])
                
                if show_ownership:
                    submodule_item.setForeground(3, QColor(THEME["light"]["agent_colors"].get(sub_owner, THEME["light"]["default"])))
                
                if show_coverage:
                    sub_coverage_color = (
                        THEME["light"]["success"] if sub_coverage["coverage"] >= 80
                        else THEME["light"]["warning"] if sub_coverage["coverage"] >= 50
                        else THEME["light"]["error"]
                    )
                    submodule_item.setForeground(4, QColor(sub_coverage_color))
                
                module_item.addChild(submodule_item)
            
            self.modules_tree.addTopLevelItem(module_item)
        
        self.modules_tree.expandAll()

    def update_metrics(self):
        """Update the metrics sidebar with current data"""
        modules = self.analysis.get("modules", {})
        total_modules = len(modules)
        total_files = sum(m.get("file_count", 0) for m in modules.values())
        
        # Calculate coverage
        total_coverage = 0
        covered_modules = 0
        for module_name in modules:
            coverage = self._get_module_coverage(module_name)
            if coverage["lines"] > 0:
                total_coverage += coverage["coverage"]
                covered_modules += 1
        avg_coverage = total_coverage / covered_modules if covered_modules > 0 else 0
        
        # Calculate orphaned files
        orphaned_files = self.analysis.get("file_counts", {}).get("orphaned_files", 0)
        
        # Calculate unowned code
        unowned_modules = sum(1 for m in modules if self._get_module_owner(m)[0] == "Unknown")
        unowned_percent = (unowned_modules / total_modules * 100) if total_modules > 0 else 0
        
        # Count active agents
        active_agents = len(set(owner for owner, _ in (self._get_module_owner(m) for m in modules) if owner != "Unknown"))
        
        # Update labels
        self.total_modules_label.setText(f"Total Modules: {total_modules}")
        self.total_files_label.setText(f"Total Files: {total_files}")
        self.coverage_label.setText(f"Test Coverage: {avg_coverage:.1f}%")
        self.orphaned_label.setText(f"Orphaned Files: {orphaned_files}")
        self.unowned_label.setText(f"Unowned Code: {unowned_percent:.1f}%")
        self.active_agents_label.setText(f"Active Agents: {active_agents}")
        
        # Update THEA insight
        self._update_thea_insight()

    def _update_thea_insight(self):
        """Generate THEA's insight about project health"""
        modules = self.analysis.get("modules", {})
        coverage = self._get_module_coverage("")
        orphaned = self.analysis.get("file_counts", {}).get("orphaned_files", 0)
        
        insights = []
        if coverage["coverage"] < 50:
            insights.append("Test coverage is below target")
        if orphaned > 0:
            insights.append(f"{orphaned} orphaned files need attention")
        
        if insights:
            self.thea_insight.setText("🧠 " + "\n".join(insights))
        else:
            self.thea_insight.setText("🧠 Project health is good!")

    def export_to_markdown(self):
        """Export current project analysis to markdown"""
        try:
            # Create episode directory if it doesn't exist
            episode_dir = ROOT_PATH / "docs" / "episode" / "episode-05"
            episode_dir.mkdir(parents=True, exist_ok=True)
            
            # Prepare markdown content
            content = [
                "# Dream.OS Project Analysis",
                f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
                "",
                "## Project Overview",
                f"Total Modules: {len(self.analysis.get('modules', {}))}",
                f"Total Files: {self.analysis.get('file_counts', {}).get('total_files', 0)}",
                f"Orphaned Files: {self.analysis.get('file_counts', {}).get('orphaned_files', 0)}",
                "",
                "## Module Analysis",
                "| Module | Files | Owner | Coverage | Status |",
                "|--------|-------|-------|----------|--------|"
            ]
            
            # Add module rows
            for module_name, module_data in self.analysis.get("modules", {}).items():
                owner, ownership = self._get_module_owner(module_name)
                coverage = self._get_module_coverage(module_name)
                
                content.append(
                    f"| {module_name} | {module_data.get('file_count', 0)} | "
                    f"{owner} ({ownership:.0f}%) | {coverage['coverage']:.0f}% | "
                    f"{'OK' if not module_data.get('issues') else 'Issues'} |"
                )
            
            # Add dependencies section
            content.extend([
                "",
                "## Dependencies",
                "| Package | Version | Status |",
                "|---------|---------|--------|"
            ])
            
            for pkg, meta in self.dependencies.get("dependencies", {}).items():
                status = "OK"
                if meta.get("outdated"):
                    status = "Outdated"
                elif meta.get("missing"):
                    status = "Missing"
                content.append(f"| {pkg} | {meta.get('version', '?')} | {status} |")
            
            # Write to file
            output_file = episode_dir / "project_snapshot.md"
            output_file.write_text("\n".join(content))
            
            # Show success message
            self.export_button.setText("✓ Exported")
            QTimer.singleShot(2000, lambda: self.export_button.setText("📤 Export to Markdown"))
            
        except Exception as e:
            print(f"Error exporting to markdown: {e}")
            self.export_button.setText("❌ Export Failed")
            QTimer.singleShot(2000, lambda: self.export_button.setText("📤 Export to Markdown"))

    def refresh_data(self):
        """Reload all data sources and refresh the UI"""
        self.context = self._load_json(CONTEXT_FILE)
        self.dependencies = self._load_json(DEPENDENCY_FILE)
        self.analysis = self._load_json(ANALYSIS_FILE)
        self.agent_logs = self._load_agent_logs()
        self.test_coverage = self._load_test_coverage()
        
        self._populate_summary()
        self._populate_dependencies()
        self._populate_modules()
        self.update_metrics()
        
        # Show refresh confirmation
        self.refresh_button.setText("✓ Refreshed")
        QTimer.singleShot(2000, lambda: self.refresh_button.setText("🔄 Refresh Analysis"))

    def update_module_tree(self):
        """Update the module tree with ownership and coverage data"""
        modules = self.analysis.get("modules", {})
        self.modules_tree.clear()
        
        show_ownership = self.ownership_check.isChecked()
        show_coverage = self.coverage_check.isChecked()
        
        for module_name, module_data in modules.items():
            # Get ownership data
            owner, ownership_percent = self._get_module_owner(module_name)
            owner_text = f"{owner} ({ownership_percent:.0f}%)" if show_ownership else ""
            
            # Get coverage data
            coverage = self._get_module_coverage(module_name)
            coverage_text = f"{coverage['coverage']:.0f}%" if show_coverage else ""
            
            # Create tree item
            module_item = QTreeWidgetItem([
                module_name,
                str(module_data.get("file_count", 0)),
                "OK" if not module_data.get("issues") else "Issues",
                owner_text,
                coverage_text
            ])
            
            # Set colors based on ownership and coverage
            if show_ownership:
                agent_color = THEME["light"]["agent_colors"].get(owner, THEME["light"]["default"])
                module_item.setForeground(3, QColor(agent_color))
            
            if show_coverage:
                coverage_color = (
                    THEME["light"]["success"] if coverage["coverage"] >= 80
                    else THEME["light"]["warning"] if coverage["coverage"] >= 50
                    else THEME["light"]["error"]
                )
                module_item.setForeground(4, QColor(coverage_color))
            
            # Add submodules
            for submodule, submodule_data in module_data.get("submodules", {}).items():
                sub_owner, sub_ownership = self._get_module_owner(f"{module_name}.{submodule}")
                sub_owner_text = f"{sub_owner} ({sub_ownership:.0f}%)" if show_ownership else ""
                
                sub_coverage = self._get_module_coverage(f"{module_name}.{submodule}")
                sub_coverage_text = f"{sub_coverage['coverage']:.0f}%" if show_coverage else ""
                
                submodule_item = QTreeWidgetItem([
                    submodule,
                    str(submodule_data.get("file_count", 0)),
                    "OK" if not submodule_data.get("issues") else "Issues",
                    sub_owner_text,
                    sub_coverage_text
                ])
                
                if show_ownership:
                    submodule_item.setForeground(3, QColor(THEME["light"]["agent_colors"].get(sub_owner, THEME["light"]["default"])))
                
                if show_coverage:
                    sub_coverage_color = (
                        THEME["light"]["success"] if sub_coverage["coverage"] >= 80
                        else THEME["light"]["warning"] if sub_coverage["coverage"] >= 50
                        else THEME["light"]["error"]
                    )
                    submodule_item.setForeground(4, QColor(sub_coverage_color))
                
                module_item.addChild(submodule_item)
            
            self.modules_tree.addTopLevelItem(module_item)
        
        self.modules_tree.expandAll()

    def show_module_details(self, item, column):
        """Show detailed information for the selected module"""
        module_name = item.text(0)
        module_data = self.analysis.get("modules", {}).get(module_name, {})
        
        # Get ownership and coverage data
        owner, ownership_percent = self._get_module_owner(module_name)
        coverage = self._get_module_coverage(module_name)
        
        # Build module info
        info_lines = [
            f"Module: {module_name}",
            f"Files: {module_data.get('file_count', 0)}",
            f"Status: {item.text(2)}",
            f"Owner: {owner} ({ownership_percent:.0f}% activity)",
            f"Test Coverage: {coverage['coverage']:.0f}% ({coverage['covered']}/{coverage['lines']} lines)",
            "\nDescription:",
            module_data.get("description", "No description available"),
            "\nDependencies:",
            *[f"- {dep}" for dep in module_data.get("dependencies", [])],
            "\nRecent Changes:",
            *[f"- {change}" for change in module_data.get("recent_changes", [])]
        ]
        self.module_info.setText("\n".join(info_lines))
        
        # Show file list
        files = module_data.get("files", [])
        if files:
            file_lines = ["Files in module:"]
            for file in files:
                status = "✓" if not file.get("issues") else "⚠"
                file_lines.append(f"{status} {file['path']}")
            self.module_files.setText("\n".join(file_lines))
        else:
            self.module_files.setText("No files found in module")
        
        # Show coverage details
        coverage_lines = [
            "Test Coverage Details:",
            f"Overall Coverage: {coverage['coverage']:.0f}%",
            f"Lines Covered: {coverage['covered']}",
            f"Total Lines: {coverage['lines']}",
            "\nTest Status:",
            *[f"- {test}" for test in module_data.get("test_status", [])]
        ]
        self.coverage_info.setText("\n".join(coverage_lines))

# ------------------- MAIN -------------------

class AgentDashboard(QMainWindow):
    """Main dashboard window for agent monitoring and control"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Agent Dashboard")
        self.setGeometry(100, 100, 1200, 800)
        
        # Load configuration
        config_path = Path("apps/dashboard/config.json")
        if config_path.exists():
            with open(config_path) as f:
                self.config = json.load(f)
        else:
            self.config = {
                "theme": "dark",
                "refresh_interval": 5000,
                "window": {
                    "width": 1200,
                    "height": 800
                }
            }
        
        # Initialize notifier
        self.notifier = Notifier(Path("runtime/config/notifier_config.json"))
        
        # Set up agent inbox base and THEA handler
        self.inbox_base = INBOX_BASE
        self.thea_handler = THEAHandler(self.inbox_base)
        
        # Setup UI
        self.setup_ui()
        
        # Start refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_timer.start(self.config.get("refresh_interval", 5000))
        
        # Initial data load
        self.refresh_data()
        
    def setup_ui(self):
        """Setup main dashboard UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Add Ping Agents button
        controls_layout = QHBoxLayout()
        self.ping_button = QPushButton("Ping Agents")
        self.ping_button.clicked.connect(self.ping_agents)
        controls_layout.addWidget(self.ping_button)
        controls_layout.addStretch()
        layout.addLayout(controls_layout)

        self.tab_widget = QTabWidget()
        self.agent_tabs = {}
        if self.inbox_base.exists():
            for agent_dir in self.inbox_base.iterdir():
                if agent_dir.is_dir() and agent_dir.name != "THEA":
                    agent_tab = AgentTab(agent_dir.name, self.inbox_base, self.thea_handler)
                    self.agent_tabs[agent_dir.name] = agent_tab
                    self.tab_widget.addTab(agent_tab, agent_dir.name)
        self.metrics_tab = EpisodeMetricsTab()
        self.tab_widget.addTab(self.metrics_tab, "Episode Metrics")
        layout.addWidget(self.tab_widget)
        self.apply_theme()

    def apply_theme(self):
        """Apply theme settings"""
        if self.config.get("theme") == "dark":
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
                QTabWidget::pane {
                    border: 1px solid #3d3d3d;
                    background-color: #2b2b2b;
                }
                QTabBar::tab {
                    background-color: #3d3d3d;
                    color: #ffffff;
                    padding: 8px 16px;
                    border: 1px solid #4d4d4d;
                }
                QTabBar::tab:selected {
                    background-color: #4d4d4d;
                }
                QGroupBox {
                    border: 1px solid #3d3d3d;
                    margin-top: 1em;
                    color: #ffffff;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 3px 0 3px;
                }
                QLabel {
                    color: #ffffff;
                }
                QPushButton {
                    background-color: #4d4d4d;
                    color: #ffffff;
                    border: 1px solid #5d5d5d;
                    padding: 5px 15px;
                }
                QPushButton:hover {
                    background-color: #5d5d5d;
                }
                QTextEdit {
                    background-color: #3d3d3d;
                    color: #ffffff;
                    border: 1px solid #4d4d4d;
                }
            """)
        
    def refresh_data(self):
        """Refresh all dashboard data"""
        try:
            # Refresh agent tab
            for agent_tab in self.tab_widget.findChildren(AgentTab):
                agent_tab.refresh_content()
            
            # Refresh metrics tab
            self.metrics_tab.refresh_metrics()
            
        except Exception as e:
            print(f"Error refreshing dashboard: {e}")
            QMessageBox.warning(
                self,
                "Refresh Error",
                f"Error refreshing dashboard data: {str(e)}"
            )
            
    def closeEvent(self, event):
        """Clean up resources when window is closed"""
        try:
            # Stop refresh timer
            self.refresh_timer.stop()
            
            # Close notifier
            if self.notifier.session:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.notifier.close())
                else:
                    loop.run_until_complete(self.notifier.close())
                    
        except Exception as e:
            print(f"Error during cleanup: {e}")
            
        super().closeEvent(event)

    def ping_agents(self):
        """Ping all agents and update their status in the tab label."""
        for idx in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(idx)
            # Only ping AgentTabs (not metrics tab)
            if isinstance(widget, AgentTab):
                agent_id = widget.agent_id
                status_file = self.inbox_base / agent_id / "status.json"
                status = "Offline"
                if status_file.exists():
                    try:
                        with open(status_file, 'r') as f:
                            data = json.load(f)
                        # Consider agent online if status is present and recent (within 60s)
                        last_ping = data.get("last_ping", 0)
                        if time.time() - last_ping < 60:
                            status = "Online"
                        else:
                            status = "Unresponsive"
                    except Exception:
                        status = "Unresponsive"
                self.tab_widget.setTabText(idx, f"{agent_id} [{status}]")

def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle("Fusion")
    
    # Create and show dashboard
    dashboard = AgentDashboard()
    dashboard.show()
    
    # Run event loop
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 