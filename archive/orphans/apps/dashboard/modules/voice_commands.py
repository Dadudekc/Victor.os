import asyncio
import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import sounddevice as sd
import soundfile as sf
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QShortcut


class VoiceCommandHandler(QObject):
    """Handles voice command processing and routing"""

    # Signals
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()
    transcription_complete = pyqtSignal(str)
    command_parsed = pyqtSignal(str, str)  # agent_id, command
    error_occurred = pyqtSignal(str)
    mic_level_updated = pyqtSignal(float)  # 0.0 to 1.0

    def __init__(self, inbox_base: Path, model_path: Path, parent=None):
        super().__init__(parent)
        self.inbox_base = inbox_base
        self.model_path = model_path
        self.audio_file = inbox_base.parent / "audio" / "command.wav"
        self.audio_file.parent.mkdir(parents=True, exist_ok=True)
        self.command_history = {}  # agent_id -> list of commands

        # Command templates as instance variable
        self.command_templates = {
            "scan": {
                "pattern": r"scan\s+(.+)(?:\s+and\s+escalate)?",
                "template": "Scan {target} and report findings",
            },
            "validate": {
                "pattern": r"validate\s+(.+)(?:\s+for\s+errors)?",
                "template": "Validate {target} for errors and inconsistencies",
            },
            "summarize": {
                "pattern": r"summarize\s+(.+)(?:\s+for\s+me)?",
                "template": "Summarize {target} and provide key insights",
            },
            "escalate": {
                "pattern": r"escalate\s+(.+)(?:\s+to\s+thea)?",
                "template": "Escalate {target} to THEA for review",
            },
        }

        self._validate_command_templates()  # Validate templates on init
        self.setup_hotkeys()

    def _validate_command_templates(self):
        """Validate command templates for proper pattern matching"""
        for cmd_name, template_info in self.command_templates.items():
            pattern = template_info["pattern"]
            if "(.+?)" in pattern:
                raise ValueError(
                    f"Non-greedy pattern in {cmd_name} template. Use (.+) instead of (.+?)"
                )
            # Test pattern with sample input
            test_input = f"{cmd_name} test target"
            if not re.search(pattern, test_input):
                raise ValueError(
                    f"Pattern for {cmd_name} does not match basic input: {test_input}"
                )

    def setup_hotkeys(self):
        """Setup keyboard shortcuts"""
        if self.parent():
            # Record command shortcut
            self.record_shortcut = QShortcut(
                QKeySequence("Ctrl+Shift+R"), self.parent()
            )
            self.record_shortcut.activated.connect(self.start_recording)

            # Clear transcript shortcut
            self.clear_shortcut = QShortcut(QKeySequence("Ctrl+Shift+C"), self.parent())
            self.clear_shortcut.activated.connect(self.clear_transcript)

    def start_recording(self):
        """Start recording (can be triggered by hotkey)"""
        asyncio.create_task(self.process_voice_command())

    def clear_transcript(self):
        """Clear the transcript display"""
        if hasattr(self.parent(), "transcript_display"):
            self.parent().transcript_display.clear()

    async def process_voice_command(self) -> None:
        """Process a voice command through the full pipeline"""
        try:
            # Record audio
            self.recording_started.emit()
            await self.record_audio()
            self.recording_stopped.emit()

            # Transcribe
            transcript = await self.transcribe()
            self.transcription_complete.emit(transcript)

            # Parse and route
            agent_id, command = self.parse_agent_command(transcript)
            if agent_id and command:
                self.command_parsed.emit(agent_id, command)
                await self.inject_to_inbox(agent_id, command)
            else:
                self.error_occurred.emit("No agent command recognized")

        except Exception as e:
            self.error_occurred.emit(f"Error processing voice command: {e}")

    async def record_audio(self, seconds: int = 5) -> None:
        """Record audio from microphone with level monitoring"""
        try:
            fs = 16000  # Sample rate
            data = sd.rec(int(seconds * fs), samplerate=fs, channels=1)

            # Monitor audio levels during recording
            while sd.get_stream().active:
                level = np.abs(data).mean()
                self.mic_level_updated.emit(
                    min(1.0, level * 10)
                )  # Scale for visibility
                await asyncio.sleep(0.1)

            sd.wait()
            sf.write(self.audio_file, data, fs)
        except Exception as e:
            raise Exception(f"Error recording audio: {e}")

    async def transcribe(self) -> str:
        """Transcribe audio using whisper.cpp"""
        try:
            result = subprocess.run(
                [
                    "./whisper.cpp/main",
                    "-m",
                    str(self.model_path),
                    "-f",
                    str(self.audio_file),
                    "-otxt",
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                raise Exception(f"Transcription failed: {result.stderr}")

            # Read transcription from output file
            txt_file = self.audio_file.with_suffix(".txt")
            if not txt_file.exists():
                raise Exception("Transcription output file not found")

            return txt_file.read_text().strip()

        except Exception as e:
            raise Exception(f"Error transcribing audio: {e}")

    def parse_agent_command(
        self, transcript: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """Parse agent command from transcript with robust regex"""
        # Improved regex: agent 1: scan the logs
        match = re.match(r"agent\s*-?(\d+)[:\s]+(.+)", transcript.lower())
        if not match:
            return None, None
        agent_id = f"Agent-{match.group(1)}"
        command = match.group(2).strip()
        # Try to match command templates
        for template_name, template_info in self.command_templates.items():
            cmd_match = re.search(template_info["pattern"], command.lower())
            if cmd_match:
                target = cmd_match.group(1)
                formatted_command = template_info["template"].format(target=target)
                self._add_to_history(agent_id, formatted_command)
                return agent_id, formatted_command
        self._add_to_history(agent_id, command)
        return agent_id, command

    def _add_to_history(self, agent_id: str, command: str):
        """Add command to history"""
        if agent_id not in self.command_history:
            self.command_history[agent_id] = []
        self.command_history[agent_id].append(
            {"command": command, "timestamp": time.time()}
        )
        # Keep only last 10 commands
        self.command_history[agent_id] = self.command_history[agent_id][-10:]

    def get_command_history(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get command history for an agent"""
        return self.command_history.get(agent_id, [])

    async def inject_to_inbox(self, agent_id: str, command: str) -> None:
        """Inject command into agent's inbox using standardized message format and flush write."""
        try:
            inbox_path = self.inbox_base / agent_id / "inbox.json"
            inbox_path.parent.mkdir(parents=True, exist_ok=True)
            # Load existing messages
            existing = []
            if inbox_path.exists():
                try:
                    existing = json.loads(inbox_path.read_text())
                except json.JSONDecodeError:
                    pass
            # Create standardized message
            command_msg = {
                "message_id": f"voice-{int(time.time())}",
                "sender_agent_id": "voice_command",
                "recipient_agent_id": agent_id,
                "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "subject": f"Voice Command: {command[:50]}...",
                "type": "COMMAND",
                "body": {
                    "command": command,
                    "source": "voice_input",
                    "original_transcript": command,
                },
                "priority": "MEDIUM",
            }
            existing.append(command_msg)
            # Write back to inbox with flush and fsync
            with open(inbox_path, "w") as f:
                json.dump(existing, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
        except Exception as e:
            raise Exception(f"Error injecting command to inbox: {e}")

    def _validate_mailbox_message(self, message: dict) -> bool:
        """Validate a mailbox message against the standard format"""
        required_fields = [
            "message_id",
            "sender_agent_id",
            "recipient_agent_id",
            "timestamp_utc",
            "subject",
            "type",
            "body",
        ]
        return all(field in message for field in required_fields)

    def _convert_legacy_message(self, message: dict) -> dict:
        """Convert a legacy message format to the new standard format"""
        if "id" in message and "type" in message and "content" in message:
            return {
                "message_id": message["id"],
                "sender_agent_id": message.get("sender", "unknown"),
                "recipient_agent_id": message.get("recipient", "unknown"),
                "timestamp_utc": time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ",
                    time.gmtime(message.get("timestamp", time.time())),
                ),
                "subject": f"Legacy Message: {message['type']}",
                "type": message["type"].upper(),
                "body": {"content": message["content"], "original_format": "legacy"},
                "priority": message.get("priority", "MEDIUM"),
            }
        return message

    def cleanup(self) -> None:
        """Clean up temporary files"""
        try:
            if self.audio_file.exists():
                self.audio_file.unlink()
            txt_file = self.audio_file.with_suffix(".txt")
            if txt_file.exists():
                txt_file.unlink()
        except Exception as e:
            print(f"Error cleaning up files: {e}")
