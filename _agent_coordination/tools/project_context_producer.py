"""
Tool/Module to analyze logs and project files to produce basic context.
See: _agent_coordination/onboarding/TOOLS_GUIDE.md

Extracts potential file paths from log snippets and lists Python files.
"""

import argparse
import json
import sys
import re
import logging
import os
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Regex to find potential file paths (simplified, single-line raw string)
PATH_REGEX = re.compile(r'(?:['\"]?(?:[a-zA-Z0-9_.-][\\/]?)+?\.(?:py|md|json|txt|yaml|yml|toml|log|sh|bat|rs|js|ts)['\"]?)|(['"])((?:[a-zA-Z0-9_.-][\\/]?)+)\1')

def find_python_files(project_dir: Path) -> list[str]:
    """Recursively finds all .py files in a directory."""
    python_files = []
    try:
        for root, _, files in os.walk(project_dir):
            for file in files:
                if file.endswith(".py"):
                    # Get path relative to project_dir
                    full_path = Path(root) / file
                    try:
                         rel_path = str(full_path.relative_to(project_dir))
                         python_files.append(rel_path.replace('\\', '/')) # Normalize slashes
                    except ValueError:
                         python_files.append(str(full_path).replace('\\', '/')) # Use absolute if not relative
    except Exception as e:
        logger.warning(f"Error walking directory {project_dir} to find Python files: {e}")
    return sorted(list(set(python_files)))

def extract_paths_from_log(log_content: str) -> list[str]:
    """Extracts potential file paths mentioned in log content using regex."""
    potential_paths = set()
    try:
        for match in PATH_REGEX.finditer(log_content):
            # Group 2 captures quoted paths, first part captures paths with known extensions
            path = match.group(2) or match.group(0) 
            if path:
                # Basic normalization/cleanup
                path = path.strip('\'" .,;\n\r\t')
                path = path.replace('\\', '/') # Normalize slashes
                # Avoid adding single words or very short strings
                if '/' in path or ('.' in path and len(path) > 3):
                    potential_paths.add(path)
    except Exception as e:
        # Catch potential errors during regex processing on complex logs
        logger.warning(f"Error during regex path extraction: {e}")
    return sorted(list(potential_paths))

def produce_project_context(conversation_log, project_dir_str, return_dict=False):
    """Produces a basic context dictionary based on log and project files."""
    logger.info("[project_context_producer.py] Analyzing context...")
    project_dir = Path(project_dir_str).resolve()
    logger.info(f"  Project Dir: {project_dir}")
    if not project_dir.is_dir():
         logger.error(f"Project directory not found or is not a directory: {project_dir}")
         sys.exit(1)

    # Analyze log snippet
    log_paths = extract_paths_from_log(conversation_log)
    logger.debug(f"  Extracted {len(log_paths)} potential paths from log.")

    # Find Python files in project
    project_py_files = find_python_files(project_dir)
    logger.debug(f"  Found {len(project_py_files)} Python files in project.")

    # Generate context dictionary
    context = {
        "analyzed_log_length": len(conversation_log),
        "project_root": str(project_dir),
        "paths_mentioned_in_log": log_paths,
        "python_files_in_project": project_py_files,
        # Add more analysis here in the future (e.g., identify stall reason)
        "potential_stall_reason": "Analysis Basic: Stall reason requires more context.", 
        "suggested_next_actions": ["Review mentioned log paths", "Check project file structure"]
    }
    
    output_filename = "agent_bridge_context.json"
    output_file = project_dir / output_filename
    
    if return_dict:
        logger.info(f"  Returning context as dictionary (would be written to {output_file})")
        return context
    else:
        try:
            logger.info(f"Writing context summary to: {output_file}")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(context, f, indent=2)
            logger.info(f"Success: Context written to {output_file}")
            return None # Indicate file was written
        except Exception as e:
            logger.error(f"Error writing context file {output_file}: {e}", exc_info=True)
            sys.exit(1) # Exit with error if file write fails

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Produce basic project context summary from logs and file structure.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
    parser.add_argument("conversation_log_snippet", help="Snippet of the conversation log (provide as string or use stdin). Use 'stdin' to read from stdin.")
    parser.add_argument("project_directory", help="Path to the project root directory.")
    parser.add_argument("--output-dict", action="store_true", help="Print context dict to stdout instead of writing file.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging.")

    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled.")
        
    log_snippet = args.conversation_log_snippet
    if log_snippet.lower() == 'stdin':
         logger.info("Reading conversation log snippet from stdin...")
         try:
              log_snippet = sys.stdin.read()
         except Exception as e:
              logger.error(f"Failed to read log snippet from stdin: {e}")
              sys.exit(1)

    result_context = produce_project_context(
        conversation_log=log_snippet,
        project_dir_str=args.project_directory,
        return_dict=args.output_dict
    )
    
    if args.output_dict and result_context:
        # Print JSON directly to stdout
        print(json.dumps(result_context, indent=2)) 