import os
import sys
import json
import uuid
import pyautogui
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QSplitter, QWidget,
    QVBoxLayout, QTableWidget, QTableWidgetItem, QTabWidget,
    QComboBox, QTextEdit, QPushButton, QShortcut, QLabel, QLineEdit, QAbstractItemView
)
from PyQt5.QtGui import QKeySequence, QColor
from PyQt5.QtCore import Qt, QTimer
try:
    from pynput.mouse import Listener
    _USE_LISTENER = True
except ImportError:
    print("pynput not available; click-to-capture will fall back to manual capture mode.")
    _USE_LISTENER = False

# Attempt to import AgentBus for integration
try:
    from core.coordination.agent_bus import AgentBus
except ImportError:
    AgentBus = None

class DashboardWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dream.os Agent Dashboard")
        self.resize(1200, 800)

        splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(splitter)

        tabs = QTabWidget()
        splitter.addWidget(tabs)

        # Mailboxes tab
        mailbox_widget = QWidget()
        mailbox_layout = QVBoxLayout(mailbox_widget)
        self.mailbox_table = QTableWidget()
        # Messages pane
        self.message_view = QTextEdit(); self.message_view.setReadOnly(True)
        mailbox_layout.addWidget(self.mailbox_table)
        mailbox_layout.addWidget(self.message_view)
        # Refresh messages when selection changes
        self.mailbox_table.itemSelectionChanged.connect(self.update_messages)
        tabs.addTab(mailbox_widget, "Mailboxes")

        # Tasks tab
        task_widget = QWidget()
        task_layout = QVBoxLayout(task_widget)
        self.task_table = QTableWidget()
        task_layout.addWidget(self.task_table)
        claim_btn = QPushButton("Claim Selected Task")
        claim_btn.clicked.connect(self.claim_task)
        task_layout.addWidget(claim_btn)
        tabs.addTab(task_widget, "Tasks")

        # Messaging tab
        msg_widget = QWidget()
        msg_layout = QVBoxLayout(msg_widget)
        self.mailbox_selector = QComboBox()
        msg_layout.addWidget(self.mailbox_selector)
        self.msg_input = QTextEdit()
        msg_layout.addWidget(self.msg_input)
        send_btn = QPushButton("Send Message")
        send_btn.clicked.connect(self.send_message)
        msg_layout.addWidget(send_btn)
        tabs.addTab(msg_widget, "Messaging")

        # Templates tab
        template_widget = QWidget()
        template_layout = QVBoxLayout(template_widget)
        self.template_selector = QComboBox()
        self.template_selector.currentIndexChanged.connect(self.update_template_view)
        template_layout.addWidget(self.template_selector)
        self.template_view = QTextEdit()
        self.template_view.setReadOnly(True)
        template_layout.addWidget(self.template_view)
        load_tpl_btn = QPushButton("Load Template into Prompt")
        load_tpl_btn.clicked.connect(self.load_template)
        template_layout.addWidget(load_tpl_btn)
        tabs.addTab(template_widget, "Templates")

        # Agents tab: configure click spots for each agent
        agents_widget = QWidget()
        agents_layout = QVBoxLayout(agents_widget)
        self.agent_table = QTableWidget()
        # Enable full-row selection
        self.agent_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.agent_table.setSelectionMode(QAbstractItemView.SingleSelection)
        agents_layout.addWidget(self.agent_table)
        # Buttons for capture and save
        capture_btn = QPushButton("Capture Spot for Selected Agent")
        capture_btn.clicked.connect(self.capture_spot)
        agents_layout.addWidget(capture_btn)
        # Button to record current mouse position directly
        record_btn = QPushButton("Record Current Position")
        record_btn.clicked.connect(self.record_spot)
        agents_layout.addWidget(record_btn)
        save_agents_btn = QPushButton("Save Agent Coordinates")
        save_agents_btn.clicked.connect(self.save_agent_coords)
        agents_layout.addWidget(save_agents_btn)
        tabs.addTab(agents_widget, "Agents")

        # Actions tab: load/send user prompts and accept/reject changes
        actions_widget = QWidget()
        actions_layout = QVBoxLayout(actions_widget)
        self.prompt_selector = QComboBox()
        actions_layout.addWidget(self.prompt_selector)
        load_prompt_btn = QPushButton("Load Prompt")
        load_prompt_btn.clicked.connect(self.load_user_prompt)
        actions_layout.addWidget(load_prompt_btn)
        send_prompt_btn = QPushButton("Send Prompt")
        send_prompt_btn.clicked.connect(self.send_message)
        actions_layout.addWidget(send_prompt_btn)
        accept_btn = QPushButton("Accept Changes")
        accept_btn.clicked.connect(lambda: pyautogui.hotkey('ctrl','enter'))
        actions_layout.addWidget(accept_btn)
        reject_btn = QPushButton("Reject Changes")
        reject_btn.clicked.connect(lambda: pyautogui.hotkey('ctrl','backspace'))
        actions_layout.addWidget(reject_btn)
        tabs.addTab(actions_widget, "Actions")

        # Inter-Agent Communication tab
        comm_widget = QWidget()
        comm_layout = QVBoxLayout(comm_widget)
        self.comm_table = QTableWidget()
        comm_layout.addWidget(self.comm_table)
        tabs.addTab(comm_widget, "Inter-Agent Comm")

        self.load_data()
        self.load_templates()
        # Auto-refresh data every 5 seconds
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.load_data)
        self.refresh_timer.timeout.connect(self.update_messages)
        self.refresh_timer.start(5000)
        # Setup AgentBus if available
        self.agent_bus = AgentBus() if AgentBus else None

        # Keyboard shortcuts for accept/reject and capture
        accept_sc = QShortcut(QKeySequence("Ctrl+Return"), self)
        accept_sc.activated.connect(self.send_message)
        reject_sc = QShortcut(QKeySequence("Ctrl+Backspace"), self)
        reject_sc.activated.connect(self.msg_input.clear)
        # Shortcut to capture spot: move mouse to desired location and press Ctrl+Shift+S
        capture_sc = QShortcut(QKeySequence("Ctrl+Shift+S"), self)
        capture_sc.activated.connect(self.capture_spot)

        # After load_data, populate agent_table
        self.load_agent_coords()
        self.populate_agent_table()
        # Refresh inter-agent communication panel
        self.load_comm_data()

    def load_data(self):
        base_dir = os.path.dirname(os.path.realpath(__file__))
        shared_dir = os.path.join(base_dir, "_agent_coordination", "shared_mailboxes")
        tasks_dir = os.path.join(base_dir, "_agent_coordination", "tasks")

        # Load mailboxes: only mailbox_*.json files
        mail_files = [f for f in os.listdir(shared_dir) if f.startswith('mailbox_') and f.endswith('.json')]
        mailboxes = []  # list of tuples (mailbox_id, data)
        for fname in mail_files:
            fpath = os.path.join(shared_dir, fname)
            try:
                with open(fpath, 'r') as fp:
                    data = json.load(fp)
                mailbox_id = os.path.splitext(fname)[0]
                mailboxes.append((mailbox_id, data))
            except Exception as e:
                print(f"Failed to load mailbox {fname}: {e}")
        # Store for message detail lookup
        self.mailboxes = mailboxes

        # Populate mailbox table
        headers = ['Mailbox ID', 'Status', 'Owner', 'Message Count']
        self.mailbox_table.setColumnCount(len(headers))
        self.mailbox_table.setHorizontalHeaderLabels(headers)
        self.mailbox_table.setRowCount(len(mailboxes))
        for row, (mb_id, m) in enumerate(mailboxes):
            # Fill cells
            self.mailbox_table.setItem(row, 0, QTableWidgetItem(mb_id))
            status = m.get('status','')
            self.mailbox_table.setItem(row, 1, QTableWidgetItem(status))
            owner = m.get('owner') or m.get('assigned_agent_id','')
            self.mailbox_table.setItem(row, 2, QTableWidgetItem(owner))
            cnt = str(len(m.get('messages', [])))
            self.mailbox_table.setItem(row, 3, QTableWidgetItem(cnt))
            # Color based on status
            color = QColor('lightgreen') if status=='online' else QColor('lightyellow') if status=='idle' else QColor('lightgray')
            for col in range(4): self.mailbox_table.item(row,col).setBackground(color)
        self.mailbox_table.resizeColumnsToContents()
        self.mailbox_table.setSortingEnabled(True)

        # Update mailbox selector
        self.mailbox_selector.clear()
        for mb_id, _ in mailboxes:
            self.mailbox_selector.addItem(mb_id)

        # Load tasks from all JSON files in tasks_dir, tagging source
        tasks = []
        for fname in os.listdir(tasks_dir):
            if fname.endswith('.json') and not fname.endswith('.schema.json'):
                fpath = os.path.join(tasks_dir, fname)
                try:
                    with open(fpath, 'r') as fp:
                        data = json.load(fp)
                    entries = data if isinstance(data, list) else data.get('tasks', [data]) if isinstance(data, dict) else []
                    for t in entries:
                        if isinstance(t, dict):
                            t['_source'] = fname
                            tasks.append(t)
                except Exception as e:
                    print(f"Failed to load tasks file {fname}: {e}")

        # Populate task table
        task_headers = ['Task ID', 'Status', 'Assigned To', 'Description', 'Source']
        self.task_table.setColumnCount(len(task_headers))
        self.task_table.setHorizontalHeaderLabels(task_headers)
        self.task_table.setRowCount(len(tasks))
        for row, t in enumerate(tasks):
            self.task_table.setItem(row, 0, QTableWidgetItem(t.get('task_id', '')))
            self.task_table.setItem(row, 1, QTableWidgetItem(t.get('status', '')))
            owner = t.get('claimed_by') or t.get('assigned_to', '')
            self.task_table.setItem(row, 2, QTableWidgetItem(owner))
            desc = t.get('description', '')
            if isinstance(desc, list):
                desc = '\n'.join(str(x) for x in desc)
            elif isinstance(desc, dict):
                desc = json.dumps(desc)
            self.task_table.setItem(row, 3, QTableWidgetItem(desc))
            source = t.get('_source', '')
            self.task_table.setItem(row, 4, QTableWidgetItem(source))
            # Color by status
            tc=QColor('lightblue') if t.get('status')=='CLAIMED' else QColor('lightgray') if t.get('status')=='COMPLETED' else QColor('lightyellow')
            for col in range(5): self.task_table.item(row,col).setBackground(tc)
        self.task_table.resizeColumnsToContents()
        self.task_table.setSortingEnabled(True)

        # After load_data, populate agent_table
        self.load_agent_coords()
        self.populate_agent_table()
        # Refresh inter-agent communication panel
        self.load_comm_data()

    def send_message(self):
        mb_id = self.mailbox_selector.currentText()
        content = self.msg_input.toPlainText().strip()
        if not mb_id or not content:
            return
        base_dir = os.path.dirname(os.path.realpath(__file__))
        shared_dir = os.path.join(base_dir, "_agent_coordination", "shared_mailboxes")
        file_path = os.path.join(shared_dir, f"mailbox_{mb_id.split('_')[-1]}.json")
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            msg = {
                "message_id": uuid.uuid4().hex,
                "sender": "GUIClient",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "content": content
            }
            data.setdefault("messages", []).append(msg)
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            # Also automate typing the prompt to active window and send via pyautogui
            try:
                pyautogui.typewrite(content)
                pyautogui.hotkey('ctrl', 'enter')
            except Exception as pg_e:
                print(f"pyautogui send failed: {pg_e}")
            # Also dispatch to agent via AgentBus
            if self.agent_bus:
                try:
                    self.agent_bus.dispatch(
                        target_agent_id='CursorControlAgent',
                        method_name='_process_mailbox_message',
                        message_path=file_path
                    )
                except Exception as e:
                    print(f"AgentBus dispatch failed: {e}")
            self.load_data()
            self.msg_input.clear()
        except Exception as e:
            print(f"Failed to send message to {mb_id}: {e}")

    def claim_task(self):
        # Claim the first unclaimed pending task for this agent
        agent_id = 'agent_001'
        tasks_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "_agent_coordination", "tasks")
        claimed = False
        for fname in os.listdir(tasks_dir):
            if not fname.endswith('.json') or fname.endswith('.schema.json'):
                continue
            file_path = os.path.join(tasks_dir, fname)
            try:
                with open(file_path, 'r', encoding='utf-8') as rf:
                    content = json.load(rf)
                tasks_list = content if isinstance(content, list) else content.get('tasks', [])
                for task in tasks_list:
                    # Skip if already claimed or completed
                    if task.get('status') in ('CLAIMED', 'COMPLETED') or task.get('claimed_by'):
                        continue
                    # Claim it
                    task['status'] = 'CLAIMED'
                    task['claimed_by'] = agent_id
                    claimed = True
                    break
                if claimed:
                    # Write back
                    to_write = tasks_list if isinstance(content, list) else {**content, 'tasks': tasks_list}
                    with open(file_path, 'w', encoding='utf-8') as wf:
                        json.dump(to_write, wf, indent=2)
                    break
            except Exception as e:
                print(f"Error claiming task in {fname}: {e}")
        if claimed:
            print(f"Agent {agent_id} claimed a new task.")
        else:
            print(f"No unclaimed tasks available for Agent {agent_id}.")
        self.load_data()

    def load_templates(self):
        # Find all schema files in shared_mailboxes and tasks
        base_dir = os.path.dirname(os.path.realpath(__file__))
        dirs = [os.path.join(base_dir, "_agent_coordination", "shared_mailboxes"),
                os.path.join(base_dir, "_agent_coordination", "tasks")]
        self.schema_files = []  # list of (filename, path)
        for d in dirs:
            for fname in os.listdir(d):
                if fname.endswith('.schema.json'):
                    self.schema_files.append((fname, os.path.join(d, fname)))
        self.template_selector.clear()
        for fname, _ in self.schema_files:
            self.template_selector.addItem(fname)
        if self.schema_files:
            self.update_template_view(0)

    def update_template_view(self, index):
        if index < 0 or index >= len(self.schema_files):
            return
        path = self.schema_files[index][1]
        try:
            with open(path, 'r') as f:
                content = f.read()
            self.template_view.setPlainText(content)
        except Exception as e:
            print(f"Failed to load template {path}: {e}")

    def load_template(self):
        # Copy template content into message input for editing
        content = self.template_view.toPlainText()
        self.msg_input.setPlainText(content)

    def update_messages(self):
        row = self.mailbox_table.currentRow()
        if row < 0:
            self.message_view.clear()
            return
        mb_id, data = self.mailboxes[row]
        msgs = data.get('messages', [])
        text = ''
        for msg in msgs:
            text += f"[{msg.get('timestamp')}] {msg.get('sender')}: {msg.get('content')}\n\n"
        self.message_view.setPlainText(text)

    def load_agent_coords(self):
        base_dir = os.path.dirname(os.path.realpath(__file__))
        cfg_dir = os.path.join(base_dir, "_agent_coordination", "config")
        cfg_file = os.path.join(cfg_dir, "agent_coords.json")
        os.makedirs(cfg_dir, exist_ok=True)
        try:
            with open(cfg_file, 'r') as f:
                self.agent_coords = json.load(f)
        except Exception:
            self.agent_coords = {}

    def populate_agent_table(self):
        agent_ids = [f"agent_{i:03d}" for i in range(1,9)]
        self.agent_table.setColumnCount(3)
        self.agent_table.setHorizontalHeaderLabels(["Agent ID","X","Y"])
        self.agent_table.setRowCount(len(agent_ids))
        for row, aid in enumerate(agent_ids):
            item = QTableWidgetItem(aid)
            item.setFlags(Qt.ItemIsEnabled)
            self.agent_table.setItem(row, 0, item)
            coords = self.agent_coords.get(aid, {})
            x = coords.get('x','')
            y = coords.get('y','')
            self.agent_table.setItem(row, 1, QTableWidgetItem(str(x)))
            self.agent_table.setItem(row, 2, QTableWidgetItem(str(y)))
        self.agent_table.resizeColumnsToContents()

    def save_agent_coords(self):
        base_dir = os.path.dirname(os.path.realpath(__file__))
        cfg_dir = os.path.join(base_dir, "_agent_coordination", "config")
        cfg_file = os.path.join(cfg_dir, "agent_coords.json")
        coords_out = {}
        for row in range(self.agent_table.rowCount()):
            aid = self.agent_table.item(row,0).text()
            try:
                x = int(self.agent_table.item(row,1).text())
                y = int(self.agent_table.item(row,2).text())
                coords_out[aid] = {'x': x, 'y': y}
            except Exception:
                continue
        with open(cfg_file, 'w') as f:
            json.dump(coords_out, f, indent=2)
        print(f"Saved agent coordinates to {cfg_file}")

    def load_user_prompts(self):
        base_dir = os.path.dirname(os.path.realpath(__file__))
        prompts_dir = os.path.join(base_dir, "_agent_coordination", "user_prompts")
        self.user_prompts = []
        self.prompt_selector.clear()
        try:
            for fname in os.listdir(prompts_dir):
                if fname.endswith('.json') or fname.endswith('.txt'):
                    path = os.path.join(prompts_dir, fname)
                    self.user_prompts.append((fname, path))
                    self.prompt_selector.addItem(fname)
        except Exception as e:
            print(f"Failed to list user_prompts directory: {e}")

    def load_user_prompt(self):
        idx = self.prompt_selector.currentIndex()
        if idx < 0 or idx >= len(self.user_prompts):
            return
        fname, path = self.user_prompts[idx]
        try:
            with open(path, 'r') as f:
                content = f.read()
            self.msg_input.setPlainText(content)
        except Exception as e:
            print(f"Failed to load prompt {fname}: {e}")

    def load_comm_data(self):
        # Load agent statuses from project_board.json
        base_dir = os.path.dirname(os.path.realpath(__file__))
        shared_dir = os.path.join(base_dir, "_agent_coordination", "shared_mailboxes")
        pb_file = os.path.join(shared_dir, "project_board.json")
        try:
            with open(pb_file, 'r') as f:
                data = json.load(f)
                agents = data.get('agents', [])
        except Exception:
            agents = []
        # Populate communication table
        headers = ['Agent ID', 'Status', 'Last Seen', 'Current Task']
        self.comm_table.setColumnCount(len(headers))
        self.comm_table.setHorizontalHeaderLabels(headers)
        self.comm_table.setRowCount(len(agents))
        for row, ag in enumerate(agents):
            self.comm_table.setItem(row, 0, QTableWidgetItem(ag.get('agent_id', '')))
            self.comm_table.setItem(row, 1, QTableWidgetItem(ag.get('status', '')))
            self.comm_table.setItem(row, 2, QTableWidgetItem(ag.get('last_seen', '')))
            self.comm_table.setItem(row, 3, QTableWidgetItem(ag.get('current_task', '')))
        self.comm_table.resizeColumnsToContents()

    def capture_spot(self):
        row = self.agent_table.currentRow()
        if row < 0:
            print("No agent selected to capture spot.")
            return
        if _USE_LISTENER:
            # Enter capture mode: next global click will record position
            self._capture_row = row
            self.message_view.setPlainText("Click anywhere on screen to capture spot for selected agent...")
            # Start global mouse listener
            self._capture_listener = Listener(on_click=self._on_click)
            self._capture_listener.start()
        else:
            # Fallback: record current mouse position immediately
            try:
                pos = pyautogui.position()
                aid = self.agent_table.item(row, 0).text()
                # Update internal store and UI
                self.agent_coords[aid] = {'x': pos.x, 'y': pos.y}
                self.agent_table.setItem(row, 1, QTableWidgetItem(str(pos.x)))
                self.agent_table.setItem(row, 2, QTableWidgetItem(str(pos.y)))
                self.message_view.setPlainText(f"Captured spot for {aid}: ({pos.x},{pos.y}) via fallback mode.")
                # Persist immediately
                self.save_agent_coords()
            except Exception as e:
                print(f"Fallback capture failed: {e}")

    def _on_click(self, x, y, button, pressed):
        if not pressed:
            return
        try:
            row = self._capture_row
            aid = self.agent_table.item(row, 0).text()
            # Update internal store
            self.agent_coords[aid] = {'x': x, 'y': y}
            # Schedule UI update on main thread
            QTimer.singleShot(0, lambda: self.agent_table.setItem(row, 1, QTableWidgetItem(str(x))))
            QTimer.singleShot(0, lambda: self.agent_table.setItem(row, 2, QTableWidgetItem(str(y))))
            QTimer.singleShot(0, lambda: self.message_view.setPlainText(f"Captured spot for {aid}: ({x},{y})"))
            # Persist immediately
            self.save_agent_coords()
        except Exception as e:
            QTimer.singleShot(0, lambda: self.message_view.setPlainText(f"Error capturing spot: {e}"))
        finally:
            # Stop listener after first click
            try:
                self._capture_listener.stop()
            except Exception:
                pass

    def record_spot(self):
        # Record mouse position at moment for selected agent
        row = self.agent_table.currentRow()
        if row < 0:
            self.message_view.setPlainText("No agent selected to record position.")
            return
        try:
            pos = pyautogui.position()
            aid = self.agent_table.item(row, 0).text()
            # Update table and store
            self.agent_table.setItem(row, 1, QTableWidgetItem(str(pos.x)))
            self.agent_table.setItem(row, 2, QTableWidgetItem(str(pos.y)))
            self.agent_coords[aid] = {'x': pos.x, 'y': pos.y}
            self.save_agent_coords()
            self.message_view.setPlainText(f"Recorded position for {aid}: ({pos.x},{pos.y})")
        except Exception as e:
            self.message_view.setPlainText(f"Error recording position: {e}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = DashboardWindow()
    win.show()
    sys.exit(app.exec_()) 