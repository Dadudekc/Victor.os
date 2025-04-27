"""
Headless login helpers for ChatGPT & DeepSeek.

▶ Usage
from dreamos.login_utils import ensure_login
await ensure_login(page, service="chatgpt")   # or "deepseek"
"""

import asyncio, os, logging
from typing import Literal
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from config/.env file
dotenv_path = Path(__file__).resolve().parents[1] / "config" / ".env"
load_dotenv(dotenv_path=dotenv_path)

# Attempt to import Playwright, handle gracefully if not installed
try:
    from playwright.async_api import Page, TimeoutError as PlaywrightTimeout
    _playwright_available = True
except ImportError:
    Page = None # Define dummy for type hinting
    PlaywrightTimeout = None # Define dummy
    _playwright_available = False

log = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
#                           high‑level entry point                             #
# --------------------------------------------------------------------------- #

async def ensure_login(page: Page, service: Literal["chatgpt", "deepseek"]) -> None:
    """
    If `page` is already in a logged‑in state, returns immediately.
    Otherwise performs full e‑mail / password flow.

    Credentials are pulled from env‑vars:
        CHATGPT_EMAIL / CHATGPT_PASSWORD
        DEEPSEEK_EMAIL / DEEPSEEK_PASSWORD
    """
    if not _playwright_available:
        log.error("Playwright is not installed. Cannot perform login.")
        raise ImportError("Playwright library not found. Please install it.")
    if not page:
        log.error("Playwright Page object is None. Cannot perform login.")
        raise ValueError("Invalid Page object provided to ensure_login.")

    try:
        match service:
            case "chatgpt":
                if await _is_chatgpt_logged_in(page):
                    log.info("ChatGPT already logged in.")
                    return
                await _login_chatgpt(
                    page,
                    os.getenv("CHATGPT_EMAIL"),
                    os.getenv("CHATGPT_PASSWORD"),
                )
            case "deepseek":
                if await _is_deepseek_logged_in(page):
                    log.info("DeepSeek already logged in.")
                    return
                await _login_deepseek(
                    page,
                    os.getenv("DEEPSEEK_EMAIL"),
                    os.getenv("DEEPSEEK_PASSWORD"),
                )
            case _:
                raise ValueError(f"Unknown service: {service}")
    except PlaywrightTimeout as e:
        log.error(f"Login flow for {service} failed due to Playwright timeout: {e}")
        # Consider capturing screenshot or page source here for debugging
        # filename = f"{service}_login_timeout_error.png"
        # try:
        #     await page.screenshot(path=filename)
        #     log.info(f"Screenshot saved to {filename}")
        # except Exception as sc_e:
        #     log.error(f"Failed to save screenshot: {sc_e}")
        raise RuntimeError(f"{service} login failed – check credentials, captcha, or selector changes.") from e
    except Exception as e:
        log.exception(f"An unexpected error occurred during {service} login flow: {e}")
        raise RuntimeError(f"{service} login failed unexpectedly: {e}") from e

# --------------------------------------------------------------------------- #
#                       ChatGPT (chat.openai.com) login                        #
# --------------------------------------------------------------------------- #

CHAT_URL = "https://chat.openai.com/"

async def _is_chatgpt_logged_in(page: Page) -> bool:
    try:
        # Check for composer or main textarea
        await page.wait_for_selector("textarea, div[data-testid='composer']", timeout=3_000, state='visible')
        log.debug("ChatGPT composer/textarea found, assuming logged in.")
        return True
    except PlaywrightTimeout:
        log.debug("ChatGPT composer/textarea not found quickly, assuming logged out.")
        return False
    except Exception as e:
        log.warning(f"Error checking ChatGPT login status: {e}")
        return False # Assume not logged in if error occurs

