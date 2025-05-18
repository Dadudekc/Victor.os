# CONSOLIDATED: This file now contains all pyautogui-related tests from both part 1 and part 2.
# The previous test_pyautogui_control_module.py has been merged here and removed as part of deduplication.

# tests/skills/test_pyautogui_control_module_part2.py

import unittest
from pathlib import Path
from unittest.mock import ANY, MagicMock, patch

# Assuming necessary imports from part 1 are available or re-imported if needed
from dreamos.core.config import AppConfig, PathsConfig, PyAutoGUIBridgeConfig
from dreamos.skills.pyautogui_control_module import (
    ClipboardError,
    ImageNotFoundError,
    PyAutoGUIActionFailedError,
    PyAutoGUIControlModule,
)

# Mocking dependencies globally for this file too
mock_pyautogui = MagicMock()
mock_pyperclip = MagicMock()
mock_pygetwindow = MagicMock()


class TestPyAutoGUIControlModulePart2(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        """Set up shared test fixtures if needed, similar to Part 1."""
        self.mock_app_config = MagicMock(spec=AppConfig)
        self.mock_app_config.paths = MagicMock(spec=PathsConfig)
        self.mock_app_config.paths.project_root = Path("/fake/project/root")
        self.mock_app_config.gui_automation = MagicMock()
        self.mock_app_config.gui_automation.pyautogui_bridge = PyAutoGUIBridgeConfig(
            default_confidence=0.8,
            default_timeout_seconds=5.0,
            image_assets_path="runtime/test_assets/cursor_gui_snippets/",  # Updated path potentially
            # Add other relevant config defaults used by tested methods
        )
        self.target_window_pattern = "Test Window Title"

        # Apply necessary patches (consider if these need setup/teardown per test or per class)
        self.pyautogui_patcher = patch(
            "dreamos.skills.pyautogui_control_module.pyautogui", mock_pyautogui
        )
        self.mock_pyautogui = self.pyautogui_patcher.start()
        # NOTE: Add patches for pygetwindow, pyperclip, Path etc. if methods under test use them directly/indirectly
        self.path_exists_patcher = patch(
            "dreamos.skills.pyautogui_control_module.Path.exists", return_value=True
        )
        self.mock_path_exists = self.path_exists_patcher.start()
        self.path_is_absolute_patcher = patch(
            "dreamos.skills.pyautogui_control_module.Path.is_absolute",
            return_value=False,
        )
        self.mock_path_is_absolute = self.path_is_absolute_patcher.start()

        self.module = PyAutoGUIControlModule(
            config=self.mock_app_config,
            target_window_title_pattern=self.target_window_pattern,
        )

        # Mock the _run_blocking_io globally for this test class for simplicity,
        # individual tests can override its side_effect if needed.
        async def default_mock_run_blocking_io(func, *args, **kwargs):
            if hasattr(func, "__name__") and func.__name__ == "locateCenterOnScreen":
                # Provide a default mock point if found, tests can override this
                return MagicMock(x=100, y=200)
            # Add default mocks for click, moveTo etc. if needed or let them be called on the global mock
            return func(*args, **kwargs)  # Call the mock func directly

        self.run_blocking_io_patcher = patch.object(
            self.module, "_run_blocking_io", side_effect=default_mock_run_blocking_io
        )
        self.mock_run_blocking_io = self.run_blocking_io_patcher.start()

        # Mock find_element_on_screen globally to return coordinates
        async def mock_find_element_success(*args, **kwargs):
            return (100, 200)  # Default coordinates

        self.find_element_patcher = patch.object(
            self.module, "find_element_on_screen", side_effect=mock_find_element_success
        )
        self.mock_find_element = self.find_element_patcher.start()

    def tearDown(self):
        self.pyautogui_patcher.stop()
        self.path_exists_patcher.stop()
        self.path_is_absolute_patcher.stop()
        self.run_blocking_io_patcher.stop()
        self.find_element_patcher.stop()
        mock_pyautogui.reset_mock()  # Reset the global mock

    # --- Test click_element --- (Based on UT-CLICK-001 to UT-CLICK-007)
    async def test_click_element_by_image_success(self):
        """UT-CLICK-001: Successfully clicks element found by image."""
        image_path = "cursor_input_box.png"
        await self.module.click_element(image_path=image_path)

        # Verify find_element_on_screen was called
        self.mock_find_element.assert_awaited_once_with(
            image_path, confidence=None, region=None, timeout=None
        )
        # Verify _run_blocking_io was called for moveTo and click
        self.mock_run_blocking_io.assert_any_call(
            self.mock_pyautogui.moveTo, 100, 200, duration=ANY
        )
        self.mock_run_blocking_io.assert_any_call(
            self.mock_pyautogui.click, button="left", clicks=1, interval=ANY
        )

    async def test_click_element_by_coords_success(self):
        """UT-CLICK-002: Successfully clicks element at specified coordinates."""
        coords = (300, 400)
        await self.module.click_element(coords=coords)

        # Verify find_element_on_screen was NOT called
        self.mock_find_element.assert_not_awaited()
        # Verify _run_blocking_io was called for moveTo and click with correct coords
        self.mock_run_blocking_io.assert_any_call(
            self.mock_pyautogui.moveTo, 300, 400, duration=ANY
        )
        self.mock_run_blocking_io.assert_any_call(
            self.mock_pyautogui.click, button="left", clicks=1, interval=ANY
        )

    async def test_click_element_with_custom_params(self):
        """UT-CLICK-003: Uses custom button, clicks, interval correctly."""
        coords = (50, 50)
        await self.module.click_element(
            coords=coords, button="right", clicks=2, interval=0.3
        )

        self.mock_find_element.assert_not_awaited()
        self.mock_run_blocking_io.assert_any_call(
            self.mock_pyautogui.moveTo, 50, 50, duration=ANY
        )
        self.mock_run_blocking_io.assert_any_call(
            self.mock_pyautogui.click, button="right", clicks=2, interval=0.3
        )

    async def test_click_element_image_not_found_raises_error(self):
        """UT-CLICK-004: Image not found by find_element_on_screen raises ImageNotFoundError."""
        self.mock_find_element.side_effect = ImageNotFoundError("Test image not found")
        with self.assertRaises(ImageNotFoundError):
            await self.module.click_element(image_path="not_found.png")
        self.mock_run_blocking_io.assert_not_called()  # Should fail before trying to click

    async def test_click_element_no_target_raises_value_error(self):
        """UT-CLICK-005: Calling without image_path or coords raises ValueError."""
        with self.assertRaises(ValueError):
            await self.module.click_element()

    async def test_click_element_pyautogui_exception_raises_custom_error(self):
        """UT-CLICK-006: Exception during pyautogui.click is wrapped and raised."""

        # Make _run_blocking_io raise error specifically for click
        async def mock_run_blocking_io_fail_click(func, *args, **kwargs):
            if func == self.mock_pyautogui.moveTo:
                return  # moveTo succeeds
            if func == self.mock_pyautogui.click:
                raise RuntimeError("Click failed")
            return func(*args, **kwargs)

        self.mock_run_blocking_io.side_effect = mock_run_blocking_io_fail_click

        with self.assertRaises(PyAutoGUIActionFailedError) as cm:
            await self.module.click_element(coords=(10, 10))
        self.assertIsInstance(cm.exception.__cause__, RuntimeError)

    async def test_click_element_offset_applied_to_image(self):
        """UT-CLICK-007: Click offset is correctly applied when clicking by image."""
        image_path = "anchor.png"
        offset = (5, -10)
        # find_element_on_screen returns (100, 200)
        await self.module.click_element(image_path=image_path, offset=offset)

        self.mock_find_element.assert_awaited_once_with(
            image_path, confidence=None, region=None, timeout=None
        )
        # Verify click happens at offset coordinates
        self.mock_run_blocking_io.assert_any_call(
            self.mock_pyautogui.moveTo, 105, 190, duration=ANY
        )
        self.mock_run_blocking_io.assert_any_call(
            self.mock_pyautogui.click, 105, 190, button="left", clicks=1, interval=ANY
        )

    # --- Test type_text --- (Based on UT-TYPE-001 to UT-TYPE-007)
    async def test_type_text_success(self):
        """UT-TYPE-001: Successfully types short text using pyautogui.write."""
        text_to_type = "Hello, world!"
        await self.module.type_text(text_to_type)

        self.mock_run_blocking_io.assert_any_call(
            self.mock_pyautogui.write,
            text_to_type,
            interval=self.mock_app_config.gui_automation.pyautogui_bridge.type_interval_seconds,
        )
        # Verify clipboard was NOT used
        self.mock_pyperclip.copy.assert_not_called()
        self.mock_pyautogui.hotkey.assert_not_called()

    async def test_type_text_success_with_custom_interval(self):
        """UT-TYPE-002: Uses custom typing interval."""
        text_to_type = "Custom interval test."
        custom_interval = 0.1
        await self.module.type_text(text_to_type, interval_seconds=custom_interval)

        self.mock_run_blocking_io.assert_any_call(
            self.mock_pyautogui.write, text_to_type, interval=custom_interval
        )

    async def test_type_text_long_text_uses_clipboard(self):
        """UT-TYPE-003: Long text uses clipboard copy-paste fallback."""
        long_text = "a" * 101  # Exceeds default threshold

        # Need to mock _set_clipboard_text and _press_hotkey for this
        with (
            patch.object(
                self.module, "_set_clipboard_text", return_value=None
            ) as mock_set_clip,
            patch.object(
                self.module, "_press_hotkey", return_value=None
            ) as mock_press_hotkey,
        ):
            await self.module.type_text(long_text)

            mock_set_clip.assert_awaited_once_with(long_text)
            mock_press_hotkey.assert_awaited_once_with(
                "ctrl", "v"
            )  # Assuming default ctrl+v

            # Verify pyautogui.write was NOT called
            write_call_args_list = [
                call.args[0]
                for call in self.mock_run_blocking_io.call_args_list
                if hasattr(call.args[0], "__name__")
                and call.args[0].__name__ == "write"
            ]
            self.assertNotIn(self.mock_pyautogui.write, write_call_args_list)

    async def test_type_text_uses_clipboard_if_flag_true(self):
        """UT-TYPE-004: Uses clipboard even for short text if use_clipboard is True."""
        short_text = "Use clipboard anyway."
        with (
            patch.object(
                self.module, "_set_clipboard_text", return_value=None
            ) as mock_set_clip,
            patch.object(
                self.module, "_press_hotkey", return_value=None
            ) as mock_press_hotkey,
        ):
            await self.module.type_text(short_text, use_clipboard_fallback=True) # Corrected parameter name
            mock_set_clip.assert_awaited_once_with(short_text)
            mock_press_hotkey.assert_awaited_once_with("ctrl", "v")


    async def test_type_text_press_enter_true(self):
        """UT-TYPE-005: Presses Enter after typing if press_enter_after is True."""
        text_to_type = "Type then Enter"
        with patch.object(self.module, "_press_key", return_value=None) as mock_press_key:
            await self.module.type_text(text_to_type, press_enter_after=True)

            self.mock_run_blocking_io.assert_any_call(
                self.mock_pyautogui.write, text_to_type, interval=ANY
            )
            mock_press_key.assert_awaited_once_with("enter")

    async def test_type_text_clear_before_typing_true(self):
        """UT-TYPE-006: Clears field (Ctrl+A, Backspace) before typing if clear_before_typing is True."""
        text_to_type = "Cleared and typed"
        with patch.object(self.module, "_press_hotkey", return_value=None) as mock_press_hotkey, \
             patch.object(self.module, "_press_key", return_value=None) as mock_press_key:

            await self.module.type_text(text_to_type, clear_before_typing=True)

            # Check for Ctrl+A
            mock_press_hotkey.assert_any_call("ctrl", "a")
            # Check for Backspace
            mock_press_key.assert_any_call("backspace")

            # Ensure write is called after clearing
            self.mock_run_blocking_io.assert_any_call(
                 self.mock_pyautogui.write, text_to_type, interval=ANY
            )


    async def test_type_text_exception_during_write_propagated(self):
        """UT-TYPE-007: Exception during pyautogui.write is wrapped."""
        async def mock_run_blocking_io_fail_write(func, *args, **kwargs):
            if func == self.mock_pyautogui.write:
                raise RuntimeError("Write failed")
            return func(*args, **kwargs)
        self.mock_run_blocking_io.side_effect = mock_run_blocking_io_fail_write

        with self.assertRaises(PyAutoGUIActionFailedError):
            await self.module.type_text("some text")

    # --- Test _press_hotkey --- (Based on UT-HOTKEY-001 to UT-HOTKEY-003)
    async def test_press_hotkey_success_two_keys(self):
        """UT-HOTKEY-001: Successfully presses two-key hotkey (e.g., Ctrl+C)."""
        await self.module._press_hotkey("ctrl", "c")
        self.mock_run_blocking_io.assert_awaited_once_with(
            self.mock_pyautogui.hotkey, "ctrl", "c"
        )

    async def test_press_hotkey_success_three_keys(self):
        """UT-HOTKEY-002: Successfully presses three-key hotkey (e.g., Ctrl+Shift+Esc)."""
        await self.module._press_hotkey("ctrl", "shift", "esc")
        self.mock_run_blocking_io.assert_awaited_once_with(
            self.mock_pyautogui.hotkey, "ctrl", "shift", "esc"
        )
    
    async def test_press_hotkey_success_single_key_passthrough(self): # Added based on previous structure
        """UT-HOTKEY-00X: Single key is passed through correctly (should use _press_key ideally, but testing hotkey)"""
        # This tests if hotkey can also handle single keys if misused, though _press_key is preferred.
        await self.module._press_hotkey("enter")
        self.mock_run_blocking_io.assert_awaited_once_with(
            self.mock_pyautogui.hotkey, "enter"
        )


    async def test_press_hotkey_exception_propagated(self):
        """UT-HOTKEY-003: Exception during pyautogui.hotkey is wrapped."""
        async def mock_run_blocking_io_fail_hotkey(func, *args, **kwargs):
            if func == self.mock_pyautogui.hotkey:
                raise RuntimeError("Hotkey failed")
            return func(*args, **kwargs)
        self.mock_run_blocking_io.side_effect = mock_run_blocking_io_fail_hotkey

        with self.assertRaises(PyAutoGUIActionFailedError):
            await self.module._press_hotkey("ctrl", "x")

    # --- Test _press_key --- (Based on UT-PRESS-001 to UT-PRESS-003)
    async def test_press_key_success(self):
        """UT-PRESS-001: Successfully presses a single key."""
        await self.module._press_key("enter")
        self.mock_run_blocking_io.assert_awaited_once_with(self.mock_pyautogui.press, "enter", presses=1)

    async def test_press_key_multiple_presses(self):
        """UT-PRESS-002: Successfully presses a single key multiple times."""
        await self.module._press_key("a", presses=3)
        self.mock_run_blocking_io.assert_awaited_once_with(self.mock_pyautogui.press, "a", presses=3)

    async def test_press_key_exception_propagated(self):
        """UT-PRESS-003: Exception during pyautogui.press is wrapped."""
        async def mock_run_blocking_io_fail_press(func, *args, **kwargs):
            if func == self.mock_pyautogui.press:
                raise RuntimeError("Press failed")
            return func(*args, **kwargs)
        self.mock_run_blocking_io.side_effect = mock_run_blocking_io_fail_press
        
        with self.assertRaises(PyAutoGUIActionFailedError):
            await self.module._press_key("esc")

    # --- Test _get_clipboard_text --- (Based on UT-CLIP-GET-001 to UT-CLIP-GET-003)
    async def test_get_clipboard_text_success(self):
        """UT-CLIP-GET-001: Successfully retrieves text from clipboard."""
        expected_text = "clipboard data"
        async def mock_run_blocking_io_paste(*args, **kwargs):
            # Assume the first arg to _run_blocking_io is the function
            if args[0] == mock_pyperclip.paste:
                return expected_text
            raise ValueError("Unexpected function call to mock_run_blocking_io_paste")

        self.mock_run_blocking_io.side_effect = mock_run_blocking_io_paste
        
        actual_text = await self.module._get_clipboard_text()
        self.assertEqual(actual_text, expected_text)
        self.mock_run_blocking_io.assert_awaited_once_with(mock_pyperclip.paste)


    async def test_get_clipboard_text_empty(self):
        """UT-CLIP-GET-002: Handles empty clipboard gracefully."""
        async def mock_run_blocking_io_paste_empty(*args, **kwargs):
            if args[0] == mock_pyperclip.paste:
                return ""
            raise ValueError("Unexpected function call to mock_run_blocking_io_paste_empty")
        self.mock_run_blocking_io.side_effect = mock_run_blocking_io_paste_empty
        
        actual_text = await self.module._get_clipboard_text()
        self.assertEqual(actual_text, "")

    async def test_get_clipboard_text_exception_propagated(self):
        """UT-CLIP-GET-003: Wraps and raises pyperclip exceptions."""
        async def mock_run_blocking_io_paste_fail(*args, **kwargs):
            if args[0] == mock_pyperclip.paste:
                raise mock_pyperclip.PyperclipException("Paste error")
            raise ValueError("Unexpected function call to mock_run_blocking_io_paste_fail")

        self.mock_run_blocking_io.side_effect = mock_run_blocking_io_paste_fail

        with self.assertRaises(ClipboardError) as cm:
            await self.module._get_clipboard_text()
        self.assertIsInstance(cm.exception.__cause__, mock_pyperclip.PyperclipException)


    # --- Test _set_clipboard_text --- (Based on UT-CLIP-SET-001 to UT-CLIP-SET-003)
    async def test_set_clipboard_text_success(self):
        """UT-CLIP-SET-001: Successfully sets text to clipboard."""
        text_to_set = "data for clipboard"
        async def mock_run_blocking_io_copy(*args, **kwargs):
             if args[0] == mock_pyperclip.copy:
                self.assertEqual(args[1], text_to_set) # Check that the correct text is being copied
                return
             raise ValueError("Unexpected function call to mock_run_blocking_io_copy")
        self.mock_run_blocking_io.side_effect = mock_run_blocking_io_copy

        await self.module._set_clipboard_text(text_to_set)
        self.mock_run_blocking_io.assert_awaited_once_with(mock_pyperclip.copy, text_to_set)

    async def test_set_clipboard_text_non_string_converted(self):
        """UT-CLIP-SET-002: Non-string input is converted to string."""
        number_to_set = 12345
        async def mock_run_blocking_io_copy_num(*args, **kwargs):
            if args[0] == mock_pyperclip.copy:
                self.assertEqual(args[1], str(number_to_set))
                return
            raise ValueError("Unexpected function call to mock_run_blocking_io_copy_num")
        self.mock_run_blocking_io.side_effect = mock_run_blocking_io_copy_num
        
        await self.module._set_clipboard_text(number_to_set)
        self.mock_run_blocking_io.assert_awaited_once_with(mock_pyperclip.copy, str(number_to_set))


    async def test_set_clipboard_text_exception_propagated(self):
        """UT-CLIP-SET-003: Wraps and raises pyperclip exceptions during copy."""
        text_to_set = "problematic text"
        async def mock_run_blocking_io_copy_fail(*args, **kwargs):
            if args[0] == mock_pyperclip.copy:
                raise mock_pyperclip.PyperclipException("Copy error")
            raise ValueError("Unexpected function call to mock_run_blocking_io_copy_fail")
        self.mock_run_blocking_io.side_effect = mock_run_blocking_io_copy_fail

        with self.assertRaises(ClipboardError) as cm:
            await self.module._set_clipboard_text(text_to_set)
        self.assertIsInstance(cm.exception.__cause__, mock_pyperclip.PyperclipException)

    # --- Composite Action Tests ---

    # Based on UT-COMPOSITE-TYPE-001 to UT-COMPOSITE-TYPE-004
    async def test_find_type_and_enter_success(self):
        """UT-COMPOSITE-TYPE-001: Finds element, types, and presses Enter successfully."""
        image_path = "input_field.png"
        text_to_type = "Composite test"
        
        # Mock dependent methods
        with patch.object(self.module, "click_element", new_callable=MagicMock) as mock_click, \
             patch.object(self.module, "type_text", new_callable=MagicMock) as mock_type:
            
            # find_element_on_screen is already mocked globally to return (100,200)
            
            await self.module.find_type_and_enter(image_path, text_to_type)

            self.mock_find_element.assert_awaited_once_with(image_path, confidence=None, region=None, timeout=None)
            mock_click.assert_awaited_once_with(coords=(100,200), button='left', clicks=1, interval=ANY, offset=None)
            mock_type.assert_awaited_once_with(
                text_to_type,
                interval_seconds=self.mock_app_config.gui_automation.pyautogui_bridge.type_interval_seconds,
                press_enter_after=True,
                clear_before_typing=False,
                use_clipboard_fallback=self.mock_app_config.gui_automation.pyautogui_bridge.use_clipboard_fallback_for_type,
                max_length_for_direct_type=self.mock_app_config.gui_automation.pyautogui_bridge.max_length_for_direct_type
            )


    async def test_find_type_and_enter_with_options(self):
        """UT-COMPOSITE-TYPE-002: Uses all options correctly (confidence, region, timeout, click options, type options)."""
        image_path = "another_field.png"
        text_to_type = "Options galore"
        confidence = 0.7
        region = (0, 0, 100, 100)
        timeout = 10.0
        click_button = "right"
        type_interval = 0.01
        clear_before = True
        use_clipboard = True
        max_direct = 5

        with patch.object(self.module, "click_element", new_callable=MagicMock) as mock_click, \
             patch.object(self.module, "type_text", new_callable=MagicMock) as mock_type:

            await self.module.find_type_and_enter(
                image_path,
                text_to_type,
                confidence=confidence,
                region=region,
                timeout_seconds=timeout,
                click_button=click_button,
                type_interval_seconds=type_interval,
                clear_before_typing=clear_before,
                use_clipboard_fallback=use_clipboard,
                max_length_for_direct_type=max_direct,
                click_offset=(1,1) # Added for completeness
            )

            self.mock_find_element.assert_awaited_once_with(image_path, confidence=confidence, region=region, timeout=timeout)
            mock_click.assert_awaited_once_with(coords=(100,200), button=click_button, clicks=1, interval=ANY, offset=(1,1))
            mock_type.assert_awaited_once_with(
                text_to_type,
                interval_seconds=type_interval,
                press_enter_after=True,
                clear_before_typing=clear_before,
                use_clipboard_fallback=use_clipboard,
                max_length_for_direct_type=max_direct
            )

    async def test_find_type_and_enter_image_not_found(self):
        """UT-COMPOSITE-TYPE-003: ImageNotFoundError from find_element is propagated."""
        self.mock_find_element.side_effect = ImageNotFoundError("Target not found for typing")
        
        with patch.object(self.module, "click_element") as mock_click, \
             patch.object(self.module, "type_text") as mock_type, \
             self.assertRaises(ImageNotFoundError):
            
            await self.module.find_type_and_enter("non_existent.png", "some text")
            
            mock_click.assert_not_awaited()
            mock_type.assert_not_awaited()


    async def test_find_type_and_enter_click_fails(self):
        """UT-COMPOSITE-TYPE-004: PyAutoGUIActionFailedError from click_element is propagated."""
        with patch.object(self.module, "click_element", side_effect=PyAutoGUIActionFailedError("Click failed during composite")) as mock_click, \
             patch.object(self.module, "type_text") as mock_type, \
             self.assertRaises(PyAutoGUIActionFailedError):

            # find_element_on_screen is mocked globally to return (100,200)
            await self.module.find_type_and_enter("clickable_image.png", "some text")
            
            mock_click.assert_awaited_once() # Ensure click was attempted
            mock_type.assert_not_awaited() # Type should not be attempted if click fails


    async def test_find_type_and_enter_type_fails(self):
        """UT-COMPOSITE-TYPE-00X: PyAutoGUIActionFailedError from type_text is propagated (New Test)."""
        with patch.object(self.module, "click_element", new_callable=MagicMock) as mock_click, \
             patch.object(self.module, "type_text", side_effect=PyAutoGUIActionFailedError("Type failed during composite")) as mock_type, \
             self.assertRaises(PyAutoGUIActionFailedError):

            # find_element_on_screen is mocked globally to return (100,200)
            await self.module.find_type_and_enter("typeable_image.png", "some text")

            mock_click.assert_awaited_once() # Ensure click was attempted
            mock_type.assert_awaited_once() # Ensure type was attempted


    # Based on UT-COMPOSITE-COPY-001 to UT-COMPOSITE-COPY-004
    async def test_find_click_select_all_copy_success(self):
        """UT-COMPOSITE-COPY-001: Finds, clicks, selects all, copies, and returns text."""
        expected_text = "Copied text"
        image_path = "text_area.png"

        with patch.object(self.module, "click_element", new_callable=MagicMock) as mock_click, \
             patch.object(self.module, "_press_hotkey", new_callable=MagicMock) as mock_press_hotkey, \
             patch.object(self.module, "_get_clipboard_text", return_value=expected_text) as mock_get_clipboard:

            # find_element_on_screen is mocked globally to return (100,200)
            
            result = await self.module.find_click_select_all_copy(image_path)

            self.assertEqual(result, expected_text)
            self.mock_find_element.assert_awaited_once_with(image_path, confidence=None, region=None, timeout=None)
            mock_click.assert_awaited_once_with(coords=(100,200), button='left', clicks=1, interval=ANY, offset=None)
            
            # Check for select all (Ctrl+A) and copy (Ctrl+C)
            mock_press_hotkey.assert_any_await("ctrl", "a")
            mock_press_hotkey.assert_any_await("ctrl", "c")
            
            mock_get_clipboard.assert_awaited_once()


    async def test_find_click_select_all_copy_with_options(self):
        """UT-COMPOSITE-COPY-002: Uses all options correctly."""
        expected_text = "Optional copy"
        image_path = "another_text_area.png"
        confidence = 0.6
        region = (10, 10, 50, 50)
        timeout = 3.0
        click_button = "middle"
        select_all_hotkey = ("alt", "a")
        copy_hotkey = ("alt", "c")

        with patch.object(self.module, "click_element", new_callable=MagicMock) as mock_click, \
             patch.object(self.module, "_press_hotkey", new_callable=MagicMock) as mock_press_hotkey, \
             patch.object(self.module, "_get_clipboard_text", return_value=expected_text) as mock_get_clipboard:
            
            result = await self.module.find_click_select_all_copy(
                image_path,
                confidence=confidence,
                region=region,
                timeout_seconds=timeout,
                click_button=click_button,
                select_all_hotkey=select_all_hotkey,
                copy_hotkey=copy_hotkey,
                click_offset=(-2, -2) # Added for completeness
            )

            self.assertEqual(result, expected_text)
            self.mock_find_element.assert_awaited_once_with(image_path, confidence=confidence, region=region, timeout=timeout)
            mock_click.assert_awaited_once_with(coords=(100,200), button=click_button, clicks=1, interval=ANY, offset=(-2,-2))
            
            mock_press_hotkey.assert_any_await(*select_all_hotkey)
            mock_press_hotkey.assert_any_await(*copy_hotkey)
            
            mock_get_clipboard.assert_awaited_once()

    async def test_find_click_select_all_copy_image_not_found(self):
        """UT-COMPOSITE-COPY-003: ImageNotFoundError from find_element is propagated."""
        self.mock_find_element.side_effect = ImageNotFoundError("Target not found for copy")

        with patch.object(self.module, "click_element") as mock_click, \
             patch.object(self.module, "_press_hotkey") as mock_press_hotkey, \
             patch.object(self.module, "_get_clipboard_text") as mock_get_clipboard, \
             self.assertRaises(ImageNotFoundError):

            await self.module.find_click_select_all_copy("non_existent_area.png")

            mock_click.assert_not_awaited()
            mock_press_hotkey.assert_not_awaited()
            mock_get_clipboard.assert_not_awaited()


    async def test_find_click_select_all_copy_click_fails(self):
        """UT-COMPOSITE-COPY-004: PyAutoGUIActionFailedError from click_element is propagated."""
        with patch.object(self.module, "click_element", side_effect=PyAutoGUIActionFailedError("Click failed during copy composite")) as mock_click, \
             patch.object(self.module, "_press_hotkey") as mock_press_hotkey, \
             patch.object(self.module, "_get_clipboard_text") as mock_get_clipboard, \
             self.assertRaises(PyAutoGUIActionFailedError):

            # find_element_on_screen is mocked globally to return (100,200)
            await self.module.find_click_select_all_copy("copy_target.png")
            
            mock_click.assert_awaited_once()
            mock_press_hotkey.assert_not_awaited()
            mock_get_clipboard.assert_not_awaited()


    async def test_find_click_select_all_copy_clipboard_fails(self):
        """UT-COMPOSITE-COPY-00X: ClipboardError from _get_clipboard_text is propagated (New Test)."""
        with patch.object(self.module, "click_element", new_callable=MagicMock) as mock_click, \
             patch.object(self.module, "_press_hotkey", new_callable=MagicMock) as mock_press_hotkey, \
             patch.object(self.module, "_get_clipboard_text", side_effect=ClipboardError("Clipboard read failed")) as mock_get_clipboard, \
             self.assertRaises(ClipboardError):

            # find_element_on_screen is mocked globally to return (100,200)
            await self.module.find_click_select_all_copy("another_copy_target.png")

            mock_click.assert_awaited_once()
            mock_press_hotkey.assert_any_await("ctrl", "a") # Default select all
            mock_press_hotkey.assert_any_await("ctrl", "c") # Default copy
            mock_get_clipboard.assert_awaited_once()


    # --- Test _capture_region --- (Based on UT-CAPTURE-001 to UT-CAPTURE-004)
    async def test_capture_region_success_with_filename(self):
        """UT-CAPTURE-001: Captures region and saves to file if filename provided."""
        region = (10, 20, 100, 150)
        filename = "test_capture.png"
        expected_path = self.mock_app_config.paths.project_root / filename
        
        # Mock screenshot to return a mock image object
        mock_image = MagicMock()
        async def mock_run_blocking_io_capture(func, *args, **kwargs):
            if func == self.mock_pyautogui.screenshot:
                self.assertEqual(kwargs.get('region'), region)
                return mock_image
            raise ValueError("Unexpected func in mock_run_blocking_io_capture")
        self.mock_run_blocking_io.side_effect = mock_run_blocking_io_capture

        # Mock Path.exists for the save path check
        with patch("dreamos.skills.pyautogui_control_module.Path.exists", return_value=False) as mock_exists:
             # We also need to mock the save method on the mock_image
            mock_image.save = MagicMock()
            
            actual_path = await self.module._capture_region(region, filename)
            
            self.assertEqual(actual_path, str(expected_path))
            self.mock_run_blocking_io.assert_awaited_once_with(self.mock_pyautogui.screenshot, region=region)
            mock_image.save.assert_called_once_with(str(expected_path))


    async def test_capture_region_success_no_filename_returns_object(self):
        """UT-CAPTURE-002: Returns PIL Image object if no filename provided."""
        region = (0, 0, 50, 50)
        mock_image_obj = MagicMock(name="PILImageObject") # Simulate a PIL Image
        async def mock_run_blocking_io_capture_obj(func, *args, **kwargs):
            if func == self.mock_pyautogui.screenshot:
                return mock_image_obj
            raise ValueError("Unexpected func in mock_run_blocking_io_capture_obj")

        self.mock_run_blocking_io.side_effect = mock_run_blocking_io_capture_obj
        
        result = await self.module._capture_region(region)
        self.assertIs(result, mock_image_obj)
        self.mock_run_blocking_io.assert_awaited_once_with(self.mock_pyautogui.screenshot, region=region)


    async def test_capture_region_invalid_region_raises_valueerror(self):
        """UT-CAPTURE-003: Invalid region tuple raises ValueError."""
        with self.assertRaises(ValueError):
            await self.module._capture_region((10, 20)) # Too short
        with self.assertRaises(ValueError):
            await self.module._capture_region((10, 20, 5, 5)) # width/height <=0
        self.mock_run_blocking_io.assert_not_called()


    async def test_capture_region_exception_during_screenshot_propagated(self):
        """UT-CAPTURE-004: Exception during pyautogui.screenshot is wrapped."""
        region = (0,0,10,10)
        async def mock_run_blocking_io_capture_fail(func, *args, **kwargs):
            if func == self.mock_pyautogui.screenshot:
                raise RuntimeError("Screenshot failed")
            raise ValueError("Unexpected func in mock_run_blocking_io_capture_fail")
        self.mock_run_blocking_io.side_effect = mock_run_blocking_io_capture_fail

        with self.assertRaises(PyAutoGUIActionFailedError):
            await self.module._capture_region(region)

    async def test_dummy_new_method(self):
        """A new dummy test method."""
        self.assertTrue(True)

    async def test_another_dummy_method(self):
        """Yet another dummy test method."""
        self.assertFalse(False)

# Standard boilerplate to run tests
if __name__ == '__main__':
    unittest.main() 