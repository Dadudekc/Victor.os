# login_utils.py
import logging, os
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

log = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
#  Universal login dispatcher
# ------------------------------------------------------------------------------

def ensure_login(page: Page, service: str = "chatgpt"):
    """Detects if already logged in. If not, calls the right login helper."""
    if service == "chatgpt":
        if _is_logged_in_chatgpt(page):
            log.info("✅ Already authenticated on ChatGPT – skipping login")
            return
        return _login_chatgpt(page)
    elif service == "deepseek":
        if _is_logged_in_deepseek(page):
            log.info("✅ Already authenticated on DeepSeek – skipping login")
            return
        return _login_deepseek(page)
    else:
        raise ValueError(f"Unknown login service: {service}")

# ------------------------------------------------------------------------------
#  ChatGPT
# ------------------------------------------------------------------------------

def _is_logged_in_chatgpt(page: Page) -> bool:
    try:
        page.goto("https://chat.openai.com", timeout=30_000)
        page.wait_for_selector("textarea", timeout=8_000)
        return True
    except PlaywrightTimeout:
        return False

def _login_chatgpt(page: Page):
    log.info("🔑 Logging in to ChatGPT...")

    email = os.getenv("CHATGPT_EMAIL")
    password = os.getenv("CHATGPT_PASSWORD")
    if not email or not password:
        raise ValueError("CHATGPT_EMAIL or CHATGPT_PASSWORD not set in env")

    page.goto("https://chat.openai.com", timeout=30_000)

    try:
        # Splash screen
        page.get_by_role("button", name="Log in", exact=True).click(timeout=6_000)
    except PlaywrightTimeout:
        pass  # might already be at email screen

    # Email
    email_selector = "input#username"
    log.info(f"Waiting for email input: {email_selector}")
    page.wait_for_selector(email_selector, state="visible", timeout=30000)
    log.info(f"Filling email input: {email_selector}")
    page.locator(email_selector).fill(email)
    page.get_by_role("button", name="Continue").click(timeout=8_000)

    # Password
    password_selector = "input#password"
    log.info(f"Waiting for password input: {password_selector}")
    page.wait_for_selector(password_selector, state="visible", timeout=30000)
    log.info(f"Filling password input: {password_selector}")
    page.locator(password_selector).fill(password)
    page.get_by_role("button", name="Continue").click(timeout=8_000)

    # Wait for main UI element after login
    final_selector = "textarea#prompt-textarea"
    log.info(f"Waiting for final UI element after login: {final_selector}")
    page.wait_for_selector(final_selector, timeout=40_000)
    log.info("✅ ChatGPT login complete")

# ------------------------------------------------------------------------------
#  DeepSeek
# ------------------------------------------------------------------------------

def _is_logged_in_deepseek(page: Page) -> bool:
    try:
        page.goto("https://chat.deepseek.com", timeout=30_000)
        page.wait_for_selector("textarea", timeout=8_000)
        return True
    except PlaywrightTimeout:
        return False

def _login_deepseek(page: Page):
    log.info("🔑 Logging in to DeepSeek...")

    email = os.getenv("DEEPSEEK_EMAIL")
    password = os.getenv("DEEPSEEK_PASSWORD")
    if not email or not password:
        raise ValueError("DEEPSEEK_EMAIL or DEEPSEEK_PASSWORD not set in env")

    page.goto("https://chat.deepseek.com", timeout=30_000)

    try:
        page.get_by_role("button", name="Log in", exact=True).click(timeout=6_000)
    except PlaywrightTimeout:
        pass  # may be already on email screen

    page.get_by_role("textbox").fill(email)
    page.get_by_role("button", name="Continue").click(timeout=8_000)

    page.get_by_label("Password").fill(password)
    page.get_by_role("button", name="Continue").click(timeout=8_000)

    page.wait_for_selector("textarea", timeout=20_000)
    log.info("✅ DeepSeek login complete") 