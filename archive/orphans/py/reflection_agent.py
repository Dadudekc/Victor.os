import json  # noqa: I001
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

# Import the standard config
from dreamos.core.config import AppConfig
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

# Load config ONCE at the start
config = AppConfig.load()

# Constants now loaded from config
# RULEBOOK_PATH = os.getenv("RULEBOOK_PATH", "rulebook.md")
# PROPOSALS_FILE_PATH = os.getenv("PROPOSALS_FILE_PATH", "rulebook_update_proposals.md")
RULEBOOK_PATH = config.paths.rulebook_path
PROPOSALS_FILE_PATH = config.paths.proposals_file_path
AGENT_ID = config.agent_id  # Use the standard agent_id from config


def load_rules_from_rulebook(rulebook_path: Path) -> Dict[str, Any]:
    """Load rules from the rulebook markdown file."""
    rules = {}
    try:
        # Ensure we use the variable passed to the function
        content = Path(rulebook_path).read_text(encoding="utf-8")
        rule_blocks = content.split("### Rule")

        for block in rule_blocks[1:]:  # Skip first empty block
            if "```yaml" in block and "```" in block:
                yaml_content = block.split("```yaml")[1].split("```")[0]
                try:
                    rule_data = yaml.safe_load(yaml_content)
                    if isinstance(rule_data, dict) and "rules" in rule_data:
                        # Ensure rule list isn't empty before accessing index 0
                        if rule_data["rules"]:
                            rule = rule_data["rules"][0]
                            if isinstance(rule, dict) and "id" in rule:
                                rules[rule["id"]] = rule
                            else:
                                print(
                                    f"Warning: Invalid rule structure in block: {block[:100]}..."  # noqa: E501
                                )
                        else:
                            print(
                                f"Warning: Empty 'rules' list in block: {block[:100]}..."  # noqa: E501
                            )
                except yaml.YAMLError as ye:
                    print(f"Warning: YAML error parsing rule block: {ye}")
                    continue
    except FileNotFoundError:
        print(f"Error: Rulebook file not found at {rulebook_path}")
    except Exception as e:
        print(f"Error loading rules from {rulebook_path}: {e}")
    return rules


