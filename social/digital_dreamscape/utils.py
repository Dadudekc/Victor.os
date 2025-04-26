import json, datetime, logging, typing
from PyQt6.QtCore import pyqtSignal, QObject
import os, requests, textwrap
import yaml, pathlib
import jinja2

# --- Setup Jinja2 Environment ---
# Assume templates are in 'discord_templates' relative to project root
# Need to determine project root reliably. Assuming utils.py is one level down.
_project_root = pathlib.Path(__file__).parent.parent 
_template_loader = jinja2.FileSystemLoader(searchpath= _project_root / "discord_templates")
_jinja_env = jinja2.Environment(
    loader=_template_loader, 
    autoescape=jinja2.select_autoescape(['html', 'xml']), # Basic autoescape
    trim_blocks=True, 
    lstrip_blocks=True
)
# --------------------------------

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
    def __init__(self):
        super().__init__()
        self._emitter = QtLogEmitter()
        self.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))

    def emit(self, record: logging.LogRecord):
        msg = self.format(record)
        self._emitter.log_signal.emit(msg)

def post_to_discord(
    content: str | None = None, 
    template: str | None = None,
    template_context: dict | None = None,
    webhook: str | None = None
) -> bool:
    """
    Sends message to Discord.
    Can send raw `content` OR render a `template` using `template_context`.
    Splits into ≤2000‑char chunks to respect Discord limits.
    """
    webhook = webhook or os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook:
        logging.warning("Discord webhook not set; skipping post")
        return False

    message_content = ""
    if template:
        if template_context is None: template_context = {}
        try:
            jinja_template = _jinja_env.get_template(template) 
            message_content = jinja_template.render(template_context)
            logging.info(f"Rendered Discord template '{template}'")
        except jinja2.TemplateNotFound:
            logging.error(f"Discord template '{template}' not found.")
            return False
        except Exception as e:
            logging.error(f"Error rendering Discord template '{template}': {e}", exc_info=True)
            return False
    elif content:
        message_content = content
    else:
        logging.warning("post_to_discord called with no content or template.")
        return False

    if not message_content.strip():
        logging.warning("post_to_discord: Resulting message content is empty.")
        return False

    # basic 2‑k chunking
    chunks = textwrap.wrap(message_content, width=1990, break_long_words=False, replace_whitespace=False)
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

# --- Filename Sanitization ---
def sanitize_filename(filename: str) -> str:
    """Replaces potentially problematic filename characters with underscores.
    
    Also trims leading/trailing underscores and limits length to 50 chars.
    """
    import re # Import regex module locally
    # Remove or replace invalid characters
    sanitized = re.sub(r'[\/*?:"<>| ]+', "_", filename)
    # Trim leading/trailing underscores that might result from replacements
    sanitized = sanitized.strip("_")
    # Limit length
    return sanitized[:50] 