async def _login_chatgpt(page: Page, email: str | None, password: str | None):
    if not email or not password:
        raise ValueError("CHATGPT_EMAIL / CHATGPT_PASSWORD env vars not set or empty")

    log.info("🔑 ChatGPT login flow starting (Robust v2)")
    await page.goto(CHAT_URL, timeout=30_000, wait_until='domcontentloaded')

    # ---------- screen 1: splash -------------------------------------------
    log.debug("Looking for initial 'Log in' button (Try Role, TestID, CSS)")
    clicked_login = False
    try:
        # Try ARIA role first
        await page.get_by_role("button", name="Log in", exact=True).click(timeout=6_000)
        log.info("Clicked 'Log in' button (Role)")
        clicked_login = True
    except PlaywrightTimeout:
        log.warning("Role 'Log in' button timed out, trying data-testid.")
        try:
            # Try data-testid (common in React apps)
            await page.locator("button[data-testid='login-button']").click(timeout=6_000) # Adjust testid if known
            log.info("Clicked 'Log in' button (data-testid)")
            clicked_login = True
        except PlaywrightTimeout:
            log.warning("data-testid 'Log in' button timed out, trying CSS fallback.")
            try:
                # Try CSS fallback
                await page.click("button:has-text('Log in')", timeout=8_000)
                log.info("Clicked 'Log in' button (CSS Fallback)")
                clicked_login = True
            except PlaywrightTimeout as e_css:
                log.error(f"All attempts to find 'Log in' button failed: {e_css}")
                if await _is_chatgpt_logged_in(page):
                    log.warning("Already logged in after failing to find login button. Proceeding.")
                    # Skip to end if already logged in
                    return
                raise RuntimeError("Could not find or click the initial 'Log in' button.") from e_css

    # Re-check if login occurred unexpectedly
    if await _is_chatgpt_logged_in(page):
        log.info("✅ Logged in state detected after clicking Login button. Success.")
        return

    # ---------- screen 2: email --------------------------------------------
    log.debug("Looking for email input (Try Placeholder, Name, Type)")
    email_filled = False
    try:
        await page.get_by_placeholder("Email address", exact=True).fill(email, timeout=10_000)
        email_filled = True
    except PlaywrightTimeout:
        log.warning("Email placeholder not found, trying name=username.")
        try:
            await page.locator("input[name='username']").fill(email, timeout=5_000)
            email_filled = True
        except PlaywrightTimeout:
            log.warning("Email name=username not found, trying type=email.")
            try:
                await page.locator("input[type='email']").fill(email, timeout=5_000)
                email_filled = True
            except PlaywrightTimeout as e_email:
                 log.error(f"Could not find email input field: {e_email}")
                 raise RuntimeError("Failed to find email input field.") from e_email

    log.debug("Filled email input. Looking for Continue button (Role, CSS)")
    try:
        await page.get_by_role("button", name="Continue").click(timeout=6_000)
    except PlaywrightTimeout:
        log.warning("Role Continue button timed out, trying CSS.")
        try:
            await page.locator("button[type='submit']:has-text('Continue')").click(timeout=6_000)
        except PlaywrightTimeout as e_cont1:
            log.error(f"Could not find first Continue button: {e_cont1}")
            raise RuntimeError("Failed to click first Continue button.") from e_cont1
    log.info("Submitted email.")

    if await _is_chatgpt_logged_in(page):
        log.info("✅ Logged in state detected after submitting email. Success.")
        return

    # ---------- screen 3: password -----------------------------------------
    log.debug("Looking for password input (Try Label, Placeholder, Type)")
    password_filled = False
    try:
        await page.get_by_label("Password").fill(password, timeout=10_000)
        password_filled = True
    except PlaywrightTimeout:
        log.warning("Password label not found, trying placeholder.")
        try:
            await page.get_by_placeholder("Password", exact=True).fill(password, timeout=5_000)
            password_filled = True
        except PlaywrightTimeout:
             log.warning("Password placeholder not found, trying type=password.")
             try:
                 await page.locator("input[type='password']").fill(password, timeout=5_000)
                 password_filled = True
             except PlaywrightTimeout as e_pass:
                 log.error(f"Could not find password input field: {e_pass}")
                 raise RuntimeError("Failed to find password input field.") from e_pass

    log.debug("Filled password input. Looking for final Continue button (Role, CSS)")
    try:
        # Often the same button as before
        await page.get_by_role("button", name="Continue").click(timeout=6_000)
    except PlaywrightTimeout:
         log.warning("Role Continue button timed out, trying CSS.")
         try:
            await page.locator("button[type='submit']:has-text('Continue')").click(timeout=6_000)
         except PlaywrightTimeout as e_cont2:
            log.error(f"Could not find second Continue button: {e_cont2}")
            raise RuntimeError("Failed to click second Continue button.") from e_cont2
    log.info("Submitted password.")

    # ---------- confirm we're in -------------------------------------------
    log.debug("Waiting for final confirmation selector (composer/textarea)")
    await page.wait_for_selector("textarea, div[data-testid='composer']", timeout=20_000, state='visible')
    log.info("✅ ChatGPT login success confirmed by presence of composer/textarea.")

