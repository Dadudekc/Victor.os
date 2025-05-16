"""
Cursor Agent Autonomy Loop Template
-----------------------------------
Drop this script into a Cursor agent prompt or wrap it in your agent's
main loop. It handles:
  • Heartbeat status emission
  • Devlog syncing
  • Drift detection & self‑resume
  • THEA escalation hook
  • Discord/Slack notifications
Customize AGENT_ID, paths, and bridge hooks as needed.
"""

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))
import asyncio
import datetime
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from src.dreamos.agents.utils.agent_status_utils import (
        append_devlog,
        check_drift,
        update_status,
    )
except ImportError:
    from dreamos.agents.utils.agent_status_utils import (
        append_devlog,
        check_drift,
        update_status,
    )

# === CONFIG ===
AGENT_ID = os.getenv("AGENT_ID", "Agent-1")
STATUS_PATH = Path(f"runtime/agent_comms/agent_mailboxes/{AGENT_ID}/status.json")
DEVLOG_PATH = Path(f"runtime/devlog/agents/{AGENT_ID}.md")
NOTIFIER_CONFIG = Path("runtime/config/notifier_config.json")
DRIFT_THRESHOLD_SECS = 300        # 5‑minute idle threshold
MAIN_LOOP_INTERVAL = 30           # seconds
RESUME_PROMPT = "resume autonomy"
BRIDGE_API_FILE = Path("runtime/bridge/queue/agent_prompts.jsonl")  # simple file‑based queue

# Ensure directories exist
STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
DEVLOG_PATH.parent.mkdir(parents=True, exist_ok=True)
BRIDGE_API_FILE.parent.mkdir(parents=True, exist_ok=True)

class AgentNotifier:
    def __init__(self, config_path: Path):
        self.config = self._load_config(config_path)
        self.session = None
        
    def _load_config(self, config_path: Path) -> Dict[str, Any]:
        """Load notification configuration"""
        if not config_path.exists():
            raise FileNotFoundError(f"Notification config not found at {config_path}")
        try:
            return json.loads(config_path.read_text(encoding='utf-8'))
        except UnicodeDecodeError:
            return json.loads(config_path.read_text(encoding='ascii', errors='ignore'))
            
    async def initialize(self):
        """Initialize HTTP session"""
        if not self.session:
            import aiohttp
            self.session = aiohttp.ClientSession()
            
    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None
            
    async def send_alert(self, 
                        level: str,
                        title: str,
                        message: str,
                        fields: Optional[Dict[str, str]] = None) -> None:
        """Send alert to configured platforms"""
        if not self.session:
            await self.initialize()
            
        # Prepare alert data
        alert_data = {
            "level": level,
            "title": title,
            "message": message,
            "fields": fields or {},
            "link": self.config["dashboard_url"],
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "episode": self.config["episode"]
        }
        
        # Send to Discord if enabled
        if self.config["discord"]["enabled"] and self.config["discord"]["webhook_url"]:
            try:
                await self._send_discord_alert(alert_data)
            except Exception as e:
                print(f"Discord alert failed: {e}")
            
        # Send to Slack if enabled
        if self.config["slack"]["enabled"] and self.config["slack"]["webhook_url"]:
            try:
                await self._send_slack_alert(alert_data)
            except Exception as e:
                print(f"Slack alert failed: {e}")
                
    async def _send_discord_alert(self, alert_data: Dict[str, Any]) -> None:
        """Send alert to Discord"""
        discord_config = self.config["discord"]
        level_config = discord_config["alert_levels"][alert_data["level"]]
        
        # Prepare Discord embed
        embed = {
            "title": f"{level_config['emoji']} {alert_data['title']}",
            "description": alert_data["message"],
            "color": level_config["color"],
            "timestamp": alert_data["timestamp"],
            "fields": [
                {
                    "name": key,
                    "value": value,
                    "inline": True
                }
                for key, value in alert_data["fields"].items()
            ],
            "footer": {
                "text": f"Episode {alert_data['episode']['number']} - {alert_data['episode']['name']}"
            }
        }
        
        # Add dashboard link
        embed["fields"].append({
            "name": "Dashboard",
            "value": f"[Open Dashboard]({alert_data['link']})",
            "inline": False
        })
        
        # Prepare payload
        payload = {
            "username": discord_config["username"],
            "avatar_url": discord_config["avatar_url"],
            "embeds": [embed]
        }
        
        # Send to Discord webhook
        async with self.session.post(
            discord_config["webhook_url"],
            json=payload
        ) as response:
            if response.status != 204:
                print(f"Discord alert failed: {response.status}")
                
    async def _send_slack_alert(self, alert_data: Dict[str, Any]) -> None:
        """Send alert to Slack"""
        slack_config = self.config["slack"]
        level_config = slack_config["alert_levels"][alert_data["level"]]
        
        # Prepare Slack blocks
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{level_config['emoji']} {alert_data['title']}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": alert_data["message"]
                }
            }
        ]
        
        # Add fields
        if alert_data["fields"]:
            fields = []
            for key, value in alert_data["fields"].items():
                fields.append(f"*{key}*: {value}")
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "\n".join(fields)
                }
            })
            
        # Add dashboard link
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"<{alert_data['link']}|Open Dashboard>"
            }
        })
        
        # Add episode info
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Episode {alert_data['episode']['number']} - {alert_data['episode']['name']}"
                }
            ]
        })
        
        # Prepare payload
        payload = {
            "channel": slack_config["channel"],
            "username": slack_config["username"],
            "icon_emoji": slack_config["icon_emoji"],
            "blocks": blocks
        }
        
        # Send to Slack webhook
        async with self.session.post(
            slack_config["webhook_url"],
            json=payload
        ) as response:
            if response.status != 200:
                print(f"Slack alert failed: {response.status}")

