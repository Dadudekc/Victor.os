import asyncio  # {{ EDIT: Ensure asyncio is imported }}
import json
import logging
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import QSize, Qt, QTimer
from PyQt5.QtGui import QColor, QIcon
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListView,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

# {{ EDIT END }}
from dreamos.coordination.agent_bus import AgentBus
from dreamos.core.coordination.event_types import AgentStatus, CoreEvents
from dreamos.core.health_checks.cursor_status_check import (
    CURSOR_ORCHESTRATOR_AVAILABLE,
    check_cursor_agent_statuses,
)

# {{ EDIT START: Import health checks }}
from dreamos.core.health_checks.cursor_window_check import (
    check_cursor_window_reachability,
)

# {{ EDIT END }}
# {{ EDIT START: Import HealthMonitor }}
from dreamos.core.health_monitor import HealthMonitor
from dreamos.hooks.chronicle_logger import ChronicleLoggerHook

# Import backend components
from dreamos.memory.memory_manager import UnifiedMemoryManager
from dreamos.rendering.template_engine import TemplateEngine

from ..dashboard.system_stats import StatsLoggingHook

# Import the new Forge Tab
from .fragment_forge_tab import FragmentForgeTab

# Commented out problematic import
# from dreamos.services.event_logger import log_structured_event


logger = logging.getLogger(__name__)

# Define path to task list
TASK_LIST_PATH = Path(__file__).parent.parent / "task_list.json"

# Determine project root for structured events logging
UI_DIR = Path(__file__).parent
PROJECT_ROOT = UI_DIR.parent


# Placeholder for Task Manager logic
class DummyTaskManager:
    def add_task(self, task):
        logger.info(f"[DummyTaskManager] Task added: {task.get('name')}")
        pass  # In a real implementation, add to internal list/db


# Define TaskManager subclass for compatibility with tests
class TaskManager(DummyTaskManager):
    """Alias for DummyTaskManager for testing compatibility."""

    pass


# Placeholder FeedbackEngine for event handling (used in tests)
class FeedbackEngine:
    """Placeholder for feedback engine in tests."""

    pass


# Manager for application tabs
class DreamOSTabManager(QTabWidget):
    """Placeholder for tab manager in tests."""

    pass


# Placeholder for tab system shutdown (used in tests)
class TabSystemShutdownManager:
    """Placeholder for tab system shutdown in tests."""

    pass


