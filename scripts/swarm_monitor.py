#!/usr/bin/env python3
"""
Swarm State Monitor (Rustbyte - Passive Watch)

Monitors the swarm_state.json file for integrity, errors, and corruption,
logging issues and triggering alerts based on defined thresholds.
"""

import logging
import sys
import json
import time
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

# --- Path Setup ---
# Assuming script is in scripts/
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    # Add relevant paths for importing core functions
    sys.path.append(str(project_root / "src"))
    sys.path.append(str(project_root))

# --- Configuration ---
MONITOR_ID = "SwarmMonitor-Rustbyte-Passive"
STATE_FILE_PATH = project_root / "runtime" / "swarm_state.json"
INTEGRITY_LOG_FILE = project_root / "runtime" / "logs" / "swarm_integrity.log"
ALERT_FILE_PATH = Path("D:\Dream.os\runtime\alerts\rustbyte_ping_thea.txt") # Use absolute path as directed
MONITOR_INTERVAL_SECONDS = 10 # Simulate 2 cycles (adjust as needed)
JSON_ERROR_THRESHOLD = 2 # Trigger alert if > this many consecutive JSON errors
EXPECTED_AGENT_FIELDS = ["last_updated_utc", "current_module", "current_cycle", "status", "health_notes"]
# Stall Detection Config
STALL_AGENT_ID = "Agent-5 (Knurlshade)"
STALL_MODULE_EXPECTED = "Module 6" # For context
STALL_THRESHOLD_SECONDS = MONITOR_INTERVAL_SECONDS * 10 # Alert if no update for 10 cycles
STALL_ALERT_FLAG_PATH = project_root / "runtime" / "alerts" / "module6_stall.flag"
# Stall Escalation Config
STALL_ESCALATION_THRESHOLD_CYCLES = 15 # Escalate if stall flag persists this many cycles
STALL_ESCALATION_FLAG_PATH = project_root / "runtime" / "alerts" / "escalation_knurlshade_critical.flag"

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger(MONITOR_ID)

# --- Swarm Sync Import ---
try:
    from dreamos.core.swarm_sync import read_swarm_state, AGENT_IDS
    logger.info("Successfully imported swarm_sync functions.")
except ImportError as e:
    logger.critical(f"Failed to import required swarm_sync module: {e}. Monitor cannot run.")
    sys.exit(1)

# --- Integrity Logging ---
def log_integrity_issue(issue_type: str, details: Dict[str, Any]):
    """Logs an integrity issue to the dedicated log file."""
    log_entry = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "monitor_id": MONITOR_ID,
        "issue_type": issue_type,
        "details": details
    }
    try:
        INTEGRITY_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(INTEGRITY_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry) + '\n')
    except Exception as e:
        logger.error(f"Failed to write to integrity log {INTEGRITY_LOG_FILE}: {e}", exc_info=True)

# --- Alerting --- 
def trigger_alert(reason: str):
    """Creates the alert file if it doesn't exist."""
    if not ALERT_FILE_PATH.exists():
        logger.critical(f"ALERT CONDITION MET: {reason}. Triggering primary alert file: {ALERT_FILE_PATH}")
        try:
            ALERT_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            with open(ALERT_FILE_PATH, 'w', encoding='utf-8') as f:
                f.write(f"ALERT TRIGGERED by {MONITOR_ID} at {timestamp}\n")
                f.write(f"Reason: {reason}\n")
        except Exception as e:
            logger.error(f"Failed to create primary alert file {ALERT_FILE_PATH}: {e}", exc_info=True)
    else:
        logger.warning(f"Primary alert condition met ({reason}), but alert file already exists: {ALERT_FILE_PATH}")

