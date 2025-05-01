"""
Transforms every ChatGPT conversation into a Dreamscape episode + JSON
state file.  Uses headless browser automation — login creds must be
supplied via ENV, not an API key.

Required AppConfig fields (env vars):
    CHATGPT_EMAIL
    CHATGPT_PASSWORD
    # Optional: CHATGPT_TOTP_SECRET  (for 2-factor, if supported)

ChatGPTScraper must already:
    • perform credential login with the above fields
    • persist cookies to avoid daily logins
    • expose the async methods used below
"""

import asyncio
import json
import logging  # Added for better logging
import textwrap
from datetime import datetime
from pathlib import Path

from src.dreamos.core.config import AppConfig
from src.dreamos.services.utils.chatgpt_scraper import ChatGPTScraper

# Configure basic logging for the script
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ---------- CONSTANT PROMPTS ----------
NARRATIVE_PROMPT = (
    "Based on the work done in this conversation, generate an episode from "
    "the MMORPG called The Dreamscape. Do NOT mention tasks, code, or instructions; "
    "produce immersive lore only."
)

SUMMARY_PROMPT = (
    "Summarize this Dreamscape episode strictly as JSON with keys:\n"
    "  stats, active_quests, completed_quests, spells, prayers, "
    "tools, weapons, skills (list {name,level,xp}), skill_tree.\n"
    "Return ONLY valid JSON."
)

PRIMER_TEMPLATE = textwrap.dedent(
    """
    You are the Lore-Forger of **The Digital Dreamscape**.
    Each ChatGPT conversation becomes the next episode of our saga.
    Carry the supplied JSON world-state forward as immutable canon.

    {state_block}
"""
).strip()

# ---------- UTILITIES ----------
SAVE_DIR = Path("runtime/dreamscape_logbook")
SAVE_DIR.mkdir(parents=True, exist_ok=True)


def safe_name(chat_id: str, ext: str) -> Path:
    # Sanitize chat_id if it contains invalid filename characters
    safe_chat_id = "".join(
        c for c in chat_id if c.isalnum() or c in ("-", "_")
    ).rstrip()
    if not safe_chat_id:  # Handle cases where ID becomes empty after sanitize
        safe_chat_id = "invalid_id"
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    return SAVE_DIR / f"episode_{ts}_{safe_chat_id[:8]}{ext}"


