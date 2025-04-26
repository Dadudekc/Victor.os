import argparse
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Union, Optional, List, Any

# NOTE: This script was separated from the original combined project_scanner.py

logger = logging.getLogger(__name__)

# --- Configuration --- #
# Default paths (Can be overridden by CLI args)
# These might need adjustment depending on where config is truly managed
DEFAULT_PROPOSALS_FILENAME = "rulebook_update_proposals.md" # Example filename
DEFAULT_SECURITY_LOG_FILENAME = "security_scan.log"
PROPOSAL_SEPARATOR = "\n---\n" # Example separator

# Keywords/Patterns to flag (examples - needs significant refinement)
RISKY_KEYWORDS = {
    "FILE_DELETION": [r"delete file", r"remove.*?\.py", r"os\.remove", r"shutil\.rmtree"],
    "MEMORY_OVERRIDE": [r"overwrite memory", r"clear history", r"reset governance log"],
    "RULEBOOK_MODIFICATION": [r"modify rulebook directly", r"change core rule", r"bypass proposal process"],
    "EXECUTION": [r"os\.system", r"subprocess\.run", r"eval\(", r"exec\("],
    "IMPORTS": [r"import os", r"import sys", r"import subprocess", r"import shutil"] # Flag risky imports
}

# --- Security Log Functionality --- #
def log_security_finding(proposal_id, finding_type, detail, context_snippet, log_file_path: Path):
    """Appends a finding to the specified security scan log file."""
    timestamp = datetime.now().isoformat() + "Z"
    log_entry = f"""---
**Timestamp:** {timestamp}
**Proposal ID:** {proposal_id}
**Finding Type:** {finding_type}
**Detail:** {detail}
**Context Snippet:**
```
{context_snippet}
```
---
"""
    try:
        log_file_path.parent.mkdir(parents=True, exist_ok=True) # Ensure log dir exists
        is_new_file = not log_file_path.exists() or log_file_path.stat().st_size == 0
        with open(log_file_path, 'a', encoding='utf-8') as f:
            # Add header only if file is new/empty
            if is_new_file:
                f.write("# Security Scan Log\n\nFlags potentially risky actions proposed by agents.\n\n")
            f.write("\n" + log_entry)
        # logger.info(f"Logged security finding ({finding_type}) for proposal {proposal_id} to {log_file_path.name}")
        return True
    except Exception as e:
        logger.error(f"Failed to write to security log {log_file_path}: {e}")
        return False

# --- Proposal Scanning Logic --- #
def scan_proposal_block(proposal_id, block_content, log_file_path: Path):
    """Scans a single proposal block for risky keywords/patterns."""
    findings_count = 0
    logger.debug(f"Scanning proposal block: {proposal_id}")
    
    for finding_type, patterns in RISKY_KEYWORDS.items():
        for pattern in patterns:
            try:
                 matches = re.finditer(pattern, block_content, re.IGNORECASE | re.MULTILINE)
                 for match in matches:
                     start = max(0, match.start() - 50) # Increased context slightly
                     end = min(len(block_content), match.end() + 50)
                     # Ensure context doesn't cross proposal boundaries if separator is simple
                     context_snippet = block_content[start:end].strip().replace('\n', ' \\n ') # Show newlines
                     detail = f"Pattern matched: '{pattern}' at position {match.start()}"
                     log_security_finding(proposal_id, finding_type, detail, context_snippet, log_file_path)
                     findings_count += 1
            except re.error as e:
                 logger.warning(f"Regex error scanning proposal {proposal_id} with pattern '{pattern}': {e}")
            except Exception as e:
                 logger.error(f"Unexpected error during regex matching for proposal {proposal_id}: {e}")

    if findings_count > 0:
         logger.warning(f"Found {findings_count} potential security issue(s) in proposal {proposal_id}.")
    else:
         logger.debug(f"No findings for proposal block: {proposal_id}")
    return findings_count

# --- Main Execution --- #
def main():
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

    parser = argparse.ArgumentParser(description="Scan agent proposals text file for potentially risky actions based on keyword patterns.")
    parser.add_argument(
        "proposals_file", 
        help=f"Path to the proposals file (e.g., {DEFAULT_PROPOSALS_FILENAME})"
    )
    parser.add_argument(
        "--log-file", 
        help=f"Path to the output security log file (default: <proposals_file_dir>/{DEFAULT_SECURITY_LOG_FILENAME})"
    )
    parser.add_argument(
         "-v", "--verbose",
         action="store_true",
         help="Enable verbose logging (DEBUG level)."
    )

    args = parser.parse_args()

    if args.verbose:
         logging.getLogger().setLevel(logging.DEBUG)
         logger.debug("Verbose logging enabled.")
         
    proposals_file_path = Path(args.proposals_file).resolve()
    
    if args.log_file:
        security_log_output_file = Path(args.log_file).resolve()
    else:
        # Default log file in the same directory as the proposals file
        security_log_output_file = proposals_file_path.parent / DEFAULT_SECURITY_LOG_FILENAME
    
    # Ensure log directory exists
    try:
         security_log_output_file.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
         logger.error(f"Could not create directory for log file {security_log_output_file}: {e}")
         sys.exit(1)
    
    logger.info(f"--- Starting Security Scan on Proposals: {proposals_file_path} ---")
    logger.info(f"--- Logging findings to: {security_log_output_file} ---")

    if not proposals_file_path.is_file():
        logger.error(f"Proposals file not found: {proposals_file_path}")
        sys.exit(1)
        
    try:
        content = proposals_file_path.read_text(encoding='utf-8')
    except Exception as e:
        logger.error(f"Error reading proposals file {proposals_file_path}: {e}")
        sys.exit(1)

    total_findings = 0
    proposals_scanned = 0
    # Split carefully, preserving potential separators within blocks
    proposal_blocks = re.split(f"^{re.escape(PROPOSAL_SEPARATOR.strip())}$", content.strip(), flags=re.MULTILINE)
        
    for i, block in enumerate(proposal_blocks):
        block = block.strip()
        if not block: continue
        
        # Try to extract a better ID from the block, e.g., a markdown header
        proposal_id = f"proposal_block_{i+1}" # Default ID (1-based)
        header_match = re.search(r"^(#+.*?)$", block, re.MULTILINE) # Look for any markdown header
        if header_match:
             proposal_id = header_match.group(1).strip()

        findings = scan_proposal_block(proposal_id, block, security_log_output_file)
        total_findings += findings
        proposals_scanned += 1

    logger.info("--- Security Scan Complete ---")
    if proposals_scanned > 0:
        logger.info(f"Scanned {proposals_scanned} proposal blocks.")
        if total_findings > 0:
             logger.warning(f"Found {total_findings} potential security findings logged to {security_log_output_file}.")
        else:
             logger.info(f"No potential security findings detected based on current patterns.")
    else:
        logger.warning("No proposal blocks found or processed.")

if __name__ == "__main__":
    main() 
