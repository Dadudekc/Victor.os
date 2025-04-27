import os
import json
import glob
import re
import time
from datetime import datetime
from pathlib import Path
import yaml

# Paths and constants that can be overridden by tests
LOG_FILE_PATH = "unnecessary_halts.md"
ABS_AGENT_DIRS_ROOT = "."
PROPOSALS_FILE_PATH = "rulebook_update_proposals.md"
RULEBOOK_PATH = "rulebook.md"
TASK_POOL_PATH = "task_pool.json"


def load_rules_from_rulebook(rulebook_path):
    """Load rules from a Markdown rulebook file with YAML blocks."""
    try:
        content = Path(rulebook_path).read_text(encoding='utf-8')
    except Exception:
        return []
    blocks = re.findall(r"```yaml(.*?)```", content, re.DOTALL)
    rules = []
    for block in blocks:
        try:
            data = yaml.safe_load(block)
            for rule in data.get('rules', []):
                rules.append(rule)
        except Exception:
            continue
    return rules


def load_tasks(task_path):
    """Load tasks from a JSON file, return empty list if missing or invalid."""
    try:
        with open(task_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
    except Exception:
        return []
    return []


def is_halt_unnecessary(message, agent_name, rules, tasks):
    """Determine if a halt message is unnecessary based on rules."""
    matched = []
    msg_lower = message.lower()
    for rule in rules:
        applies = rule.get('applies_to')
        if applies == 'all_agents' or applies == agent_name:
            for kw in rule.get('keywords', []):
                if kw.lower() in msg_lower:
                    matched.append(rule.get('id'))
                    break
    if matched:
        return True, matched
    return False, "Reason not found"


def log_unnecessary_halt(agent_name, reason, rule_info, timestamp):
    """Append a record of an unnecessary halt to the log file."""
    ts = timestamp.isoformat()
    entry = (
        "### Unnecessary Halt\n"
        f"- Agent: {agent_name}\n"
        f"- Reason: {reason}\n"
        f"- Rule: {rule_info}\n"
        f"- Timestamp: {ts}\n\n"
    )
    with open(LOG_FILE_PATH, 'a', encoding='utf-8') as f:
        f.write(entry)


def broadcast_alert(agent_name, message, detail, rules):
    """Broadcast an alert JSON to each agent's inbox directory."""
    for agent_dir in os.listdir(ABS_AGENT_DIRS_ROOT):
        inbox = os.path.join(ABS_AGENT_DIRS_ROOT, agent_dir, "inbox")
        if os.path.isdir(inbox):
            # Format message to ensure lowercase 'r' at start for rule text compatibility
            alert_msg = detail[0].lower() + detail[1:] if isinstance(detail, str) and detail else ""
            payload = {
                "type": "rule_alert",
                "violating_agent": agent_name,
                "message": alert_msg
            }
            filename = f"{int(time.time()*1000)}.json"
            filepath = os.path.join(inbox, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(payload, f)


def request_rulebook_update(agent_name, reason, detail):
    """Append a clarification request to the proposals file."""
    entry = (
        "### [AUTO] Clarification Rule\n"
        f"- Agent: {agent_name}\n"
        f"- Reason: {reason}\n"
        f"{json.dumps(detail)}\n"
    )
    with open(PROPOSALS_FILE_PATH, 'a', encoding='utf-8') as f:
        f.write(entry)


class HaltStatusHandler:
    """Handler for processing agent status files, especially 'halted' status."""
    def __init__(self, rules, tasks):
        self.rules = rules
        self.tasks = tasks

    def process_status_file(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            return
        status = data.get('status')
        if status != 'halted':
            return
        agent_name = data.get('agent_name')
        reason = data.get('reason')
        unnecessary, details = is_halt_unnecessary(reason, agent_name, self.rules, self.tasks)
        if unnecessary:
            # Log the unnecessary halt
            log_unnecessary_halt(
                agent_name,
                reason,
                f"Reason potentially covered by rule {details[0]}",
                datetime.now()
            )
            # Broadcast an alert
            broadcast_alert(agent_name, reason, details[0], self.rules)
            # Request rulebook update
            request_rulebook_update(agent_name, reason, details[0]) 
