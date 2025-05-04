# Move archive_defunct_tests.py
# Target: src/dreamos/tools/discovery/archive_defunct_tests.py
# Content will be identical to the original file, just moved.

import argparse
import json
import logging
from pathlib import Path

# EDIT START: Import ArchivingError
from dreamos.core.errors import ArchivingError

# EDIT END

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Constants
DEFAULT_INPUT_FILE = "runtime/logs/defunct_tests.jsonl"
# Adjust archive root relative to the NEW location if necessary, but likely fine
DEFAULT_ARCHIVE_ROOT_REL_FROM_PROJ = "_archive/tests"
ARCHIVE_HEADER = "# ARCHIVED: Defunct test, source module potentially missing.\n"


def archive_defunct_tests(input_file: str, archive_root_rel: str):
    """
    Reads a list of potentially defunct test files from a JSONL file,
    prepends an archive header, moves them to an archive directory,
    and deletes the originals.
    """
    # Adjust project root calculation based on new file depth
    # src/dreamos/tools/discovery/archive_defunct_tests.py -> 4 levels up?
    project_root = Path(__file__).resolve().parents[4]  # EDIT: Corrected parent level?
    input_path = project_root / input_file
    archive_root_abs = project_root / archive_root_rel

    logger.info(f"Project root detected as: {project_root}")
    logger.info(f"Reading defunct test list from: {input_path}")
    logger.info(f"Archiving tests to: {archive_root_abs}")

    if not input_path.is_file():
        logger.error(f"Input file not found: {input_path}")
        return

    archived_count = 0
    error_count = 0
    errors_encountered = []  # Store specific error details

    try:
        with open(input_path, "r") as f:
            for line in f:
                relative_test_path_str = None  # Initialize for error logging
                try:
                    data = json.loads(line)
                    relative_test_path_str = data.get("defunct_test_file")
                    if not relative_test_path_str:
                        logger.warning(
                            f"Skipping line without 'defunct_test_file' key: {line.strip()}"  # noqa: E501
                        )
                        continue

                    original_test_path = project_root / relative_test_path_str
                    # Construct archive path using the relative path from JSONL
                    target_archive_path = archive_root_abs / Path(
                        relative_test_path_str
                    ).relative_to(Path(relative_test_path_str).parts[0])

                    if not original_test_path.is_file():
                        logger.warning(
                            f"Original test file not found, skipping: {original_test_path}"  # noqa: E501
                        )
                        continue

                    # Ensure target directory exists
                    target_archive_path.parent.mkdir(parents=True, exist_ok=True)

                    # Read, prepend header, write to archive
                    logger.info(
                        f"Archiving {original_test_path} to {target_archive_path}"
                    )
                    with open(original_test_path, "r", encoding="utf-8") as orig_f:
                        original_content = orig_f.read()

                    with open(target_archive_path, "w", encoding="utf-8") as arch_f:
                        arch_f.write(ARCHIVE_HEADER)
                        arch_f.write(original_content)

                    # Delete original file
                    original_test_path.unlink()
                    logger.debug(f"Deleted original file: {original_test_path}")

                    archived_count += 1

                except json.JSONDecodeError as e_json:
                    err_msg = f"Failed to parse JSON line: {line.strip()}"
                    logger.error(err_msg + f": {e_json}")
                    errors_encountered.append(err_msg)
                    error_count += 1
                except OSError as e_os:
                    path_info = (
                        relative_test_path_str
                        if relative_test_path_str
                        else "<unknown path from line>"
                    )
                    err_msg = f"OS error processing {path_info}: {e_os}"
                    logger.error(err_msg)
                    errors_encountered.append(err_msg)
                    error_count += 1
                except Exception as e_other:
                    path_info = (
                        relative_test_path_str
                        if relative_test_path_str
                        else "<unknown path from line>"
                    )
                    err_msg = f"Unexpected error processing {path_info}: {e_other}"
                    logger.exception(err_msg)  # Use exception for unexpected errors
                    errors_encountered.append(err_msg)
                    error_count += 1

        logger.info("Archiving process complete.")
        logger.info(f"Successfully archived {archived_count} files.")
        if error_count > 0:
            summary_err_msg = f"Encountered {error_count} errors during archiving. First error: {errors_encountered[0] if errors_encountered else 'N/A'}"  # noqa: E501
            logger.error(summary_err_msg)
            # EDIT START: Raise summary error
            raise ArchivingError(summary_err_msg)
            # EDIT END

    except IOError as e:
        err_msg_io = f"Failed to read input file {input_path}: {e}"
        logger.error(err_msg_io)
        # EDIT START: Raise summary error
        raise ArchivingError(err_msg_io) from e
        # EDIT END
    except Exception as e_outer:
        # Catch any other unexpected errors during file open/loop setup
        err_msg_outer = f"Unexpected error during archiving setup: {e_outer}"
        logger.exception(err_msg_outer)  # Log with traceback
        # EDIT START: Wrap in ArchivingError
        raise ArchivingError(err_msg_outer) from e_outer
        # EDIT END


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Archive potentially defunct test files identified by the discovery script."  # noqa: E501
    )
    parser.add_argument(
        "--input-file",
        default=DEFAULT_INPUT_FILE,
        help=f"Path to the JSONL file containing defunct test paths (default: {DEFAULT_INPUT_FILE})",  # noqa: E501
    )
    parser.add_argument(
        "--archive-dir",
        default=DEFAULT_ARCHIVE_ROOT_REL_FROM_PROJ,
        help=f"Relative path from project root to the directory for archived tests (default: {DEFAULT_ARCHIVE_ROOT_REL_FROM_PROJ})",  # noqa: E501
    )

    args = parser.parse_args()

    try:
        archive_defunct_tests(args.input_file, args.archive_dir)
        logger.info("Script finished successfully.")
    except ArchivingError as e:
        logger.error(f"Script finished with errors: {e}")
        # Optionally exit with non-zero status code
        exit(1)
    except Exception as e:
        logger.exception(f"Unhandled exception during script execution: {e}")
        exit(1)
