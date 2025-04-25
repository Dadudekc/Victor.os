import os
import requests
from typing import Any
from .base_adapter import Adapter

class DiscordAdapter(Adapter):
    def __init__(self, webhook_url: str = None):
        self.webhook_url = webhook_url or os.getenv("DISCORD_WEBHOOK_URL")
        if not self.webhook_url:
            raise ValueError("DISCORD_WEBHOOK_URL environment variable not set")

    def execute(self, payload: Any) -> Any:
        """
        Send a message payload to the Discord webhook.
        Payload can be a string or a dict for advanced embeds.
        """
        if isinstance(payload, str):
            data = {"content": payload}
        elif isinstance(payload, dict):
            data = payload
        else:
            data = {"content": str(payload)}
        response = requests.post(self.webhook_url, json=data)
        response.raise_for_status()
        return {"status": response.status_code} 