def manage_stall_flag(is_stalled: bool):
    """Creates or deletes the stall flag file based on the detected state."""
    if is_stalled:
        if not STALL_ALERT_FLAG_PATH.exists():
            logger.warning(f"Stall detected for {STALL_AGENT_ID}. Creating flag file: {STALL_ALERT_FLAG_PATH}")
            try:
                STALL_ALERT_FLAG_PATH.parent.mkdir(parents=True, exist_ok=True)
                STALL_ALERT_FLAG_PATH.touch()
            except OSError as e:
                logger.error(f"Failed to create stall flag file {STALL_ALERT_FLAG_PATH}: {e}. Log only.")
    else:
        if STALL_ALERT_FLAG_PATH.exists():
            logger.info(f"Stall condition cleared for {STALL_AGENT_ID}. Removing flag file: {STALL_ALERT_FLAG_PATH}")
            try:
                STALL_ALERT_FLAG_PATH.unlink()
            except OSError as e:
                logger.error(f"Failed to delete stall flag file {STALL_ALERT_FLAG_PATH}: {e}. Manual cleanup may be required.")

def trigger_escalation_flag(duration_cycles: int):
    """Creates the critical escalation flag file if it doesn't exist."""
    if not STALL_ESCALATION_FLAG_PATH.exists():
        reason = f"Stall condition for {STALL_AGENT_ID} ({STALL_MODULE_EXPECTED}) persisted for {duration_cycles} cycles."
        logger.critical(f"ESCALATION: {reason} Triggering escalation flag: {STALL_ESCALATION_FLAG_PATH}")
        log_integrity_issue("StallEscalation", {"agent_id": STALL_AGENT_ID, "duration_cycles": duration_cycles})
        try:
            STALL_ESCALATION_FLAG_PATH.parent.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            with open(STALL_ESCALATION_FLAG_PATH, 'w', encoding='utf-8') as f:
                 f.write(f"ESCALATION TRIGGERED by {MONITOR_ID} at {timestamp}\n")
                 f.write(f"Reason: {reason}\n")
        except OSError as e:
            logger.error(f"Failed to create escalation flag file {STALL_ESCALATION_FLAG_PATH}: {e}. Log only.")
    else:
        logger.warning(f"Escalation condition met, but escalation flag already exists: {STALL_ESCALATION_FLAG_PATH}")

# --- Helper Functions ---
def parse_iso_utc(timestamp_str: str) -> Optional[datetime]:
    """
    Parses an ISO 8601 timestamp string, ensuring it's UTC.

    Handles strings ending with 'Z' by replacing it with '+00:00' for broad
    compatibility with datetime.fromisoformat across Python versions.
    If the parsed datetime object is naive, it's localized to UTC.

    Args:
        timestamp_str: The ISO 8601 formatted timestamp string.

    Returns:
        A timezone-aware datetime object in UTC, or None if parsing fails.
    """
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        if dt.tzinfo is None:
             # Should not happen if ledger format is correct, but handle defensively
             return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError):
        logger.warning(f"Could not parse timestamp string: {timestamp_str}")
        return None

