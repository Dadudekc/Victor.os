# tools/generate_chatgpt_cookies.py
from dreamos.core.config import AppConfig
from dreamos.services.utils.chatgpt_scraper import ChatGPTScraper


def main():
    config = AppConfig()
    scraper = ChatGPTScraper(config=config, headless=False)

    with scraper:
        print("🚀 Browser launched. Please log in manually to https://chat.openai.com")
        input("⚠️ After logging in, press Enter to save cookies...")
        scraper.save_cookies()
        print("✅ Cookies saved to:", config.paths.runtime / "chatgpt_cookies.json")


if __name__ == "__main__":
    main()
