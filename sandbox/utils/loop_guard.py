import argparse
import re
from collections import deque

# --- Configuration ---
# Number of most recent log lines to analyze for loops
LOG_WINDOW_SIZE = 20 # Check last 20 lines, should be enough to catch 4+ cycles
# Consecutive cycles threshold to trigger alert (Detect >= N repetitions)
LOOP_THRESHOLD = 4
# Pivot suggestion
PIVOT_SUGGESTION = "Try CLAIM_OR_CREATE_TASK pivot"

# --- Pattern Definitions (Regex) ---
# These patterns need refinement based on actual, consistent log formats
# Using explanations from previous loop as placeholders
MAILBOX_SCAN_PATTERN = r"list_dir.*agent_mailboxes/.*/inbox"
BACKLOG_CHECK_PATTERN = r"read_file.*task_backlog\.json"
BACKLOG_FAIL_PATTERN = r"read_file.*task_backlog\.json.*timed out" # Or other failure indicator
DEVLOG_CHECK_PATTERN = r"read_file.*devlog\.md"
SPP_FAIL_PATTERN = r"read_file.*SELF_PROMPTING_PROTOCOL\.md.*Could not find file" # Or other failure

# Simplified action identifiers derived from patterns
ACTION_MAILBOX = "SCAN_MAILBOX"
ACTION_BACKLOG = "CHECK_BACKLOG"
ACTION_BACKLOG_FAIL = "FAIL_BACKLOG"
ACTION_DEVLOG = "CHECK_DEVLOG"
ACTION_SPP_FAIL = "FAIL_SPP"

# The target idle loop sequence pattern
# Allowing for backlog check success OR failure
IDLE_LOOP_SEQUENCE = [
    ACTION_MAILBOX,
    (ACTION_BACKLOG, ACTION_BACKLOG_FAIL), # Tuple indicates OR condition
    ACTION_DEVLOG,
    ACTION_SPP_FAIL
]

def parse_log_line_action(line):
    \"\"\"Identifies the action based on predefined patterns.\"\"\"
    line_lower = line.lower() # Case-insensitive matching
    if re.search(MAILBOX_SCAN_PATTERN, line_lower):
        return ACTION_MAILBOX
    if re.search(BACKLOG_FAIL_PATTERN, line_lower):
        return ACTION_BACKLOG_FAIL
    if re.search(BACKLOG_CHECK_PATTERN, line_lower):
        return ACTION_BACKLOG
    if re.search(DEVLOG_CHECK_PATTERN, line_lower):
        return ACTION_DEVLOG
    if re.search(SPP_FAIL_PATTERN, line_lower):
        return ACTION_SPP_FAIL
    return None # Not a recognized action relevant to the loop

def detect_idle_loop(log_file_path):
    \"\"\"Analyzes the recent log history for the repetitive idle loop.\"\"\"
    try:
        with open(log_file_path, 'r') as f:
            # Use deque to efficiently get the last N lines
            log_lines = deque(f, maxlen=LOG_WINDOW_SIZE)
    except FileNotFoundError:
        print(f"Error: Log file not found: {log_file_path}")
        return False
    except Exception as e:
        print(f"Error reading log file {log_file_path}: {e}")
        return False

    if len(log_lines) < len(IDLE_LOOP_SEQUENCE) * LOOP_THRESHOLD:
        # Not enough lines to possibly contain the loop N times
        print(f"Log file {log_file_path} has too few lines ({len(log_lines)}) to detect {LOOP_THRESHOLD} loops.")
        return False

    # Extract the sequence of recent actions
    recent_actions = []
    for line in log_lines:
        action = parse_log_line_action(line)
        if action:
            recent_actions.append(action)

    # Check for consecutive repetitions of the IDLE_LOOP_SEQUENCE
    sequence_len = len(IDLE_LOOP_SEQUENCE)
    match_count = 0
    consecutive_matches = 0

    # Iterate backwards through recent actions to find the latest sequence repeats
    i = len(recent_actions) - 1
    while i >= sequence_len - 1:
        current_sequence_match = True
        # Check if the slice matches the target sequence pattern
        for j in range(sequence_len):
            target_pattern_step = IDLE_LOOP_SEQUENCE[sequence_len - 1 - j]
            actual_action = recent_actions[i - j]

            if isinstance(target_pattern_step, tuple): # Handle OR condition
                if actual_action not in target_pattern_step:
                    current_sequence_match = False
                    break
            elif actual_action != target_pattern_step:
                current_sequence_match = False
                break

        if current_sequence_match:
            match_count += 1
            i -= sequence_len # Move index back by the sequence length
            if match_count >= LOOP_THRESHOLD: # Found enough consecutive matches
                 consecutive_matches = match_count
                 break # Stop searching once threshold is met/exceeded
        else:
            # Reset match count if sequence is broken
            # Only reset if we were actively counting consecutive matches
            if match_count > 0 :
                 consecutive_matches = match_count # Store the last count
                 break # We only care about the *most recent* consecutive block
            match_count = 0
            i -= 1 # Move back one step

    # If we exit the loop due to index and have matches, store count
    if i < sequence_len - 1 and match_count > 0 and consecutive_matches == 0:
         consecutive_matches = match_count


    if consecutive_matches >= LOOP_THRESHOLD:
        print(f"ALERT: Detected {consecutive_matches} consecutive idle loop cycles in {log_file_path}.")
        print(f"SUGGESTED_PIVOT: {PIVOT_SUGGESTION}")
        return True
    else:
        print(f"No idle loop pattern detected ({consecutive_matches} consecutive matches found) in recent logs of {log_file_path}.")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Detect repetitive idle loops in agent logs.")
    parser.add_argument("log_file", help="Path to the agent log file to analyze.")
    args = parser.parse_args()

    detect_idle_loop(args.log_file) 