"""Client abstracting browser automation (e.g., Playwright)."""

import asyncio  # noqa: I001
import logging

from playwright.async_api import Page, async_playwright

from dreamos.core.config import get_config
from ..core.errors import DreamOSError


# Define Integration/API/Browser errors locally
class IntegrationError(DreamOSError):
    """Base error for integration issues."""

    pass


class APIError(IntegrationError):
    """Error related to external API interaction."""

    pass


class BrowserClientError(IntegrationError):
    """Specific error for Browser Client operations."""

    pass


logger = logging.getLogger(__name__)

# TODO: Add 'playwright' to project dependencies (e.g., requirements.txt or pyproject.toml)  # noqa: E501
# TODO: Run 'playwright install' in the terminal to install browser binaries


class BrowserClient:
    """Asynchronous client for browser automation using Playwright."""

    def __init__(self):
        """Initializes the Playwright client, loading config via get_config."""
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._functional = False
        self.browser_type = "chrome"  # Default
        self.headless = True  # Default

        try:
            config = get_config()
            # Assuming path like: config.integrations.playwright.browser_type
            self.browser_type = (
                config.integrations.playwright.browser_type.lower()
                if hasattr(config.integrations, "playwright")
                else "chrome"
            )
            self.headless = (
                config.integrations.playwright.headless
                if hasattr(config.integrations, "playwright")
                else True
            )

            if self.browser_type not in ["chromium", "firefox", "webkit"]:
                logger.error(
                    f"Unsupported browser type in config: '{self.browser_type}'. Use 'chromium', 'firefox', or 'webkit'. Defaulting to chromium."
                )
                self.browser_type = "chromium"
                # Or raise ConfigurationError here

            self._functional = (
                True  # Mark as potentially functional, connect() does the real work
            )
            logger.info(
                f"BrowserClient configured (Type: {self.browser_type}, Headless: {self.headless})"
            )
        except Exception as e:
            logger.error(
                f"Failed to configure BrowserClient using get_config: {e}",
                exc_info=True,
            )
            # Keep defaults
            self._functional = False  # Cannot be functional if config load fails

    async def connect(self):
        """Connects to Playwright and launches the browser."""
        if self._functional:
            logger.info("BrowserClient already connected.")
            return

        logger.info(f"Connecting to Playwright and launching {self.browser_type}...")
        try:
            self._playwright = await async_playwright().start()
            browser_launcher = getattr(self._playwright, self.browser_type, None)
            if browser_launcher is None:
                raise IntegrationError(
                    f"Unsupported browser type configured: {self.browser_type}"
                )

            self._browser = await browser_launcher.launch(headless=self.headless)
            self._functional = True
            logger.info(f"BrowserClient connected successfully to {self.browser_type}.")
        except Exception as e:
            logger.error(f"Failed to connect or launch browser: {e}", exc_info=True)
            self._functional = False
            await self.close()  # Attempt cleanup
            raise IntegrationError(f"Failed to initialize browser client: {e}") from e

    async def close(self):
        """Closes the browser and disconnects from Playwright."""
        logger.info("Closing browser client connection...")
        if self._browser:
            try:
                await self._browser.close()
                logger.debug("Playwright browser closed.")
            except Exception as e:
                logger.error(f"Error closing Playwright browser: {e}", exc_info=True)
            self._browser = None
        if self._playwright:
            try:
                await self._playwright.stop()
                logger.debug("Playwright context stopped.")
            except Exception as e:
                logger.error(f"Error stopping Playwright: {e}", exc_info=True)
            self._playwright = None
        self._functional = False
        logger.info("Browser client connection closed.")

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    def is_functional(self) -> bool:
        """Returns True if the browser driver is initialized and functional."""
        return self._functional and self._browser is not None

    async def _get_new_page(self) -> Page:
        """Helper to get a new browser page."""
        if not self.is_functional() or self._browser is None:
            raise IntegrationError("Browser client is not connected or functional.")
        try:
            # Consider context options (viewport, user agent etc.) if needed
            context = await self._browser.new_context()
            page = await context.new_page()
            return page
        except Exception as e:
            logger.error(f"Failed to create new browser page: {e}", exc_info=True)
            raise IntegrationError(f"Failed to create browser page: {e}") from e

    async def get_page_dom(self, url: str) -> str:
        """Navigates to a URL and returns the page DOM/source."""
        logger.info(f"Attempting to get DOM for URL: {url}")
        page = await self._get_new_page()
        try:
            response = await page.goto(
                url, wait_until="domcontentloaded", timeout=30000
            )  # 30s timeout
            if response is None or not response.ok:
                status = response.status if response else "N/A"
                error_msg = (
                    f"Failed to load page {url}. Server responded with status: {status}"
                )
                logger.error(error_msg)
                raise APIError(error_msg)

            content = await page.content()
            logger.info(
                f"Successfully retrieved DOM for {url} (length: {len(content)} chars)"
            )
            return content
        except playwright.async_api.Error as pe:  # noqa: F821
            logger.error(f"Playwright error getting DOM for {url}: {pe}", exc_info=True)
            raise APIError(f"Playwright error getting DOM for {url}: {pe}") from pe
        except asyncio.TimeoutError as te:
            logger.error(f"Timeout error getting DOM for {url}: {te}", exc_info=True)
            raise APIError(f"Timeout getting DOM for {url}") from te
        except Exception as e:
            logger.error(f"Unexpected error getting DOM for {url}: {e}", exc_info=True)
            raise APIError(f"Failed to get DOM for {url}: {e}") from e
        finally:
            if page and not page.is_closed():
                await page.context.close()  # Close context which closes the page
                logger.debug(f"Closed browser page/context used for {url}")

    async def perform_action(self, url: str, action_details: dict):
        """Opens a URL and performs a browser action (e.g., click, type).

        Args:
            url: The URL to navigate to first.
            action_details: Dict defining the action.
                            Example: {'action': 'click', 'selector': '#myButton'}
                                     {'action': 'type', 'selector': 'input[name=q]', 'text': 'Search term'}
                                     {'action': 'get_text', 'selector': '.content'}
        Returns:
            Any result from the action (e.g., text content for 'get_text'), or None.
        """  # noqa: E501
        logger.info(
            f"Performing action {action_details.get('action')} on {url} with selector {action_details.get('selector')}"  # noqa: E501
        )
        page = await self._get_new_page()
        try:
            response = await page.goto(
                url, wait_until="domcontentloaded", timeout=30000
            )
            if response is None or not response.ok:
                status = response.status if response else "N/A"
                error_msg = f"Failed to load page {url} before action. Server responded with status: {status}"  # noqa: E501
                logger.error(error_msg)
                raise APIError(error_msg)

            action = action_details.get("action")
            selector = action_details.get("selector")
            text_to_type = action_details.get("text")
            attribute_name = action_details.get("attribute")
            timeout_ms = action_details.get(
                "timeout", 10000
            )  # Default 10s action timeout
            path_to_save = action_details.get("path")  # For screenshot

            if not action:
                raise ValueError("Action details must include 'action'.")
            # Selector not needed for all actions (e.g., page screenshot)
            # if not selector and action not in ['screenshot_page']:
            #     raise ValueError(f"Action '{action}' requires a 'selector'.")

            result = None
            locator = page.locator(selector) if selector else None

            # --- Action Implementations ---
            if action == "click":
                if not locator:
                    raise ValueError("Action 'click' requires a 'selector'.")
                await locator.click(timeout=timeout_ms)
                logger.info(f"Clicked element with selector: {selector}")
            elif action == "type":
                if not locator:
                    raise ValueError("Action 'type' requires a 'selector'.")
                if text_to_type is None:
                    raise ValueError("Action 'type' requires 'text' in action_details.")
                await locator.fill(text_to_type, timeout=timeout_ms)
                logger.info(f"Typed text into element with selector: {selector}")
            elif action == "get_text":
                if not locator:
                    raise ValueError("Action 'get_text' requires a 'selector'.")
                result = await locator.text_content(timeout=timeout_ms)
                logger.info(
                    f"Retrieved text from element {selector}: '{result[:50]}...'"
                    if result
                    else "Retrieved empty text."
                )
            elif action == "get_attribute":
                if not locator:
                    raise ValueError("Action 'get_attribute' requires a 'selector'.")
                if not attribute_name:
                    raise ValueError(
                        "Action 'get_attribute' requires 'attribute' in action_details."
                    )
                result = await locator.get_attribute(attribute_name, timeout=timeout_ms)
                logger.info(
                    f"Retrieved attribute '{attribute_name}' from element {selector}: '{result}'"  # noqa: E501
                )
            elif action == "wait_for_selector":
                if not selector:
                    raise ValueError(
                        "Action 'wait_for_selector' requires a 'selector'."
                    )
                # Use page.wait_for_selector as locator might not exist yet
                await page.wait_for_selector(
                    selector, state="visible", timeout=timeout_ms
                )
                logger.info(f"Waited for selector '{selector}' to become visible.")
            elif action == "screenshot":
                if not path_to_save:
                    raise ValueError(
                        "Action 'screenshot' requires 'path' in action_details."
                    )
                screenshot_kwargs = {"path": path_to_save, "timeout": timeout_ms}
                if locator:  # Screenshot specific element
                    await locator.screenshot(**screenshot_kwargs)
                    logger.info(
                        f"Saved screenshot of element {selector} to {path_to_save}"
                    )
                else:  # Screenshot full page
                    await page.screenshot(**screenshot_kwargs)
                    logger.info(f"Saved screenshot of full page to {path_to_save}")
            else:
                raise ValueError(f"Unsupported browser action: {action}")

            return result

        except playwright.async_api.Error as pe:  # noqa: F821
            logger.error(
                f"Playwright error performing action {action_details.get('action')} on {url}: {pe}",  # noqa: E501
                exc_info=True,
            )
            raise APIError(
                f"Playwright error performing action '{action_details.get('action')}': {pe}"  # noqa: E501
            ) from pe
        except asyncio.TimeoutError as te:
            logger.error(
                f"Timeout error performing action {action_details.get('action')} on {url}: {te}",  # noqa: E501
                exc_info=True,
            )
            raise APIError(
                f"Timeout performing action '{action_details.get('action')}'"
            ) from te
        except Exception as e:
            logger.error(
                f"Unexpected error performing action {action_details} on {url}: {e}",
                exc_info=True,
            )
            raise APIError(
                f"Failed to perform action {action_details.get('action')} on {url}: {e}"
            ) from e
        finally:
            if page and not page.is_closed():
                await page.context.close()
                logger.debug(f"Closed browser page/context used for action on {url}")


# Removed redundant asyncio import at the end
