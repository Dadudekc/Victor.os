from pathlib import Path
import yaml
from datetime import datetime

# Ensure this path is consistent with your discord_bot_core.py or a shared config
JOURNAL_FILE = Path("logs/trading_journal.yaml") 

def log_agent_event(agent_id: str, title: str, description: str):
    """Logs an event from an agent to the shared YAML journal."""
    event_data = {
        "agent_id": agent_id, # Using agent_id for clarity, can be mapped to 'author' if needed by bot
        "type": "agent_event", # To distinguish from manual trade entries
        "timestamp": datetime.utcnow().isoformat(),
        "title": title,
        "description": description,
    }

    # Consolidate data field for consistency with existing !addtrade entries if possible,
    # or keep it flat as per your design. For now, using a flat structure for agent events.
    entry_to_log = {
        "timestamp": event_data["timestamp"],
        "author": f"Agent: {agent_id}", # For display in journal
        "data": {
            "event_title": title,
            "event_description": description,
            "event_agent_id": agent_id,
            "log_source": "agent_internal"
        }
    }

    JOURNAL_FILE.parent.mkdir(parents=True, exist_ok=True)

    if JOURNAL_FILE.exists():
        with open(JOURNAL_FILE, "r") as f:
            try:
                existing_journal = yaml.safe_load(f) or []
                if not isinstance(existing_journal, list):
                    existing_journal = [] # Reset if not a list
            except yaml.YAMLError:
                existing_journal = [] # Reset if corrupted
    else:
        existing_journal = []

    existing_journal.append(entry_to_log)
    
    with open(JOURNAL_FILE, "w") as f:
        yaml.dump(existing_journal, f, indent=2, sort_keys=False)

    return entry_to_log # Return the logged entry for confirmation or further use

if __name__ == '__main__':
    # Example usage (for testing this module directly)
    print(f"Logging a test event to {JOURNAL_FILE.resolve()}")
    test_event = log_agent_event(
        agent_id="Agent-Test-007", 
        title="Module Test", 
        description="This is a test event logged directly from journal_api.py"
    )
    print("Test event logged:")
    print(yaml.dump(test_event, indent=2))

    with open(JOURNAL_FILE, "r") as f:
        print("\nJournal content after test event:")
        print(f.read()) 