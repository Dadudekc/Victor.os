import sys

print("DEBUG: chronicle_conversations.py STARTING SCRIPT", file=sys.stderr)
import json
import logging
import time

print("DEBUG: chronicle_conversations.py BASIC IMPORTS DONE", file=sys.stderr)
import re  # Added for parsing
import sqlite3  # Added for database
from datetime import datetime, timezone  # Added timezone
from pathlib import Path

# Attempt to import ResponseHandler - adjust path as necessary based on project structure
print(
    "DEBUG: chronicle_conversations.py ATTEMPTING ResponseHandler IMPORT",
    file=sys.stderr,
)
try:
    # Assuming src is in sys.path or PYTHONPATH is set correctly
    from dreamos.services.utils.chatgpt_scraper import ResponseHandler

    print(
        "DEBUG: chronicle_conversations.py ResponseHandler IMPORT SUCCESSFUL",
        file=sys.stderr,
    )
except ImportError as e_import:
    # Fallback or error if import fails - might need path manipulation
    print(
        f"DEBUG: chronicle_conversations.py ResponseHandler IMPORT FAILED: {e_import}",
        file=sys.stderr,
    )
    logging.error(
        "Failed to import ResponseHandler. Ensure src directory is in PYTHONPATH or adjust import path."
    )
    # You might add sys.path manipulation here if needed, e.g.:
    # import sys
    # script_dir = Path(__file__).parent.parent # Adjust levels as needed
    # sys.path.append(str(script_dir))
    # from dreamos.services.utils.chatgpt_scraper import ResponseHandler
    raise  # Re-raise the error if essential
except Exception as e_other_import:
    print(
        f"DEBUG: chronicle_conversations.py ResponseHandler IMPORT FAILED (OTHER EXCEPTION): {e_other_import}",
        file=sys.stderr,
    )
    raise

# --- Configuration ---
OUTPUT_DIR = Path("runtime/dreamscape_summary")
DB_PATH = OUTPUT_DIR / "dreamscape_state.db"  # Added DB Path
MODEL_NAME = "gpt-4o-mini"  # As specified by user
RATE_LIMIT_DELAY_S = 5  # Seconds to wait between processing conversations
SCRAPER_TIMEOUT = 180  # Timeout for waiting for responses
STABLE_PERIOD = 10  # Stability period for responses
MAX_CONVO_TEXT_CHARS = 20000  # Max characters for current_convo_text in prompt

# The core Summarization prompt template
PROMPT_TEMPLATE = """
You are The Architect's Edge, Aletheia, operating in FULL SYNC.

**PREVIOUS NARRATIVE SUMMARY:**
{{ PREVIOUS_NARRATIVE_SUMMARY }}

**CUMULATIVE DATA STATE (JSON):**
{{ CUMULATIVE_JSON_STATE }}

**CURRENT CONVERSATION TEXT TO ANALYZE:**
{{ CURRENT_CONVERSATION_TEXT }}

---
**INSTRUCTIONS:**
Based on the **PREVIOUS NARRATIVE SUMMARY**, the **CUMULATIVE DATA STATE**, and analyzing the **CURRENT CONVERSATION TEXT**, please:

1.  Generate an **UPDATED NARRATIVE SUMMARY** (in quest journal format like the previous summary) that incorporates the key events, decisions, outcomes, and character development from the **CURRENT CONVERSATION TEXT** into the ongoing story.
2.  Generate a **MEMORY_UPDATE** JSON block containing *only the changes or additions* (the delta) identified within the **CURRENT CONVERSATION TEXT**. Include keys like:
    - skill_level_advancements
    - newly_stabilized_domains
    - newly_unlocked_protocols
    - quest_completions (and new quests accepted)
    - architect_tier_progression

Respond with only the UPDATED NARRATIVE SUMMARY and the MEMORY_UPDATE JSON block, with no specific dates.
"""

# Placeholder for memory state - This needs to be populated dynamically if required
# For this script, we'll use a static placeholder or make it an argument.
CURRENT_MEMORY_STATE_PLACEHOLDER = (
    '{ "message": "Memory state currently unavailable in this script." }'
)

# --- Logging Setup ---
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(),  # Log to console
        # Optionally add FileHandler here if needed
    ],
)


