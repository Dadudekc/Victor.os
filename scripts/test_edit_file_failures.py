# scripts/test_edit_file_failures.py
import json
import os
import time
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Test Configuration ---
TEST_DIR = Path("runtime/temp/edit_test_files")

# Content variations
JSON_INITIAL = {"key1": "value1", "nested": {"key2": 123}}
JSON_OVERWRITE = {"keyA": "valueA", "claimed_task_id": None}

TOML_INITIAL = """\
[table]
key = "value"
number = 42
"""
TOML_OVERWRITE = """\
key_b = "value_b"
active = false
"""

PY_INITIAL = """\
# Initial Python content
def main():
    print("Hello")

if __name__ == "__main__":
    main()
"""
PY_OVERWRITE = """\
# Overwritten Python content
import sys

def run():
    print(f"Args: {sys.argv}")

run()
"""

# --- Test Functions ---

def setup_test_files():
    """Creates the test directory and initial files."""
    TEST_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Created/Ensured test directory: {TEST_DIR}")

    # Create initial files
    try:
        with open(TEST_DIR / "test.json", "w") as f:
            json.dump(JSON_INITIAL, f, indent=2)
        with open(TEST_DIR / "test.toml", "w") as f:
            f.write(TOML_INITIAL)
        with open(TEST_DIR / "test.py", "w") as f:
            f.write(PY_INITIAL)
        logger.info("Initial test files created.")
    except Exception as e:
        logger.error(f"Error creating initial test files: {e}", exc_info=True)
        raise

def attempt_edit_overwrite(target_file: Path, content_to_write: str):
    """Simulates calling the edit_file tool to overwrite a file."""
    logger.info(f"Attempting OVERWRITE edit on: {target_file}")
    logger.info(f"--- Content to Write ---\n{content_to_write}\n------------------------")

    # *** Placeholder for actual edit_file tool invocation ***
    # In a real scenario, this would call the tool API:
    # success = call_edit_file_tool(
    #     target_file=str(target_file),
    #     code_edit=content_to_write,
    #     instructions="OVERWRITE the entire file content."
    # )
    # For this test script, we simulate the *observed problematic behavior*
    # by appending instead of overwriting for JSON, or emptying for others.

    simulated_failure = True # Change to False to simulate success

    if simulated_failure:
        logger.warning("SIMULATING edit_file overwrite failure...")
        try:
            if target_file.suffix == '.json':
                # Simulate incorrect append behavior
                with open(target_file, "r+") as f:
                    try:
                        data = json.load(f)
                        if isinstance(data, dict):
                            data.update(json.loads(content_to_write)) # Simplistic merge
                        else: # Assume list or scalar, just append string
                            data = str(data) + "\n" + content_to_write
                    except json.JSONDecodeError:
                         # If initial file corrupt, just append
                         f.seek(0, os.SEEK_END)
                         f.write("\n" + content_to_write)
                    else:
                        f.seek(0)
                        f.truncate()
                        json.dump(data, f, indent=2)
                logger.warning(f"Simulated incorrect append/merge for {target_file}")
                return False # Simulate failure indication
            else:
                 # Simulate emptying file
                 with open(target_file, "w") as f:
                     f.write("")
                 logger.warning(f"Simulated emptying file for {target_file}")
                 return False # Simulate failure indication

        except Exception as e:
             logger.error(f"Error during simulated failure for {target_file}: {e}")
             return False # Simulate failure indication
    else:
        # Simulate successful overwrite
        try:
            with open(target_file, "w") as f:
                f.write(content_to_write)
            logger.info(f"Simulated successful overwrite for {target_file}")
            return True
        except Exception as e:
            logger.error(f"Error during simulated success write for {target_file}: {e}")
            return False

def verify_file_content(target_file: Path, expected_content: str):
    """Reads the file and compares its content to the expected content."""
    logger.info(f"Verifying content of: {target_file}")
    try:
        with open(target_file, "r") as f:
            actual_content = f.read()

        # Normalize line endings for comparison
        actual_norm = actual_content.replace('\r\n', '\n').strip()
        expected_norm = expected_content.replace('\r\n', '\n').strip()

        if actual_norm == expected_norm:
            logger.info(f"SUCCESS: Content matches expected for {target_file.name}.")
            return True
        else:
            logger.error(f"FAILURE: Content mismatch for {target_file.name}.")
            logger.error(f"--- Expected ---\n{expected_norm}\n----------------")
            logger.error(f"--- Actual ---\n{actual_norm}\n--------------")
            return False
    except FileNotFoundError:
        logger.error(f"FAILURE: File not found: {target_file}")
        return False
    except Exception as e:
        logger.error(f"Error verifying file {target_file}: {e}", exc_info=True)
        return False

# --- Main Test Execution ---
if __name__ == "__main__":
    logger.info("Starting edit_file overwrite failure test script...")
    results = {"json": False, "toml": False, "py": False}

    try:
        setup_test_files()

        # Test JSON Overwrite
        logger.info("\n--- Testing JSON Overwrite ---")
        json_file = TEST_DIR / "test.json"
        json_overwrite_str = json.dumps(JSON_OVERWRITE, indent=2)
        edit_success_json = attempt_edit_overwrite(json_file, json_overwrite_str)
        time.sleep(0.1) # Small delay
        # We expect verification to FAIL if the edit simulation failed
        results["json"] = verify_file_content(json_file, json_overwrite_str)
        logger.info(f"JSON Test Result (Verification == Expected Overwrite): {results['json']}")

        # Test TOML Overwrite
        logger.info("\n--- Testing TOML Overwrite ---")
        toml_file = TEST_DIR / "test.toml"
        edit_success_toml = attempt_edit_overwrite(toml_file, TOML_OVERWRITE)
        time.sleep(0.1)
        results["toml"] = verify_file_content(toml_file, TOML_OVERWRITE)
        logger.info(f"TOML Test Result (Verification == Expected Overwrite): {results['toml']}")

        # Test Python Overwrite
        logger.info("\n--- Testing Python Overwrite ---")
        py_file = TEST_DIR / "test.py"
        edit_success_py = attempt_edit_overwrite(py_file, PY_OVERWRITE)
        time.sleep(0.1)
        results["py"] = verify_file_content(py_file, PY_OVERWRITE)
        logger.info(f"Python Test Result (Verification == Expected Overwrite): {results['py']}")

    except Exception as e:
        logger.critical(f"Test script encountered critical error: {e}", exc_info=True)

    finally:
        logger.info("\n--- Test Summary ---")
        logger.info(f"JSON Overwrite Verification Passed: {results['json']}")
        logger.info(f"TOML Overwrite Verification Passed: {results['toml']}")
        logger.info(f"Python Overwrite Verification Passed: {results['py']}")
        logger.info("Note: If 'Simulated Failure' was enabled, Verification Passed should be False.")
        logger.info("Test script finished.") 