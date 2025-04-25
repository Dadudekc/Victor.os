import os
import sys
import json
import uuid
from datetime import datetime

import pyautogui
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QSplitter, QWidget,
    QVBoxLayout, QTableWidget, QTableWidgetItem, QTabWidget,
    QComboBox, QTextEdit, QPushButton, QShortcut, QLabel,
    QLineEdit, QAbstractItemView, QInputDialog, QMessageBox,
    QCheckBox
)
from PyQt5.QtGui import QKeySequence, QColor
from PyQt5.QtCore import Qt, QTimer

try:
    from pynput.mouse import Listener
    _USE_LISTENER = True
except ImportError:
    _USE_LISTENER = False

try:
    from dream_os.services.task_nexus import add_task, get_all_tasks, claim_task
except ImportError:
    # Fallback stubs
    def add_task(task_type: str, content: str) -> str:
        return uuid.uuid4().hex
    def get_all_tasks() -> list:
        return []
    def claim_task(agent_id: str) -> bool:
        return False

try:
    from core.coordination.agent_bus import AgentBus
except ImportError:
    AgentBus = None

try:
    from core.hooks.chatgpt_responder import ChatGPTResponder
except ImportError:
    ChatGPTResponder = None

from core.agent_utils import save_agent_spot, _load_coords, click_agent_spot


