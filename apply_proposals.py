import os
import re
import yaml
from pathlib import Path

STATUS_PREFIX = "**Status:**"
STATUS_PROPOSED = "Proposed"
STATUS_ACCEPTED = "Accepted"
STATUS_REJECTED = "Rejected"

PROPOSAL_SEPARATOR = "\n---\n"
APPLIED_RULES_HEADER = "# Applied Rules"

# Default file paths for rulebook and proposals; tests may patch these
RULEBOOK_PATH = Path("rulebook.md")
PROPOSALS_FILE_PATH = Path("proposals.md")

def get_existing_rule_ids(rulebook_path):
    try:
        content = Path(rulebook_path).read_text(encoding='utf-8')
    except Exception:
        return set()
    ids = set()
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("- ID:"):
            parts = line.split(":", 1)
            if len(parts) == 2:
                ids.add(parts[1].strip())
    return ids

def parse_proposal(proposal_text):
    status = STATUS_PROPOSED
    reason = None
    rule_data = None
    # Detect explicit status
    for line in proposal_text.splitlines():
        if line.strip().startswith(STATUS_PREFIX):
            status_line = line.strip()[len(STATUS_PREFIX):].strip()
            if status_line.startswith(STATUS_ACCEPTED):
                status = STATUS_ACCEPTED
            elif status_line.startswith(STATUS_REJECTED):
                status = STATUS_REJECTED
                parts = status_line.split("-", 1)
                if len(parts) == 2:
                    reason = parts[1].strip()
                else:
                    reason = None
            break
    # Accepted or rejected have no rule data
    if status in (STATUS_ACCEPTED, STATUS_REJECTED):
        return status, reason, None
    # Proposed: parse YAML block
    yaml_blocks = re.findall(r"```yaml(.*?)```", proposal_text, re.DOTALL)
    if not yaml_blocks:
        return STATUS_REJECTED, "No YAML block found in proposal.", None
    yaml_text = yaml_blocks[0]
    try:
        data = yaml.safe_load(yaml_text)
    except Exception as e:
        return STATUS_REJECTED, f"Invalid YAML syntax: {e}", None
    if not data or 'rules' not in data or not isinstance(data['rules'], list) or len(data['rules']) != 1:
        return STATUS_REJECTED, "Proposal does not contain a single rule definition.", None
    rule = data['rules'][0]
    if 'id' not in rule or 'description' not in rule:
        return STATUS_REJECTED, "Proposal missing id or description.", None
    rule_data = {'id': rule['id'], 'description': rule['description']}
    return status, reason, rule_data

def update_proposal_block_status(proposal_block, new_status, reason=""):
    lines = proposal_block.splitlines(True)
    status_line = STATUS_PREFIX + new_status
    if reason:
        status_line += f" - {reason}"
    found = False
    updated = []
    for line in lines:
        if line.strip().startswith(STATUS_PREFIX):
            updated.append(status_line + "\n")
            found = True
        else:
            updated.append(line)
    if not found:
        new_lines = []
        inserted = False
        for line in lines:
            new_lines.append(line)
            if not inserted and line.strip().startswith("###"):
                new_lines.append(status_line + "\n")
                inserted = True
        return "".join(new_lines)
    return "".join(updated)

def append_rule_to_rulebook(proposal_block, rule_data, rulebook_path=RULEBOOK_PATH):
    try:
        path = Path(rulebook_path)
        if not path.exists():
            path.write_text("", encoding='utf-8')
        content = path.read_text(encoding='utf-8')
        if APPLIED_RULES_HEADER not in content:
            content = APPLIED_RULES_HEADER + "\n" + content
        entry = f"\nRule ID: {rule_data['id']}\n{proposal_block}\n"
        content += entry
        path.write_text(content, encoding='utf-8')
        return True
    except Exception:
        return False 