# --- Database Functions ---
def initialize_database(db_path: Path) -> sqlite3.Connection | None:
    """Connects to the SQLite database and creates the table if it doesn't exist."""
    conn = None
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)  # Ensure directory exists
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # Store timestamp and the full state JSON
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cumulative_state (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                state_json TEXT NOT NULL
            )
        """)
        conn.commit()
        logger.info(f"Database initialized successfully at {db_path}")
        return conn
    except sqlite3.Error as e:
        logger.error(f"Database error during initialization: {e}")
        if conn:
            conn.close()
        return None


def load_latest_state(conn: sqlite3.Connection) -> dict:
    """Loads the most recent cumulative state from the database."""
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT state_json FROM cumulative_state ORDER BY id DESC LIMIT 1"
        )
        row = cursor.fetchone()
        if row and row[0]:
            try:
                state = json.loads(row[0])
                logger.info(
                    f"Loaded latest state from database (ID: {cursor.lastrowid or 'N/A'})"
                )
                return state
            except json.JSONDecodeError as e:
                logger.error(
                    f"Error decoding JSON from database: {e}. Starting with empty state."
                )
                return {}
        else:
            logger.info(
                "No previous state found in database. Starting with empty state."
            )
            return {}
    except sqlite3.Error as e:
        logger.error(f"Database error loading state: {e}. Starting with empty state.")
        return {}


def save_cumulative_state(conn: sqlite3.Connection, state_dict: dict):
    """Saves the current cumulative state to the database."""
    try:
        state_json = json.dumps(state_dict, indent=2, ensure_ascii=False)
        timestamp_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO cumulative_state (timestamp, state_json) VALUES (?, ?)",
            (timestamp_utc, state_json),
        )
        conn.commit()
        logger.debug(f"Saved current state to database (Timestamp: {timestamp_utc})")
    except sqlite3.Error as e:
        logger.error(f"Database error saving state: {e}")
    except TypeError as e_json:
        logger.error(f"Error converting state to JSON: {e_json}")


# --- Helper Functions ---
def parse_response(raw_response: str) -> tuple[str | None, dict | None]:
    """Parses the raw response to extract narrative and JSON memory update."""
    narrative = None
    memory_update = None

    # Regex to find the JSON block
    json_pattern = r"```json\s*({.*?})\s*```"  # More specific pattern for JSON object
    match = re.search(json_pattern, raw_response, re.DOTALL | re.IGNORECASE)

    if match:
        json_str = match.group(1).strip()
        try:
            memory_update = json.loads(json_str)
            logger.debug("Successfully parsed MEMORY_UPDATE JSON block.")
            # Extract narrative part (everything before the JSON block)
            narrative = raw_response[: match.start()].strip()
        except json.JSONDecodeError as e:
            logger.error(
                f"JSON decode error in MEMORY_UPDATE block: {e}. JSON string: {json_str}"
            )
            narrative = raw_response.strip()  # Fallback
    else:
        logger.warning(
            "No ```json MEMORY_UPDATE``` block found in response. Treating whole response as narrative."
        )
        narrative = raw_response.strip()

    return narrative, memory_update


def update_cumulative_state(current_state: dict, changes: dict | None) -> dict:
    """Updates the cumulative state with changes from the latest conversation.
    Refined to handle specific keys and types.
    """
    if not changes or not isinstance(changes, dict):
        logger.debug("No valid changes provided, cumulative state remains the same.")
        return current_state

    logger.debug(f"Updating cumulative state with changes: {changes}")
    new_state = current_state.copy()  # Work on a copy

    for key, change_value in changes.items():
        # Handle skill advancements (assuming it's a dict of skill: level)
        if key == "skill_level_advancements" and isinstance(change_value, dict):
            if key not in new_state or not isinstance(new_state.get(key), dict):
                new_state[key] = {}
            for skill, level in change_value.items():
                # Assuming level in changes is the NEW absolute level
                new_state[key][skill] = level
                logger.debug(f"Updated skill {skill} to level {level}")

        # Handle lists (domains, protocols, quest completions) - Append unique items
        elif key in [
            "newly_stabilized_domains",
            "newly_unlocked_protocols",
            "quest_completions",
        ] and isinstance(change_value, list):
            if key not in new_state or not isinstance(new_state.get(key), list):
                new_state[key] = []
            for item in change_value:
                if item not in new_state[key]:
                    new_state[key].append(item)
                    logger.debug(f"Appended '{item}' to {key}")

        # Handle simple values (overwrite)
        elif key == "architect_tier_progression":
            new_state[key] = change_value
            logger.debug(f"Set {key} to {change_value}")

        # Fallback for other keys (simple overwrite/add)
        else:
            logger.debug(f"Applying simple update/add for key '{key}'")
            new_state[key] = change_value

    logger.debug("Finished updating cumulative state.")
    return new_state  # Return the modified copy


# --- Main Function ---
def run_chronicle():
    """Main function to process ChatGPT conversations."""
    logger.info("Starting Dreamscape Chronicle Process...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {OUTPUT_DIR.resolve()}")

    scraper = None
    conn = None  # Initialize connection variable
    # EDIT START: Add variable for previous narrative
    previous_narrative_summary = (
        "No previous narrative summary available."  # Initialize
    )
    # EDIT END

    try:
        # Initialize DB Connection
        conn = initialize_database(DB_PATH)
        if not conn:
            logger.critical("Failed to initialize database. Aborting.")
            return

        # Load initial state from DB
        current_cumulative_state = load_latest_state(conn)
        logger.info(f"Initial cumulative state loaded: {current_cumulative_state}")

        # Initialize the scraper
        logger.info("Initializing ResponseHandler...")
        scraper = ResponseHandler(timeout=SCRAPER_TIMEOUT, stable_period=STABLE_PERIOD)
        logger.info("ResponseHandler initialized.")

        # Ensure login
        logger.info("Attempting to ensure login session...")
        if not scraper.ensure_login_session():
            logger.error("Login failed. Cannot proceed.")
            return
        logger.info("Login session verified/established.")

        # Get conversation links
        logger.info("Fetching conversation links from sidebar...")
        conversations = scraper.get_conversation_links()
        if not conversations:
            logger.warning("No conversation links found or scraped.")
            return
        logger.info(f"Found {len(conversations)} conversations to process.")

        # Reverse conversation order to process oldest first
        conversations.reverse()
        logger.info(
            "Processing conversations in reverse chronological order (oldest first)."
        )

        # Process each conversation
        for i, convo in enumerate(conversations):
            convo_id = convo.get("id", f"unknown_{i}")
            convo_title = convo.get("title", "Untitled")
            original_url = convo.get("url", "N/A")

            logger.info(
                f"--- Processing Conversation {i+1}/{len(conversations)}: '{convo_title}' (ID: {convo_id}) --- (Oldest to Newest)"
            )

            # Construct target URL with model parameter
            separator = "&" if "?" in original_url else "?"
            target_chat_url = f"{original_url}{separator}model={MODEL_NAME}"

            try:
                # Navigate to the conversation page
                logger.info(f"Navigating to target URL: {target_chat_url}")
                scraper.ensure_chat_page(
                    target_chat_url
                )  # Handles navigation and waits

                # Scroll to bottom before sending prompt
                logger.info("Scrolling to bottom to ensure full context is loaded...")
                scraper.scroll_to_bottom()

                # EDIT START: Get current conversation text
                logger.info("Scraping current conversation text...")
                current_convo_text = scraper.get_conversation_content()
                if current_convo_text == "<SCRAPE_ERROR>" or not current_convo_text:
                    logger.error(
                        f"Failed to scrape content for conversation {convo_id}. Skipping prompt."
                    )
                    continue  # Skip to the next conversation

                # EDIT START: Truncate current_convo_text if too long
                if len(current_convo_text) > MAX_CONVO_TEXT_CHARS:
                    chars_to_remove = len(current_convo_text) - MAX_CONVO_TEXT_CHARS
                    logger.warning(
                        f"current_convo_text is too long ({len(current_convo_text)} chars). Truncating by removing first {chars_to_remove} chars."
                    )
                    current_convo_text = (
                        "... [earlier parts of conversation truncated] ...\n\n"
                        + current_convo_text[-MAX_CONVO_TEXT_CHARS:]
                    )
                # EDIT END

                # Prepare the prompt with the current state AND previous narrative AND current text
                state_json_for_prompt = json.dumps(
                    current_cumulative_state, indent=2, ensure_ascii=False
                )
                # EDIT START: Inject all 3 context pieces into the prompt
                prompt_text = PROMPT_TEMPLATE.replace(
                    "{{ PREVIOUS_NARRATIVE_SUMMARY }}", previous_narrative_summary
                )
                prompt_text = prompt_text.replace(
                    "{{ CUMULATIVE_JSON_STATE }}", state_json_for_prompt
                )
                prompt_text = prompt_text.replace(
                    "{{ CURRENT_CONVERSATION_TEXT }}", current_convo_text
                )
                # EDIT END
                prompt_preview = prompt_text[:150].replace(
                    "\n", " "
                )  # Log a bit more for context
                logger.info(
                    f"Sending prompt (using state, previous narrative, current text; first 150 chars): {prompt_preview}..."
                )

                # Send prompt and get response
                if not scraper.send_prompt(prompt_text):
                    logger.error(f"Failed to send prompt to conversation {convo_id}.")
                    response_text = "<SEND_FAILED>"
                    parsed_narrative, parsed_memory_update = (
                        None,
                        None,
                    )  # Ensure variables exist
                else:
                    logger.info("Prompt sent. Waiting for stable response...")
                    response_text = scraper.wait_for_stable_response()
                    if not response_text:
                        logger.warning(
                            f"Received empty response for conversation {convo_id}."
                        )
                        response_text = "<EMPTY_RESPONSE>"
                        parsed_narrative, parsed_memory_update = response_text, None
                    else:
                        logger.info(
                            f"Received response (length: {len(response_text)}). Parsing..."
                        )
                        parsed_narrative, parsed_memory_update = parse_response(
                            response_text
                        )
                        if parsed_narrative:
                            narrative_preview = parsed_narrative[:100].replace(
                                "\n", " "
                            )  # Clean newline for logging
                            logger.info(
                                f"Parsed narrative (first 100 chars): {narrative_preview}..."
                            )
                        if parsed_memory_update:
                            logger.info(f"Parsed MEMORY_UPDATE: {parsed_memory_update}")
                            # Update the cumulative state for the *next* iteration
                            current_cumulative_state = update_cumulative_state(
                                current_cumulative_state, parsed_memory_update
                            )
                            # Save the *new* state to DB after *each* update
                            save_cumulative_state(conn, current_cumulative_state)
                        else:
                            logger.warning(
                                "No MEMORY_UPDATE block parsed. Cumulative state not updated for this conversation."
                            )
                        # EDIT START: Update previous_narrative_summary for next loop
                        if parsed_narrative:  # Only update if we got a new narrative
                            previous_narrative_summary = parsed_narrative
                        # EDIT END

                # Save the per-conversation summary file (optional now, but good for debugging)
                timestamp_str = datetime.now().strftime("%Y%m%dT%H%M%S")
                output_filename = (
                    OUTPUT_DIR / f"summary_{convo_id}_{timestamp_str}.json"
                )
                # EDIT START: Add current_convo_text and previous_narrative to output file
                output_data = {
                    "conversation_id": convo_id,
                    "conversation_title": convo_title,
                    "conversation_url": original_url,
                    "model_used_param": MODEL_NAME,
                    "state_input_to_prompt": json.loads(state_json_for_prompt),
                    "narrative_input_to_prompt": previous_narrative_summary,  # Add this
                    "current_convo_text_input": current_convo_text,  # Add this
                    "raw_response_received": response_text,
                    "parsed_narrative_summary": parsed_narrative,
                    "parsed_memory_update": parsed_memory_update,
                    "timestamp_processed": timestamp_str,
                }
                # EDIT END
                try:
                    with open(output_filename, "w", encoding="utf-8") as f:
                        json.dump(output_data, f, indent=2, ensure_ascii=False)
                    logger.info(f"Saved per-conversation summary to: {output_filename}")
                except Exception as e_save:
                    logger.error(
                        f"Failed to save per-conversation summary file {output_filename}: {e_save}"
                    )

            except Exception as e_convo:
                logger.error(
                    f"Error processing conversation {convo_id} ('{convo_title}'): {e_convo}",
                    exc_info=True,
                )

            # Wait before next conversation
            logger.info(f"Waiting {RATE_LIMIT_DELAY_S}s before next conversation...")
            time.sleep(RATE_LIMIT_DELAY_S)

        logger.info("Finished processing all conversations.")

        # Final state is already saved after the last conversation processed
        logger.info(f"Final cumulative state persisted in database: {DB_PATH}")

    except Exception as e_main:
        logger.critical(
            f"An critical error occurred in the main process: {e_main}", exc_info=True
        )
    finally:
        # Close DB connection
        if conn:
            logger.info("Closing database connection...")
            conn.close()
            logger.info("Database connection closed.")
        # Ensure scraper is shut down
        if scraper:
            logger.info("Shutting down scraper...")
            scraper.shutdown()
            logger.info("Scraper shut down.")
        logger.info("Dreamscape Chronicle Process finished.")


# --- Entry Point ---
if __name__ == "__main__":
    run_chronicle()