class DreamOSMainWindow(QMainWindow):
    """Main application window for Dream.OS using Sidebar Navigation."""

    def __init__(self, parent=None):
        super().__init__(parent)
        logger.info("Initializing DreamOSMainWindow GUI with Sidebar Navigation...")
        self.setWindowTitle("Dream.OS")
        self.setGeometry(100, 100, 1200, 800)  # Default size

        # --- Instantiate Core Backend Components ---
        self.memory_manager = UnifiedMemoryManager()
        self.template_engine = TemplateEngine()
        self.task_manager = TaskManager()
        self.chronicle_logger_hook = ChronicleLoggerHook()
        # Tab manager for state persistence
        self.tab_manager = DreamOSTabManager()

        # --- Core Components (Placeholders/Basic Implementation) ---
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        # --- Main Layout: Sidebar + Content Stack ---
        self.main_h_layout = QHBoxLayout(self.central_widget)
        self.main_h_layout.setSpacing(0)  # No space between sidebar and content
        self.main_h_layout.setContentsMargins(0, 0, 0, 0)

        # --- Sidebar ---
        self.sidebar = QListWidget()
        self.sidebar.setViewMode(QListView.IconMode)  # Use IconMode for better visuals
        self.sidebar.setMovement(QListView.Static)  # Prevent item dragging
        self.sidebar.setMaximumWidth(120)  # Set a max width for the sidebar
        self.sidebar.setSpacing(10)
        self.sidebar.setIconSize(QSize(48, 48))  # Example icon size
        # Basic styling (can be enhanced with stylesheets)
        self.sidebar.setStyleSheet(
            """
            QListWidget {
                background-color: #f0f0f0;
                border-right: 1px solid #d0d0d0;
            }
            QListWidget::item {
                padding: 10px;
                margin: 2px;
                border-radius: 4px; /* Rounded corners */
            }
            QListWidget::item:selected {
                background-color: #cce5ff; /* Light blue for selection */
                color: black;
                border: 1px solid #99cfff;
            }
            QListWidget::item:hover {
                background-color: #e6e6e6;
            }
        """
        )
        self.main_h_layout.addWidget(self.sidebar)

        # --- Content Stack ---
        self.content_stack = QStackedWidget()
        self.main_h_layout.addWidget(self.content_stack)

        # --- Status Bar ---
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Dream.OS Initialized.")

        # --- Populate Sidebar and Content Stack ---
        self._create_navigation()

        # Connect sidebar selection to stack change
        self.sidebar.currentRowChanged.connect(self.content_stack.setCurrentIndex)

        # Select the first item by default
        self.sidebar.setCurrentRow(0)

        logger.info("DreamOSMainWindow GUI Initialized.")

        # --- Background Initialization and Health Checks ---
        # {{ EDIT START: Schedule async bootstrap checks }}
        QTimer.singleShot(0, self._run_async_bootstrap)
        # {{ EDIT END }}

        # --- Subscribe to prompt success/failure/escalation events ---
        self.agent_counters = {}  # initialize per-agent metrics including escalation
        import asyncio

        from dreamos.coordination.agent_bus import AgentBus
        from dreamos.coordination.dispatcher import EventType

        self._agent_bus = AgentBus()

        # Async handler for system events
        async def _on_prompt_event(evt):
            etype = evt.data.get("type")
            agent_id = evt.data.get("agent_id", evt.source_id)
            # ensure counters exist
            if agent_id not in self.agent_counters:
                self.agent_counters[agent_id] = {
                    "success": 0,
                    "failure": 0,
                    "escalation": 0,
                }
            # handle event types
            if etype == "prompt_success":
                self.agent_counters[agent_id]["success"] += 1
                self.status_bar.showMessage(f"✅ Prompt success: {agent_id}", 3000)
            elif etype == "prompt_failure":
                self.agent_counters[agent_id]["failure"] += 1
                self.status_bar.showMessage(f"❌ Prompt failure: {agent_id}", 3000)
            elif etype == "ESCALATION":
                # record escalation event
                self.agent_counters[agent_id]["escalation"] += 1
                # EDIT START: store timestamp of last escalation
                self.agent_counters[agent_id][
                    "last_escalation"
                ] = datetime.now().timestamp()
                # EDIT END
                self.status_bar.showMessage(f"⚠️ Escalation: {agent_id}", 3000)
            # refresh UI lists
            self._update_agents_list()
            self._update_escalated_agents_list()
            # flash the escalated agent briefly
            if etype == "ESCALATION":
                for i in range(self.agents_list.count()):
                    item = self.agents_list.item(i)
                    if item.data(Qt.UserRole) == agent_id:
                        item.setBackground(QColor("yellow"))
                        break
                QTimer.singleShot(1000, self._update_agents_list)
            # persist dashboard state
            try:
                out_dir = Path("runtime/logs")
                out_dir.mkdir(parents=True, exist_ok=True)
                with open(out_dir / "dashboard_state.json", "w", encoding="utf-8") as f:
                    json.dump(self.agent_counters, f, indent=2)
            except Exception:
                pass

        # EDIT START: defer AgentBus subscription until Qt event loop is running
        def _subscribe_prompt_event():
            try:
                asyncio.create_task(
                    self._agent_bus.register_handler(EventType.SYSTEM, _on_prompt_event)
                )
            except Exception as e:
                logger.error(f"Failed to subscribe to prompt events: {e}")

        QTimer.singleShot(0, _subscribe_prompt_event)
        # EDIT END
        # Initialize the Escalated Agents view
        self._update_escalated_agents_list()

    # {{ EDIT START: Update async bootstrap to use HealthMonitor }}
    def _run_async_bootstrap(self):
        """Runs asynchronous initialization tasks like health checks after event loop starts."""

        async def bootstrap_tasks():
            logger.info("Running async bootstrap health checks via HealthMonitor...")
            all_systems_go = True

            try:
                # --- Run All Health Checks via Monitor ---
                monitor = HealthMonitor()
                health_report = await monitor.run_all_checks()
                overall_status = health_report["overall_status"]

                # --- Process Aggregated Results ---
                logger.info(f"Aggregated System Health Status: {overall_status}")

                if overall_status == "PASS":
                    self.status_bar.showMessage("System Health: OK", 5000)
                elif overall_status == "WARN":
                    self.status_bar.showMessage(
                        "⚠️ System Health: Warnings Detected", 10000
                    )
                    # Log details for warnings
                    for check_result in health_report["results"]:
                        if check_result["status"] == "WARN":
                            logger.warning(
                                f"Health Check Warning: {check_result['check_name']} - Details: {check_result.get('details')}"
                            )
                    # Optionally show a non-critical message box
                    # QMessageBox.warning(self, "Bootstrap Warning", "System health checks reported warnings. Check logs for details.")
                    all_systems_go = False  # Treat warnings as potentially blocking for full readiness?
                elif overall_status == "FAIL" or overall_status == "ERROR":
                    self.status_bar.showMessage(
                        "❌ System Health: Critical Failures Detected!", 0
                    )  # Persistent
                    all_systems_go = False
                    # Log detailed results for failures/errors
                    for check_result in health_report["results"]:
                        if check_result["status"] in ["FAIL", "ERROR"]:
                            logger.error(
                                f"Health Check Failed: {check_result['check_name']} - Status: {check_result['status']} - Details: {check_result.get('details')}"
                            )
                    # Show critical error message
                    QMessageBox.critical(
                        self,
                        "System Health Failure",
                        "Critical health checks failed. System may be unstable. Check logs.",
                    )
                    # Consider preventing full startup or entering a degraded mode

            except Exception as e:
                logger.exception(f"Error during HealthMonitor execution: {e}")
                self.status_bar.showMessage("❌ System Health: Error during checks!", 0)
                QMessageBox.critical(
                    self,
                    "Bootstrap Error",
                    "An unexpected error occurred during system health checks. Check logs.",
                )
                all_systems_go = False

            # --- Final Logging ---
            if all_systems_go:
                logger.info("All async bootstrap health checks passed.")
            else:
                logger.error(
                    "One or more bootstrap health checks failed or reported warnings."
                )

        # Execute the async function (logic remains the same)
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            asyncio.create_task(bootstrap_tasks())
        else:
            loop.run_until_complete(bootstrap_tasks())

    # {{ EDIT END }}

    def _create_navigation(self):
        """Creates sidebar items and corresponding content widgets."""
        # 1. Dashboard (Placeholder)
        dashboard_widget = QWidget()
        dash_layout = QVBoxLayout(dashboard_widget)
        dash_layout.addWidget(QLabel("Welcome to Dream.OS - Dashboard"))
        dash_layout.setAlignment(Qt.AlignCenter)
        self.add_navigation_item(
            "Dashboard", "icons/dashboard.png", dashboard_widget
        )  # Assumes icon path

        # 2. Fragment Forge (Pass backend instances)
        forge_widget = FragmentForgeTab(  # Pass instances
            memory_manager=self.memory_manager,
            template_engine=self.template_engine,
            parent=self,
        )
        self.add_navigation_item("Forge", "icons/forge.png", forge_widget)

        # 3. Agents (with counters)
        self.agents_widget = QWidget()
        agents_layout = QVBoxLayout(self.agents_widget)
        self.agents_list = QListWidget()
        agents_layout.addWidget(self.agents_list)
        self.add_navigation_item("Agents", "icons/agents.png", self.agents_widget)

        # 4. Tasks (Placeholder)
        tasks_widget = QWidget()
        tasks_layout = QVBoxLayout(tasks_widget)
        tasks_layout.addWidget(QLabel("Task Management"))
        tasks_layout.setAlignment(Qt.AlignCenter)
        self.add_navigation_item("Tasks", "icons/tasks.png", tasks_widget)

        # 5. Escalated Agents (new view)
        escalated_widget = QWidget()
        escalated_layout = QVBoxLayout(escalated_widget)
        self.escalated_list = QListWidget()
        escalated_layout.addWidget(QLabel("Agents with active escalations:"))
        escalated_layout.addWidget(self.escalated_list)
        self.add_navigation_item(
            "Escalated Agents", "icons/escalation.png", escalated_widget
        )
        logger.debug("Navigation structure created.")

    def add_navigation_item(self, text: str, icon_path: str, widget: QWidget):
        """Adds an item to the sidebar and its corresponding widget to the stack."""
        item = QListWidgetItem(self.sidebar)
        # Try loading icon, fallback to text only if fails
        icon = QIcon(icon_path)
        if not icon.isNull():
            item.setIcon(icon)
        else:
            logger.warning(f"Icon not found or invalid: {icon_path}")
            # Consider adding placeholder icon

        item.setText(text)
        item.setTextAlignment(Qt.AlignCenter)
        item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        # item.setSizeHint(QSize(100, 70)) # Adjust size hint if needed

        self.content_stack.addWidget(widget)
        logger.debug(f"Added navigation item: '{text}'")

    # --- Methods called by main.py test mode (Enhanced Stubs) ---

    def get_sidebar_items(self) -> list:
        """Returns names of the sidebar items."""
        names = [self.sidebar.item(i).text() for i in range(self.sidebar.count())]
        logger.debug(f"Returning sidebar item names: {names}")
        return names

    def log_event(self, event_name: str, event_data: dict):
        """Logs an event locally and using the core structured event logger."""
        logger.info(f"[Stub] Event logged locally: {event_name} - Data: {event_data}")
        # Log using the core service (Commented out)
        # log_structured_event(
        #     event_type=f"GUI_{event_name}",
        #     data=event_data,
        #     source="DreamOSMainWindow"
        # )
        # Simulate notifying mailbox (as seen in main.py test)
        self.notify_mailbox(event_name, event_data)

    def notify_mailbox(self, event_name: str, event_data: dict):
        """Placeholder for sending notification to agent mailbox."""
        log_info = {
            "event_name": event_name,
            "event_data_keys": list(event_data.keys()),
        }
        logger.info(
            f"[Stub] Sending notification to Agent Mailbox: Event '{event_name}' occurred."
        )
        # Log using the core service (Commented out)
        # log_structured_event("GUI_MAILBOX_NOTIFY_SENT", log_info, "DreamOSMainWindow")
        # Simulate syncing with board (as seen in main.py test)
        self.sync_event_with_board("mailbox_update", {"event": event_name})

    def sync_event_with_board(self, sync_type: str, data: dict):
        """Placeholder for syncing event/task/state with a central board.
        Enhanced to append test task to task_list.json when sync_type is 'task_add'.
        """
        log_info = {"sync_type": sync_type, "data_keys": list(data.keys())}
        logger.info(
            f"[Stub] Syncing '{sync_type}' with Central Agent Board. Data: {data}"
        )
        # Handle state_save events with validation and atomic writing
        if sync_type == "state_save":
            # Enforce schema: 'status' must be present
            if not isinstance(data, dict) or "status" not in data:
                logger.error(
                    "sync_event_with_board: 'state_save' missing required 'status' field"
                )
                # Fallback: reload last known good state and alert recovery flow
                logger.info("sync_event_with_board: triggering fallback reload")
                try:
                    self.load_state_fallback()
                except Exception as e:
                    logger.error(f"Error during fallback load: {e}")
                # Alert recovery downstream
                self.notify_mailbox(
                    "state_recovery_needed", {"reason": "missing status"}
                )
                return
            # Atomic append to structured_events.jsonl
            try:
                structured_file = PROJECT_ROOT / "runtime" / "structured_events.jsonl"
                tmp_file = structured_file.with_suffix(".tmp")
                record = {
                    "id": uuid.uuid4().hex,
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "GUI_STATE_SAVE",
                    "source": "DreamOSMainWindow",
                    "data": data,
                }
                # Preserve existing lines
                existing = []
                if structured_file.exists():
                    existing = structured_file.read_text(encoding="utf-8").splitlines(
                        keepends=True
                    )
                with open(tmp_file, "w", encoding="utf-8") as f:
                    for line in existing:
                        f.write(line)
                    f.write(json.dumps(record) + "\n")
                os.replace(str(tmp_file), str(structured_file))
                logger.info("sync_event_with_board: state_save event logged atomically")
            except Exception as e:
                logger.error(
                    f"sync_event_with_board: failed to write state_save event: {e}",
                    exc_info=True,
                )
            return

        # If this is the task add sync, append to task_list.json
        if sync_type == "task_add" and isinstance(data, dict) and "id" in data:
            self._append_task_to_list(data)

    def save_state(self):
        """Placeholder for saving application/agent state."""
        logger.info("[Stub] Saving local agent/application state...")
        # Simulate syncing state with board, ensure status is passed
        state_data = {"status": "saved"}
        self.sync_event_with_board("state_save", state_data)

    def _append_task_to_list(self, task_data: dict):
        """Appends a task dictionary to the task_list.json file."""
        logger.info(
            f"Attempting to append task {task_data.get('id')} to {TASK_LIST_PATH}"
        )
        try:
            tasks = []
            if TASK_LIST_PATH.exists():
                try:
                    with open(TASK_LIST_PATH, "r", encoding="utf-8") as f:
                        content = f.read()
                        if content.strip():
                            tasks = json.loads(content)
                        if not isinstance(tasks, list):
                            logger.warning(
                                f"Task list file {TASK_LIST_PATH} does not contain a valid list. Resetting."
                            )
                            tasks = []
                except json.JSONDecodeError:
                    logger.error(
                        f"Failed to decode existing task list {TASK_LIST_PATH}. Resetting."
                    )
                    tasks = []

            tasks.append(task_data)

            with open(TASK_LIST_PATH, "w", encoding="utf-8") as f:
                json.dump(tasks, f, indent=2)  # Write back with indentation
            logger.info(
                f"Successfully appended task {task_data.get('id')} to {TASK_LIST_PATH}"
            )
            # Log using the core service (Commented out)
            # log_structured_event("GUI_TASK_APPENDED", {"task_id": task_data.get('id')}, "DreamOSMainWindow")
        except Exception as e:
            logger.error(
                f"Failed to append task to {TASK_LIST_PATH}: {e}", exc_info=True
            )
            # Log using the core service (Commented out)
            # log_structured_event("GUI_TASK_APPEND_FAILED", {"task_id": task_data.get('id'), "error": str(e)}, "DreamOSMainWindow")

    def load_state_fallback(self):
        """
        Fallback routine to reload the last known good state.
        """
        logger.warning(
            "load_state_fallback: reloading last known good state (not implemented)"
        )
        # TODO: integrate with core state loader or recovery agent flow
        pass

    # --- Window Management ---

    def closeEvent(self, event):
        """Handle window close event."""
        logger.info("Close event triggered. Cleaning up...")
        # Add any necessary cleanup here (e.g., stopping threads, saving final state)
        self.cleanup_resources()
        super().closeEvent(event)

    def cleanup_resources(self):
        """Clean up resources like timers, threads, file handlers."""
        logger.info("Cleaning up main window resources...")
        # Example: Stop timers
        # if hasattr(self, 'refresh_timer') and self.refresh_timer.isActive():
        #     self.refresh_timer.stop()

        if hasattr(self, "chronicle_logger_hook"):
            self.chronicle_logger_hook.stop()

        logger.info("Main window resources cleaned up.")

    def _save_state(self):
        """Saves the state of each tab to the state file."""
        import json

        states = {}
        for name, widget in getattr(self.tab_manager, "_tabs", {}).items():
            if hasattr(widget, "get_state"):
                states[name] = widget.get_state()
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(states, f)
        except Exception as e:
            logger.error(
                f"Failed to save state to {self.state_file}: {e}", exc_info=True
            )

    def _load_state(self):
        """Loads and restores state from the state file for each tab."""
        import json
        from pathlib import Path

        if not hasattr(self, "state_file") or not Path(self.state_file).exists():
            return
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            QMessageBox.warning(self, "Load State", "Failed to load state file.")
            return
        count = 0
        for name, state in data.items():
            widget = self.tab_manager.get_tab_by_name(name)
            if widget and hasattr(widget, "restore_state"):
                widget.restore_state(state)
                count += 1
        self.statusBar().showMessage(f"Restored state for {count} tabs.", 5000)

    def _update_agents_list(self):
        """Refresh the Agents list view based on current counters."""
        self.agents_list.clear()
        threshold = 5  # failures threshold for highlight
        for aid, stats in self.agent_counters.items():
            succ = stats.get("success", 0)
            fail = stats.get("failure", 0)
            esc = stats.get("escalation", 0)
            total = succ + fail
            rate = (fail / total * 100) if total else 0
            # Build display text with optional escalation icon
            prefix = "⚠️ " if esc > 0 else ""
            text = f"{prefix}{aid} | ✅ {succ} / ❌ {fail}"
            item = QListWidgetItem(text)
            # Highlight agents with high failures or rate
            if fail >= threshold:
                item.setBackground(QColor("red"))
            elif rate >= threshold:
                item.setBackground(QColor("yellow"))
            # Build tooltip with failure rate and escalation count
            tooltip = f"Failure rate: {rate:.1f}%"
            if esc > 0:
                tooltip += f"; Escalations: {esc}"
            item.setToolTip(tooltip)
            item.setData(Qt.UserRole, aid)
            self.agents_list.addItem(item)

    def _update_escalated_agents_list(self):
        """Refresh the Escalated Agents list view, showing agents with escalation > 0."""
        try:
            self.escalated_list.clear()
            for agent_id, stats in self.agent_counters.items():
                esc = stats.get("escalation", 0)
                if esc > 0:
                    text = f"{agent_id}: {esc}"
                    # Include last escalation timestamp if available
                    last_ts = stats.get("last_escalation")
                    if last_ts:
                        ts_str = datetime.fromtimestamp(last_ts).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )
                        text += f" (last: {ts_str})"
                    item = QListWidgetItem(text)
                    self.escalated_list.addItem(item)
        except Exception as e:
            logger.error(f"Failed to update escalated agents list: {e}")
        finally:
            # Auto-hide the Escalated Agents tab if no items
            try:
                # Find sidebar item by text
                for i in range(self.sidebar.count()):
                    it = self.sidebar.item(i)
                    if it.text() == "Escalated Agents":
                        it.setHidden(self.escalated_list.count() == 0)
                        break
            except Exception:
                pass


# Example of running this window directly (for testing)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = QApplication(sys.argv)
    main_window = DreamOSMainWindow()
    main_window.show()
    sys.exit(app.exec_())
