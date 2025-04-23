"""
Tool to apply code content to a target file using various modes.
See: _agent_coordination/onboarding/TOOLS_GUIDE.md
"""

import argparse
import sys
import shutil
import logging
import uuid # Needed for atomic writes
import os # Import os for os.replace
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def apply_code(target_file_str, code_input, code_file, code_stdin, mode, create_dirs, backup, start_marker, end_marker, verbose):
    """Applies code to a target file based on the specified mode."""
    
    if verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled.")
        logger.debug(f"Received Request - Target: {target_file_str}, Mode: {mode}, Create Dirs: {create_dirs}, Backup: {backup}")

    # --- Determine Code Source --- #
    code_content = None
    source_description = ""
    try:
        if code_input is not None:
            code_content = code_input
            source_description = "direct input string"
        elif code_file is not None:
            code_file_path = Path(code_file)
            if not code_file_path.is_file():
                 logger.error(f"Code file not found: {code_file_path}")
                 sys.exit(1)
            code_content = code_file_path.read_text(encoding='utf-8')
            source_description = f"file ({code_file_path})"
        elif code_stdin:
            logger.debug("Reading code from standard input...")
            code_content = sys.stdin.read()
            source_description = "standard input"
        else:
            # This case should be prevented by argparse mutually exclusive group
            logger.error("Internal Error: No code source specified despite argparse requirement.")
            sys.exit(1)

        if code_content is None:
            logger.error(f"Failed to retrieve code content from {source_description}.")
            sys.exit(1)
            
        logger.debug(f"Successfully retrieved code from {source_description}. Length: {len(code_content)} chars.")

    except Exception as e:
        logger.error(f"Error retrieving code from {source_description}: {e}", exc_info=verbose)
        sys.exit(1)

    # --- Prepare Target Path --- #
    try:
        target_file = Path(target_file_str).resolve() # Use resolved absolute path
        target_dir = target_file.parent

        if create_dirs:
            if not target_dir.exists():
                logger.info(f"Target directory does not exist, creating: {target_dir}")
                target_dir.mkdir(parents=True, exist_ok=True)
            elif not target_dir.is_dir():
                 logger.error(f"Target path's parent exists but is not a directory: {target_dir}")
                 sys.exit(1)
                 
        # Check existence *after* potential creation
        if not target_dir.is_dir():
             logger.error(f"Target directory {target_dir} does not exist or couldn't be created. Use --create-dirs?" )
             sys.exit(1)
             
        # Check if target itself is a directory (can happen if path ends with /)
        if target_file.is_dir():
             logger.error(f"Target path specified is a directory, not a file: {target_file}")
             sys.exit(1)

    except Exception as e:
        logger.error(f"Error preparing target path {target_file_str}: {e}", exc_info=verbose)
        sys.exit(1)

    # --- Backup --- #
    if backup and target_file.exists():
        backup_file = target_file.with_suffix(target_file.suffix + '.bak')
        try:
            shutil.copy2(target_file, backup_file)
            logger.info(f"Backup created: {backup_file}")
        except Exception as e:
            logger.error(f"Error creating backup for {target_file}: {e}. Continuing without backup.", exc_info=verbose)
            # Non-fatal error

    # --- Apply Code Based on Mode --- #
    try:
        logger.info(f"Applying code to {target_file} (Mode: {mode})")
        if mode == 'overwrite':
            # Write atomically using temp file + os.replace()
            temp_file_path = target_file.with_suffix(f'.{uuid.uuid4()}.tmp')
            try:
                 with open(temp_file_path, 'w', encoding='utf-8') as f:
                      f.write(code_content)
                 # Use os.replace for atomic overwrite
                 os.replace(temp_file_path, target_file)
                 logger.info(f"Success: Overwrote {target_file}")
            except Exception as write_err:
                 # Clean up temp file on error
                 if temp_file_path.exists():
                      try: temp_file_path.unlink()
                      except: pass
                 raise write_err # Re-raise the exception

        elif mode == 'append':
            # Simple append
            with open(target_file, 'a', encoding='utf-8') as f:
                f.write(code_content)
            logger.info(f"Success: Appended code to {target_file}")

        elif mode == 'replace_markers':
            if not target_file.exists():
                logger.error(f"Error: Target file {target_file} must exist for 'replace_markers' mode.")
                sys.exit(1)
                
            original_content = target_file.read_text(encoding='utf-8')
            start_index = original_content.find(start_marker)
            if start_index == -1:
                logger.error(f"Error: Start marker '{start_marker}' not found in {target_file}.")
                sys.exit(1)
                
            end_index = original_content.find(end_marker, start_index + len(start_marker))
            if end_index == -1:
                 logger.error(f"Error: End marker '{end_marker}' not found after start marker in {target_file}.")
                 sys.exit(1)
                 
            # Construct new content
            new_content = (
                original_content[:start_index + len(start_marker)] +
                '\n' + # Ensure newline after start marker
                code_content +
                 '\n' + # Ensure newline before end marker
                original_content[end_index:]
            )
            
            # Write atomically using temp file + os.replace()
            temp_file_path = target_file.with_suffix(f'.{uuid.uuid4()}.tmp')
            try:
                 with open(temp_file_path, 'w', encoding='utf-8') as f:
                      f.write(new_content)
                 # Use os.replace for atomic overwrite
                 os.replace(temp_file_path, target_file)
                 logger.info(f"Success: Replaced content between markers in {target_file}")
            except Exception as write_err:
                 if temp_file_path.exists():
                      try: temp_file_path.unlink()
                      except: pass
                 raise write_err

        else:
            # Should be caught by argparse choices, but good practice
            logger.error(f"Internal Error: Unknown mode '{mode}'")
            sys.exit(1)
            
        # Success if no exception raised

    except FileNotFoundError:
         logger.error(f"Error: Target file not found: {target_file}. This might occur if the file was deleted after path preparation.")
         sys.exit(1)
    except OSError as e:
         logger.error(f"OS error applying code to {target_file}: {e}")
         sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error applying code to {target_file}: {e}", exc_info=verbose)
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Apply code to a file using various modes.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
    parser.add_argument("--target-file", required=True, help="Path to the target file.")

    # Input source group - mutually exclusive
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--code-input", help="Code content as a string.")
    input_group.add_argument("--code-file", help="Path to file containing code.")
    input_group.add_argument("--code-stdin", action='store_true', help="Read code from stdin.")

    parser.add_argument("--mode", choices=['overwrite', 'replace_markers', 'append'], default='overwrite', help="Application mode.")
    parser.add_argument("--create-dirs", action='store_true', help="Create parent directories if missing.")
    parser.add_argument("--backup", action='store_true', help="Create a .bak backup before modifying.")
    parser.add_argument("--start-marker", default="# CODE_APPLICATOR_START", help="Start marker for replace_markers mode.")
    parser.add_argument("--end-marker", default="# CODE_APPLICATOR_END", help="End marker for replace_markers mode.")
    parser.add_argument("-v", "--verbose", action='store_true', help="Enable verbose logging.")

    args = parser.parse_args()

    apply_code(
        target_file_str=args.target_file,
        code_input=args.code_input,
        code_file=args.code_file,
        code_stdin=args.code_stdin,
        mode=args.mode,
        create_dirs=args.create_dirs,
        backup=args.backup,
        start_marker=args.start_marker,
        end_marker=args.end_marker,
        verbose=args.verbose
    ) 