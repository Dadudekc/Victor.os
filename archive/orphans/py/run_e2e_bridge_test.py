import json
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format="%(message)s")

CHAT_URL = "https://chatgpt.com/?model=gpt-4o"

PROMPT_FILE = Path("prompts/test_prompt.txt")
OUTBOX_DIR = Path("runtime/bridge_outbox")
COORDS_FILE = Path("runtime/config/cursor_agent_coords.json")
AGENT_ID = "1"


def validate_prompt_file():
    logger.info("🛠️  Step 1: Ensure prompt file exists")
    # Ensure parent directory of PROMPT_FILE exists
    PROMPT_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not PROMPT_FILE.exists():
        PROMPT_FILE.write_text("What is the meaning of life?\n", encoding="utf-8")
        logger.info(f"✅ Created prompt file → {PROMPT_FILE}")
    else:
        logger.info(f"✅ Prompt already exists → {PROMPT_FILE}")


def validate_coords():
    logger.info("🛠️  Step 2: Verify cursor_agent_coords.json contains Agent-1")
    # Ensure parent directory of COORDS_FILE exists
    COORDS_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        if not COORDS_FILE.exists():
            # Create a dummy coords file if it doesn't exist
            dummy_coords = {
                f"Agent-{AGENT_ID}": {
                    "input_box": {"x": 100, "y": 200},
                    "copy_button": {"x": 300, "y": 400},
                }
            }
            COORDS_FILE.write_text(json.dumps(dummy_coords, indent=4), encoding="utf-8")
            logger.info(f"✅ Created dummy coordinates file → {COORDS_FILE}")

        contents = json.loads(COORDS_FILE.read_text(encoding="utf-8"))
        key = f"Agent-{AGENT_ID}"
        assert key in contents
        assert "input_box" in contents[key]
        logger.info(f"✅ Found Agent-{AGENT_ID} with input_box coordinates.")
    except Exception as e:
        logger.error(f"❌ Step 2 failed: {e}")
        raise


def run_bridge_loop():
    logger.info("🛠️  Step 3: Run bridge loop subprocess")
    # Ensure OUTBOX_DIR exists
    OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
    command = [
        "python",
        "-m",
        "dreamos.bridge.run_bridge_loop",
        "--agent-id",
        AGENT_ID,
        "--prompt-file",
        str(PROMPT_FILE),
        "--coords",
        str(COORDS_FILE),
        "--chat-url",
        CHAT_URL,
        "--response-timeout",
        "90",  # Using a string as originally specified in one version
        "--outbox",
        str(OUTBOX_DIR),
    ]
    logger.debug(f"DEBUG: Running command: {' '.join(command)}")
    # The following subprocess.run call captures stdout and stderr.
    # ResponseHandler logs (via run_bridge_loop.py's logger) go to stderr.
    result = subprocess.run(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False
    )

    logger.info("\n--- Subprocess STDOUT ---")
    print(result.stdout)
    logger.info("--- Subprocess STDERR (includes ResponseHandler logs) ---")
    print(result.stderr)  # This line prints the ResponseHandler logs.

    if result.returncode != 0:
        logger.error(f"❌ Subprocess failed with exit code {result.returncode}")
        # Optionally, raise an exception here to make the test fail explicitly
        # raise subprocess.CalledProcessError(result.returncode, command, output=result.stdout, stderr=result.stderr)


def validate_output():
    logger.info("🛠️  Step 4: Validate output JSON")
    # Ensure OUTBOX_DIR exists before globbing
    OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(OUTBOX_DIR.glob(f"agent{AGENT_ID}_*.json"), reverse=True)
    if not files:
        logger.error("❌ No output JSON files found.")
        raise FileNotFoundError(
            f"Missing agent{AGENT_ID}_*.json response output in {OUTBOX_DIR.resolve()}"
        )

    latest = files[0]
    logger.info(f"Validating latest file: {latest}")
    data = json.loads(latest.read_text(encoding="utf-8"))
    ts_str = data.get("timestamp")
    if not ts_str:
        raise ValueError("Missing timestamp in output.")

    resp = data.get("response")
    if resp is None:  # Allow empty string but not None
        raise ValueError("Missing response field in output.")

    ts = datetime.strptime(ts_str, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    delta = (now - ts).total_seconds()

    # Allow for some clock skew and processing time, e.g., up to 5 minutes (300s) for the file to be considered recent
    # And not significantly in the future (e.g., more than 60s)
    if not (-60 < delta < 300):  # Timestamp should be recent but not in the future
        raise ValueError(
            f"Timestamp {ts_str} is not recent or is in the future. Delta: {delta}s"
        )

    logger.info(f"✅ Output file verified: {latest}")


if __name__ == "__main__":
    print("🔍 Starting E2E Bridge Loop Test\n")
    try:
        validate_prompt_file()
        validate_coords()
        run_bridge_loop()
        validate_output()
        print("\n✅ E2E Bridge Loop Test Succeeded")
    except Exception as e:
        logger.error(
            f"❌ E2E Bridge Loop Test FAILED: {type(e).__name__} - {e}", exc_info=True
        )
        # Optionally, exit with a non-zero code to indicate failure to CI systems
        # sys.exit(1)
        raise  # Re-raise to ensure test frameworks see the failure
