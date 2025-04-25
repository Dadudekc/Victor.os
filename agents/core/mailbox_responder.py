# agents/mailbox_responder.py
import os, json, time
from core.hooks.chatgpt_responder import ChatGPTResponder

MAILBOX_PATH = os.path.join(os.path.dirname(__file__), "..", "_agent_coordination", "shared_mailboxes")

if __name__ == "__main__":
    responder = ChatGPTResponder(dev_mode=True)
    print("📬 AgentMailboxResponderLoop started.")
    while True:
        for fname in os.listdir(MAILBOX_PATH):
            if not fname.startswith("mailbox_") or not fname.endswith(".json"):
                continue
            fpath = os.path.join(MAILBOX_PATH, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # skip if already responded
                if any("ChatGPTResponder" in m.get("sender", "") for m in data.get("messages", [])):
                    continue
                # generate response
                updated = responder.respond_to_mailbox(data)
                with open(fpath, "w", encoding="utf-8") as f:
                    json.dump(updated, f, indent=2)
            except Exception as e:
                print(f"⚠️ Error processing {fname}: {e}")
        time.sleep(3) 