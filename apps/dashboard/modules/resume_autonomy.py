from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QTextEdit, QComboBox, QMenu,
    QAction, QStyleFactory, QProgressBar, QWidget,
    QGroupBox, QGridLayout
)
from PyQt5.QtCore import Qt, QTimer, pyqtSlot, QSize
from PyQt5.QtGui import QPainter, QColor, QPen
from typing import Dict, Any, List, Optional
import json
from pathlib import Path
from .voice_commands import VoiceCommandHandler
import time
from datetime import datetime, timedelta
import asyncio
from .notifier import Notifier

# Theme configuration
THEME = {
    "light": {
        "background": "#ffffff",
        "text": "#000000",
        "accent": "#007bff",
        "success": "#28a745",
        "warning": "#ffc107",
        "error": "#dc3545",
        "border": "#dee2e6"
    },
    "dark": {
        "background": "#212529",
        "text": "#ffffff",
        "accent": "#0d6efd",
        "success": "#198754",
        "warning": "#ffc107",
        "error": "#dc3545",
        "border": "#495057"
    }
    }

class TaskActionMenu(QMenu):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_actions()
        
    def setup_actions(self):
        self.resume_action = QAction("Resume Autonomy", self)
        self.stop_action = QAction("Stop Task", self)
        self.logs_action = QAction("View Logs", self)
        
        self.addAction(self.resume_action)
        self.addAction(self.stop_action)
        self.addAction(self.logs_action)