class DashboardWindow(QMainWindow):
    """Main dashboard for Dream.OS agents, tasks, mailboxes, etc."""
    REFRESH_MS = 5000

    def __init__(self):
        super().__init__()
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.setWindowTitle("Dream.OS Agent Dashboard")
        self.resize(1200, 800)

        # Central splitter and tabs
        splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(splitter)
        self.tabs = QTabWidget()
        splitter.addWidget(self.tabs)

        # Setup all tabs
        self._setup_tasks_tab()
        self._setup_mailboxes_tab()
        self._setup_agents_tab()
        self._setup_comm_tab()

        # Load saved agent coordinates into the Agents table
        self.refresh_agents_table()

        # AgentBus, if available
        self.agent_bus = AgentBus() if AgentBus else None
        # Auto-response mode using ChatGPTResponder hook
        self.auto_mode_enabled = True
        self.responder = ChatGPTResponder(dev_mode=True)
        # Auto-click UI spot upon task claim
        self.auto_click_on_claim = True

        # Auto-refresh
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_all)
        self.timer.start(self.REFRESH_MS)

        # Shortcuts
        QShortcut(QKeySequence("Ctrl+Return"), self).activated.connect(self._on_accept)
        QShortcut(QKeySequence("Ctrl+Backspace"), self).activated.connect(self._on_reject)
        QShortcut(QKeySequence("Ctrl+Shift+S"), self).activated.connect(self.capture_spot)

    # ────────────────────────────────────────────────────────────────────────
    # Tab setup methods
    # ────────────────────────────────────────────────────────────────────────
    def _setup_tasks_tab(self):
        w = QWidget(); layout = QVBoxLayout(w)
        self.task_table = QTableWidget()
        layout.addWidget(QLabel("Live Task Queue"))
        layout.addWidget(self.task_table)

        # injection form
        row = QWidget(); h = QVBoxLayout(row)
        self.task_type = QComboBox(); self.task_type.addItems(["plan", "code", "social"])
        self.task_input = QLineEdit(); self.task_input.setPlaceholderText("Task description…")
        inject = QPushButton("Inject Task"); inject.clicked.connect(self.inject_task)
        form = QSplitter(Qt.Horizontal)
        form.addWidget(self.task_type); form.addWidget(self.task_input); form.addWidget(inject)
        layout.addWidget(form)

        # claim button
        claim = QPushButton("Claim Next Task"); claim.clicked.connect(self.claim_next_task)
        layout.addWidget(claim)

        self.tabs.addTab(w, "Tasks")

    def _setup_mailboxes_tab(self):
        w = QWidget(); layout = QVBoxLayout(w)
        # Dev/Prod toggle for ChatGPTResponder
        self.dev_toggle = QCheckBox("Dev Mode", w)
        self.dev_toggle.setChecked(self.responder.dev_mode)
        self.dev_toggle.stateChanged.connect(self._toggle_dev_mode)
        layout.addWidget(self.dev_toggle)
        self.mailbox_table = QTableWidget(); self.msg_view = QTextEdit(); self.msg_view.setReadOnly(True)
        self.mailbox_table.itemSelectionChanged.connect(self.update_messages)
        layout.addWidget(QLabel("Shared Mailboxes"))
        layout.addWidget(self.mailbox_table)
        layout.addWidget(QLabel("Messages"))
        layout.addWidget(self.msg_view)
        self.tabs.addTab(w, "Mailboxes")

    def _setup_agents_tab(self):
        w = QWidget(); layout = QVBoxLayout(w)
        self.agent_table = QTableWidget()
        self.agent_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.agent_table.setSelectionMode(QAbstractItemView.SingleSelection)
        layout.addWidget(QLabel("Agent Coordinates"))
        layout.addWidget(self.agent_table)
        self.tabs.addTab(w, "Agents")

    def _setup_comm_tab(self):
        w = QWidget(); layout = QVBoxLayout(w)
        self.comm_table = QTableWidget()
        layout.addWidget(QLabel("Inter-Agent Communication"))
        layout.addWidget(self.comm_table)
        self.tabs.addTab(w, "Comm")

    # ────────────────────────────────────────────────────────────────────────
    # Refresh / load routines
    # ────────────────────────────────────────────────────────────────────────
    def refresh_all(self):
        self._load_tasks()
        self._load_mailboxes()
        # Future: self._load_agents(), self._load_comm()

    def _load_tasks(self):
        tasks = get_all_tasks()
        self.task_table.clear()
        self.task_table.setColumnCount(4)
        self.task_table.setHorizontalHeaderLabels(["ID","Type","Status","Content"])
        self.task_table.setRowCount(len(tasks))
        for i, t in enumerate(tasks):
            self.task_table.setItem(i, 0, QTableWidgetItem(t.get("id","")[:8]))
            self.task_table.setItem(i, 1, QTableWidgetItem(t.get("type","")))
            self.task_table.setItem(i, 2, QTableWidgetItem(t.get("status","queued")))
            self.task_table.setItem(i, 3, QTableWidgetItem(t.get("content","")))
        self.task_table.resizeColumnsToContents()

    def _load_mailboxes(self):
        path = os.path.join(self.base_dir, "_agent_coordination", "shared_mailboxes")
        files = sorted([f for f in os.listdir(path) if f.startswith("mailbox_") and f.endswith(".json")])
        boxes = []
        for fn in files:
            mailbox_path = os.path.join(path, fn)
            try:
                data = json.load(open(mailbox_path))
            except:
                continue
            # Auto-respond with ChatGPTResponder if enabled and not yet replied
            if self.auto_mode_enabled and 'ChatGPTResponder' not in [m.get('sender','') for m in data.get('messages', [])]:
                updated = self.responder.respond_to_mailbox(data)
                # Persist the updated mailbox
                with open(mailbox_path, 'w', encoding='utf-8') as f:
                    json.dump(updated, f, indent=2)
                data = updated
            boxes.append((fn, data))
        self.mailboxes = boxes
        self.mailbox_table.clear()
        self.mailbox_table.setColumnCount(4)
        self.mailbox_table.setHorizontalHeaderLabels(["Mailbox","Status","Owner","#Msgs"])
        self.mailbox_table.setRowCount(len(boxes))
        for i, (fn, m) in enumerate(boxes):
            self.mailbox_table.setItem(i,0, QTableWidgetItem(fn))
            self.mailbox_table.setItem(i,1, QTableWidgetItem(m.get("status","")))
            self.mailbox_table.setItem(i,2, QTableWidgetItem(m.get("owner","")))
            self.mailbox_table.setItem(i,3, QTableWidgetItem(str(len(m.get("messages",[])))))
        self.mailbox_table.resizeColumnsToContents()

    # ────────────────────────────────────────────────────────────────────────
    # Actions
    # ────────────────────────────────────────────────────────────────────────
    def inject_task(self):
        desc = self.task_input.text().strip()
        if not desc:
            return
        tid = add_task(task_type=self.task_type.currentText(), content=desc)
        print(f"✅ Injected task {tid}")
        self.task_input.clear()
        self._load_tasks()

    def claim_next_task(self):
        agent_id = "agent_001"
        ok = claim_task(agent_id=agent_id)
        if ok:
            print("✅ Claimed")
            if self.auto_click_on_claim:
                try:
                    click_agent_spot(agent_id)
                except Exception as e:
                    print(f"⚠ Failed to click spot for {agent_id}: {e}")
        else:
            print("❌ No tasks to claim")
        # Refresh task list view
        self._load_tasks()

    def update_messages(self):
        row = self.mailbox_table.currentRow()
        if row < 0: 
            self.msg_view.clear(); return
        _, m = self.mailboxes[row]
        text = "\n\n".join(f"[{msg['timestamp']}] {msg['sender']}: {msg['content']}"
                           for msg in m.get("messages",[]))
        self.msg_view.setPlainText(text)

    def capture_spot(self):
        # Capture an agent coordinate spot
        # Show crosshair cursor
        QApplication.setOverrideCursor(Qt.CrossCursor)
        QMessageBox.information(self, "Capture Spot",
            "Place mouse cursor at agent position.\nPress OK when ready.")
        x, y = pyautogui.position()
        agent_id, ok = QInputDialog.getText(self, "Agent ID",
            "Enter Agent ID (e.g., agent_001):")
        if ok and agent_id.strip():
            save_agent_spot(agent_id.strip(), (x, y))
            QMessageBox.information(self, "Capture Successful",
                f"Captured {agent_id.strip()} at ({x}, {y}).")
            # Refresh the Agents table
            self.refresh_agents_table()
        # Restore default cursor
        QApplication.restoreOverrideCursor()
    
    def refresh_agents_table(self):
        """Load saved agent coordinates and display in the Agents tab."""
        coords = _load_coords()
        table = self.agent_table
        table.clear()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Agent ID", "Coordinates"])
        table.setRowCount(len(coords))
        for i, (agent_id, pos) in enumerate(coords.items()):
            table.setItem(i, 0, QTableWidgetItem(agent_id))
            table.setItem(i, 1, QTableWidgetItem(f"({pos['x']}, {pos['y']})"))
        table.resizeColumnsToContents()

    def _on_accept(self):
        pyautogui.hotkey("ctrl","enter")

    def _on_reject(self):
        pyautogui.hotkey("ctrl","backspace")

    def _toggle_dev_mode(self, state: int):
        """Recreate the ChatGPTResponder in dev or prod mode."""
        dev = self.dev_toggle.isChecked()
        self.responder = ChatGPTResponder(dev_mode=dev) if ChatGPTResponder else None
        mode = 'dev' if dev else 'prod'
        print(f"🔄 ChatGPTResponder switched to {mode} mode")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = DashboardWindow()
    win.show()
    sys.exit(app.exec_())
