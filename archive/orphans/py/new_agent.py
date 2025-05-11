# Agent Script for Agent-9

import json
import os
import time

# Define agent-specific parameters (replace with actual values)
AGENT_ID = "Agent-9"
MAILBOX_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../runtime/agent_comms/agent_mailboxes")
)
MAILBOX_PATH = os.path.join(MAILBOX_DIR, f"{AGENT_ID}.json")
HEARTBEAT_INTERVAL = 60  # seconds
MAX_IDLE_INTERVALS = 3

# --- UNIVERSAL_AGENT_LOOP Structure ---


def read_mailbox():
    """Reads the agent's mailbox file."""
    try:
        with open(MAILBOX_PATH, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"ERROR: Mailbox not found at {MAILBOX_PATH}")
        # Initialize mailbox if not found
        mailbox_data = {
            "inbox": [],
            "outbox": [],
            "loop_state": {"status": "initializing"},
        }
        write_mailbox(mailbox_data)
        return mailbox_data
    except json.JSONDecodeError:
        print(f"ERROR: Invalid JSON in mailbox {MAILBOX_PATH}")
        # Handle corrupted mailbox (e.g., backup/reset)
        return {
            "inbox": [],
            "outbox": [],
            "loop_state": {"status": "error_mailbox_corrupt"},
        }  # Indicate error state


def write_mailbox(data):
    """Writes data to the agent's mailbox file."""
    try:
        with open(MAILBOX_PATH, "w") as f:
            json.dump(data, f, indent=2)
    except IOError as e:
        print(f"ERROR: Could not write to mailbox {MAILBOX_PATH}: {e}")


def process_inbox(messages):
    """Processes messages from the inbox. Placeholder implementation."""
    processed_ids = []
    new_outbox_messages = []
    print(f"Processing {len(messages)} inbox messages...")
    for msg in messages:
        # TODO: Implement actual message processing logic based on message type/content
        print(f"  Processing message ID: {msg.get('id', 'N/A')}")
        # Example: Create a dummy response
        response = {
            "id": f"response_{msg.get('id', 'unknown')}_{int(time.time())}",
            "type": "receipt",
            "status": "processed",
            "original_message_id": msg.get("id"),
        }
        new_outbox_messages.append(response)
        processed_ids.append(msg.get("id"))  # Assuming messages have unique IDs
    return processed_ids, new_outbox_messages


def update_loop_state(current_state, status="running", last_processed_count=0):
    """Updates the loop_state field in the mailbox."""
    current_state["status"] = status
    current_state["last_update_utc"] = time.strftime(
        "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
    )
    current_state["last_processed_count"] = last_processed_count
    current_state["idle_intervals"] = 0  # Reset idle counter on activity
    return current_state


def check_idle_state(loop_state):
    """Checks if the agent has been idle for too long."""
    idle_intervals = loop_state.get("idle_intervals", 0)
    if idle_intervals >= MAX_IDLE_INTERVALS:
        print(
            f"WARNING: Agent {AGENT_ID} idle for {idle_intervals} intervals. Potential issue."
        )
        # TODO: Implement escalation or self-correction logic if needed
    return idle_intervals + 1


def new_agent_loop():
    """Main operational loop for the agent."""
    print(f"Starting loop for {AGENT_ID}...")
    last_heartbeat_time = time.time()

    while True:
        current_time = time.time()
        mailbox = read_mailbox()
        loop_state = mailbox.get("loop_state", {})

        # Process Inbox
        inbox_messages = mailbox.get("inbox", [])
        processed_message_ids, new_outbox_items = process_inbox(inbox_messages)

        # Update Mailbox
        if processed_message_ids or new_outbox_items:
            # Remove processed messages from inbox
            mailbox["inbox"] = [
                msg
                for msg in inbox_messages
                if msg.get("id") not in processed_message_ids
            ]
            # Add new messages to outbox
            mailbox["outbox"] = mailbox.get("outbox", []) + new_outbox_items
            # Update loop state (active)
            mailbox["loop_state"] = update_loop_state(
                loop_state,
                status="active",
                last_processed_count=len(processed_message_ids),
            )
            write_mailbox(mailbox)
            print(
                f"Processed {len(processed_message_ids)} messages. {len(new_outbox_items)} items added to outbox."
            )
        else:
            # Update loop state (idle)
            idle_intervals = check_idle_state(loop_state)
            loop_state["idle_intervals"] = idle_intervals
            mailbox["loop_state"] = update_loop_state(loop_state, status="idle")
            # Only write if state changed significantly (e.g., idle count update)
            if loop_state != mailbox.get("loop_state", {}):  # Avoid unnecessary writes
                write_mailbox(mailbox)
            print("No new messages to process. Status: Idle.")

        # Heartbeat/Idle Check
        if current_time - last_heartbeat_time >= HEARTBEAT_INTERVAL:
            print(
                f"Heartbeat: {AGENT_ID} loop running. Status: {loop_state.get('status', 'unknown')}"
            )
            last_heartbeat_time = current_time
            # Potentially write heartbeat to loop_state even if idle, TBD by governance

        # Prevent tight spinning
        time.sleep(5)  # Sleep for a short duration


if __name__ == "__main__":
    # Basic check to ensure mailbox path is correct relative to script location
    if not os.path.exists(MAILBOX_DIR):
        print(
            f"FATAL ERROR: Mailbox directory not found at expected location: {MAILBOX_DIR}"
        )
        print(
            "Ensure the script is run from the correct working directory or adjust MAILBOX_DIR."
        )
        exit(1)
    new_agent_loop()