class ResumeAutonomyAgentTab(QWidget):
    def __init__(self, agent_id: str, inbox_base: Path, thea_handler, parent=None):
        super().__init__(parent)
        self.agent_id = agent_id
        self.inbox_base = inbox_base
        self.thea_handler = thea_handler
        self.current_task = None
        self.notifier = None
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Theme selector
        theme_layout = QHBoxLayout()
        theme_label = QLabel("Theme:")
        self.theme_selector = QComboBox()
        self.theme_selector.addItems(QStyleFactory.keys())
        self.theme_selector.currentTextChanged.connect(self.apply_theme)
        theme_layout.addWidget(theme_label)
        theme_layout.addWidget(self.theme_selector)
        theme_layout.addStretch()
        layout.addLayout(theme_layout)
        
        # Inbox display
        self.inbox_display = QTextEdit()
        self.inbox_display.setReadOnly(True)
        self.inbox_display.setContextMenuPolicy(Qt.CustomContextMenu)
        self.inbox_display.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.inbox_display)
        
        # Devlog section
        devlog_label = QLabel("Devlog")
        self.devlog_display = QTextEdit()
        self.devlog_display.setReadOnly(True)
        layout.addWidget(devlog_label)
        layout.addWidget(self.devlog_display)
        
        # Action buttons
        button_layout = QHBoxLayout()
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_content)
        button_layout.addWidget(self.refresh_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_content)
        self.refresh_timer.start(5000)  # Refresh every 5 seconds
        
    async def check_drift(self):
        """Check for drift and trigger resume if needed"""
        status_path = self.inbox_base / self.agent_id / "status.json"
        if not status_path.exists():
            return
            
        status = json.loads(status_path.read_text())
        last_heartbeat = datetime.fromisoformat(status["last_heartbeat"])
        
        # Check if heartbeat is too old (5 minutes)
        if datetime.utcnow() - last_heartbeat > timedelta(minutes=5):
            await self.notifier.send_alert(
                level="warning",
                title="Drift Detected",
                message=f"Agent {self.agent_id} has drifted",
                fields={"Agent": self.agent_id, "Last Heartbeat": last_heartbeat.isoformat()}
            )
            
            # Enqueue resume prompt
            bridge_file = Path("runtime/bridge/queue/agent_prompts.jsonl")
            bridge_file.parent.mkdir(parents=True, exist_ok=True)
            
            prompt = {
                "agent_id": self.agent_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "prompt": "resume autonomy",
                "reason": "Drift detected"
            }
            
            with open(bridge_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(prompt) + "\n")
    
    async def resume_autonomy(self):
        """Resume the agent's autonomy loop"""
        status_path = self.inbox_base / self.agent_id / "status.json"
        if not status_path.exists():
            return
            
        status = json.loads(status_path.read_text())
        status["loop_active"] = True
        status["compliance_score"] = 100
        status["last_heartbeat"] = datetime.utcnow().isoformat()
        
        status_path.write_text(json.dumps(status))
        
        await self.notifier.send_alert(
            level="info",
            title="Autonomy Resumed",
            message=f"Agent {self.agent_id} autonomy resumed",
            fields={"Agent": self.agent_id}
        )
    
    def update_status(self, current_task: str = None, compliance_score: int = None):
        """Update the agent's status file"""
        status_path = self.inbox_base / self.agent_id / "status.json"
        if not status_path.exists():
            status = {
                "agent_id": self.agent_id,
                "current_task": current_task or "idle",
                "loop_active": True,
                "last_heartbeat": datetime.utcnow().isoformat(),
                "compliance_score": compliance_score or 100
            }
        else:
            status = json.loads(status_path.read_text())
            if current_task:
                status["current_task"] = current_task
            if compliance_score is not None:
                status["compliance_score"] = compliance_score
            status["last_heartbeat"] = datetime.utcnow().isoformat()
        
        status_path.write_text(json.dumps(status))
        
    def show_context_menu(self, position):
        if self.current_task:
            menu = TaskActionMenu(self)
            action = menu.exec_(self.inbox_display.mapToGlobal(position))
            
            if action == menu.resume_action:
                from .task_manager import update_task_status
                update_task_status(self.agent_id, self.current_task["id"], "completed", self.inbox_base)
                self.refresh_content()
            elif action == menu.stop_action:
                # TODO: Show agent selection dialog
                pass
            elif action == menu.logs_action:
                # TODO: Implement logs action
                pass
                
    def refresh_content(self):
        from .task_manager import load_inbox, load_devlog
        inbox = load_inbox(self.agent_id, self.inbox_base)
        devlog = load_devlog(self.agent_id, self.inbox_base)
        
        # Format and display inbox messages
        if isinstance(inbox, list):
            formatted_messages = []
            for msg in inbox:
                if isinstance(msg, dict):
                    self.current_task = msg
                    if msg.get("type") == "instruction":
                        formatted_messages.append(f"📝 Instruction: {msg.get('content', 'No content')}")
                    elif msg.get("type") == "RESUME_PROMPT":
                        formatted_messages.append("⭮ Resume Request")
                    elif msg.get("type") == "ONBOARDING_PACKET":
                        formatted_messages.append("📄 Onboarding Packet")
                    elif msg.get("type") == "escalation":
                        formatted_messages.append(f"🚨 Escalation from {msg.get('source_agent')}: {msg.get('content')}")
                    elif msg.get("type") == "thea_response":
                        thea_content = msg.get("content", {})
                        formatted_messages.append(
                            f"👑 THEA Response:\n"
                            f"Status: {thea_content.get('status', 'unknown')}\n"
                            f"Response: {thea_content.get('response', 'No response')}\n"
                            f"Next Steps:\n" + "\n".join(f"  • {step}" for step in thea_content.get('next_steps', []))
                        )
                    else:
                        formatted_messages.append(f"Message: {json.dumps(msg, indent=2)}")
                else:
                    formatted_messages.append(str(msg))
            
            self.inbox_display.setText("\n\n---\n\n".join(formatted_messages))
        else:
            self.inbox_display.setText("Invalid inbox format")
            
        # Display devlog
        self.devlog_display.setText(devlog)
        
    def apply_theme(self, theme_name: str):
        """Apply selected theme to the UI"""
        theme = THEME["dark"] if theme_name.lower() == "dark" else THEME["light"]
        
        # Apply theme to widgets
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {theme['background']};
                color: {theme['text']};
            }}
            QTextEdit {{
                border: 1px solid {theme['border']};
                border-radius: 4px;
                padding: 8px;
            }}
            QPushButton {{
                background-color: {theme['accent']};
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {theme['accent']}dd;
            }}
            QComboBox {{
                border: 1px solid {theme['border']};
                border-radius: 4px;
                padding: 4px;
            }}
        """) 

class MicLevelWidget(QWidget):
    """Widget to display microphone level"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.level = 0.0
        self.setMinimumSize(100, 20)
        self.setMaximumHeight(20)
        
    def set_level(self, level: float):
        """Update mic level"""
        self.level = level
        self.update()
        
    def paintEvent(self, event):
        """Paint the mic level visualization"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw background
        painter.fillRect(self.rect(), QColor("#2d2d2d"))
        
        # Draw level bar
        width = int(self.width() * self.level)
        painter.fillRect(0, 0, width, self.height(), QColor("#28a745"))
        
        # Draw peak marker
        if self.level > 0.8:
            painter.setPen(QPen(QColor("#dc3545"), 2))
            painter.drawLine(width, 0, width, self.height())

class CommandHistoryWidget(QWidget):
    """Widget to display command history"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        """Setup command history UI"""
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("Recent Commands")
        title.setStyleSheet("font-weight: bold;")
        layout.addWidget(title)
        
        # History display
        self.history_display = QTextEdit()
        self.history_display.setReadOnly(True)
        self.history_display.setMaximumHeight(150)
        layout.addWidget(self.history_display)
        
        self.setLayout(layout)
        
    def update_history(self, history: List[Dict[str, Any]]):
        """Update command history display"""
        if not history:
            self.history_display.clear()
            return
            
        lines = []
        for cmd in history:
            timestamp = datetime.fromtimestamp(cmd["timestamp"]).strftime("%H:%M:%S")
            lines.append(f"[{timestamp}] {cmd['command']}")
            
        self.history_display.setText("\n".join(lines))

class VoiceCommandWidget(QWidget):
    """Widget for voice command input"""
    
    def __init__(self, inbox_base: Path, model_path: Path, parent=None):
        super().__init__(parent)
        self.voice_handler = VoiceCommandHandler(inbox_base, model_path, self)
        self.setup_ui()
        self.connect_signals()
        
    def setup_ui(self):
        """Setup voice command UI"""
        layout = QVBoxLayout()
        
        # Status and controls
        control_layout = QHBoxLayout()
        
        # Record button
        self.record_button = QPushButton("🎤 Record Command")
        self.record_button.clicked.connect(self.start_recording)
        control_layout.addWidget(self.record_button)
        
        # Hotkey hint
        hotkey_label = QLabel("(Ctrl+Shift+R)")
        hotkey_label.setStyleSheet("color: #6c757d;")
        control_layout.addWidget(hotkey_label)
        
        control_layout.addStretch()
        layout.addLayout(control_layout)
        
        # Mic level
        self.mic_level = MicLevelWidget()
        layout.addWidget(self.mic_level)
        
        # Status label
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        layout.addWidget(self.progress)
        
        # Transcript display
        transcript_label = QLabel("Transcript:")
        layout.addWidget(transcript_label)
        
        self.transcript_display = QTextEdit()
        self.transcript_display.setReadOnly(True)
        self.transcript_display.setMaximumHeight(100)
        layout.addWidget(self.transcript_display)
        
        # Command history
        self.history_widget = CommandHistoryWidget()
        layout.addWidget(self.history_widget)
        
        self.setLayout(layout)
        
    def connect_signals(self):
        """Connect voice handler signals"""
        self.voice_handler.recording_started.connect(self.on_recording_started)
        self.voice_handler.recording_stopped.connect(self.on_recording_stopped)
        self.voice_handler.transcription_complete.connect(self.on_transcription_complete)
        self.voice_handler.command_parsed.connect(self.on_command_parsed)
        self.voice_handler.error_occurred.connect(self.on_error)
        self.voice_handler.mic_level_updated.connect(self.on_mic_level_updated)
        
    @pyqtSlot()
    def start_recording(self):
        """Start voice command recording"""
        self.record_button.setEnabled(False)
        self.status_label.setText("Recording...")
        self.progress.setValue(0)
        self.voice_handler.start_recording()
        
    @pyqtSlot()
    def on_recording_started(self):
        """Handle recording started"""
        self.status_label.setText("Recording...")
        self.progress.setValue(25)
        
    @pyqtSlot()
    def on_recording_stopped(self):
        """Handle recording stopped"""
        self.status_label.setText("Transcribing...")
        self.progress.setValue(50)
        
    @pyqtSlot(str)
    def on_transcription_complete(self, transcript: str):
        """Handle transcription complete"""
        self.transcript_display.setText(transcript)
        self.status_label.setText("Processing command...")
        self.progress.setValue(75)
        
    @pyqtSlot(str, str)
    def on_command_parsed(self, agent_id: str, command: str):
        """Handle command parsed"""
        self.status_label.setText(f"Command sent to {agent_id}")
        self.progress.setValue(100)
        self.record_button.setEnabled(True)
        
        # Update command history
        history = self.voice_handler.get_command_history(agent_id)
        self.history_widget.update_history(history)
        
    @pyqtSlot(str)
    def on_error(self, error: str):
        """Handle error"""
        self.status_label.setText(f"Error: {error}")
        self.progress.setValue(0)
        self.record_button.setEnabled(True)
        
    @pyqtSlot(float)
    def on_mic_level_updated(self, level: float):
        """Handle mic level update"""
        self.mic_level.set_level(level) 

class EpisodeMetricsTab(QWidget):
    """Widget to display episode metrics and status"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_metrics)
        self.refresh_timer.start(5000)  # Refresh every 5 seconds
        
        # Initialize notifier
        self.notifier = Notifier(Path("runtime/config/notifier_config.json"))
        # Don't initialize notifier here - it will be initialized when needed
        
    def setup_ui(self):
        """Setup episode metrics UI"""
        layout = QVBoxLayout()
        
        # Status Overview
        status_group = QGroupBox("Episode Status")
        status_layout = QGridLayout()
        
        # THEA Status
        self.thea_status = QLabel("THEA: Active")
        self.thea_status.setStyleSheet("color: #28a745; font-weight: bold;")
        status_layout.addWidget(QLabel("THEA Oversight:"), 0, 0)
        status_layout.addWidget(self.thea_status, 0, 1)
        
        # Monitoring Status
        self.monitor_status = QLabel("Monitoring: Online")
        self.monitor_status.setStyleSheet("color: #28a745; font-weight: bold;")
        status_layout.addWidget(QLabel("Live Monitoring:"), 1, 0)
        status_layout.addWidget(self.monitor_status, 1, 1)
        
        # Midnight Runner Status
        self.runner_status = QLabel("Midnight Runner: Active")
        self.runner_status.setStyleSheet("color: #28a745; font-weight: bold;")
        status_layout.addWidget(QLabel("Midnight Runner:"), 2, 0)
        status_layout.addWidget(self.runner_status, 2, 1)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # Metrics Display
        metrics_group = QGroupBox("Episode Metrics")
        metrics_layout = QVBoxLayout()
        
        # THEA Metrics
        thea_metrics = QGroupBox("THEA Oversight")
        thea_layout = QGridLayout()
        
        self.ping_count = QLabel("Pings: 0")
        self.confidence = QLabel("Confidence: 100%")
        self.drift_count = QLabel("Drift Events: 0")
        self.escalations = QLabel("Escalations: 0")
        
        thea_layout.addWidget(QLabel("Ping Count:"), 0, 0)
        thea_layout.addWidget(self.ping_count, 0, 1)
        thea_layout.addWidget(QLabel("Confidence:"), 1, 0)
        thea_layout.addWidget(self.confidence, 1, 1)
        thea_layout.addWidget(QLabel("Drift Events:"), 2, 0)
        thea_layout.addWidget(self.drift_count, 2, 1)
        thea_layout.addWidget(QLabel("Escalations:"), 3, 0)
        thea_layout.addWidget(self.escalations, 3, 1)
        
        thea_metrics.setLayout(thea_layout)
        metrics_layout.addWidget(thea_metrics)
        
        # Agent Metrics
        agent_metrics = QGroupBox("Agent Activity")
        agent_layout = QGridLayout()
        
        self.active_agents = QLabel("Active Agents: 0")
        self.completed_tasks = QLabel("Completed Tasks: 0")
        self.pending_tasks = QLabel("Pending Tasks: 0")
        self.failed_tasks = QLabel("Failed Tasks: 0")
        
        agent_layout.addWidget(QLabel("Active Agents:"), 0, 0)
        agent_layout.addWidget(self.active_agents, 0, 1)
        agent_layout.addWidget(QLabel("Completed Tasks:"), 1, 0)
        agent_layout.addWidget(self.completed_tasks, 1, 1)
        agent_layout.addWidget(QLabel("Pending Tasks:"), 2, 0)
        agent_layout.addWidget(self.pending_tasks, 2, 1)
        agent_layout.addWidget(QLabel("Failed Tasks:"), 3, 0)
        agent_layout.addWidget(self.failed_tasks, 3, 1)
        
        agent_metrics.setLayout(agent_layout)
        metrics_layout.addWidget(agent_metrics)
        
        metrics_group.setLayout(metrics_layout)
        layout.addWidget(metrics_group)
        
        # Recent Activity
        activity_group = QGroupBox("Recent Activity")
        activity_layout = QVBoxLayout()
        
        self.activity_display = QTextEdit()
        self.activity_display.setReadOnly(True)
        activity_layout.addWidget(self.activity_display)
        
        activity_group.setLayout(activity_layout)
        layout.addWidget(activity_group)
        
        # Add last updated label
        self.last_updated_label = QLabel("Last Updated: —")
        self.last_updated_label.setAlignment(Qt.AlignRight)
        layout.addWidget(self.last_updated_label)
        
        self.setLayout(layout)
        
    def set_waiting_state(self):
        """Set all fields to 'Waiting for data…'"""
        waiting = "Waiting for data…"
        self.thea_status.setText(waiting)
        self.monitor_status.setText(waiting)
        self.runner_status.setText(waiting)
        self.ping_count.setText(waiting)
        self.confidence.setText(waiting)
        self.drift_count.setText(waiting)
        self.escalations.setText(waiting)
        self.active_agents.setText(waiting)
        self.completed_tasks.setText(waiting)
        self.pending_tasks.setText(waiting)
        self.failed_tasks.setText(waiting)
        self.activity_display.setText(waiting)

    def refresh_metrics(self):
        """Refresh episode metrics from status files"""
        try:
            # Load episode status
            status_path = Path("runtime/state/episode_05_status.json")
            status = {}
            updated = False
            if status_path.exists():
                try:
                    status = json.loads(status_path.read_text())
                    updated = True
                except json.JSONDecodeError:
                    print(f"Error parsing status file: {status_path}")
            
            if not status:
                self.set_waiting_state()
                self.last_updated_label.setText("Last Updated: —")
                return
            
            # Update THEA metrics with defaults if missing
            thea_metrics = status.get("thea_metrics", {})
            if not thea_metrics:
                self.ping_count.setText("Waiting for data…")
                self.confidence.setText("Waiting for data…")
                self.drift_count.setText("Waiting for data…")
                self.escalations.setText("Waiting for data…")
            else:
                self.ping_count.setText(f"Pings: {thea_metrics.get('ping_count', 0)}")
                self.confidence.setText(f"Confidence: {thea_metrics.get('confidence', 100)}%")
                self.drift_count.setText(f"Drift Events: {thea_metrics.get('drift_count', 0)}")
                self.escalations.setText(f"Escalations: {thea_metrics.get('escalations', 0)}")
            
            # Check for drift and send alert if needed
            confidence = thea_metrics.get('confidence', 100)
            if confidence < self.notifier.config["alert_thresholds"].get("drift_confidence", 100):
                # Initialize notifier if needed
                if not self.notifier.session:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        loop.create_task(self.notifier.initialize())
                    else:
                        loop.run_until_complete(self.notifier.initialize())
                # Send alert
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.notifier.alert_drift_detected(
                        confidence,
                        "THEA confidence below threshold"
                    ))
            
            # Update agent metrics with defaults if missing
            agent_metrics = status.get("agent_metrics", {})
            if not agent_metrics:
                self.active_agents.setText("Waiting for data…")
                self.completed_tasks.setText("Waiting for data…")
                self.pending_tasks.setText("Waiting for data…")
                self.failed_tasks.setText("Waiting for data…")
            else:
                self.active_agents.setText(f"Active Agents: {agent_metrics.get('active_agents', 0)}")
                self.completed_tasks.setText(f"Completed Tasks: {agent_metrics.get('completed_tasks', 0)}")
                self.pending_tasks.setText(f"Pending Tasks: {agent_metrics.get('pending_tasks', 0)}")
                self.failed_tasks.setText(f"Failed Tasks: {agent_metrics.get('failed_tasks', 0)}")
            
            # Check system metrics with defaults if missing
            system_metrics = status.get("system_metrics", {})
            memory_usage = system_metrics.get("memory_usage", 0)
            cpu_usage = system_metrics.get("cpu_usage", 0)
            
            if memory_usage > self.notifier.config["alert_thresholds"].get("memory_usage", 90):
                # Initialize notifier if needed
                if not self.notifier.session:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        loop.create_task(self.notifier.initialize())
                    else:
                        loop.run_until_complete(self.notifier.initialize())
                # Send alert
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.notifier.alert_resource_warning(
                        "Memory",
                        memory_usage
                    ))
            if cpu_usage > self.notifier.config["alert_thresholds"].get("cpu_usage", 90):
                # Initialize notifier if needed
                if not self.notifier.session:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        loop.create_task(self.notifier.initialize())
                    else:
                        loop.run_until_complete(self.notifier.initialize())
                # Send alert
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.notifier.alert_resource_warning(
                        "CPU",
                        cpu_usage
                    ))
            
            # Update activity log if exists
            log_path = Path("runtime/logs/episode_05.log")
            if log_path.exists():
                try:
                    recent_activity = log_path.read_text().splitlines()[-10:]  # Last 10 lines
                    if recent_activity:
                        self.activity_display.setText("\n".join(recent_activity))
                    else:
                        self.activity_display.setText("Waiting for data…")
                except Exception as e:
                    print(f"Error reading activity log: {e}")
                    self.activity_display.setText("Waiting for data…")
            else:
                self.activity_display.setText("Waiting for data…")
                
            # If we got here, data was found
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.last_updated_label.setText(f"Last Updated: {now}")
            
        except Exception as e:
            print(f"Error refreshing metrics: {e}")
            self.set_waiting_state()
            self.last_updated_label.setText("Last Updated: —")
        
    def closeEvent(self, event):
        """Clean up resources when widget is closed"""
        if self.notifier.session:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.notifier.close())
            else:
                loop.run_until_complete(self.notifier.close())
        super().closeEvent(event) 