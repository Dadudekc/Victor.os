import uuid, time
from datetime import datetime

class ChatGPTResponder:
    def __init__(self, dev_mode=False):
        self.dev_mode = dev_mode
        if dev_mode:
            from social.utils.chatgpt_scraper import ChatGPTScraper
            self.scraper = ChatGPTScraper()
        else:
            from dream_os.adapters.openai_adapter import OpenAIAdapter
            self.adapter = OpenAIAdapter()

    def get_response(self, message: str) -> str:
        if self.dev_mode:
            return self.scraper.ask(message)
        else:
            return self.adapter.execute({"prompt": message})

    def respond_to_mailbox(self, mailbox_data: dict) -> dict:
        """Processes last user message and appends the GPT reply to messages."""
        messages = mailbox_data.get("messages", [])
        if not messages:
            return mailbox_data

        last_user = messages[-1]
        response = self.get_response(last_user["content"])

        reply = {
            "message_id": uuid.uuid4().hex,
            "sender": "ChatGPTResponder",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "content": response
        }
        messages.append(reply)
        return mailbox_data 