last_action_ts = time.time()
compliance_score = 100
notifier = None

def emit_heartbeat(current_task: str = ""):
    payload = {
        "agent_id": AGENT_ID,
        "last_ping": datetime.datetime.utcnow().isoformat() + "Z",
        "current_task": current_task,
        "loop_active": True,
        "compliance_score": compliance_score,
    }
    STATUS_PATH.write_text(json.dumps(payload, indent=2))

def append_devlog(agent_id, mailbox_path, entry):
    with open(DEVLOG_PATH, "a", encoding="utf-8") as f:
        f.write(entry)

def enqueue_resume_prompt():
    """Append a resume prompt into bridge queue for Cursor automation"""
    item = {
        "agent_id": AGENT_ID,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "prompt": RESUME_PROMPT
    }
    with open(BRIDGE_API_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(item) + "\n")
    append_devlog(AGENT_ID, STATUS_PATH.parent, f"🚨 Drift detected; enqueued resume prompt: '{RESUME_PROMPT}'")
    
    # Send drift alert
    if notifier:
        asyncio.create_task(notifier.send_alert(
            level="warning",
            title="Agent Drift Detected",
            message=f"Agent {AGENT_ID} has been idle for {DRIFT_THRESHOLD_SECS} seconds",
            fields={
                "Agent": AGENT_ID,
                "Idle Time": f"{DRIFT_THRESHOLD_SECS} seconds",
                "Action": "Resume prompt enqueued"
            }
        ))

async def main_loop():
    global last_action_ts, notifier
    
    # Initialize notifier
    notifier = AgentNotifier(NOTIFIER_CONFIG)
    await notifier.initialize()
    
    try:
        append_devlog(AGENT_ID, STATUS_PATH.parent, "🔄 Agent autonomy loop STARTED")
        
        # Send startup notification
        await notifier.send_alert(
            level="info",
            title="Agent Started",
            message=f"Agent {AGENT_ID} autonomy loop initialized",
            fields={
                "Agent": AGENT_ID,
                "Status": "Running",
                "Compliance": f"{compliance_score}%"
            }
        )
        
        cycle_count = 0
        while True:
            cycle_count += 1
            # 1. Update status heartbeat
            update_status(AGENT_ID, STATUS_PATH.parent, task="Main loop running", loop_active=True, compliance_score=100)
            # 2. Append devlog entry
            append_devlog(AGENT_ID, STATUS_PATH.parent, f"Cycle {cycle_count}: Heartbeat and devlog updated.")
            # 3. Check for drift
            if check_drift(AGENT_ID, STATUS_PATH.parent, threshold_minutes=5):
                append_devlog(AGENT_ID, STATUS_PATH.parent, f"Cycle {cycle_count}: Drift detected, triggering recovery.")
                enqueue_resume_prompt()
            # 4. Main agent logic would go here
            await asyncio.sleep(MAIN_LOOP_INTERVAL)
            
    except Exception as exc:
        # Send error notification
        await notifier.send_alert(
            level="error",
            title="Agent Error",
            message=f"Unhandled exception in agent loop",
            fields={
                "Agent": AGENT_ID,
                "Error": str(exc)
            }
        )
        append_devlog(AGENT_ID, STATUS_PATH.parent, f"❌ Unhandled exception: {exc}")
        raise
    finally:
        # Send shutdown notification
        await notifier.send_alert(
            level="info",
            title="Agent Stopped",
            message=f"Agent {AGENT_ID} autonomy loop terminated",
            fields={
                "Agent": AGENT_ID,
                "Status": "Stopped",
                "Compliance": f"{compliance_score}%"
            }
        )
        await notifier.close()

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        append_devlog(AGENT_ID, STATUS_PATH.parent, "⏹️ Agent autonomy loop stopped by KeyboardInterrupt") 