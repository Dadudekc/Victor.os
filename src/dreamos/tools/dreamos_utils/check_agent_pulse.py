import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

# NOTE: The import below might fail if run directly as a script from outside 'src'
# We will handle this in the __main__ block.
# from dreamos.utils.core import get_utc_iso_timestamp

# Configuration
MANUAL_STATUS_FILE = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "../../../runtime/manual_status_reports/agent_status.yaml",
    )
)
STALE_THRESHOLD_MINUTES = 15  # Alert if no update from an agent for this long
EXPECTED_AGENTS = {
    "Agent2",
    "Agent3",
    "Agent4",
    "Agent5",
    "Agent6",
    "Agent8",
}  # Agents expected to report


def get_core_timestamp_utility():
    """Dynamically imports the core timestamp utility, handling potential ModuleNotFoundError."""  # noqa: E501
    try:
        from dreamos.utils.common_utils import get_utc_iso_timestamp

        return get_utc_iso_timestamp
    except ModuleNotFoundError:
        # Fallback for script execution if 'dreamos' not in path
        # Define a compatible function locally
        print(
            "Warning: dreamos.utils.common_utils not found in path. Using fallback timestamp function.",  # noqa: E501
            file=sys.stderr,
        )

        def fallback_timestamp(timespec="milliseconds"):
            # Replicate core logic simply
            valid_timespecs = ["auto", "microseconds", "milliseconds", "seconds"]
            if timespec not in valid_timespecs:
                timespec = "milliseconds"
            return (
                datetime.now(timezone.utc)
                .isoformat(timespec=timespec)
                .replace("+00:00", "Z")
            )

        return fallback_timestamp


# Assign the function globally after attempting import
get_utc_iso_timestamp = get_core_timestamp_utility()


def check_agent_pulse(
    status_file_path: str, threshold_minutes: int, expected_agents: set
) -> dict:
    """
    Checks the manual agent status file for recent updates from expected agents.

    Args:
        status_file_path: Path to the agent_status.yaml file.
        threshold_minutes: How many minutes old an update can be before considered stale.
        expected_agents: A set of agent IDs expected to be reporting.

    Returns:
        A dictionary containing:
        - 'active_agents': set of agents reporting within the threshold
        - 'stale_agents': set of agents whose last report is older than the threshold
        - 'missing_agents': set of expected agents who have never reported
        - 'last_seen': dict mapping agent_id to their last seen timestamp (ISO string)
        - 'errors': list of any errors encountered during processing
    """  # noqa: E501
    results = {
        "active_agents": set(),
        "stale_agents": set(),
        "missing_agents": expected_agents.copy(),
        "last_seen": {},
        "errors": [],
    }
    now_utc = datetime.now(timezone.utc)
    stale_cutoff = now_utc - timedelta(minutes=threshold_minutes)

    if not os.path.exists(status_file_path):
        results["errors"].append(f"Status file not found: {status_file_path}")
        results["missing_agents"] = expected_agents  # All are missing if file not found
        return results

    try:
        with open(status_file_path, "r") as f:
            # Use safe_load_all for potentially multiple YAML documents (though we expect one list)  # noqa: E501
            # Handle empty file gracefully
            content = f.read()
            if not content.strip():
                # File exists but is empty
                results["missing_agents"] = expected_agents
                return results

            # Reset cursor and load
            f.seek(0)
            try:
                all_reports = list(yaml.safe_load_all(f))
            except yaml.YAMLError as e:
                results["errors"].append(
                    f"YAML parsing error in {status_file_path}: {e}"
                )
                # Cannot determine status if file is corrupt
                results["missing_agents"] = expected_agents
                return results

            if not all_reports or not isinstance(all_reports[0], list):
                results["errors"].append(
                    f"Expected a list of reports in {status_file_path}, found unexpected format."  # noqa: E501
                )
                # Cannot determine status if format is wrong
                results["missing_agents"] = expected_agents
                return results

            reports = all_reports[0]

            # Process reports chronologically (assuming they are appended)
            # Find the *last* report for each agent
            agent_last_report_time = {}
            for report in reports:
                if (
                    not isinstance(report, dict)
                    or "agent_id" not in report
                    or "timestamp_utc_iso" not in report
                ):
                    results["errors"].append(f"Skipping invalid report entry: {report}")
                    continue

                agent_id = report["agent_id"]
                timestamp_str = report["timestamp_utc_iso"]

                try:
                    # Handle potential 'Z' suffix and parse
                    if timestamp_str.endswith("Z"):
                        timestamp_str = timestamp_str[:-1] + "+00:00"
                    report_time = datetime.fromisoformat(timestamp_str)

                    # Ensure timezone awareness (assume UTC if missing, though ISO format should have it)  # noqa: E501
                    if report_time.tzinfo is None:
                        report_time = report_time.replace(tzinfo=timezone.utc)

                    agent_last_report_time[agent_id] = report_time
                    results["last_seen"][agent_id] = report[
                        "timestamp_utc_iso"
                    ]  # Store original string

                except ValueError as e_ts:
                    err_msg = f"Invalid timestamp format for agent {agent_id}: {timestamp_str} - {e_ts}"  # noqa: E501
                    results["errors"].append(err_msg)
                    logger.warning(err_msg)  # Also log it  # noqa: F821
                    continue  # Skip agent if timestamp unparseable

            # Determine status based on last report time
            for agent_id, last_time in agent_last_report_time.items():
                if agent_id in results["missing_agents"]:
                    results["missing_agents"].remove(agent_id)

                if last_time >= stale_cutoff:
                    results["active_agents"].add(agent_id)
                else:
                    results["stale_agents"].add(agent_id)

            # Any expected agent not seen at all remains in missing_agents

    except IOError as e:
        results["errors"].append(f"Error reading status file {status_file_path}: {e}")
        results["missing_agents"] = expected_agents  # Assume all missing if read fails
    except Exception as e:
        err_msg_unexp = f"An unexpected error occurred processing {status_file_path}: {type(e).__name__} - {e}"  # noqa: E501
        results["errors"].append(err_msg_unexp)
        logger.exception(err_msg_unexp)  # Log with traceback  # noqa: F821
        # Avoid making assumptions if unexpected error occurs

    return results