async def run_episode(scraper: ChatGPTScraper, convo: Dict, prev_state: str | None):
    # Assume convo is a dict with at least 'id' and potentially 'title'
    cid = convo.get("id")
    if not cid:
        logger.warning(
            f"Skipping conversation with missing ID: {convo.get('title', '[No Title]')}"
        )
        return prev_state  # Return previous state unchanged

    title = convo.get("title", "[No Title]")
    logger.info(f"\n▶ Processing {cid} – Title: {title!r}")

    try:
        logger.info(f"  Navigating to chat {cid}...")
        await scraper.load_chat(cid)
        logger.info(f"  Scrolling chat {cid}...")
        await scraper.scroll_to_bottom()

        # Inject state primer if available
        if prev_state:
            logger.info(f"  Injecting state primer for {cid}...")
            primer = PRIMER_TEMPLATE.format(state_block=f"```json\n{prev_state}\n```")
            await scraper.send_message_and_wait(primer)
            logger.debug(f"  Primer sent for {cid}")
            # Optional: Add a small delay after priming
            await asyncio.sleep(1)

        # 1️⃣ Generate and save Lore episode
        logger.info(f"  Injecting narrative prompt for {cid}...")
        await scraper.send_message_and_wait(NARRATIVE_PROMPT)
        story = await scraper.extract_latest_reply()
        story_path = safe_name(cid, ".md")
        story_path.write_text(
            story or "[ERROR: Empty story received]", encoding="utf-8"
        )
        logger.info(f"  • Lore saved to {story_path.name}")
        await asyncio.sleep(1)  # Small delay between prompts

        # 2️⃣ Generate and save JSON summary
        logger.info(f"  Injecting summary prompt for {cid}...")
        await scraper.send_message_and_wait(SUMMARY_PROMPT)
        raw_summary = await scraper.extract_latest_reply()

        summary = None
        parsed_successfully = False
        if raw_summary:
            try:
                # Try parsing directly
                summary = json.loads(raw_summary)
                parsed_successfully = True
            except json.JSONDecodeError:
                logger.warning(
                    f"  Initial JSON parse failed for {cid}. Trying to clean...",
                    exc_info=False,
                )
                try:
                    # Attempt to clean markdown code fences
                    cleaned_summary = raw_summary.strip()
                    if cleaned_summary.startswith("```json"):
                        cleaned_summary = cleaned_summary[len("```json") :].strip()
                    if cleaned_summary.startswith("```"):
                        cleaned_summary = cleaned_summary[len("```") :].strip()
                    if cleaned_summary.endswith("```"):
                        cleaned_summary = cleaned_summary[: -len("```") :].strip()

                    if cleaned_summary:  # Ensure not empty after stripping
                        summary = json.loads(cleaned_summary)
                        parsed_successfully = True
                    else:
                        logger.error(
                            f"  Summary for {cid} became empty after cleaning markdown fences."
                        )

                except json.JSONDecodeError as json_err:
                    logger.error(
                        f"  Failed to parse JSON summary for {cid} even after cleaning: {json_err}"
                    )
                    logger.debug(f"  Raw summary received for {cid}:\n{raw_summary}")
                except Exception as parse_err:  # Catch other potential errors
                    logger.error(
                        f"  Unexpected error parsing summary for {cid}: {parse_err}",
                        exc_info=True,
                    )
        else:
            logger.error(f"  Received empty summary response for {cid}.")

        # Save summary (even if parsing failed, save raw for debug)
        summary_path = safe_name(cid, ".json")
        if parsed_successfully and summary is not None:
            summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
            logger.info(f"  • JSON summary saved to {summary_path.name}")
            # Return compact JSON string for next iteration
            return json.dumps(summary, separators=(",", ":"))
        else:
            # Save the raw failing output for debugging
            summary_path.write_text(
                raw_summary or "[ERROR: Empty summary received]", encoding="utf-8"
            )
            logger.error(
                f"  • Failed to parse JSON summary; saved raw response to {summary_path.name}"
            )
            # Don't pass invalid state forward
            return prev_state

    except Exception as e:
        logger.error(
            f"❌ Unexpected error processing conversation {cid}: {e}", exc_info=True
        )
        # Return previous state so subsequent conversations don't fail due to missing primer
        return prev_state


async def main():
    logger.info("Loading configuration...")
    # cfg = AppConfig.load_from_env() # Original - relies on specific method
    cfg = AppConfig.load()  # Use standard load method
    logger.info("Configuration loaded.")

    scraper_cfg = cfg.chatgpt_scraper
    if not (scraper_cfg.email and scraper_cfg.password):
        logger.error(
            "Missing environment variables: Set DREAMOS_CHATGPT_SCRAPER__EMAIL and DREAMOS_CHATGPT_SCRAPER__PASSWORD"
        )
        return  # Exit if creds missing

    logger.info("Initializing ChatGPT Scraper...")
    # Pass the whole AppConfig; scraper __init__ should extract needed parts
    async with ChatGPTScraper(config=cfg, headless=True) as scraper:
        logger.info("Scraper initialized. Getting conversation list...")
        convos = await scraper.get_all_conversations()
        logger.info(f"Found {len(convos)} conversations.")

        state = None
        for convo in convos:
            # Process conversations one by one
            state = await run_episode(scraper, convo, state)
            # Optional: Add delay between processing conversations
            await asyncio.sleep(2)

    logger.info("Dreamscape conversation sync complete.")


if __name__ == "__main__":
    asyncio.run(main())
