from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit,
    QComboBox, QListWidget, QHBoxLayout, QLineEdit, QSplitter
)
from PyQt5.QtCore import Qt
import json
from pathlib import Path
from datetime import datetime

# --- Dream.OS Discord Integration Placeholder ---
# The core Discord bot functionality (handling commands like !addtrade)
# resides in: src/dreamos/discord_integration/discord_bot_core.py
# Future enhancements to this UI could involve:
# 1. Displaying status of the discord_bot_core.py process.
# 2. Sending messages/commands TO the Discord bot FROM this UI.
# 3. Receiving notifications or logs FROM the Discord bot TO this UI.
# This would likely require inter-process communication (e.g., sockets, message queues)
# or a shared API/database if the bot and UI need to interact deeply.

class DiscordCommanderTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QHBoxLayout()
        self.setLayout(layout)

        # LEFT PANE: Agent status & feed
        left_pane = QVBoxLayout()
        self.agent_list = QListWidget()
        left_pane.addWidget(QLabel("Agents (Status):"))
        left_pane.addWidget(self.agent_list)

        self.refresh_agents_button = QPushButton("Refresh Agents")
        self.refresh_agents_button.clicked.connect(self.load_agents)
        left_pane.addWidget(self.refresh_agents_button)

        self.feed_label = QLabel("Activity Feed (last 5 entries):")
        left_pane.addWidget(self.feed_label)
        self.activity_feed = QListWidget()
        left_pane.addWidget(self.activity_feed)

        # RIGHT PANE: Prompt controls
        right_pane = QVBoxLayout()
        right_pane.addWidget(QLabel("Prompt Type:"))
        self.prompt_type = QComboBox()
        self.prompt_type.addItems(["custom", "resume", "onboarding"])
        right_pane.addWidget(self.prompt_type)

        right_pane.addWidget(QLabel("Prompt Template:"))
        self.prompt_template = QComboBox()
        self.prompt_template.addItems([
            "Default", "Resume Agent", "Onboarding", "Custom"
        ])
        right_pane.addWidget(self.prompt_template)

        right_pane.addWidget(QLabel("Prompt Content:"))
        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText("Type your prompt message or select a template...")
        right_pane.addWidget(self.prompt_input)

        agent_row = QHBoxLayout()
        agent_row.addWidget(QLabel("Target Agent:"))
        self.agent_selector = QComboBox()
        self.agent_selector.addItems([f"Agent-{i}" for i in range(1, 9)])
        agent_row.addWidget(self.agent_selector)
        right_pane.addLayout(agent_row)

        self.send_button = QPushButton("Send Prompt")
        self.send_button.clicked.connect(self.send_prompt)
        right_pane.addWidget(self.send_button)

        right_pane.addWidget(QLabel("Command Log:"))
        self.command_log = QListWidget()
        right_pane.addWidget(self.command_log)

        right_pane.addWidget(QLabel("Last 5 Outbox Replies:"))
        self.reply_feed = QListWidget()
        right_pane.addWidget(self.reply_feed)

        # Layout: Side-by-side panes
        splitter = QSplitter(Qt.Horizontal)
        left_widget = QWidget()
        left_widget.setLayout(left_pane)
        splitter.addWidget(left_widget)

        right_widget = QWidget()
        right_widget.setLayout(right_pane)
        splitter.addWidget(right_widget)
        layout.addWidget(splitter)

        # Load data on startup
        self.load_agents()
        self.load_activity_feed()
        self.load_reply_feed()

    def load_agents(self):
        self.agent_list.clear()
        mailbox_root = Path("runtime/agent_comms/agent_mailboxes")
        now = datetime.now()
        for agent_dir in sorted(mailbox_root.glob("Agent-*")):
            devlog_path = agent_dir / "devlog.md"
            last_update = None
            if devlog_path.exists():
                last_update = datetime.fromtimestamp(devlog_path.stat().st_mtime)
                minutes_ago = (now - last_update).total_seconds() / 60
                if minutes_ago < 5:
                    status = "🟢"
                elif minutes_ago < 15:
                    status = "🟡"
                else:
                    status = "🔴"
            else:
                status = "⚫"
            self.agent_list.addItem(f"{status} {agent_dir.name}")

    def load_activity_feed(self):
        self.activity_feed.clear()
        # Example: Load last 5 actions from devlog of Agent-1 (customize as needed)
        devlog_path = Path("runtime/agent_comms/agent_mailboxes/Agent-1/devlog.md")
        if devlog_path.exists():
            try:
                with open(devlog_path, "r") as f:
                    lines = f.readlines()
                for line in lines[-5:]:
                    self.activity_feed.addItem(line.strip())
            except Exception as e:
                self.activity_feed.addItem(f"Error loading devlog: {e}")

    def load_reply_feed(self):
        self.reply_feed.clear()
        outbox_dir = Path("runtime/bridge_outbox")
        if outbox_dir.exists():
            replies = sorted(outbox_dir.glob("*.json"), reverse=True)[:5]
            for reply_file in replies:
                try:
                    with open(reply_file, "r") as f:
                        data = json.load(f)
                    msg = data.get("content", str(data)[:80])
                    self.reply_feed.addItem(msg)
                except Exception as e:
                    self.reply_feed.addItem(f"{reply_file.name}: {e}")

    def send_prompt(self):
        agent = self.agent_selector.currentText()
        prompt_type = self.prompt_type.currentText()
        template = self.prompt_template.currentText()
        prompt = self.prompt_input.toPlainText().strip()

        # Optionally auto-populate for known prompt types/templates
        if not prompt and template != "Custom":
            if template == "Resume Agent":
                prompt = "Resume your UNIVERSAL_AGENT_LOOP immediately."
            elif template == "Onboarding":
                prompt = "Begin onboarding and initialize your personal devlog and task loop."

        if not prompt:
            self.command_log.addItem("Prompt empty, not sent.")
            return

        # Write to target agent inbox.json as a message (replace this with Discord relay if needed)
        inbox_path = Path(f"runtime/agent_comms/agent_mailboxes/{agent}/inbox.json")
        message = {
            "id": f"{prompt_type.upper()}-{datetime.utcnow().isoformat()}",
            "type": prompt_type,
            "content": prompt,
            "processed": False,
            "priority": 100,
            "timestamp": datetime.utcnow().isoformat()
        }
        try:
            inbox = []
            if inbox_path.exists():
                with open(inbox_path, "r") as f:
                    inbox = json.load(f)
            inbox.append(message)
            with open(inbox_path, "w") as f:
                json.dump(inbox, f, indent=2)
            self.command_log.addItem(f"Sent to {agent}: {prompt[:60]}")
        except Exception as e:
            self.command_log.addItem(f"Failed to send: {e}")

        # Optionally refresh reply feed if relay is implemented
        self.load_reply_feed()

    # --- Placeholder for Discord Bot Interaction ---
    def _init_discord_bot_interaction_ui(self):
        # This section could be expanded to show Discord bot status or offer controls.
        self.discord_status_label = QLabel("Discord Bot Status: (Not directly managed by this UI)")
        # self.layout().addWidget(self.discord_status_label) # Example: Add to main layout if needed
        # Placeholder for a button to send a message via bot, etc.
        # self.send_discord_message_button = QPushButton("Send Message via Discord Bot")
        # self.send_discord_message_button.clicked.connect(self.on_send_discord_message)
        # self.layout().addWidget(self.send_discord_message_button)
        pass # Current implementation does not directly control the bot from UI

    def on_send_discord_message(self):
        # Example: This function would need to communicate with the running discord_bot_core.py
        # (e.g., via an API, socket, or message queue established by the bot)
        self.command_log.addItem("[INFO] Sending message via Discord Bot (Not Implemented)")
        pass

    # Call this in __init__ if you decide to add UI elements for bot interaction
    # self._init_discord_bot_interaction_ui()
