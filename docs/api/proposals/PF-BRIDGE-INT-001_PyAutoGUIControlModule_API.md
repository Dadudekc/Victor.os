# API Proposal: PyAutoGUIControlModule

**Task ID**: `PF-BRIDGE-INT-001`
**Agent**: `agent-1` (Pathfinder)
**Date**: {{TODAY_YYYY-MM-DD}} # Updated Date
**Related Document**: `ai_docs/architecture/PF-BRIDGE-INT-001_PyAutoGUI_Component_Map.md`

## 1. Introduction

The `PyAutoGUIControlModule` is designed to be a foundational component used by a more specialized service that orchestrates the actual scraping or interaction logic with the target application (e.g., ChatGPT via a browser).

Let's consider a hypothetical `ChatGPTScraperService` that wants to submit a prompt and retrieve a response:

```python
# Example: Hypothetical ChatGPTScraperService (Illustrative)
import asyncio
import logging
from dreamos.core.config import AppConfig
from dreamos.skills.pyautogui_control_module import PyAutoGUIControlModule, ImageNotFoundError, WindowNotFoundError, PyAutoGUIControlError
# from dreamos.services.browser_automation_service import BrowserAutomationService # If using hybrid approach

class ChatGPTScraperService:
    def __init__(self, config: AppConfig, control_module: PyAutoGUIControlModule):
        self.app_config = config
        self.logger = logging.getLogger(__name__)
        self.gui_control = control_module
        # self.browser_control = BrowserAutomationService(config) # If hybrid
        self.target_app_title_pattern = "ChatGPT - My Browser Profile" # Example, should be configurable

    async def submit_prompt_and_get_response(self, prompt: str) -> Optional[str]:
        """
        Orchestrates the sequence to submit a prompt to ChatGPT and retrieve its response.
        This is a simplified example.
        """
        try:
            # Ensure target application (e.g., browser with ChatGPT) is ready
            # This might involve launching the browser, navigating to the URL, and logging in,
            # potentially handled by a dedicated browser automation module or setup script.
            # For this example, assume PyAutoGUIControlModule is configured for the correct window.
            
            self.logger.info(f"Ensuring '{self.target_app_title_pattern}' is focused for prompt submission.")
            await self.gui_control.ensure_window_focused() # Module uses its own target pattern

            # Use the high-level find_type_and_enter
            # Image paths would come from AppConfig or be constants known to this service
            prompt_field_image = self.app_config.pyautogui_bridge.get('image_chatgpt_prompt_field', 'chatgpt_prompt_input_field_active.png')
            send_button_image = self.app_config.pyautogui_bridge.get('image_chatgpt_send_button', 'chatgpt_send_button_enabled.png') # Used as readiness cue
            
            self.logger.info(f"Submitting prompt to ChatGPT: '{prompt[:50]}...'")
            success = await self.gui_control.find_type_and_enter(
                target_image_to_click=prompt_field_image,
                text_to_type=prompt,
                clear_before_typing=True,
                wait_for_readiness_image=send_button_image, # e.g., wait for send button to re-enable or a spinner to disappear
                readiness_timeout=self.app_config.pyautogui_bridge.get('chatgpt_readiness_timeout', 60.0) # Longer timeout for response generation
            )

            if not success:
                self.logger.error("Failed to submit prompt and wait for readiness via find_type_and_enter.")
                return None

            self.logger.info("Prompt submitted, attempting to retrieve response.")

            # Retrieve response using find_click_select_all_copy
            response_anchor_image = self.app_config.pyautogui_bridge.get('image_chatgpt_response_anchor', 'chatgpt_response_area_anchor.png')
            
            # Small delay for response to fully render even after readiness cue
            await asyncio.sleep(self.app_config.pyautogui_bridge.get('pause_after_response_ready', 2.0))

            response_text = await self.gui_control.find_click_select_all_copy(
                anchor_image_to_click=response_anchor_image,
                # Confidence/timeouts for find/clipboard can use module defaults or be configured
            )

            if response_text:
                self.logger.info(f"Successfully retrieved response (length: {len(response_text)}).")
                return response_text
            else:
                self.logger.error("Failed to retrieve response text after submission.")
                return None

        except WindowNotFoundError:
            self.logger.error(f"Target application window '{self.target_app_title_pattern}' not found or could not be focused.")
            return None
        except ImageNotFoundError as e:
            self.logger.error(f"A required image for ChatGPT interaction was not found: {e}")
            return None
        except PyAutoGUIControlError as e:
            self.logger.error(f"A PyAutoGUI control error occurred during ChatGPT interaction: {e}")
            return None
        except Exception as e: # Catch-all for other unexpected errors
            self.logger.error(f"Unexpected error during ChatGPT interaction: {e}", exc_info=True)
            return None

# Example instantiation (conceptual):
# async def main():
#     config = load_config() # Assume AppConfig is loaded
#     if not config.pyautogui_bridge:
#        print("PyAutoGUI Bridge config not found!")
#        return
# 
#     # PyAutoGUIControlModule needs the AppConfig and the *specific window title pattern* for its target.
#     # This pattern might be derived from a more general ChatGPTScraper config if desired.
#     chatgpt_window_pattern = config.chatgpt_scraper_settings.get("target_window_title", "ChatGPT") 
#     gui_controller = PyAutoGUIControlModule(config=config, target_window_title_pattern=chatgpt_window_pattern)
#     
#     scraper_service = ChatGPTScraperService(config=config, control_module=gui_controller)
#     
#     response = await scraper_service.submit_prompt_and_get_response("Explain quantum entanglement briefly.")
#     if response:
#         print("ChatGPT Response:", response)
#     else:
#         print("Failed to get response.")

# Note on Configuration: The `PyAutoGUIControlModule` itself is initialized with the main `AppConfig`.
# It expects a `PyAutoGUIBridgeConfig` model (defined in `src/dreamos/core/config.py`) 
# to be present under `app_config.pyautogui_bridge` for its specific settings like 
# default timeouts, confidence levels, and image asset paths. The `ChatGPTScraperService` example above
# also shows accessing these settings via `self.app_config.pyautogui_bridge.get(...)` for its own logic.

## 9. Open Questions & Future Considerations

*   **Thread Safety & Asynchronous Usage**:
    *   While PyAutoGUI itself is not thread-safe for concurrent calls to its functions from *multiple Python threads*, the proposed `_run_blocking_io` method using `asyncio.run_in_executor` allows the `PyAutoGUIControlModule`'s `async` methods to be safely called from multiple asyncio tasks. Each blocking PyAutoGUI call is dispatched to a thread pool executor, serializing its execution within that specific call but allowing the asyncio event loop to remain unblocked.
    *   Care must be taken if multiple methods of *this module* are called concurrently if they might internally try to drive `pyautogui` at the exact same microsecond from different threads in the pool. However, typical usage patterns (e.g., `ensure_focus` then `find_element` then `click`) are sequential calls from a single asyncio task context, mitigating this.
    *   Consideration: If truly parallel GUI interactions are ever needed (e.g., controlling two completely separate GUI applications simultaneously), a more complex architecture involving multiple `PyAutoGUIControlModule` instances, potentially with dedicated thread pools or process-based isolation, might be required. For the bridge, sequential interaction with one target application is assumed.

*   **Coordinate vs. Image-Based Targeting Strategy**:
    *   The API supports both: `click_element` can take `coords` or an `image_path`.
    *   **Best Practice**: Strongly prefer image-based targeting (`find_element_on_screen` followed by an action on the found coordinates) for most interactions. This is more resilient to minor UI layout changes, resolution differences, and theme changes.
    *   **Coordinate Use Cases**: Direct coordinate use should be reserved for:
        *   Highly static elements where image recognition is unreliable or slow.
        *   Relative movements (e.g., clicking an offset from a found image anchor).
        *   Situations where the `calibrate_gui_coords.py` workflow is actively maintained for the target application.
    *   The module should log warnings if direct coordinates are used extensively without clear justification, encouraging image-based approaches.

*   **Browser-Specific Automation (Key Consideration for ChatGPTScraper)**:
    *   If the ChatGPTScraper targets a web browser to interact with ChatGPT, `PyAutoGUIControlModule` can handle some interactions but has limitations for complex web scraping:
        *   **Strengths**: Good for clicking buttons, typing in fields, and general window control if the browser window itself is the target.
        *   **Weaknesses**: Cannot easily access the DOM, inspect element properties, handle dynamic web content (AJAX updates, JavaScript rendering) reliably, or extract structured data from HTML.
    *   **Hybrid Approach Recommendation (Expanded)**: For robust browser-based scraping, a hybrid approach is strongly recommended, dividing tasks based on capability:
        *   **1. Dedicated Browser Automation Library (e.g., Selenium, Playwright)**:
            *   **Responsibilities**: 
                *   Launching and managing the browser instance (profiles, extensions, window size).
                *   Navigating to specific URLs.
                *   Interacting with web page elements using DOM-aware selectors (ID, XPath, CSS selectors, text content).
                *   Extracting text content directly from HTML elements.
                *   Executing JavaScript for specific interactions or data retrieval.
                *   Handling cookies, local storage, and session management within the browser.
                *   Waiting for specific DOM elements to be present, visible, or interactive (using the library's built-in explicit wait mechanisms).
                *   Managing iframes and shadow DOMs if necessary.
            *   **Interface**: This library would be wrapped in its own service/module (e.g., `BrowserInteractionService`).
        *   **2. `PyAutoGUIControlModule`**:
            *   **Responsibilities (in a hybrid setup)**:
                *   **OS-Level Window Management**: Ensuring the main browser window (managed by Selenium/Playwright) is focused before the browser automation library attempts interactions, *if* the library itself doesn't robustly handle this or if focus is lost to other OS windows. (`ensure_window_focused`)
                *   **Interacting with Browser Chrome/UI Outside Web Page**: If needed, clicking browser extension buttons, OS-level dialogs triggered by the browser (e.g., file save/upload dialogs that Selenium might not handle well), or managing browser tabs/windows at an OS level if the dedicated library has limitations.
                *   **Fallback for Simple Interactions**: In rare cases where a very simple, visually distinct UI element *within* a webpage is unusually difficult for Selenium/Playwright to target but easy for image recognition, `PyAutoGUIControlModule` could serve as a fallback (though this should be minimized).
                *   **Non-Browser GUI Targets**: If the overall workflow involves interacting with other desktop applications in sequence with the browser (e.g., copying data from a local app to paste into the browser), `PyAutoGUIControlModule` handles those non-browser parts.
        *   **Coordination (`ChatGPTScraperService`)**:
            *   The higher-level service (e.g., `ChatGPTScraperService`) would orchestrate calls to both the `BrowserInteractionService` and the `PyAutoGUIControlModule`.
            *   Example flow for submitting a prompt:
                1.  `ChatGPTScraperService` -> `BrowserInteractionService.navigate_and_login(...)`
                2.  `ChatGPTScraperService` -> `PyAutoGUIControlModule.ensure_window_focused(browser_window_title_pattern)` (to ensure the browser controlled by Selenium/Playwright is foremost)
                3.  `ChatGPTScraperService` -> `BrowserInteractionService.type_into_prompt_field(prompt_text)`
                4.  `ChatGPTScraperService` -> `BrowserInteractionService.click_send_button()`
                5.  `ChatGPTScraperService` -> `BrowserInteractionService.wait_for_response_element()`
                6.  `ChatGPTScraperService` -> `BrowserInteractionService.extract_response_text()`
                7.  (If response extraction needs OS-level copy/paste due to complex UI or for consistency with other tools): 
                    `ChatGPTScraperService` -> `PyAutoGUIControlModule.ensure_window_focused(...)`
                    `ChatGPTScraperService` -> `PyAutoGUIControlModule.find_click_select_all_copy(response_anchor_image)`
    *   **Integration**: This requires a clear interface definition for the `BrowserInteractionService` similar to what has been done for `PyAutoGUIControlModule`. The `AppConfig` would also need settings for this browser automation service (e.g., WebDriver path, browser type).
    *   The `PyAutoGUIControlModule` could still be responsible for initially launching the browser application itself (e.g., `os.system("start chrome")`) if the dedicated browser automation library is only meant to *control* an already running instance, though most browser libraries can handle launching too.

*   **OCR Integration for Text Extraction**:
    *   For scenarios where text is rendered as part of an image or cannot be selected/copied via clipboard (e.g., in some custom UI elements, remote desktop sessions, or specific parts of games/applications).
    *   **Future Enhancement**: A new method like `get_text_from_image_region(self, region: Tuple[int, int, int, int], image_path: Optional[str] = None, lang: str = 'eng') -> Optional[str]` could be added.
    *   This would internally use `capture_region` and then pass the captured image to an OCR engine (e.g., Tesseract via `pytesseract`).
    *   Requires adding `pytesseract` and a Tesseract OCR installation as dependencies.

*   **Advanced Error Recovery & Recalibration**:
    *   The current `ensure_window_focused` includes a basic recovery attempt (sending ESC).
    *   The `trigger_recalibration` utility (from `gui_utils.py`, called by `CursorOrchestrator`) suggests a pattern for handling cases where predefined coordinates might become invalid.
    *   **Future Enhancement**: The `PyAutoGUIControlModule` could incorporate more sophisticated error recovery, such as:
        *   Attempting to re-find critical anchor images if an interaction fails.
        *   Having a mechanism to flag coordinates or image assets that consistently fail, potentially triggering an alert or an automated recalibration request (if a programmatic recalibration interface existed beyond the CLI script).

*   **Security Considerations (PyAutoGUI)**:
    *   PyAutoGUI has full control over mouse and keyboard. Ensure that prompts or data being typed/pasted by the module are properly sanitized if they originate from untrusted sources to prevent injection of malicious commands or keystrokes.
    *   Fail-safes (`pyautogui.FAILSAFE = True` is default) are important. The module relies on this PyAutoGUI feature.

*   **Testability**: 
    *   Testing GUI automation is inherently challenging. 
    *   Consider strategies like using a mock/dummy target application or a virtual display (e.g., Xvfb on Linux) for automated tests.
    *   Unit tests can cover logic that doesn't directly call PyAutoGUI (e.g., config handling, path resolution).
    *   Integration tests will be crucial and may require careful setup.

## 10. Testing Strategy (NEW SECTION)

Testing the `PyAutoGUIControlModule` will require a multi-faceted approach due to its direct interaction with the OS GUI layer.

*   **1. Unit Tests (Limited Scope)**:
    *   **Target**: Focus on methods and logic that do *not* directly invoke `pyautogui` or `pyperclip` calls that manipulate the GUI or clipboard.
    *   **Examples**:
        *   Configuration parsing in `__init__` (e.g., correct defaults, handling of missing sections).
        *   Image path resolution logic within methods like `find_element_on_screen` (mocking `Path.exists()` and `self.image_assets_base_path`).
        *   Input validation (e.g., `capture_region` validating region tuple format).
        *   Error raising logic for non-GUI errors (e.g., `ValueError` for bad arguments).
    *   **Tools**: Standard Python `unittest` or `pytest` framework.
    *   **Mocking**: Extensively use `unittest.mock.patch` to mock `pyautogui`, `pyperclip`, `pygetwindow`, `Path.exists()`, and `asyncio.get_running_loop().run_in_executor` (to test the flow without actual execution).

*   **2. Integration Tests (Simulated Environment - If Possible)**:
    *   **Target**: Test the core GUI interaction methods (`find_element_on_screen`, `click_element`, `type_text`, `press_hotkey`, `get_clipboard_text`, etc.) in a controlled environment.
    *   **Approach A: Virtual Display (Linux)**:
        *   On Linux, use `Xvfb` (X Virtual Framebuffer) to create a headless display where a mock target application can be run.
        *   The mock target application could be a simple Tkinter, PyQt, or even a basic web page served locally that has known UI elements (images) to interact with.
        *   Tests would launch the mock app in Xvfb, then instruct `PyAutoGUIControlModule` to interact with it, asserting outcomes (e.g., did a click on a mock button trigger a change in the mock app's state that can be programmatically verified?).
    *   **Approach B: Dedicated Test Application (Cross-Platform)**:
        *   Develop a very simple, cross-platform GUI application (e.g., using Tkinter, Kivy, or a minimal web page with `eel`) specifically for testing. This application would have:
            *   Known images for buttons, input fields, text areas.
            *   Ways to report interactions (e.g., text changing in a label after a button click, content appearing in an input after typing).
        *   Tests would need to reliably launch and position this test application before running `PyAutoGUIControlModule` methods against it.
        *   Requires careful management of window focus and ensuring the test app is the target.
    *   **Challenges**: 
        *   Setting up and tearing down these environments reliably in CI/CD.
        *   Making assertions about GUI state changes can be complex.

*   **3. Manual / Semi-Automated Tests (Against Real Target Application)**:
    *   **Target**: Validate functionality against the actual intended target application (e.g., a web browser open to `chat.openai.com`).
    *   **Approach**: 
        *   Develop test scripts that use `PyAutoGUIControlModule` to perform common sequences.
        *   These scripts would require an operator to set up the environment (e.g., log in to the target service, open the correct page).
        *   Assertions might be a mix of automated checks (e.g., `get_clipboard_text` returning expected content) and visual verification by the operator.
    *   **Use Cases**: Essential for validating real-world robustness, especially for image recognition accuracy with actual UI elements.

*   **4. Focused Tests for `_run_blocking_io`**:
    *   Test that it correctly executes functions passed to it.
    *   Test that it correctly passes arguments and keyword arguments.
    *   Test that it propagates exceptions raised by the executed function.
    *   Mock `asyncio.get_running_loop().run_in_executor` to verify it's called as expected.

*   **General Considerations for Integration/Manual Tests**:
    *   **Image Assets**: Maintain a dedicated set of image assets for testing, separate from production assets if necessary, to ensure test stability.
    *   **Delays & Timeouts**: Tests may need to use slightly more generous timeouts than production settings to account for test environment variability.
    *   **Focus Management**: Tests must be extremely careful about window focus. Running tests in an active user session can lead to interference.
    *   **Screen Resolution & DPI**: GUI tests are sensitive to screen resolution and DPI scaling. Test environments should match production as closely as possible or tests should be designed to be somewhat resilient (e.g., using image recognition for everything, avoiding hardcoded coordinates).

This testing strategy aims to provide reasonable confidence in the module's functionality while acknowledging the inherent difficulties of GUI automation testing.

This proposal provides a starting point for the `PyAutoGUIControlModule`. Further refinements will occur during implementation and testing. 