if __name__ == "__main__":
    # Add project root to path to allow imports
    # This assumes the script is run from within the dreamos/tools/dreamos_utils directory  # noqa: E501
    # or that the caller sets up the Python path correctly.
    current_dir = Path(__file__).parent
    project_root = (
        current_dir.parent.parent.parent.parent
    )  # Adjust based on actual depth
    src_path = project_root / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
        print(f"Added {src_path} to sys.path for imports")

    # Configure logging for script execution
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,  # Explicitly send to stderr to not mix with stdout report
    )

    # Now the import should work if the structure is correct
    # This allows the 'from dreamos.utils.common_utils import ...' at the top level

    # Example Call:
    agent_id_to_check = "Agent1"  # Example Agent ID

    pulse_results = check_agent_pulse(
        MANUAL_STATUS_FILE, STALE_THRESHOLD_MINUTES, EXPECTED_AGENTS
    )

    print("--- Agent Pulse Check Report ---")
    # Use the potentially dynamically imported/fallback function
    print(f"Timestamp: {get_utc_iso_timestamp(timespec='seconds')}")
    print(f"Monitoring File: {MANUAL_STATUS_FILE}")
    print(f"Stale Threshold: {STALE_THRESHOLD_MINUTES} minutes")
    print(f"Expected Agents: {sorted(list(EXPECTED_AGENTS))}")
    print("---")

    print(
        f"Active Agents (seen in last {STALE_THRESHOLD_MINUTES} min): {sorted(list(pulse_results['active_agents']))}"  # noqa: E501
    )
    print(
        f"Stale Agents (last seen > {STALE_THRESHOLD_MINUTES} min ago): {sorted(list(pulse_results['stale_agents']))}"  # noqa: E501
    )
    print(
        f"Missing Agents (never reported): {sorted(list(pulse_results['missing_agents']))}"  # noqa: E501
    )

    if pulse_results["last_seen"]:
        print("\nLast Seen Timestamps:")
        for agent, ts in sorted(pulse_results["last_seen"].items()):
            print(f"  - {agent}: {ts}")

    if pulse_results["errors"]:
        print("\nErrors Encountered:")
        for error in pulse_results["errors"]:
            print(f"  - {error}")
        sys.exit(1)
    elif pulse_results["stale_agents"] or pulse_results["missing_agents"]:
        # Exit with non-zero code if any agents are stale or missing, but no fatal errors occurred  # noqa: E501
        sys.exit(2)
    else:
        print("\nAll expected agents are active.")
        sys.exit(0)
