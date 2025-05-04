# src/dreamos/core/narrative/lore_parser.py
import logging
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict

# Assuming access to DB adapter instance
# from dreamos.core.db.sqlite_adapter import SQLiteAdapter, TaskDict

logger = logging.getLogger(__name__)


# Define types for context window and output
class ContextWindow(TypedDict, total=False):
    start_time_iso: Optional[str]
    end_time_iso: Optional[str]
    task_ids: Optional[List[str]]
    commit_range: Optional[str]  # e.g., "HEAD~5..HEAD"
    agent_ids: Optional[List[str]]
    include_lore_files: Optional[List[str]]  # Specific lore files to include


class NarrativeContextData(TypedDict):
    tasks: List[Dict]  # List of TaskDict or relevant fields
    commits: str  # Formatted git log output
    agent_logs: Dict[str, List[str]]  # agent_id -> list of log lines
    captain_logs: str  # Concatenated relevant text
    lore_context: str  # Concatenated text from specified lore files


def fetch_task_data(adapter: Any, context: ContextWindow) -> List[Dict]:
    """Fetches relevant task data from the database."""
    logger.debug(f"Fetching task data for context: {context}")
    tasks = []
    task_ids = context.get("task_ids")
    # TODO: Implement filtering by time range if needed
    # Requires querying tasks and filtering by completed_at/updated_at
    try:
        if task_ids:
            for tid in task_ids:
                task = adapter.get_task(tid)
                if task:
                    tasks.append(task)
        else:
            # Fetch recent completed? Or based on time?
            # For now, return empty if no specific IDs given
            logger.warning("Task ID list not provided, returning no task data.")
            pass
            # Example: Fetch last N completed? Adapter might need new method.
            # tasks = adapter.get_tasks_by_status("completed", limit=10)
    except Exception as e:
        logger.error(f"Failed to fetch task data from DB: {e}", exc_info=True)
    logger.info(f"Fetched {len(tasks)} tasks from DB.")
    return tasks


def fetch_git_log(context: ContextWindow, repo_path: Path) -> str:
    """Fetches git log information within the context window."""
    logger.debug(f"Fetching git log for context: {context}")
    log_output = ""
    cmd = [
        "git",
        "log",
        "--pretty=format:Commit: %H%nAuthor: %an%nDate: %aI%nSubject: %s%n%b%n---",
    ]

    start_time = context.get("start_time_iso")
    end_time = context.get("end_time_iso")
    commit_range = context.get("commit_range")

    if commit_range:
        cmd.append(commit_range)
    else:
        if start_time:
            cmd.append(f"--since={start_time}")
        if end_time:
            cmd.append(f"--until={end_time}")

    try:
        # Ensure execution in the correct directory
        result = subprocess.run(
            cmd, cwd=repo_path, capture_output=True, text=True, check=False
        )
        if result.returncode == 0:
            log_output = result.stdout.strip()
            logger.info(f"Fetched git log (Length: {len(log_output)} chars).")
        else:
            logger.error(
                f"Git log command failed (Code: {result.returncode}): {result.stderr}"
            )
    except FileNotFoundError:
        logger.error("'git' command not found. Ensure Git is installed and in PATH.")
    except Exception as e:
        logger.error(f"Failed to fetch git log: {e}", exc_info=True)
    return log_output


