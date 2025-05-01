# scripts/generate_dreamscape_from_session.py

import asyncio

from src.dreamos.core.config import AppConfig
from src.dreamos.services.utils.chatgpt_scraper import ChatGPTScraper

DREAMSCAPE_INSTRUCTION = (
    "Based on the work done in this conversation, generate an episode "
    "from the MMORPG called The Dreamscape. Don't mention actual tasks, code, or implementation steps. "
    "Transform this into stylized narrative lore only. Keep it immersive."
)


async def main():
    # config = AppConfig.load_from_env() # Assuming AppConfig has load_from_env or similar
    # Let's use the standard load method for now
    config = AppConfig.load()

    print("🌌 Launching browser and logging into ChatGPT...")
    # Ensure ChatGPTScraper exists and takes config
    # Need to confirm ChatGPTScraper implementation details
    try:
        async with ChatGPTScraper(
            config=config
        ) as scraper:  # Assuming context manager usage
            print(
                "📜 Navigating to current session and scrolling through full conversation..."
            )
            # Check if these methods exist on scraper
            await scraper.load_latest_conversation()
            await scraper.scroll_to_bottom()

            print("🧠 Injecting Dreamscape transformation prompt...")
            await scraper.send_message_and_wait(DREAMSCAPE_INSTRUCTION)

            print("📥 Capturing ChatGPT's narrative response...")
            story = await scraper.extract_latest_reply()

            print("\n🎮 Dreamscape Episode:\n")
            print(story)

    except ImportError:
        print(
            "ERROR: Failed to import ChatGPTScraper. Is it implemented at src/dreamos/services/utils/chatgpt_scraper.py?"
        )
    except AttributeError as e:
        print(f"ERROR: ChatGPTScraper might be missing a required method: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    # Basic logging setup for the script itself
    import logging

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    asyncio.run(main())
