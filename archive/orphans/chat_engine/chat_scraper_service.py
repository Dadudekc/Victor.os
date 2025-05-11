# chat_scraper_service.py

import logging
import time

logger = logging.getLogger("ChatScraper")


class ChatScraperService:
    """
    ChatScraperService retrieves available chat titles and links from the chat UI.
    It handles exclusions and filtering for downstream execution cycles.
    """

    def __init__(self, driver_manager, exclusions=None, reverse_order=False):
        self.driver_manager = driver_manager
        self.driver = self.driver_manager.driver
        self.exclusions = exclusions if exclusions else []
        self.reverse_order = reverse_order

    def get_all_chats(self) -> list:
        """
        Retrieves all chat titles, links, and additional metadata available in the sidebar.
        Returns a list of dictionaries with 'title', 'link', 'last_active_time', and 'snippet'.
        Metadata fields will be None if not found.
        """
        logger.info("🔎 Scraping all chats from sidebar with extended metadata...")
        try:
            time.sleep(2)  # Give time for elements to load
            # Assuming each chat item is within a distinct container element.
            # This XPath needs to be adjusted based on the actual page structure.
            # For now, we'll still iterate over link elements and try to find metadata relative to them.
            chat_link_elements = self.driver.find_elements(
                "xpath", "//a[contains(@class, 'group') and contains(@href, '/c/')]"
            )

            if not chat_link_elements:
                logger.warning("⚠️ No chats found in the sidebar.")
                return []

            chats = []
            for link_el in chat_link_elements:
                title = link_el.text.strip() or "Untitled"
                link = link_el.get_attribute("href")
                last_active_time = None
                snippet = None

                if not link:
                    logger.warning(f"⚠️ Chat '{title}' has no link, skipping.")
                    continue

                # Attempt to find metadata - THESE ARE HYPOTHETICAL SELECTORS
                # Assumes metadata elements are siblings or children of a common parent of the link.
                # This part is highly dependent on the actual DOM structure.
                try:
                    # Example: Try to find a timestamp if it's a sibling div to the link's parent
                    # Or, if the link_el is inside a larger div for the chat item:
                    parent_item_el = link_el.find_element(
                        "xpath",
                        "./ancestor::div[contains(@class, 'chat-item-container') or contains(@class, 'relative')][1]",
                    )  # Common pattern for item containers

                    # --- Try multiple selectors for timestamp ---
                    timestamp_selectors = [
                        ".//span[contains(@class, 'time') or contains(@class, 'timestamp') or contains(@class, 'date') or contains(@data-testid, 'time') or contains(@data-testid, 'timestamp') or contains(@data-testid, 'date')]",  # Common classes/testids
                        ".//div[contains(@class, 'time') or contains(@class, 'timestamp') or contains(@class, 'date') or contains(@data-testid, 'time') or contains(@data-testid, 'timestamp') or contains(@data-testid, 'date')][not(self::a)]",  # Also check divs, exclude links
                    ]
                    for idx, selector in enumerate(timestamp_selectors):
                        try:
                            time_el = parent_item_el.find_element("xpath", selector)
                            text = time_el.text.strip()
                            if text:  # Ensure element found and has text
                                last_active_time = text
                                logger.debug(
                                    f"Found last_active_time for '{title}' using selector #{idx+1}: {selector}"
                                )
                                break  # Stop after first success
                        except Exception:
                            continue  # Try next selector
                    if not last_active_time:
                        logger.debug(
                            f"Could not find last_active_time for chat '{title}' using any defined selectors."
                        )

                    # --- Try multiple selectors for snippet ---
                    snippet_selectors = [
                        ".//div[contains(@class, 'snippet') or contains(@class, 'preview') or contains(@class, 'summary') or contains(@data-testid, 'snippet') or contains(@data-testid, 'preview') or contains(@data-testid, 'summary')]",  # Common classes/testids
                        ".//span[contains(@class, 'snippet') or contains(@class, 'preview') or contains(@class, 'summary') or contains(@data-testid, 'snippet') or contains(@data-testid, 'preview') or contains(@data-testid, 'summary')]",  # Also check spans
                    ]
                    for idx, selector in enumerate(snippet_selectors):
                        try:
                            snippet_el = parent_item_el.find_element("xpath", selector)
                            text = snippet_el.text.strip()
                            if text:  # Ensure element found and has text
                                snippet = text
                                logger.debug(
                                    f"Found snippet for '{title}' using selector #{idx+1}: {selector}"
                                )
                                break  # Stop after first success
                        except Exception:
                            continue  # Try next selector
                    if not snippet:
                        logger.debug(
                            f"Could not find snippet for chat '{title}' using any defined selectors."
                        )

                except Exception:
                    logger.debug(
                        f"Could not find common parent 'chat-item-container' for chat '{title}' to search for metadata."
                    )

                chats.append(
                    {
                        "title": title,
                        "link": link,
                        "last_active_time": last_active_time,
                        "snippet": snippet,
                    }
                )

            logger.info(
                f"✅ Retrieved {len(chats)} chats from sidebar with attempted metadata."
            )
            return chats

        except Exception as e:
            logger.error(f"❌ Error while scraping chats with metadata: {e}")
            return []

    def get_filtered_chats(self) -> list:
        """
        Filters out chats listed in self.exclusions.
        Can reverse order if self.reverse_order is True.
        """
        all_chats = self.get_all_chats()
        logger.info(f"🔍 Filtering {len(all_chats)} chats...")

        filtered = [chat for chat in all_chats if chat["title"] not in self.exclusions]

        logger.info(f"✅ {len(filtered)} chats after exclusion filter.")

        if self.reverse_order:
            filtered.reverse()
            logger.info("🔄 Reversed chat order as requested.")

        return filtered

    def validate_login(self) -> bool:
        """
        Checks if the user is logged in based on the presence of sidebar elements.
        """
        logger.info("🔐 Validating OpenAI chat login status...")
        try:
            sidebar = self.driver.find_element(
                "xpath", "//nav[contains(@class, 'flex h-full')]"
            )
            if sidebar:
                logger.info("✅ User is logged in.")
                return True
        except Exception:
            logger.warning("⚠️ User is NOT logged in or sidebar is missing.")
        return False

    def manual_login_flow(self):
        """
        Prompts the user to manually log in via the browser.
        """
        logger.info("🛂 Manual login flow initiated. Waiting for user login...")
        self.driver.get("https://chat.openai.com/auth/login")

        while not self.validate_login():
            time.sleep(5)
            logger.info("🔄 Waiting for login...")

        logger.info("✅ Login detected! Proceeding with chat scraping.")
