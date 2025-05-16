from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
import json
from datetime import datetime, timedelta
from pathlib import Path

class AgentManagementTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)

        mailbox_root = Path("runtime/agent_comms/agent_mailboxes")
        agents = sorted(mailbox_root.glob("Agent-*"))
        now = datetime.now()

        for agent_dir in agents:
            agent_name = agent_dir.name
            inbox_path = agent_dir / "inbox.json"
            devlog_path = agent_dir / "devlog.md"
            inbox_count = 0
            last_update_str = "N/A"
            status_label = QLabel()

            # Read inbox
            if inbox_path.exists():
                try:
                    with open(inbox_path, "r") as f:
                        inbox = json.load(f)
                        inbox_count = len(inbox)
                except:
                    inbox_count = -1
            
            # Read devlog timestamp
            last_update = None
            if devlog_path.exists():
                last_update = datetime.fromtimestamp(devlog_path.stat().st_mtime)
                last_update_str = last_update.isoformat()

            # Determine activity state
            if last_update:
                minutes_diff = (now - last_update).total_seconds() / 60
                if minutes_diff < 5:
                    status_label.setText("🟢 Active")
                elif minutes_diff < 15:
                    status_label.setText("🟡 Idle")
                else:
                    status_label.setText("🔴 Stale")
            else:
                status_label.setText("⚫ No Activity")

            # Agent UI block
            agent_block = QVBoxLayout()
            agent_block.addWidget(QLabel(f"Agent: {agent_name}"))
            agent_block.addWidget(QLabel(f"  Tasks Claimed: {inbox_count if inbox_count >= 0 else 'Error'}"))
            agent_block.addWidget(QLabel(f"  Last Devlog Update: {last_update_str}"))
            agent_block.addWidget(status_label)

            # Resume / Onboard buttons
            button_row = QHBoxLayout()
            resume_button = QPushButton("Resume Agent")
            onboard_button = QPushButton("Trigger Onboarding")

            resume_button.clicked.connect(lambda _, a=agent_name: self.send_resume_prompt(a))
            onboard_button.clicked.connect(lambda _, a=agent_name: self.send_onboard_prompt(a))

            button_row.addWidget(resume_button)
            button_row.addWidget(onboard_button)
            agent_block.addLayout(button_row)

            layout.addLayout(agent_block)
            layout.addSpacing(20)

    def send_resume_prompt(self, agent_name):
        inbox_path = Path(f"runtime/agent_comms/agent_mailboxes/{agent_name}/inbox.json")
        message = {
            "id": "RESUME-AGENT-001",
            "type": "resume",
            "content": "Resume your UNIVERSAL_AGENT_LOOP immediately.",
            "processed": False,
            "priority": 100,
            "timestamp": datetime.utcnow().isoformat()
        }
        self._inject_message(inbox_path, message)

    def send_onboard_prompt(self, agent_name):
        inbox_path = Path(f"runtime/agent_comms/agent_mailboxes/{agent_name}/inbox.json")
        message = {
            "id": "ONBOARD-AGENT-001",
            "type": "onboarding",
            "content": "Begin onboarding and initialize your personal devlog and task loop.",
            "processed": False,
            "priority": 100,
            "timestamp": datetime.utcnow().isoformat()
        }
        self._inject_message(inbox_path, message)

    def _inject_message(self, inbox_path, message):
        try:
            inbox = []
            if inbox_path.exists():
                with open(inbox_path, "r") as f:
                    inbox = json.load(f)
            inbox.append(message)
            with open(inbox_path, "w") as f:
                json.dump(inbox, f, indent=2)
        except Exception as e:
            print(f"Failed to inject message into {inbox_path}: {e}")