def fetch_agent_logs(context: ContextWindow, log_dir: Path) -> Dict[str, List[str]]:
    """Fetches relevant agent log entries within the context window using regex parsing."""
    logger.debug(f"Fetching agent logs for context: {context}")
    agent_logs: Dict[str, List[str]] = {}
    target_agent_ids = context.get("agent_ids")  # Optional filter
    start_time_str = context.get("start_time_iso")
    end_time_str = context.get("end_time_iso")

    # Compile regex for common log format (adapt if needed)
    # Example format: 2024-05-06T10:00:00.123Z - AGENT_NAME - LEVEL - Message
    # Or:             [2024-05-06T10:00:00] [LEVEL] [AgentID] Message
    # Combining potential formats - adjust based on actual log structure
    # FIX: Use raw string literal for multi-line regex and escape backslashes if needed
    log_pattern = re.compile(
        r"^\"?"  # Optional quote
        r"(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?)"  # ISO Timestamp (optional Z)
        r"\"?"  # Optional quote
        r"(?:\s*[- ]\s*|\s*\]?\s*\[?)"  # Separator (e.g., ' - ', ' ] [')
        r"(?P<level>\w+)"  # Log level (e.g., INFO)
        r"(?:\s*\]?\s*\[?)"  # Separator
        r"(?P<agent_id>[\w-]+)"  # Agent ID
        r"(?:\s*[-:]\s*|\s*\]\s*)?"  # Separator (optional)
        r"(?P<message>.*)"  # Rest of the message
        r"$",
        re.IGNORECASE,
    )
    # Simpler pattern assuming brackets format:
    # log_pattern = re.compile(r'^\[(?P<timestamp>.*?)\]\s+\[(?P<level>.*?)\]\s+\[(?P<agent_id>.*?)\]\s+(?P<message>.*)$')

    # Parse time strings if provided
    start_time_dt: Optional[datetime] = None
    end_time_dt: Optional[datetime] = None
    try:
        if start_time_str:
            start_time_dt = datetime.fromisoformat(
                start_time_str.replace("Z", "+00:00")
            )
        if end_time_str:
            end_time_dt = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))
    except ValueError as e:
        logger.error(f"Invalid ISO timestamp format in context window: {e}")
        # Decide if we should proceed without time filtering or return error
        return {}  # Return empty for now on bad timestamp

    try:
        if not log_dir.is_dir():
            logger.warning(f"Agent log directory not found: {log_dir}")
            return agent_logs

        for log_file in log_dir.glob("*.log"):
            if log_file.is_file():
                agent_id_from_filename = (
                    log_file.stem
                )  # Assuming filename is agent_id.log
                if target_agent_ids and agent_id_from_filename not in target_agent_ids:
                    continue  # Skip if filtering by agent ID

                agent_log_lines = []
                try:
                    with open(log_file, "r", encoding="utf-8") as f:
                        for line_num, line in enumerate(f, 1):
                            line = line.strip()
                            if not line:
                                continue  # Skip empty lines

                            match = log_pattern.match(line)
                            if not match:
                                # logger.debug(f"Skipping non-matching log line {line_num} in {log_file.name}: {line[:100]}...")
                                continue  # Skip lines not matching the pattern

                            log_data = match.groupdict()
                            timestamp_str = log_data.get("timestamp")

                            if not timestamp_str:
                                # logger.debug(f"Skipping log line {line_num} with missing timestamp in {log_file.name}: {line[:100]}...")
                                continue

                            # Robust timestamp parsing
                            log_dt: Optional[datetime] = None
                            try:
                                # Handle potential 'Z' for UTC
                                timestamp_str_adj = timestamp_str.replace("Z", "+00:00")
                                log_dt = datetime.fromisoformat(timestamp_str_adj)
                                # Ensure timezone awareness for comparison (assume UTC if no offset)
                                if log_dt.tzinfo is None:
                                    log_dt = log_dt.replace(tzinfo=timezone.utc)
                            except ValueError:
                                # logger.warning(f"Could not parse timestamp '{timestamp_str}' on line {line_num} in {log_file.name}")
                                continue  # Skip lines with unparsable timestamps

                            # Check time window
                            # Ensure consistent timezone awareness (start/end times are parsed as aware)
                            if start_time_dt and log_dt < start_time_dt:
                                continue
                            if end_time_dt and log_dt > end_time_dt:
                                continue

                            # Append the original line if it falls within the time window
                            agent_log_lines.append(line)

                except Exception as read_e:
                    logger.error(f"Failed to read agent log file {log_file}: {read_e}")
                    continue  # Skip this file on read error

                if agent_log_lines:
                    agent_logs[agent_id_from_filename] = agent_log_lines
                    logger.debug(
                        f"Fetched {len(agent_log_lines)} relevant lines for agent {agent_id_from_filename}"
                    )

    except Exception as e:
        logger.error(f"Failed to fetch agent logs: {e}", exc_info=True)

    logger.info(f"Fetched logs for {len(agent_logs)} agents.")
    return agent_logs


