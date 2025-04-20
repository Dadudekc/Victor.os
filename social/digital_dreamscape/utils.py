import json, datetime, logging, typing
from PyQt5.QtCore import pyqtSignal, QObject
import os, requests, textwrap
import yaml, pathlib

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

def load_models_yaml(path="models.yaml") -> list[str]:
    p = pathlib.Path(path)
    if not p.exists():
        logging.warning("models.yaml not found; falling back to defaults")
        return ["gpt-4o", "o4-mini"] # Default fallback
    try:
        with open(p, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        models = data.get("models", [])
        if not isinstance(models, list):
             logging.warning("'models' key in models.yaml is not a list; falling back to defaults")
             return ["gpt-4o", "o4-mini"]
        return [str(m) for m in models] # Ensure strings
    except yaml.YAMLError as e:
        logging.error(f"Error parsing models.yaml: {e}; falling back to defaults")
        return ["gpt-4o", "o4-mini"]
    except Exception as e:
        logging.error(f"Error loading models.yaml: {e}; falling back to defaults")
        return ["gpt-4o", "o4-mini"]

def load_prompt_templates(template_dir="dreamscape_generator/templates") -> dict:
    """Scans a directory for .txt files and loads them as prompt templates."""
    templates = {}
    template_path = pathlib.Path(template_dir)
    if not template_path.is_dir():
        logging.warning(f"Template directory not found: {template_path}")
        return templates # Return empty dict

    logging.info(f"Loading prompt templates from: {template_path}")
    for filepath in template_path.glob("*.txt"):
        try:
            # Use filename without extension as template name
            template_name = filepath.stem 
            content = filepath.read_text(encoding='utf-8')
            templates[template_name] = content
            logging.debug(f"Loaded template: '{template_name}'")
        except Exception as e:
            logging.error(f"Failed to load template {filepath.name}: {e}")
            
    if not templates:
         logging.warning(f"No .txt templates found in {template_path}")
         
    return templates 