# --- Main Monitoring Loop ---
def run_monitor():
    """
    Main monitoring loop for the Swarm State.

    Continuously reads the swarm_state.json file, checks for JSON validity,
    validates the presence and structure of expected agent data, checks for
    agents in an "Error" state, and implements specific stall detection logic
    for a designated agent (Agent-5 Knurlshade).

    Logs integrity issues and triggers alerts (primary, stall, escalation)
    by creating flag files based on configured thresholds and conditions.
    Maintains state across cycles for consecutive errors and stall duration.
    """
    logger.info(f"Starting Swarm Monitor ({MONITOR_ID}). Interval: {MONITOR_INTERVAL_SECONDS}s")
    consecutive_json_errors = 0
    knurlshade_stalled = STALL_ALERT_FLAG_PATH.exists() # Initial state based on flag presence
    stall_flag_consecutive_cycles = 0 # Will be corrected in first loop if flag exists
    escalation_triggered = STALL_ESCALATION_FLAG_PATH.exists()
    logger.info(f"Initial stall state for {STALL_AGENT_ID}: {knurlshade_stalled}")
    logger.info(f"Initial escalation state: {escalation_triggered}")

    while True:
        logger.debug("Starting monitoring cycle.")
        alert_reason: Optional[str] = None
        state_read_error = False
        now_utc = datetime.now(timezone.utc)
        
        # 1. Read State (Handle JSON errors directly)
        current_state = None
        if not STATE_FILE_PATH.exists():
            logger.warning(f"Swarm state file not found: {STATE_FILE_PATH}. Cannot monitor.")
            state_read_error = True # Treat as error for consecutive counting
        else:
            try:
                 with open(STATE_FILE_PATH, 'r', encoding='utf-8') as f:
                    current_state = json.load(f)
                 # Basic validation: Check if it's a dictionary
                 if not isinstance(current_state, dict):
                     logger.error(f"Swarm state file {STATE_FILE_PATH} does not contain a valid JSON object.")
                     log_integrity_issue("FormatError", {"file": str(STATE_FILE_PATH), "error": "Not a JSON object"})
                     current_state = None # Treat as error
                     state_read_error = True
                 else:
                     logger.debug("Successfully read and parsed swarm state.")
                     consecutive_json_errors = 0 # Reset error count on success

            except json.JSONDecodeError as e:
                logger.error(f"Swarm state file {STATE_FILE_PATH} contains invalid JSON: {e}")
                log_integrity_issue("JSONError", {"file": str(STATE_FILE_PATH), "error": str(e)})
                state_read_error = True
            except OSError as e:
                logger.error(f"Error reading swarm state file {STATE_FILE_PATH}: {e}. Treating as read error.")
                state_read_error = True
            except Exception as e:
                logger.error(f"Unexpected error reading swarm state: {e}. Treating as read error.")
                state_read_error = True
                
        if state_read_error:
             consecutive_json_errors += 1
             logger.warning(f"Consecutive JSON/Read errors: {consecutive_json_errors}")
             if consecutive_json_errors > JSON_ERROR_THRESHOLD:
                  alert_reason = f"Exceeded JSON/Read error threshold ({consecutive_json_errors} consecutive errors) for {STATE_FILE_PATH}"
        
        # 2. Validate Structure & Status if read was successful
        stall_check_performed = False
        agent_currently_stalled = False # Assume not stalled for this cycle unless proven otherwise
        if current_state is not None:
            present_agents = set(current_state.keys())
            expected_agents = set(AGENT_IDS)
            missing_agents = expected_agents - present_agents
            extra_agents = present_agents - expected_agents
            
            if missing_agents:
                msg = f"Missing expected agents in swarm state: {sorted(list(missing_agents))}"
                logger.warning(msg)
                log_integrity_issue("MissingAgents", {"file": str(STATE_FILE_PATH), "missing": sorted(list(missing_agents))})
                
            if extra_agents:
                msg = f"Found unexpected agents in swarm state: {sorted(list(extra_agents))}"
                logger.warning(msg)
                log_integrity_issue("ExtraAgents", {"file": str(STATE_FILE_PATH), "extra": sorted(list(extra_agents))})
            
            for agent_id in expected_agents:
                if agent_id not in current_state: continue # Already logged as missing
                
                agent_data = current_state[agent_id]
                if not isinstance(agent_data, dict):
                    msg = f"Agent data for {agent_id} is not a dictionary."
                    logger.warning(msg)
                    log_integrity_issue("SchemaError", {"file": str(STATE_FILE_PATH), "agent_id": agent_id, "error": "Data not a dict"})
                    continue

                # Check required fields
                for field in EXPECTED_AGENT_FIELDS:
                     if field not in agent_data:
                        msg = f"Missing field '{field}' for agent {agent_id}."
                        logger.warning(msg)
                        log_integrity_issue("SchemaError", {"file": str(STATE_FILE_PATH), "agent_id": agent_id, "missing_key": field})

                # Check status for "Error"
                agent_status = agent_data.get("status")
                if isinstance(agent_status, str) and agent_status.strip().lower() == "error":
                    msg = f"Agent {agent_id} reported status 'Error'."
                    logger.error(msg)
                    log_integrity_issue("AgentError", {"file": str(STATE_FILE_PATH), "agent_id": agent_id, "status": agent_status, "health_notes": agent_data.get("health_notes")})
                    if alert_reason is None: # Prioritize error status alert over JSON errors
                         alert_reason = msg
                
                # === Stall Detection Logic ===
                if agent_id == STALL_AGENT_ID:
                    stall_check_performed = True
                    last_update_str = agent_data.get("last_updated_utc")
                    last_update_dt = parse_iso_utc(last_update_str) if last_update_str else None
                    
                    if last_update_dt:
                        time_since_last_update = now_utc - last_update_dt
                        if time_since_last_update.total_seconds() > STALL_THRESHOLD_SECONDS:
                            agent_currently_stalled = True
                            # Only log/flag if state changes from not stalled -> stalled
                            if not knurlshade_stalled:
                                stall_details = {
                                    "agent_id": STALL_AGENT_ID,
                                    "module": STALL_MODULE_EXPECTED,
                                    "threshold_seconds": STALL_THRESHOLD_SECONDS,
                                    "last_update_utc": last_update_str,
                                    "seconds_since_update": time_since_last_update.total_seconds()
                                }
                                logger.warning(f"Stall detected for {STALL_AGENT_ID} ({STALL_MODULE_EXPECTED}): Last update {time_since_last_update.total_seconds():.0f}s ago.")
                                log_integrity_issue("StallDetected", stall_details)
                                manage_stall_flag(is_stalled=True)
                                knurlshade_stalled = True # Update internal state
                        else:
                            # Agent is not currently stalled
                            agent_currently_stalled = False 
                            # Only log/unflag if state changes from stalled -> not stalled
                            if knurlshade_stalled:
                                logger.info(f"Stall condition cleared for {STALL_AGENT_ID}. Update received.")
                                log_integrity_issue("StallResumed", {"agent_id": STALL_AGENT_ID, "last_update_utc": last_update_str})
                                manage_stall_flag(is_stalled=False)
                                knurlshade_stalled = False # Update internal state
                    else:
                         logger.warning(f"Could not parse last_updated_utc for {STALL_AGENT_ID}. Cannot perform stall check.")
                         log_integrity_issue("SchemaError", {"agent_id": STALL_AGENT_ID, "error": "Missing or unparseable last_updated_utc"})
        
            if not stall_check_performed and STALL_AGENT_ID not in missing_agents:
                 logger.warning(f"Stall check could not be performed for {STALL_AGENT_ID} (agent present but data likely invalid). Check integrity logs.")

        # 3. Update Stall Counter & Check Escalation
        if knurlshade_stalled: # Check internal state flag reflecting current cycle's check
            stall_flag_consecutive_cycles += 1
            logger.debug(f"Stall flag for {STALL_AGENT_ID} present. Consecutive cycles: {stall_flag_consecutive_cycles}")
            if stall_flag_consecutive_cycles >= STALL_ESCALATION_THRESHOLD_CYCLES and not escalation_triggered:
                 trigger_escalation_flag(duration_cycles=stall_flag_consecutive_cycles)
                 escalation_triggered = True
        else:
            if stall_flag_consecutive_cycles > 0:
                 logger.info(f"Stall flag for {STALL_AGENT_ID} removed. Resetting consecutive cycle count from {stall_flag_consecutive_cycles}.")
            stall_flag_consecutive_cycles = 0
            if escalation_triggered:
                logger.info("Stall condition cleared, resetting escalation trigger.")
                escalation_triggered = False # Reset escalation if stall clears
                # Optionally delete the escalation flag? Directive doesn't specify, leave for now.

        # 4. Trigger Primary Alert if needed (JSON errors or Agent status Error)
        if alert_reason:
            trigger_alert(alert_reason)

        # 5. Wait for next cycle
        logger.debug(f"Monitoring cycle complete. Sleeping for {MONITOR_INTERVAL_SECONDS} seconds.")
        time.sleep(MONITOR_INTERVAL_SECONDS)

if __name__ == "__main__":
    # Ensure log/alert directories exist
    INTEGRITY_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    ALERT_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STALL_ALERT_FLAG_PATH.parent.mkdir(parents=True, exist_ok=True) # Ensure alerts dir exists
    STALL_ESCALATION_FLAG_PATH.parent.mkdir(parents=True, exist_ok=True) # Ensure escalation dir exists
    
    try:
        run_monitor()
    except KeyboardInterrupt:
        logger.info(f"Swarm Monitor ({MONITOR_ID}) stopped by user.")
    except Exception as e:
        logger.critical(f"Swarm Monitor ({MONITOR_ID}) encountered a critical error: {e}", exc_info=True)
        sys.exit(1) 