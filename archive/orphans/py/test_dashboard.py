import json
import os
import sys
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_dashboard import AgentDashboard
from modules.task_manager import load_inbox, load_status


class TestDashboard:
    def setup_method(self):
        """Setup test environment"""
        self.app = QApplication(sys.argv)
        self.inbox_base = Path("runtime/agent_comms/agent_mailboxes")
        self.inbox_base.mkdir(parents=True, exist_ok=True)

        # Create test agent directory
        self.test_agent = "Agent-Test"
        agent_dir = self.inbox_base / self.test_agent
        agent_dir.mkdir(exist_ok=True)

        # Create test files
        self.create_test_files(agent_dir)

        # Initialize dashboard
        self.dashboard = AgentDashboard()

    def create_test_files(self, agent_dir: Path):
        """Create test mailbox files"""
        # Create inbox.json
        inbox_data = [
            {
                "id": "TEST-001",
                "type": "instruction",
                "content": "Test task content",
                "status": "pending",
                "timestamp": "2024-03-10T12:00:00Z",
            }
        ]
        (agent_dir / "inbox.json").write_text(json.dumps(inbox_data, indent=2))

        # Create status.json
        status_data = {"status": "active", "last_updated": "2024-03-10T12:00:00Z"}
        (agent_dir / "status.json").write_text(json.dumps(status_data, indent=2))

        # Create devlog.json
        devlog_data = "# Test Devlog\n\nTest entry"
        (agent_dir / "devlog.json").write_text(devlog_data)

    def test_dashboard_initialization(self):
        """Test dashboard initializes correctly"""
        assert self.dashboard is not None
        assert self.dashboard.windowTitle() == "Agent Dashboard"

    def test_agent_list_population(self):
        """Test agent list is populated"""
        self.dashboard.load_agents()
        assert self.dashboard.agent_list.count() > 0
        assert self.dashboard.agent_list.item(0).text() == self.test_agent

    def test_agent_details_display(self):
        """Test agent details are displayed correctly"""
        # Select test agent
        self.dashboard.load_agents()
        self.dashboard.agent_list.setCurrentRow(0)

        # Check status table
        status = load_status(self.test_agent, self.inbox_base)
        assert self.dashboard.status_table.rowCount() == len(status)

        # Check tab creation
        assert self.dashboard.tab_widget.count() > 0
        assert self.dashboard.tab_widget.tabText(0) == self.test_agent

    def test_task_actions(self):
        """Test task actions (complete, requeue, escalate)"""
        # Select test agent
        self.dashboard.load_agents()
        self.dashboard.agent_list.setCurrentRow(0)

        # Get agent tab
        agent_tab = self.dashboard.tab_widget.widget(0)

        # Test task completion
        agent_tab.current_task = {
            "id": "TEST-001",
            "type": "instruction",
            "content": "Test task",
        }
        agent_tab.show_context_menu(
            agent_tab.inbox_display.mapToGlobal(Qt.QPoint(0, 0))
        )

        # Verify task status update
        inbox = load_inbox(self.test_agent, self.inbox_base)
        assert any(
            msg.get("id") == "TEST-001" and msg.get("status") == "completed"
            for msg in inbox
        )

    def teardown_method(self):
        """Cleanup test environment"""
        # Remove test files
        agent_dir = self.inbox_base / self.test_agent
        if agent_dir.exists():
            for file in agent_dir.glob("*"):
                file.unlink()
            agent_dir.rmdir()

        # Clean up dashboard
        self.dashboard.close()
        self.app.quit()


if __name__ == "__main__":
    # Run tests
    test = TestDashboard()
    test.setup_method()

    try:
        test.test_dashboard_initialization()
        test.test_agent_list_population()
        test.test_agent_details_display()
        test.test_task_actions()
        print("All tests passed!")
    except AssertionError as e:
        print(f"Test failed: {e}")
    finally:
        test.teardown_method()
