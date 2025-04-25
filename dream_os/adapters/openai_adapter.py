import os
import openai
from typing import Any
from .base_adapter import Adapter

class OpenAIAdapter(Adapter):
    def __init__(self, model: str = None):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        openai.api_key = self.api_key
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

    def execute(self, payload: Any) -> Any:
        """
        Execute an OpenAI completion request.
        Payload can include:
          - 'messages': list of chat messages for ChatCompletion
          - 'prompt': text for Completion
        Additional OpenAI parameters can be passed in payload.
        """
        if not isinstance(payload, dict):
            raise ValueError("Payload must be a dict for OpenAIAdapter")
        # ChatCompletion
        if "messages" in payload:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=payload["messages"],
                **{k: v for k, v in payload.items() if k not in ["messages"]}
            )
            return response.choices[0].message.content
        # Text Completion
        elif "prompt" in payload:
            response = openai.Completion.create(
                model=self.model,
                prompt=payload["prompt"],
                **{k: v for k, v in payload.items() if k not in ["prompt"]}
            )
            return response.choices[0].text
        else:
            raise ValueError("Payload must contain 'prompt' or 'messages'") 