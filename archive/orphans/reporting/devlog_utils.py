"""Utilities for devlog manipulation."""

import logging
import re
from pathlib import Path
from typing import List, Tuple

from dreamos.utils.file_io import read_text_file, write_text_file_atomic

logger = logging.getLogger(__name__)

# Regex to find cycle markers (e.g., "**Cycle X/25**" or similar)
# Making it more robust to variations
CYCLE_MARKER_REGEX = re.compile(
    r"^\\*\\*Cycle\\s+(\\d+)(?:/\\d+)?\\*?\\*?.*", re.IGNORECASE
)
# Regex to find existing index section
INDEX_SECTION_REGEX = re.compile(r"^## Devlog Index.*?^---", re.MULTILINE | re.DOTALL)


def _generate_index_markdown(entries: List[Tuple[int, str]]) -> str:
    """Generates the markdown for the devlog index."""
    if not entries:
        return "## Devlog Index\\n\\n*   No cycles found.\\n\\n---\\n\\n"

    # Sort entries by cycle number, handling potential resets
    # Simple numeric sort for now
    sorted_entries = sorted(entries, key=lambda x: x[0])

    index_lines = ["## Devlog Index", ""]
    for cycle_num, timestamp in sorted_entries:
        # Create a simple anchor link (GitHub style)
        anchor = f"#cycle-{cycle_num}"
        ts_display = timestamp if timestamp else "N/A"
        index_lines.append(
            f"*   [Cycle {cycle_num}]({anchor}) - Timestamp: {ts_display}"
        )

    index_lines.extend(["", "---", ""])  # Add separator
    return "\\n".join(index_lines)


def _parse_devlog_for_index(content: str) -> List[Tuple[int, str]]:
    """Parses devlog content to find cycle numbers and timestamps."""
    entries = []
    timestamp_placeholder = "{{iso_timestamp_utc()}}"  # Placeholder common in logs
    current_timestamp = None

    lines = content.splitlines()
    for i, line in enumerate(lines):
        # Check for cycle marker
        cycle_match = CYCLE_MARKER_REGEX.match(line)
        if cycle_match:
            try:
                cycle_num = int(cycle_match.group(1))
                # Look for a timestamp marker in the next few lines for this cycle
                found_ts = None
                for j in range(i + 1, min(i + 5, len(lines))):
                    if "Timestamp:" in lines[j]:
                        ts_part = lines[j].split("Timestamp:", 1)[1].strip()
                        # Keep the placeholder if it exists, otherwise capture timestamp
                        if timestamp_placeholder in ts_part:
                            found_ts = timestamp_placeholder
                        elif ts_part and ts_part != "N/A":
                            found_ts = ts_part  # Capture actual timestamp if present
                        else:
                            found_ts = None  # Explicitly None if missing or N/A
                        break
                entries.append((cycle_num, found_ts))
            except (IndexError, ValueError):
                logger.warning(f"Failed to parse cycle number near line {i+1}")
                continue
    return entries


def update_devlog_index(agent_id: str, devlog_dir: Path):
    """Reads an agent's devlog, generates an index, and prepends it."""
    devlog_filename = f"{agent_id}.md"  # Assuming Agent-X.md format
    devlog_path = devlog_dir / "agents" / devlog_filename

    if not devlog_path.exists():
        logger.warning(
            f"Devlog file not found for {agent_id} at {devlog_path}, cannot update index."
        )
        return

    try:
        logger.info(f"Updating devlog index for {agent_id} in {devlog_path}")
        content = read_text_file(devlog_path)
        if not content:
            logger.warning(f"Devlog file for {agent_id} is empty.")
            return

        # Parse entries
        entries = _parse_devlog_for_index(content)

        # Generate new index
        new_index_md = _generate_index_markdown(entries)

        # Remove old index if exists
        content_without_index = INDEX_SECTION_REGEX.sub("", content).strip()

        # Prepend new index
        new_content = new_index_md + content_without_index

        # Write back atomically
        write_text_file_atomic(devlog_path, new_content)
        logger.info(f"Successfully updated devlog index for {agent_id}.")

    except Exception as e:
        logger.error(
            f"Failed to update devlog index for {agent_id}: {e}", exc_info=True
        )
