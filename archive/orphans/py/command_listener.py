import json
import logging
import time
from pathlib import Path

import jsonschema

# Assuming src is in PYTHONPATH or this script is adjusted to find dreamos utils
from dreamos.utils import file_io
from payload_handler import process_gpt_command
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

# Configure logging (integrate with KNURLSHADE later)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# MODIFIED: Use Path objects
SCRIPT_DIR = Path(__file__).resolve().parent
COMMAND_DIR = (SCRIPT_DIR / "../incoming_commands").resolve()
SCHEMA_PATH = (SCRIPT_DIR / "../schemas/gpt_command_schema.json").resolve()
PROCESSED_DIR = (COMMAND_DIR / "processed").resolve()
ERROR_DIR = (COMMAND_DIR / "error").resolve()

# Load the command schema
try:
    with open(SCHEMA_PATH, "r") as f:
        command_schema = json.load(f)
    logger.info(f"Successfully loaded command schema from {SCHEMA_PATH}")
except FileNotFoundError:
    logger.error(f"FATAL: Command schema not found at {SCHEMA_PATH}. Exiting.")
    exit(1)
except json.JSONDecodeError:
    logger.error(f"FATAL: Error decoding JSON schema at {SCHEMA_PATH}. Exiting.")
    exit(1)


class CommandFileHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith(".json"):
            logger.info(f"Detected new command file: {event.src_path}")
            self.process_file(Path(event.src_path))

    def process_file(self, file_path: Path):
        try:
            # Short delay to ensure file write is complete
            time.sleep(0.2)
            with open(file_path, "r") as f:
                payload = json.load(f)
            logger.info(f"Read payload from {file_path.name}")

            # Validate payload against schema
            jsonschema.validate(instance=payload, schema=command_schema)
            logger.info(
                f"Payload {payload.get('request_id', '')} validated against schema."
            )

            # Process the command
            result = process_gpt_command(payload)
            logger.info(
                f"Processing result for {payload.get('request_id', '')}: {result.get('status')}"
            )

            # Move to processed directory (or error directory)
            target_dir = (
                PROCESSED_DIR if result.get("status") == "success" else ERROR_DIR
            )

            # MODIFIED: Use file_io.move_file (which also handles dir creation)
            moved_path = file_io.move_file(
                source_path=file_path, destination_dir=target_dir
            )
            if moved_path:
                logger.info(f"Moved {file_path.name} to {target_dir.name} directory.")
            else:
                logger.error(
                    f"Failed to move {file_path.name} to {target_dir.name} directory using file_io. See previous logs."
                )

        except json.JSONDecodeError:
            logger.error(
                f"Error decoding JSON from {file_path}. Moving to error directory."
            )
            # MODIFIED: Use file_io.move_file
            file_io.move_file(source_path=file_path, destination_dir=ERROR_DIR)
        except jsonschema.exceptions.ValidationError as ve:
            logger.error(
                f"Schema validation failed for {file_path}: {ve.message}. Moving to error directory."
            )
            # MODIFIED: Use file_io.move_file
            file_io.move_file(source_path=file_path, destination_dir=ERROR_DIR)
        except FileNotFoundError:
            logger.warning(
                f"File {file_path} not found, likely processed already or race condition."
            )
        except Exception as e:
            logger.error(f"Unexpected error processing {file_path}: {e}", exc_info=True)
            # Attempt to move to error directory
            try:
                # MODIFIED: Use file_io.move_file
                file_io.move_file(source_path=file_path, destination_dir=ERROR_DIR)
            except Exception as move_err:
                # file_io.move_file logs its own errors, this is for the very outer failure.
                logger.error(
                    f"Failed to move corrupted file {file_path} to error dir during exception handling: {move_err}"
                )


def start_listener():
    # Ensure directories exist
    # MODIFIED: Use file_io.ensure_directory
    dirs_to_ensure = [COMMAND_DIR, PROCESSED_DIR, ERROR_DIR]
    for d in dirs_to_ensure:
        if not file_io.ensure_directory(d):
            logger.error(
                f"FATAL: Failed to create critical directory {d}. Listener cannot start."
            )
            return

    logger.info(f"Monitoring directory for commands: {COMMAND_DIR}")

    event_handler = CommandFileHandler()
    observer = Observer()
    observer.schedule(event_handler, COMMAND_DIR, recursive=False)
    observer.start()
    logger.info("Command listener started.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        logger.info("Command listener stopped.")
    observer.join()


if __name__ == "__main__":
    start_listener()
