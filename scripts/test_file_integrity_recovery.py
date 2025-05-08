#!/usr/bin/env python3
"""
Test File Integrity Recovery Script

Simulates mid-write file corruption and tests recovery using .bak files.
Covers .py, .json, and .md file types.
"""

import hashlib
import json
import logging
import shutil
import time
from pathlib import Path

# --- Configuration ---
TEST_DIR = Path("runtime/temp/integrity_test_files")
CONTENT_PY = """
# Original Python Content
import sys

def main():
    print("Running Python script")
    return 0

if __name__ == "__main__":
    sys.exit(main())
"""
CONTENT_JSON = {"key": "original_value", "count": 1, "nested": {"status": True}}
CONTENT_MD = """
# Markdown Document

This is the *original* content.

- Point 1
- Point 2
"""

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("IntegrityRecoveryTest")

# --- Helper Functions ---


def calculate_sha256(filepath: Path) -> str:
    """Calculates the SHA256 hash of a file."""
    hasher = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            while chunk := f.read(4096):
                hasher.update(chunk)
        return hasher.hexdigest()
    except FileNotFoundError:
        return ""
    except Exception as e:
        logger.error(f"Error hashing {filepath}: {e}")
        return ""


def setup_test_environment():
    """Creates the test directory and initial files with backups."""
    if TEST_DIR.exists():
        logger.info(f"Cleaning up existing test directory: {TEST_DIR}")
        shutil.rmtree(TEST_DIR)
    TEST_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Created test directory: {TEST_DIR}")

    files_to_create = {
        "test.py": CONTENT_PY,
        "test.json": json.dumps(CONTENT_JSON, indent=2),
        "test.md": CONTENT_MD,
    }

    for filename, content in files_to_create.items():
        filepath = TEST_DIR / filename
        bak_filepath = filepath.with_suffix(filepath.suffix + ".bak")
        try:
            # Write original content
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"Created original file: {filepath}")

            # Create backup
            shutil.copy2(filepath, bak_filepath)
            logger.info(f"Created backup file: {bak_filepath}")
        except Exception as e:
            logger.error(f"Error creating {filename} or its backup: {e}", exc_info=True)
            raise


def simulate_corruption(filepath: Path, content_to_write: str):
    """Simulates a mid-write corruption by writing partial content."""
    logger.warning(f"Simulating corruption for: {filepath}")
    try:
        # Calculate approximate midpoint
        midpoint = len(content_to_write) // 2
        partial_content = content_to_write[:midpoint]

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(partial_content)
            # Simulate interruption before flush/close
            f.flush()  # May or may not happen in real crash
            # os.fsync(f.fileno()) # Even stronger sync, often skipped
            logger.warning(f"Write interrupted after {len(partial_content)} bytes.")
            # NOTE: No f.close() here to simulate unexpected termination
        time.sleep(0.1)  # Brief pause
        return True
    except Exception as e:
        logger.error(
            f"Error during simulated corruption of {filepath}: {e}", exc_info=True
        )
        return False


def attempt_recovery(filepath: Path) -> bool:
    """Attempts to recover the file from its .bak counterpart."""
    bak_filepath = filepath.with_suffix(filepath.suffix + ".bak")
    logger.info(f"Attempting recovery for {filepath} from {bak_filepath}")

    if not bak_filepath.exists():
        logger.error(f"Recovery failed: Backup file not found: {bak_filepath}")
        return False

    try:
        shutil.copy2(bak_filepath, filepath)  # Use copy2 to preserve metadata
        logger.info(f"Successfully recovered {filepath} from backup.")
        return True
    except Exception as e:
        logger.error(f"Recovery failed for {filepath}: {e}", exc_info=True)
        return False


def verify_integrity(filepath: Path, original_hash: str) -> bool:
    """Verifies the file's integrity by comparing its hash to the original."""
    current_hash = calculate_sha256(filepath)
    logger.info(
        f"Verifying integrity of {filepath}. Original Hash: {original_hash}, Current Hash: {current_hash}"
    )
    if current_hash == original_hash:
        logger.info(f"SUCCESS: Integrity verified for {filepath}.")
        return True
    else:
        logger.error(f"FAILURE: Integrity check failed for {filepath}.")
        # Log content for debugging json specifically
        if filepath.suffix == ".json":
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    logger.error(f"Actual content: {f.read()}")
            except Exception:
                logger.error("Could not read actual content.")
        return False


# --- Main Test Execution ---
if __name__ == "__main__":
    logger.info("Starting File Integrity Recovery Test Script...")
    results = {}

    try:
        setup_test_environment()

        # Store original hashes
        original_hashes = {}
        for filename in ["test.py", "test.json", "test.md"]:
            original_hashes[filename] = calculate_sha256(TEST_DIR / filename)
            if not original_hashes[filename]:
                raise ValueError(f"Could not calculate initial hash for {filename}")

        # --- Test Loop ---
        files_to_test = {
            "test.py": CONTENT_PY.replace(
                "Original", "MODIFIED"
            ),  # Use modified content for corruption attempt
            "test.json": json.dumps({"key": "MODIFIED", "count": 2}, indent=2),
            "test.md": CONTENT_MD.replace("original", "MODIFIED"),
        }

        for filename, modified_content in files_to_test.items():
            logger.info(f"\n--- Testing {filename} ---")
            filepath = TEST_DIR / filename
            test_passed = False

            # 1. Simulate Corruption
            if simulate_corruption(filepath, modified_content):
                # Verify corruption happened (hash should differ)
                if calculate_sha256(filepath) == original_hashes[filename]:
                    logger.error(
                        f"Corruption simulation failed for {filename} - hash unchanged."
                    )
                else:
                    logger.info(f"Corruption confirmed for {filename} (hash changed).")
                    # 2. Attempt Recovery
                    if attempt_recovery(filepath):
                        # 3. Verify Integrity
                        test_passed = verify_integrity(
                            filepath, original_hashes[filename]
                        )
            else:
                logger.error(
                    f"Skipping recovery for {filename} due to corruption simulation error."
                )

            results[filename] = test_passed

    except Exception as e:
        logger.critical(f"Test script encountered critical error: {e}", exc_info=True)
    finally:
        logger.info("\n--- Test Summary ---")
        for filename, passed in results.items():
            logger.info(f"{filename}: {'PASSED' if passed else 'FAILED'}")

        # Optional: Keep test files for inspection
        # logger.info(f"Test files located at: {TEST_DIR}")
        # Optional: Cleanup
        if TEST_DIR.exists():
            logger.info("Cleaning up test directory.")
            # shutil.rmtree(TEST_DIR)

        logger.info("Test script finished.")
