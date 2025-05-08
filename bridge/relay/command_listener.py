import json
import logging
import os
import time

import jsonschema
from payload_handler import process_gpt_command
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

# Configure logging (integrate with KNURLSHADE later)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

COMMAND_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../incoming_commands")
)
SCHEMA_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../schemas/gpt_command_schema.json")
)
PROCESSED_DIR = os.path.abspath(os.path.join(COMMAND_DIR, "processed"))
ERROR_DIR = os.path.abspath(os.path.join(COMMAND_DIR, "error"))

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
            self.process_file(event.src_path)

    def process_file(self, file_path):
        try:
            # Short delay to ensure file write is complete
            time.sleep(0.2)
            with open(file_path, "r") as f:
                payload = json.load(f)
            logger.info(f"Read payload from {os.path.basename(file_path)}")

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
            os.makedirs(target_dir, exist_ok=True)
            os.rename(file_path, os.path.join(target_dir, os.path.basename(file_path)))
            logger.info(
                f"Moved {os.path.basename(file_path)} to {os.path.basename(target_dir)} directory."
            )

        except json.JSONDecodeError:
            logger.error(
                f"Error decoding JSON from {file_path}. Moving to error directory."
            )
            os.makedirs(ERROR_DIR, exist_ok=True)
            os.rename(file_path, os.path.join(ERROR_DIR, os.path.basename(file_path)))
        except jsonschema.exceptions.ValidationError as ve:
            logger.error(
                f"Schema validation failed for {file_path}: {ve.message}. Moving to error directory."
            )
            os.makedirs(ERROR_DIR, exist_ok=True)
            os.rename(file_path, os.path.join(ERROR_DIR, os.path.basename(file_path)))
        except FileNotFoundError:
            logger.warning(
                f"File {file_path} not found, likely processed already or race condition."
            )
        except Exception as e:
            logger.error(f"Unexpected error processing {file_path}: {e}", exc_info=True)
            # Attempt to move to error directory
            try:
                os.makedirs(ERROR_DIR, exist_ok=True)
                os.rename(
                    file_path, os.path.join(ERROR_DIR, os.path.basename(file_path))
                )
            except Exception as move_err:
                logger.error(
                    f"Failed to move corrupted file {file_path} to error dir: {move_err}"
                )


def start_listener():
    # Ensure directories exist
    os.makedirs(COMMAND_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    os.makedirs(ERROR_DIR, exist_ok=True)
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
