"""
Tool to run basic diagnostic checks on the Dream.OS environment.
See: _agent_coordination/onboarding/TOOLS_GUIDE.md
"""

import argparse
import sys
import json
import logging
import os # Import os for path checks if needed, though pathlib is preferred
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# --- Diagnostic Checks --- #

def check_directory_exists(dir_path: Path) -> bool:
    """Checks if a directory exists and is a directory."""
    if not dir_path.exists():
        logger.warning(f"Directory check FAILED: Path not found: {dir_path}")
        return False
    if not dir_path.is_dir():
        logger.warning(f"Directory check FAILED: Path is not a directory: {dir_path}")
        return False
    logger.info(f"Directory check PASSED: {dir_path}")
    return True

def check_file_exists(file_path: Path) -> bool:
    """Checks if a file exists and is a file."""
    if not file_path.exists():
        logger.warning(f"File check FAILED: Path not found: {file_path}")
        return False
    if not file_path.is_file():
        logger.warning(f"File check FAILED: Path is not a file: {file_path}")
        return False
    logger.info(f"File check PASSED: {file_path}")
    return True

def check_json_file(file_path: Path) -> bool:
    """Checks if a file exists and contains valid JSON."""
    if not check_file_exists(file_path):
        # check_file_exists already logged the warning
        return False
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            json.load(f)
        logger.info(f"JSON check PASSED: Valid JSON in {file_path}")
        return True
    except json.JSONDecodeError as e:
        logger.warning(f"JSON check FAILED: Invalid JSON in {file_path}: {e}")
        return False
    except Exception as e:
         logger.warning(f"JSON check FAILED: Could not read {file_path}: {e}")
         return False

# --- Main Diagnostic Function --- #

def run_diagnostics(level: str, auto: bool):
    """Runs diagnostic checks based on the specified level."""
    logger.info(f"Running diagnostics (Level: {level}, Auto: {auto})")

    # Assume CWD is project root (as per onboarding)
    project_root = Path.cwd()

    results = {}
    all_passed = True

    # Basic Checks (always run)
    logger.info("--- Running Basic Checks ---")
    agent_coord_path = project_root / "_agent_coordination"
    results['agent_coord_dir'] = check_directory_exists(agent_coord_path)
    if results['agent_coord_dir']:
        results['agent_coord_tools_dir'] = check_directory_exists(agent_coord_path / "tools")
        results['agent_coord_onboarding_dir'] = check_directory_exists(agent_coord_path / "onboarding")
        results['agent_coord_shared_mailboxes_dir'] = check_directory_exists(agent_coord_path / "shared_mailboxes")
    else:
         # If base coord dir fails, subdirs implicitly fail
         results['agent_coord_tools_dir'] = False
         results['agent_coord_onboarding_dir'] = False
         results['agent_coord_shared_mailboxes_dir'] = False

    # Full Checks (optional)
    if level == 'full':
        logger.info("--- Running Full Checks ---")

        # Check essential onboarding files
        onboarding_dir = project_root / "_agent_coordination" / "onboarding"
        if results['agent_coord_onboarding_dir']:
             essential_onboarding_files = [
                 "agent_onboarding_prompt.md",
                 "rulebook.md",
                 "TOOLS_GUIDE.md"
             ]
             missing_onboarding = []
             for ob_file in essential_onboarding_files:
                  path = onboarding_dir / ob_file
                  check_key = f'onboarding_{ob_file}'
                  results[check_key] = check_file_exists(path)
                  if not results[check_key]:
                       missing_onboarding.append(ob_file)

             if missing_onboarding:
                   logger.warning(f"Full Check FAILED: Missing essential onboarding files: {', '.join(missing_onboarding)}")
             else:
                   logger.info("Full Check PASSED: Found essential onboarding files.")
        else:
             logger.warning("Full Check SKIPPED: Onboarding directory check failed.")
             results['onboarding_rulebook.md'] = False # Mark as failed if dir missing
             results['onboarding_TOOLS_GUIDE.md'] = False
             results['onboarding_agent_onboarding_prompt.md'] = False

        # Check shared mailbox files
        mailbox_dir = project_root / "_agent_coordination" / "shared_mailboxes"
        if results['agent_coord_shared_mailboxes_dir']:
            missing_mailboxes = []
            for i in range(1, 9): # Check mailbox_1.json to mailbox_8.json
                mailbox_file = f"mailbox_{i}.json"
                path = mailbox_dir / mailbox_file
                check_key = f"shared_{mailbox_file}"
                # Check existence AND json validity
                results[check_key] = check_json_file(path)
                if not results[check_key]:
                    missing_mailboxes.append(mailbox_file)

            if missing_mailboxes:
                logger.warning(f"Full Check FAILED: Missing or invalid shared mailbox files: {', '.join(missing_mailboxes)}")
            else:
                logger.info("Full Check PASSED: Found and validated essential shared mailbox files.")
        else:
            logger.warning("Full Check SKIPPED: Shared mailboxes directory check failed.")
            for i in range(1, 9):
                results[f'shared_mailbox_{i}.json'] = False # Mark as failed if dir missing

        # Optionally add checks for other important files/configs if needed
        # e.g., results['project_board_json'] = check_json_file(mailbox_dir / "project_board.json")

    # Determine overall outcome based on required checks for the level
    critical_checks_passed = results.get('agent_coord_dir', False)

    # Iterate through all results to determine final outcome for the *requested level*
    final_outcome_passed = True
    checks_to_consider = results.keys() if level == 'full' else ['agent_coord_dir', 'agent_coord_tools_dir', 'agent_coord_onboarding_dir', 'agent_coord_shared_mailboxes_dir']

    for check_name in checks_to_consider:
        # Use .get() to handle cases where a check might not have run (e.g., subdir check skipped)
        if not results.get(check_name, False):
            final_outcome_passed = False
            # No need to break, log all failures below

    logger.info("--- Diagnostics Summary ---")
    # Sort items for consistent output
    for check, result in sorted(results.items()):
         # Show SKIPPED explicitly if parent dir failed
         status_str = 'PASSED' if result else 'FAILED'
         # Example: If agent_coord_dir failed, mark subdir checks visually as skipped/failed due to parent
         if not results.get('agent_coord_dir') and check.startswith('agent_coord_'):
             if check != 'agent_coord_dir': status_str = 'FAILED (Parent Missing)'
         elif not results.get('agent_coord_onboarding_dir') and check.startswith('onboarding_'):
             status_str = 'FAILED (Parent Missing)'
         elif not results.get('agent_coord_shared_mailboxes_dir') and check.startswith('shared_'):
              status_str = 'FAILED (Parent Missing)'

         logger.info(f"  {check}: {status_str}")

    if final_outcome_passed:
        logger.info(f"Result: Diagnostics (Level: {level}) completed successfully.")
        sys.exit(0)
    else:
        logger.warning(f"Result: Diagnostics (Level: {level}) completed with warnings/failures.")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run diagnostic checks on the Dream.OS environment.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
    parser.add_argument("--level", choices=['basic', 'full'], default='basic', help="Diagnostic level.")
    parser.add_argument("--auto", action='store_true', help="Automated execution mode (currently only affects logging).")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging.")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled.")

    run_diagnostics(level=args.level, auto=args.auto) 