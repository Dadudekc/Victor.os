import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import aiohttp


class Notifier:
    def __init__(self, config_path: Path):
        self.config = self._load_config(config_path)
        self.session = None

    def _load_config(self, config_path: Path) -> Dict[str, Any]:
        """Load notification configuration"""
        if not config_path.exists():
            print(
                f"[WARN] Notification config not found at {config_path} -- using defaults, notifications will be disabled."
            )
            return {
                "dashboard_url": "",
                "episode": {"number": 0, "name": "Unknown"},
                "discord": {
                    "enabled": False,
                    "webhook_url": "",
                    "username": "DreamOS",
                    "avatar_url": "",
                    "alert_levels": {
                        "info": {"emoji": "ℹ️", "color": 3447003},
                        "warning": {"emoji": "⚠️", "color": 16776960},
                        "error": {"emoji": "🚨", "color": 15158332},
                    },
                },
                "slack": {
                    "enabled": False,
                    "webhook_url": "",
                    "channel": "",
                    "username": "DreamOS",
                    "icon_emoji": ":robot_face:",
                    "alert_levels": {
                        "info": {"emoji": "ℹ️"},
                        "warning": {"emoji": "⚠️"},
                        "error": {"emoji": "🚨"},
                    },
                },
                "alert_thresholds": {"drift_confidence": 100},
            }
        try:
            # Try UTF-8 first
            return json.loads(config_path.read_text(encoding="utf-8"))
        except UnicodeDecodeError:
            # Fall back to ASCII
            return json.loads(config_path.read_text(encoding="ascii", errors="ignore"))

    async def initialize(self):
        """Initialize HTTP session"""
        if not self.session:
            self.session = aiohttp.ClientSession()

    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None

    async def send_alert(
        self,
        level: str,
        title: str,
        message: str,
        fields: Optional[Dict[str, str]] = None,
        link: Optional[str] = None,
    ) -> None:
        """Send alert to configured platforms"""
        if not self.session:
            await self.initialize()

        # Prepare alert data
        alert_data = {
            "level": level,
            "title": title,
            "message": message,
            "fields": fields or {},
            "link": link or self.config["dashboard_url"],
            "timestamp": datetime.utcnow().isoformat(),
            "episode": self.config["episode"],
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
                {"name": key, "value": value, "inline": True}
                for key, value in alert_data["fields"].items()
            ],
            "footer": {
                "text": f"Episode {alert_data['episode']['number']} - {alert_data['episode']['name']}"
            },
        }

        # Add dashboard link
        embed["fields"].append(
            {
                "name": "Dashboard",
                "value": f"[Open Dashboard]({alert_data['link']})",
                "inline": False,
            }
        )

        # Prepare payload
        payload = {
            "username": discord_config["username"],
            "avatar_url": discord_config["avatar_url"],
            "embeds": [embed],
        }

        # Send to Discord webhook
        async with self.session.post(
            discord_config["webhook_url"], json=payload
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
                    "text": f"{level_config['emoji']} {alert_data['title']}",
                },
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": alert_data["message"]},
            },
        ]

        # Add fields
        if alert_data["fields"]:
            fields = []
            for key, value in alert_data["fields"].items():
                fields.append(f"*{key}*: {value}")
            blocks.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "\n".join(fields)},
                }
            )

        # Add dashboard link
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"<{alert_data['link']}|Open Dashboard>",
                },
            }
        )

        # Add episode info
        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Episode {alert_data['episode']['number']} - {alert_data['episode']['name']}",
                    }
                ],
            }
        )

        # Prepare payload
        payload = {
            "channel": slack_config["channel"],
            "username": slack_config["username"],
            "icon_emoji": slack_config["icon_emoji"],
            "blocks": blocks,
        }

        # Send to Slack webhook
        async with self.session.post(
            slack_config["webhook_url"], json=payload
        ) as response:
            if response.status != 200:
                print(f"Slack alert failed: {response.status}")

    async def alert_thea_escalation(
        self, agent_id: str, task_id: str, reason: str
    ) -> None:
        """Alert on THEA escalation"""
        await self.send_alert(
            level="error",
            title="THEA Escalation",
            message=f"Task {task_id} from {agent_id} escalated to THEA",
            fields={"Agent": agent_id, "Task": task_id, "Reason": reason},
        )

    async def alert_drift_detected(self, confidence: float, details: str) -> None:
        """Alert on drift detection"""
        level = (
            "warning"
            if confidence >= self.config["alert_thresholds"]["drift_confidence"]
            else "error"
        )
        await self.send_alert(
            level=level,
            title="Drift Detected",
            message=f"System drift detected with {confidence}% confidence",
            fields={"Confidence": f"{confidence}%", "Details": details},
        )

    async def alert_loop_halt(self, agent_id: str, reason: str) -> None:
        """Alert on loop halt"""
        await self.send_alert(
            level="error",
            title="Loop Halt",
            message=f"Agent {agent_id} loop halted",
            fields={"Agent": agent_id, "Reason": reason},
        )

    async def alert_resource_warning(self, resource: str, usage: float) -> None:
        """Alert on resource usage warning"""
        await self.send_alert(
            level="warning",
            title="Resource Warning",
            message=f"High {resource} usage detected",
            fields={"Resource": resource, "Usage": f"{usage}%"},
        )
