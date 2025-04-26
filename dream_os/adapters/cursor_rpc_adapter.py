import os
import requests
from typing import Any
from .base_adapter import Adapter

class CursorRPCAdapter(Adapter):
    def __init__(self, host: str = None, port: int = None):
        self.host = host or os.getenv('CURSOR_RPC_HOST', 'localhost')
        self.port = port or int(os.getenv('CURSOR_RPC_PORT', 8765))
        self.url = f"http://{self.host}:{self.port}/execute"

    def execute(self, payload: Any) -> Any:
        """
        Execute a request to the local Cursor RPC endpoint with JSON payload.
        """
        response = requests.post(self.url, json=payload)
        response.raise_for_status()
        return response.json() 
