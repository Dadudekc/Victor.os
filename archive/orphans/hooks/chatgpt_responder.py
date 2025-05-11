import sys

# import time # F401 Unused
import uuid
from datetime import datetime


class ChatGPTResponder:
    def __init__(self, dev_mode=False):
        self.dev_mode = dev_mode
        self.scraper = None
        self.adapter = None
        if dev_mode:
            try:
                from social.utils.chatgpt_scraper import ChatGPTScraper

                self.scraper = ChatGPTScraper()
            except Exception as e:
                # E501 Fix: Split long line
                print(f"Warning: ChatGPTScraper init failed: {e}", file=sys.stderr)
                self.scraper = None
        else:
            try:
                from dream_os.adapters.openai_adapter import OpenAIAdapter

                self.adapter = OpenAIAdapter()
            except Exception as e:
                # E501 Fix: Split long line
                print(f"Warning: OpenAIAdapter init failed: {e}", file=sys.stderr)
                self.adapter = None

    def get_response(self, message: str) -> str:
        if self.dev_mode:
            if self.scraper:
                return self.scraper.ask(message)
            else:
                # E501 Fix: Split long line
                raise RuntimeError("ChatGPTScraper not available in dev mode")
        else:
            if self.adapter:
                return self.adapter.execute({"prompt": message})
            else:
                raise RuntimeError("OpenAIAdapter not available in prod mode")

    def respond_to_mailbox(self, mailbox_data: dict) -> dict:
        """Processes last user message and appends the GPT reply to messages if responder is available."""  # noqa: E501
        # No-op if no valid responder
        if self.dev_mode and not self.scraper:
            return mailbox_data
        if not self.dev_mode and not self.adapter:
            return mailbox_data
        messages = mailbox_data.get("messages", [])
        if not messages:
            return mailbox_data

        last_user = messages[-1]
        response = self.get_response(last_user["content"])

        reply = {
            "message_id": uuid.uuid4().hex,
            "sender": "ChatGPTResponder",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "content": response,
        }
        messages.append(reply)
        return mailbox_data