def generate_reflection(
    alert_data: Dict[str, Any], rules: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate a reflection based on the alert data and current rules."""
    reflection = {
        "type": "agent_reflection",
        # Use agent_id loaded from config
        # 'reflection_agent': os.getenv('AGENT_NAME', 'UnknownAgent'),
        "reflection_agent": AGENT_ID,
        "violating_agent": alert_data.get("violating_agent"),
        "mentioned_rule_id": None,
        "suggested_action": "monitor_situation",
        "proposal_content": None,
        "thoughts": [],
    }

    # Extract rule ID if mentioned in analysis
    analysis = alert_data.get("analysis", "")
    for rule_id in rules.keys():
        if rule_id in analysis:
            reflection["mentioned_rule_id"] = rule_id
            break

    # Determine if we need to propose a new rule
    needs_proposal = False
    halt_reason = alert_data.get("halt_reason", "")
    analysis_lower = analysis.lower()
    if isinstance(halt_reason, str):  # Basic type check for safety
        halt_reason_lower = halt_reason.lower()
        if (
            "unclear" in halt_reason_lower
            or "vague" in halt_reason_lower
            or "not found" in analysis_lower
        ):
            needs_proposal = True
    elif (
        "not found" in analysis_lower
    ):  # Still propose if analysis indicates 'not found'
        needs_proposal = True

    if needs_proposal:
        reflection["suggested_action"] = "propose_rule_update"
        # Use f-string safely, handle potential None values
        target_rule = reflection["mentioned_rule_id"] or "NEW_RULE"
        reasoning = alert_data.get("analysis", "Analysis not provided.")
        violating_agent = alert_data.get("violating_agent", "Unknown Agent")
        halt = halt_reason if isinstance(halt_reason, str) else "Reason not specified."

        reflection["proposal_content"] = f"""### [REFLECT] Proposal
**Target Rule ID:** {target_rule}

**Reasoning:** {reasoning}

**Proposed Change Summary:**
Based on the alert from {violating_agent},
we need to clarify the rules regarding: {halt}
"""
        reflection["thoughts"].append("Action: Proposing clarification/new rule.")
    else:
        reflection["thoughts"].append("Action: Monitoring situation.")

    return reflection


def save_reflection(reflection_data: Dict[str, Any], outbox_path: Path) -> None:
    """Save reflection data to a JSON file in the outbox."""
    reflection_id = reflection_data.get("reflection_id")
    if not reflection_id:
        print("Warning: Cannot save reflection, missing 'reflection_id'.")
        return

    try:
        outfile = Path(outbox_path) / f"{reflection_id}.json"
        # Ensure outbox directory exists
        outfile.parent.mkdir(parents=True, exist_ok=True)
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump(reflection_data, f, indent=2)
        print(f"Reflection saved to {outfile}")
    except Exception as e:
        print(f"Error saving reflection {reflection_id} to {outbox_path}: {e}")


def submit_proposal(proposal_content: Optional[str], reflection_id: str) -> None:
    """Submit a proposal to the proposals file."""
    if not proposal_content:
        return
    # Use the constant loaded from config
    proposals_path = Path(PROPOSALS_FILE_PATH)
    header = f"\n### Proposal from Reflection '{reflection_id}'\n"
    try:
        # Ensure parent directory exists
        proposals_path.parent.mkdir(parents=True, exist_ok=True)
        with open(proposals_path, "a", encoding="utf-8") as f:
            f.write(f"{header}{proposal_content}\n")
        print(f"Proposal from {reflection_id} submitted to {proposals_path}")
    except Exception as e:
        print(f"Error submitting proposal to {proposals_path}: {e}")


class AlertHandler(FileSystemEventHandler):
    """Handles new alert files in the inbox directory."""

    def __init__(self, agent_name: str, inbox_path: str, outbox_path: str):
        # Use agent_id from config, ignore passed agent_name for consistency?
        # For now, keep passed agent_name but log it
        print(
            f"AlertHandler initialized for agent: {agent_name} (Config AGENT_ID: {AGENT_ID})"  # noqa: E501
        )
        self.agent_name = agent_name
        self.inbox_path = Path(inbox_path)
        self.outbox_path = Path(outbox_path)
        # Use the constant loaded from config
        self.rules = load_rules_from_rulebook(Path(RULEBOOK_PATH))

    def on_created(self, event):
        print(f"File created event: {event.src_path}")
        if not event.is_directory and event.src_path.endswith(".json"):
            filepath = Path(event.src_path)
            # Add a small delay to ensure file write is complete
            import time

            time.sleep(0.2)
            try:
                print(f"Processing alert file: {filepath.name}")
                with open(filepath, "r", encoding="utf-8") as f:
                    alert_data = json.load(f)

                if alert_data.get("type") == "rule_alert":
                    print("Rule alert detected, generating reflection...")
                    reflection = generate_reflection(alert_data, self.rules)
                    reflection_id = (
                        f"reflect-{alert_data.get('message_id', 'unknown_msg')}"
                    )
                    reflection["reflection_id"] = reflection_id  # Add ID to data

                    save_reflection(reflection, self.outbox_path)

                    if reflection.get("proposal_content"):
                        print("Submitting rule proposal...")
                        submit_proposal(
                            reflection["proposal_content"], reflection["reflection_id"]
                        )
                    print(f"Processing complete for {filepath.name}")
                else:
                    print(f"Ignoring non-rule_alert file: {filepath.name}")
            except json.JSONDecodeError as je:
                print(f"Error decoding JSON from {filepath.name}: {je}")
            except Exception as e:
                print(f"Error processing alert {filepath.name}: {e}")
                import traceback

                traceback.print_exc()


def start_monitoring(agent_name: str, inbox_path: str, outbox_path: str):
    """Start monitoring the inbox for new alerts."""
    print(f"Starting monitoring for agent {agent_name} on inbox: {inbox_path}")
    event_handler = AlertHandler(agent_name, inbox_path, outbox_path)
    observer = Observer()
    observer.schedule(event_handler, inbox_path, recursive=False)
    observer.start()
    print("Observer started.")
    return observer


# Example main execution block (if run directly)
if __name__ == "__main__":
    print("Reflection Agent Example Starting...")
    # Use paths from loaded config
    # These paths likely need to be configured in config.yaml or use agent-specific mailboxes  # noqa: E501
    agent_inbox = Path(f"runtime/agent_comms/agent_mailboxes/{AGENT_ID}/inbox")
    agent_outbox = Path(f"runtime/agent_comms/agent_mailboxes/{AGENT_ID}/outbox")

    # Ensure directories exist
    agent_inbox.mkdir(parents=True, exist_ok=True)
    agent_outbox.mkdir(parents=True, exist_ok=True)

    print(f"Monitoring Inbox: {agent_inbox.resolve()}")
    print(f"Using Outbox: {agent_outbox.resolve()}")
    print(f"Rulebook: {RULEBOOK_PATH.resolve()}")
    print(f"Proposals File: {PROPOSALS_FILE_PATH.resolve()}")

    observer = start_monitoring(AGENT_ID, str(agent_inbox), str(agent_outbox))

    try:
        while True:
            time.sleep(10)  # Keep main thread alive  # noqa: F821
            print(".", end="", flush=True)  # Heartbeat
    except KeyboardInterrupt:
        observer.stop()
        print("\nObserver stopped.")
    observer.join()
    print("Reflection Agent Example Exiting.")