def fetch_captain_logs(context: ContextWindow, report_dir: Path) -> str:
    """Fetches relevant captain log entries within the context window."""
    logger.debug(f"Fetching captain logs for context: {context}")
    log_texts = []
    start_time_str = context.get("start_time_iso")
    end_time_str = context.get("end_time_iso")

    # Parse time strings if provided (ensure timezone awareness)
    start_time_dt: Optional[datetime] = None
    end_time_dt: Optional[datetime] = None
    try:
        if start_time_str:
            start_time_dt = datetime.fromisoformat(
                start_time_str.replace("Z", "+00:00")
            )
        if end_time_str:
            end_time_dt = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))
    except ValueError as e:
        logger.error(f"Invalid ISO timestamp format in context window: {e}")
        return ""  # Return empty on bad timestamp

    # EDIT: Regex to extract date from filenames like captain_log_YYYYMMDD.md or similar
    filename_date_pattern = re.compile(r"_(\d{8})\.(?:md|txt)$")

    try:
        if not report_dir.is_dir():
            logger.warning(f"Captain report directory not found: {report_dir}")
            return ""

        # Assuming filenames might contain dates like captain_agent_X_log_YYYYMMDD.md or similar
        # Or parse date from within the markdown content?
        # Simple approach: Iterate all *.md files and filter by content date if possible, or just include all in range
        # This needs a more robust date detection/parsing strategy based on actual file format

        for report_file in report_dir.glob("captain_*.md"):
            if report_file.is_file():
                # EDIT: Implement date filtering based on filename or content
                should_include = False
                file_dt: Optional[datetime] = None

                # 1. Try extracting date from filename
                match = filename_date_pattern.search(report_file.name)
                if match:
                    date_str = match.group(1)
                    try:
                        file_dt = datetime.strptime(date_str, "%Y%m%d").replace(
                            tzinfo=timezone.utc
                        )
                    except ValueError:
                        logger.warning(
                            f"Could not parse date '{date_str}' from filename {report_file.name}"
                        )

                # 2. TODO: If filename parsing fails, try parsing date from file content (e.g., first few lines)
                if file_dt is None:
                    # Add logic here to read first few lines and search for a date pattern
                    logger.debug(
                        f"Could not determine date from filename {report_file.name}, content parsing not implemented."
                    )
                    # Default behavior if no date found: Include if no time filter, exclude if time filter exists?
                    # For now, exclude if time filter exists and date is unknown.
                    if not start_time_dt and not end_time_dt:
                        should_include = True  # Include if no time filter is set at all
                    else:
                        should_include = False  # Exclude if time filter exists but we can't parse date

                # Check against time window if date was found
                if file_dt:
                    if start_time_dt and file_dt < start_time_dt.replace(
                        hour=0, minute=0, second=0, microsecond=0
                    ):
                        should_include = (
                            False  # Exclude if file date is before start date
                        )
                    elif end_time_dt and file_dt > end_time_dt.replace(
                        hour=23, minute=59, second=59, microsecond=999999
                    ):
                        should_include = False  # Exclude if file date is after end date
                    else:
                        should_include = (
                            True  # Include if within range or filters not set
                        )

                if should_include:
                    try:
                        log_texts.append(f"\n--- Captain Log: {report_file.name} ---\n")
                        log_texts.append(report_file.read_text(encoding="utf-8"))
                        logger.debug(f"Included captain log: {report_file.name}")
                    except Exception as read_e:
                        logger.error(
                            f"Failed to read captain log file {report_file}: {read_e}"
                        )

    except Exception as e:
        logger.error(f"Failed to fetch captain logs: {e}", exc_info=True)

    logger.info(f"Fetched {len(log_texts)} captain log sections.")
    return "\n".join(log_texts)


def fetch_lore_context(context: ContextWindow, lore_dir: Path) -> str:
    """Fetches content from specified lore files."""
    logger.debug(f"Fetching lore context for context: {context}")
    content = []
    files_to_include = context.get("include_lore_files", [])
    if not files_to_include:
        return ""

    for filename in files_to_include:
        # Basic security: prevent directory traversal
        if ".." in filename or filename.startswith("/"):
            logger.warning(f"Skipping potentially unsafe lore file path: {filename}")
            continue
        file_path = lore_dir / filename
        try:
            if file_path.is_file():
                content.append(f"\n--- Lore File: {filename} ---\n")
                content.append(file_path.read_text(encoding="utf-8"))
            else:
                logger.warning(f"Specified lore file not found: {file_path}")
        except Exception as e:
            logger.error(f"Failed to read lore file {file_path}: {e}", exc_info=True)

    logger.info(f"Fetched context from {len(files_to_include)} lore files.")
    return "\n".join(content)


def gather_narrative_context(
    context_window: ContextWindow,
    adapter: Any,  # Should be SQLiteAdapter
    repo_path: Path,  # Path to git repo
    log_dir: Path,  # Path to agent logs
    report_dir: Path,  # Path to captain reports
    lore_dir: Path,  # Path to lore repo
) -> NarrativeContextData:
    """Gathers all relevant data sources based on the context window."""

    tasks = fetch_task_data(adapter, context_window)
    commits = fetch_git_log(context_window, repo_path)
    agent_logs = fetch_agent_logs(context_window, log_dir)
    captain_logs = fetch_captain_logs(context_window, report_dir)
    lore_context = fetch_lore_context(context_window, lore_dir)

    return {
        "tasks": tasks,
        "commits": commits,
        "agent_logs": agent_logs,
        "captain_logs": captain_logs,
        "lore_context": lore_context,
    }
