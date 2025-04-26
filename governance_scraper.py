import os
import json
import glob
from pathlib import Path

# Constants that can be overridden by tests
AGENT_COORD_DIR = "./_agent_coordination"
GOVERNANCE_LOG_FILE = "governance_memory.jsonl"
RULEBOOK_PATH = "rulebook.md"
PROPOSAL_FILE = "rulebook_update_proposals.md"
REFLECTION_LOG_PATTERN = os.path.join(AGENT_COORD_DIR, "*", "reflection", "reflection_log.md")

# Configuration defaults
RECENT_HOURS = 24
MAX_LOG_LINES = 100


def load_recent_governance_events(max_lines=MAX_LOG_LINES):
    """Load recent governance events from a JSONL file."""
    events = []
    try:
        with open(GOVERNANCE_LOG_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()[-max_lines:]
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        return []
    return events


def load_recent_reflections(max_reflections=None):
    """Load recent reflection entries from multiple agent directories."""
    files = sorted(glob.glob(REFLECTION_LOG_PATTERN))
    reflections = []
    for filepath in files:
        try:
            text = Path(filepath).read_text(encoding='utf-8')
            # Parse alert_id
            alert_id = None
            for line in text.splitlines():
                if line.startswith("**Alert ID:**"):
                    alert_id = line.split("**Alert ID:**", 1)[1].strip()
                    break
            if alert_id:
                reflections.append({"alert_id": alert_id})
        except Exception:
            continue
    if max_reflections is not None:
        return reflections[:max_reflections]
    return reflections


def load_proposals(status_filter=None):
    """Load proposals from a Markdown file, optionally filtering by status."""
    proposals = []
    try:
        content = Path(PROPOSAL_FILE).read_text(encoding='utf-8')
        blocks = content.split("---")
        for block in blocks:
            block = block.strip()
            if not block:
                continue
            pid = None
            status = None
            for line in block.splitlines():
                if line.startswith("## Proposal ID:"):
                    pid = line.split("## Proposal ID:", 1)[1].strip()
                if line.startswith("**Status:**"):
                    status = line.split("**Status:**", 1)[1].strip()
            if pid is None:
                continue
            if status_filter and status != status_filter:
                continue
            proposals.append({"id": pid, "status": status})
    except FileNotFoundError:
        return []
    return proposals


def get_rulebook_summary():
    """Generate a summary of core and auto-applied rules in the rulebook."""
    try:
        content = Path(RULEBOOK_PATH).read_text(encoding='utf-8')
    except Exception:
        return ""
    core_rules = sum(1 for line in content.splitlines() if line.startswith("### Rule:"))
    auto_applied = sum(1 for line in content.splitlines() if "# --- AUTO-APPLIED RULE" in line)
    return f"{core_rules} core rules and {auto_applied} auto-applied rules"


def generate_governance_data():
    """Compile governance data into a dictionary for reporting."""
    recent_events = load_recent_governance_events(MAX_LOG_LINES)
    recent_reflections = load_recent_reflections()
    open_proposals = load_proposals(status_filter="Proposed")
    data = {
        "rulebook_summary": get_rulebook_summary(),
        "open_proposals": open_proposals,
        "recent_reflections": recent_reflections,
        "recent_events": recent_events,
        "recent_hours": RECENT_HOURS,
        "max_log_lines": MAX_LOG_LINES
    }
    return data 
