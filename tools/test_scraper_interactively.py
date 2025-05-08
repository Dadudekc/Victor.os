from dreamos.core.config import AppConfig
from dreamos.services.utils.chatgpt_scraper import ChatGPTScraper

TARGET_URL = "https://chat.openai.com/chat"  # Or your custom GPT URL if needed


def main():
    config = AppConfig()
    scraper = ChatGPTScraper(config=config, headless=False)

    with scraper:
        scraper.navigate(TARGET_URL)
        input(
            "🟢 Browser ready. Is ChatGPT fully loaded? Press Enter to attempt prompt injection..."
        )

        prompt = "Say: Bridge test complete."
        print("⚙️ Sending prompt:", prompt)
        scraper.send_message_and_wait(prompt)

        input("⏳ Waiting for reply to render. Press Enter to extract...")
        reply = scraper.extract_latest_reply()
        print("✅ Extracted reply:", reply)

        input("Press Enter to close browser...")


if __name__ == "__main__":
    main()
