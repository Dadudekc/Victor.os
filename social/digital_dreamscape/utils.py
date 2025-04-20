import json, datetime, logging, typing
from PyQt5.QtCore import pyqtSignal, QObject
import os, requests, textwrap

# --- event logger -----------------------------------------------------------
def log_event(tag, who, payload):
    entry = {
        "ts": datetime.datetime.now().isoformat(),
        "tag": tag, "who": who, "payload": payload,
    }
    with open("logs/generation_log.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")

# --- Qt‑aware logging handler ----------------------------------------------
class QtLogEmitter(QObject):
    log_signal = pyqtSignal(str)

class GuiLogHandler(logging.Handler):
    """
    Emits each formatted record via Qt signal so the GUI thread
    can safely append to a QTextEdit.
    """
    _emitter = QtLogEmitter()

    def __init__(self):
        super().__init__()
        self.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))

    def emit(self, record: logging.LogRecord):
        msg = self.format(record)
        self._emitter.log_signal.emit(msg)

def post_to_discord(content: str, webhook: str | None = None) -> bool:
    """
    Sends `content` to a Discord channel via webhook.
    Splits into ≤2000‑char chunks to respect Discord limits.
    """
    webhook = webhook or os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook:
        logging.warning("Discord webhook not set; skipping post")
        return False

    # basic 2‑k chunking
    chunks = textwrap.wrap(content, width=1990, break_long_words=False, replace_whitespace=False)
    for chunk in chunks:
        resp = requests.post(webhook, json={"content": chunk})
        if resp.status_code >= 300:
            logging.error("Discord post failed (%s): %s", resp.status_code, resp.text)
            return False
    logging.info("Posted %s chunk(s) to Discord", len(chunks))
    return True 