# --------------------------------------------------------------------------- #
#                         DeepSeek (deepseek.com) login                       #
# --------------------------------------------------------------------------- #

DEEP_URL  = "https://chat.deepseek.com/"

async def _is_deepseek_logged_in(page: Page) -> bool:
    try:
        await page.wait_for_selector("textarea", timeout=3_000, state='visible')
        log.debug("DeepSeek main textarea found, assuming logged in.")
        return True
    except PlaywrightTimeout:
        log.debug("DeepSeek main textarea not found quickly, assuming logged out.")
        return False
    except Exception as e:
        log.warning(f"Error checking DeepSeek login status: {e}")
        return False

async def _login_deepseek(page: Page, email: str | None, password: str | None):
    if not email or not password:
        raise ValueError("DEEPSEEK_EMAIL / DEEPSEEK_PASSWORD env vars not set or empty")

    log.info("🔑 DeepSeek login flow starting")
    await page.goto(DEEP_URL, timeout=30_000, wait_until='domcontentloaded')

    # ---------- screen 1: splash (optional) --------------------------------
    log.debug("Looking for initial 'Log in' button (Role) - Optional for DeepSeek")
    try:
        # Use a shorter timeout as this screen might not appear
        await page.get_by_role("button", name="Log in", exact=True).click(timeout=5_000)
        log.info("Clicked initial 'Log in' button (Role)")
    except PlaywrightTimeout:
        log.info("Initial 'Log in' button not found or timed out (might be normal for DeepSeek). Proceeding.")
        pass  # sometimes DeepSeek jumps directly to email

    # Check if already logged in after optional splash click
    if await _is_deepseek_logged_in(page):
        log.info("✅ Logged in state detected early. Success.")
        return

    # ---------- screen 2: email --------------------------------------------
    log.debug("Looking for email textbox (Role)")
    # Assuming the textbox might not have a specific accessible name
    await page.get_by_role("textbox").first.fill(email, timeout=10_000)
    log.debug("Filled email textbox. Looking for Continue button (Role)")
    await page.get_by_role("button", name="Continue").click(timeout=6_000)
    log.info("Submitted email.")

    if await _is_deepseek_logged_in(page):
        log.info("✅ Logged in state detected after submitting email. Success.")
        return

    # ---------- screen 3: password -----------------------------------------
    log.debug("Looking for password label/textbox (Label)")
    # If 'Password' label doesn't work, inspect element for aria-label or use CSS
    await page.get_by_label("Password").fill(password, timeout=10_000)
    log.debug("Filled password textbox. Looking for Continue button (Role)")
    await page.get_by_role("button", name="Continue").click(timeout=6_000)
    log.info("Submitted password.")

    # ---------- confirm we're in -------------------------------------------
    log.debug("Waiting for final confirmation selector (textarea)")
    await page.wait_for_selector("textarea", timeout=20_000, state='visible')
    log.info("✅ DeepSeek login success confirmed by presence of textarea.")

# --------------------------------------------------------------------------- #
#                      helper: type + click utility                           #
# --------------------------------------------------------------------------- #

async def _type_and_click(page: Page, input_sel: str, value: str, btn_sel: str, input_desc: str = "Input", button_desc: str = "Button"):
    log.debug(f"(Helper) Attempting to fill {input_desc} ('{input_sel}')")
    await page.wait_for_selector(input_sel, timeout=10_000, state='visible')
    await page.fill(input_sel, value, timeout=5_000)
    log.debug(f"(Helper) Filled {input_desc}. Pausing briefly.")
    await asyncio.sleep(0.5)
    log.debug(f"(Helper) Attempting to click {button_desc} ('{btn_sel}')")
    await page.click(btn_sel, timeout=5_000)
    log.debug(f"(Helper) Clicked {button_desc}.") 
