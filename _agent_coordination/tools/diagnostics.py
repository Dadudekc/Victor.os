"""
Tool to run basic diagnostic checks on the Dream.OS environment.
See: _agent_coordination/onboarding/TOOLS_GUIDE.md
"""

import argparse
import sys
import json
import logging
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

def check_json_file(file_path: Path) -> bool:
    """Checks if a file exists and contains valid JSON."""
    if not file_path.exists():
        logger.info(f"JSON check SKIPPED: File not found: {file_path}")
        return True # Not a failure if file is optional
    if not file_path.is_file():
        logger.warning(f"JSON check FAILED: Path is not a file: {file_path}")
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
    
    # Assume CWD is project root
    project_root = Path.cwd()
    
    results = {}
    all_passed = True

    # Basic Checks (always run)
    logger.info("--- Running Basic Checks ---")
    results['mailbox_dir'] = check_directory_exists(project_root / "mailboxes")
    # Use new path for agent coordination tools/protocols
    agent_coord_path = project_root / "_agent_coordination"
    results['agent_coord_dir'] = check_directory_exists(agent_coord_path)
    if results['agent_coord_dir']:
        results['agent_coord_tools_dir'] = check_directory_exists(agent_coord_path / "tools")
        results['agent_coord_protocols_dir'] = check_directory_exists(agent_coord_path / "protocols")
    else:
         results['agent_coord_tools_dir'] = False
         results['agent_coord_protocols_dir'] = False
         
    # results['tools_dir'] = check_directory_exists(project_root / "tools") # Check old tools dir too? Maybe remove later.

    # Full Checks (optional)
    if level == 'full':
        logger.info("--- Running Full Checks ---")
        # Example: Check task queue format (assuming it's optional)
        results['task_queue_json'] = check_json_file(project_root / "dreamos" / "task_queue.json")
        
        # Example: Check if key protocol files exist within _agent_coordination/protocols
        protocol_dir = project_root / "_agent_coordination" / "protocols"
        results['protocols_dir_exists'] = check_directory_exists(protocol_dir) # Redundant if checked above, keep for clarity
        if results['protocols_dir_exists']:
             essential_protocols = [
                 "agent_onboarding_rules.md", 
                 "general_principles.md", 
                 "messaging_format.md"
             ]
             missing_protocols = []
             for proto_file in essential_protocols:
                  path = protocol_dir / proto_file
                  if not path.is_file():
                       missing_protocols.append(proto_file)
                       results[f'protocol_{proto_file}'] = False
                  else:
                       results[f'protocol_{proto_file}'] = True
                       
             if missing_protocols:
                   logger.warning(f"Full Check FAILED: Missing essential protocol files: {', '.join(missing_protocols)}")
             else: 
                   logger.info("Full Check PASSED: Found essential protocol files.")
        else:
             logger.warning("Full Check SKIPPED: Protocol directory not found.")

    # Determine overall outcome
    # Basic level: only checks basic dir existence
    # Full level: checks everything accumulated in results
    critical_checks_passed = results.get('mailbox_dir', False) and results.get('agent_coord_dir', False) and results.get('agent_coord_tools_dir', False) and results.get('agent_coord_protocols_dir', False)
    
    if level == 'full':
         for check_name, passed in results.items():
              if not passed:
                  all_passed = False
                  break # No need to check further if one failed
         final_outcome_passed = all_passed
    else: # Basic level
         final_outcome_passed = critical_checks_passed
            
    logger.info("--- Diagnostics Summary ---")
    for check, result in sorted(results.items()): # Sort for consistent output
         logger.info(f"  {check}: {'PASSED' if result else 'FAILED/SKIPPED'}")
         
    if final_outcome_passed:
        logger.info(f"Result: Diagnostics (Level: {level}) completed without critical warnings.")
        sys.exit(0) # Exit code 0 indicates required checks passed for the level
    else:
        logger.warning(f"Result: Diagnostics (Level: {level}) completed with warnings/failures.")
        sys.exit(1) # Exit code 1 indicates issues found

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