import json
import logging
import sys
from pathlib import Path

# --- Configuration ---
SUMMARY_DIR = Path("runtime/dreamscape_summary")
OUTPUT_DEVLOG_MD = SUMMARY_DIR / "compiled_devlog.md"

# --- Logging Setup ---
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],  # Log to stdout for this script
)


def compile_devlog():
    logger.info(f"Starting devlog compilation from: {SUMMARY_DIR}")
    SUMMARY_DIR.mkdir(parents=True, exist_ok=True)

    summary_files = sorted(SUMMARY_DIR.glob("summary_*.json"))

    if not summary_files:
        logger.warning(
            f"No summary_*.json files found in {SUMMARY_DIR}. Nothing to compile."
        )
        return

    logger.info(f"Found {len(summary_files)} summary files to process.")

    full_devlog_content = []
    processed_count = 0

    for summary_file_path in summary_files:
        logger.debug(f"Processing file: {summary_file_path.name}")
        try:
            with open(summary_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            title = data.get("conversation_title", "Untitled Conversation")
            # Use parsed_narrative_summary, fallback to raw_response_received if narrative is missing/None
            narrative = data.get("parsed_narrative_summary")
            status_message_for_failed = ""

            if not narrative:  # Check if None or empty
                raw_response = data.get(
                    "raw_response_received", "No content available for this entry."
                )
                if (
                    raw_response == "<SEND_FAILED>"
                    or raw_response == "<EMPTY_RESPONSE>"
                ):
                    logger.warning(
                        f"Narrative missing or marked as failed for '{title}' (Status: {raw_response}). Using placeholder."
                    )
                    status_message_for_failed = raw_response  # Store the actual status
                    narrative = f"**Narrative**: *The chronicle for this chapter is currently unavailable. The attempt to summarize this part of the journey encountered an obstacle (Status: {status_message_for_failed}). Further investigation may be required to recover the tale.*"
                elif (
                    not raw_response
                ):  # Still none or empty after checking raw_response
                    narrative = "**Narrative**: *No narrative content was recorded for this entry. The archives are silent on this chapter.*"
                else:  # Raw response exists but parsed_narrative was missing, use raw as fallback
                    logger.info(
                        f"Using raw_response_received as fallback narrative for '{title}'."
                    )
                    narrative = raw_response

            # Fallback for title if it's an empty string
            if not title.strip():
                title = f"Untitled Entry ({summary_file_path.stem})"

            # Basic Markdown formatting
            full_devlog_content.append(f"## {title}\n")
            full_devlog_content.append(f"{narrative}\n")
            full_devlog_content.append("\n---\n")  # Separator
            processed_count += 1

        except json.JSONDecodeError:
            logger.error(
                f"Error decoding JSON from {summary_file_path.name}. Skipping."
            )
        except Exception as e:
            logger.error(
                f"Error processing file {summary_file_path.name}: {e}. Skipping."
            )

    if not full_devlog_content:
        logger.info("No content was successfully processed. Devlog will be empty.")
        final_output = "No devlog entries could be compiled."
    else:
        final_output = "\n".join(full_devlog_content)
        logger.info(f"Successfully processed {processed_count} entries for the devlog.")

    # Print to console
    print("\n--- COMPILED DEVLOG ---")
    print(final_output)
    print("--- END OF DEVLOG ---\n")

    # Save to markdown file
    try:
        with open(OUTPUT_DEVLOG_MD, "w", encoding="utf-8") as f:
            f.write(final_output)
        logger.info(f"Devlog successfully saved to: {OUTPUT_DEVLOG_MD.resolve()}")
    except Exception as e:
        logger.error(f"Error saving devlog to file {OUTPUT_DEVLOG_MD}: {e}")


if __name__ == "__main__":
    compile_devlog()
