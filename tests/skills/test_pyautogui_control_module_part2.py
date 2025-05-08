# tests/skills/test_pyautogui_control_module_part2.py

import asyncio
import logging
import unittest
from unittest.mock import MagicMock, patch, ANY
from pathlib import Path
import platform
import time

# Assuming necessary imports from part 1 are available or re-imported if needed
from dreamos.core.config import AppConfig, PyAutoGUIBridgeConfig, PathsConfig
from dreamos.skills.pyautogui_control_module import (
    PyAutoGUIControlModule,
    WindowNotFoundError,
    ImageNotFoundError,
    InteractionTimeoutError,
    ClipboardError,
    PyAutoGUIActionFailedError,
    PyAutoGUIControlError,
    PYGETWINDOW_AVAILABLE
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
            image_assets_path="runtime/test_assets/cursor_gui_snippets/", # Updated path potentially
            # Add other relevant config defaults used by tested methods
        )
        self.target_window_pattern = "Test Window Title"

        # Apply necessary patches (consider if these need setup/teardown per test or per class)
        self.pyautogui_patcher = patch('dreamos.skills.pyautogui_control_module.pyautogui', mock_pyautogui)
        self.mock_pyautogui = self.pyautogui_patcher.start()
        # NOTE: Add patches for pygetwindow, pyperclip, Path etc. if methods under test use them directly/indirectly
        self.path_exists_patcher = patch('dreamos.skills.pyautogui_control_module.Path.exists', return_value=True)
        self.mock_path_exists = self.path_exists_patcher.start()
        self.path_is_absolute_patcher = patch('dreamos.skills.pyautogui_control_module.Path.is_absolute', return_value=False)
        self.mock_path_is_absolute = self.path_is_absolute_patcher.start()

        self.module = PyAutoGUIControlModule(config=self.mock_app_config, target_window_title_pattern=self.target_window_pattern)
        # Mock the _run_blocking_io globally for this test class for simplicity,
        # individual tests can override its side_effect if needed.
        async def default_mock_run_blocking_io(func, *args, **kwargs):
            if hasattr(func, '__name__') and func.__name__ == 'locateCenterOnScreen':
                # Provide a default mock point if found, tests can override this
                return MagicMock(x=100, y=200)
            # Add default mocks for click, moveTo etc. if needed or let them be called on the global mock
            return func(*args, **kwargs) # Call the mock func directly
            
        self.run_blocking_io_patcher = patch.object(self.module, '_run_blocking_io', side_effect=default_mock_run_blocking_io)
        self.mock_run_blocking_io = self.run_blocking_io_patcher.start()
        
        # Mock find_element_on_screen globally to return coordinates
        async def mock_find_element_success(*args, **kwargs):
            return (100, 200) # Default coordinates
        self.find_element_patcher = patch.object(self.module, 'find_element_on_screen', side_effect=mock_find_element_success)
        self.mock_find_element = self.find_element_patcher.start()

    def tearDown(self):
        self.pyautogui_patcher.stop()
        self.path_exists_patcher.stop()
        self.path_is_absolute_patcher.stop()
        self.run_blocking_io_patcher.stop()
        self.find_element_patcher.stop()
        mock_pyautogui.reset_mock() # Reset the global mock

    # --- Test click_element --- (Based on UT-CLICK-001 to UT-CLICK-007)
    async def test_click_element_by_image_success(self):
        """UT-CLICK-001: Successfully clicks element found by image."""
        image_path = "cursor_input_box.png"
        await self.module.click_element(image_path=image_path)
        
        # Verify find_element_on_screen was called
        self.mock_find_element.assert_awaited_once_with(image_path, confidence=None, region=None, timeout=None)
        # Verify _run_blocking_io was called for moveTo and click
        self.mock_run_blocking_io.assert_any_call(self.mock_pyautogui.moveTo, 100, 200, duration=ANY)
        self.mock_run_blocking_io.assert_any_call(self.mock_pyautogui.click, button='left', clicks=1, interval=ANY)

    async def test_click_element_by_coords_success(self):
        """UT-CLICK-002: Successfully clicks element at specified coordinates."""
        coords = (300, 400)
        await self.module.click_element(coords=coords)
        
        # Verify find_element_on_screen was NOT called
        self.mock_find_element.assert_not_awaited()
        # Verify _run_blocking_io was called for moveTo and click with correct coords
        self.mock_run_blocking_io.assert_any_call(self.mock_pyautogui.moveTo, 300, 400, duration=ANY)
        self.mock_run_blocking_io.assert_any_call(self.mock_pyautogui.click, button='left', clicks=1, interval=ANY)

    async def test_click_element_with_custom_params(self):
        """UT-CLICK-003: Uses custom button, clicks, interval correctly."""
        coords = (50, 50)
        await self.module.click_element(coords=coords, button='right', clicks=2, interval=0.3)
        
        self.mock_find_element.assert_not_awaited()
        self.mock_run_blocking_io.assert_any_call(self.mock_pyautogui.moveTo, 50, 50, duration=ANY)
        self.mock_run_blocking_io.assert_any_call(self.mock_pyautogui.click, button='right', clicks=2, interval=0.3)

    async def test_click_element_image_not_found_raises_error(self):
        """UT-CLICK-004: Image not found by find_element_on_screen raises ImageNotFoundError."""
        self.mock_find_element.side_effect = ImageNotFoundError("Test image not found")
        with self.assertRaises(ImageNotFoundError):
            await self.module.click_element(image_path="not_found.png")
        self.mock_run_blocking_io.assert_not_called() # Should fail before trying to click

    async def test_click_element_no_target_raises_value_error(self):
        """UT-CLICK-005: Calling without image_path or coords raises ValueError."""
        with self.assertRaises(ValueError):
            await self.module.click_element() 

    async def test_click_element_pyautogui_exception_raises_custom_error(self):
        """UT-CLICK-006: Exception during pyautogui.click is wrapped and raised."""
        # Make _run_blocking_io raise error specifically for click
        async def mock_run_blocking_io_fail_click(func, *args, **kwargs):
            if func == self.mock_pyautogui.moveTo: return # moveTo succeeds
            if func == self.mock_pyautogui.click: raise RuntimeError("Click failed")
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
        
        self.mock_find_element.assert_awaited_once_with(image_path, confidence=None, region=None, timeout=None)
        # Verify click happens at offset coordinates
        self.mock_run_blocking_io.assert_any_call(self.mock_pyautogui.moveTo, 105, 190, duration=ANY) 
        self.mock_run_blocking_io.assert_any_call(self.mock_pyautogui.click, 105, 190, button='left', clicks=1, interval=ANY)

    # --- Test type_text --- (Based on UT-TYPE-001 to UT-TYPE-007)
    async def test_type_text_success(self):
        """UT-TYPE-001: Successfully types short text using pyautogui.write."""
        text_to_type = "Hello, world!"
        await self.module.type_text(text_to_type)
        
        self.mock_run_blocking_io.assert_any_call(
            self.mock_pyautogui.write,
            text_to_type,
            interval=self.mock_app_config.gui_automation.pyautogui_bridge.type_interval_seconds
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
            self.mock_pyautogui.write,
            text_to_type,
            interval=custom_interval
        )

    async def test_type_text_long_text_uses_clipboard(self):
        """UT-TYPE-003: Long text uses clipboard copy-paste fallback."""
        long_text = "a" * 101 # Exceeds default threshold
        
        # Need to mock _set_clipboard_text and _press_hotkey for this
        with patch.object(self.module, '_set_clipboard_text', return_value=None) as mock_set_clip, \
             patch.object(self.module, '_press_hotkey', return_value=None) as mock_press_hotkey:
            
            await self.module.type_text(long_text)

            mock_set_clip.assert_awaited_once_with(long_text)
            mock_press_hotkey.assert_awaited_once_with('ctrl', 'v') # Assuming default ctrl+v
            
            # Verify pyautogui.write was NOT called
            write_call_args_list = [call.args[0] for call in self.mock_run_blocking_io.call_args_list if hasattr(call.args[0], '__name__') and call.args[0].__name__ == 'write']
            self.assertNotIn(self.mock_pyautogui.write, write_call_args_list)
            
    async def test_type_text_uses_clipboard_if_flag_true(self):
        """UT-TYPE-004: Uses clipboard even for short text if use_clipboard is True."""
        short_text = "Use clipboard anyway."
        with patch.object(self.module, '_set_clipboard_text', return_value=None) as mock_set_clip, \
             patch.object(self.module, '_press_hotkey', return_value=None) as mock_press_hotkey:
            
            await self.module.type_text(short_text, use_clipboard=True)

            mock_set_clip.assert_awaited_once_with(short_text)
            mock_press_hotkey.assert_awaited_once_with('ctrl', 'v')
            
            write_call_args_list = [call.args[0] for call in self.mock_run_blocking_io.call_args_list if hasattr(call.args[0], '__name__') and call.args[0].__name__ == 'write']
            self.assertNotIn(self.mock_pyautogui.write, write_call_args_list)

    async def test_type_text_press_enter_true(self):
        """UT-TYPE-005: Presses Enter key after typing."""
        text_to_type = "Type and enter."
        with patch.object(self.module, '_press_key', return_value=None) as mock_press_key:
            await self.module.type_text(text_to_type, press_enter_after=True)
            
            self.mock_run_blocking_io.assert_any_call(self.mock_pyautogui.write, text_to_type, interval=ANY)
            mock_press_key.assert_awaited_once_with('enter')

    async def test_type_text_clear_before_typing_true(self):
        """UT-TYPE-006: Performs select-all and delete before typing."""
        text_to_type = "Cleared first."
        with patch.object(self.module, '_press_hotkey', return_value=None) as mock_press_hotkey, \
             patch.object(self.module, '_press_key', return_value=None) as mock_press_key:
            
            await self.module.type_text(text_to_type, clear_before_typing=True)
            
            mock_press_hotkey.assert_awaited_once_with('ctrl', 'a') # Assuming ctrl+a
            mock_press_key.assert_awaited_once_with('delete')
            self.mock_run_blocking_io.assert_any_call(self.mock_pyautogui.write, text_to_type, interval=ANY)

    async def test_type_text_exception_during_write_propagated(self):
        """UT-TYPE-007: Exception during pyautogui.write is wrapped and raised."""
        text_to_type = "This will fail."
        async def mock_run_blocking_io_fail_write(func, *args, **kwargs):
            if func == self.mock_pyautogui.write: raise RuntimeError("Write failed")
            return func(*args, **kwargs)
        self.mock_run_blocking_io.side_effect = mock_run_blocking_io_fail_write

        with self.assertRaises(PyAutoGUIActionFailedError) as cm:
            await self.module.type_text(text_to_type)
        self.assertIsInstance(cm.exception.__cause__, RuntimeError)

    # --- Test press_hotkey --- (Based on UT-HOTKEY-001 to UT-HOTKEY-004)
    async def test_press_hotkey_success_two_keys(self):
        """UT-HOTKEY-001: Successfully presses a two-key hotkey (e.g., ctrl+c)."""
        await self.module.press_hotkey('ctrl', 'c')
        self.mock_run_blocking_io.assert_any_call(self.mock_pyautogui.hotkey, 'ctrl', 'c')

    async def test_press_hotkey_success_three_keys(self):
        """UT-HOTKEY-002: Successfully presses a three-key hotkey."""
        await self.module.press_hotkey('ctrl', 'shift', 'esc')
        self.mock_run_blocking_io.assert_any_call(self.mock_pyautogui.hotkey, 'ctrl', 'shift', 'esc')

    async def test_press_hotkey_success_single_key_passthrough(self):
        """UT-HOTKEY-003: Successfully presses a single key via hotkey (passthrough to press_key)."""
        with patch.object(self.module, '_press_key', return_value=None) as mock_press_key:
             await self.module.press_hotkey('enter')
             mock_press_key.assert_awaited_once_with('enter')
        # Ensure pyautogui.hotkey itself wasn't called via _run_blocking_io
        hotkey_call_args_list = [call.args[0] for call in self.mock_run_blocking_io.call_args_list if hasattr(call.args[0], '__name__') and call.args[0].__name__ == 'hotkey']
        self.assertNotIn(self.mock_pyautogui.hotkey, hotkey_call_args_list)

    async def test_press_hotkey_exception_propagated(self):
        """UT-HOTKEY-004: Exception during pyautogui.hotkey is wrapped and raised."""
        async def mock_run_blocking_io_fail_hotkey(func, *args, **kwargs):
            if func == self.mock_pyautogui.hotkey: raise RuntimeError("Hotkey failed")
            return func(*args, **kwargs)
        self.mock_run_blocking_io.side_effect = mock_run_blocking_io_fail_hotkey
        
        with self.assertRaises(PyAutoGUIActionFailedError) as cm:
            await self.module.press_hotkey('alt', 'tab')
        self.assertIsInstance(cm.exception.__cause__, RuntimeError)

    # --- Test press_key --- (Based on UT-PRESSKEY-001 to UT-PRESSKEY-003)
    async def test_press_key_success(self):
        """UT-PRESSKEY-001: Successfully presses a single key (e.g., enter)."""
        await self.module.press_key('enter')
        self.mock_run_blocking_io.assert_any_call(self.mock_pyautogui.press, 'enter')
        
    async def test_press_key_multiple_presses(self):
        """UT-PRESSKEY-002: Presses a key multiple times."""
        await self.module.press_key('down', presses=3)
        self.mock_run_blocking_io.assert_any_call(self.mock_pyautogui.press, 'down', presses=3)

    async def test_press_key_exception_propagated(self):
        """UT-PRESSKEY-003: Exception during pyautogui.press is wrapped and raised."""
        async def mock_run_blocking_io_fail_press(func, *args, **kwargs):
            if func == self.mock_pyautogui.press: raise RuntimeError("Press failed")
            return func(*args, **kwargs)
        self.mock_run_blocking_io.side_effect = mock_run_blocking_io_fail_press
        
        with self.assertRaises(PyAutoGUIActionFailedError) as cm:
            await self.module.press_key('esc')
        self.assertIsInstance(cm.exception.__cause__, RuntimeError)

    # --- Test get_clipboard_text --- (Based on UT-CLIP-GET-001 to UT-CLIP-GET-003)
    async def test_get_clipboard_text_success(self):
        """UT-CLIP-GET-001: Successfully retrieves text from clipboard."""
        expected_text = "Clipboard content"
        async def mock_run_blocking_io_paste(*args, **kwargs):
            # Assume the first arg to _run_blocking_io is the function
            if args[0] == self.mock_pyperclip.paste:
                return expected_text
            return None # Or raise error for unexpected calls
        self.mock_run_blocking_io.side_effect = mock_run_blocking_io_paste
        
        text = await self.module.get_clipboard_text()
        self.assertEqual(text, expected_text)
        self.mock_run_blocking_io.assert_any_call(self.mock_pyperclip.paste)

    async def test_get_clipboard_text_empty(self):
        """UT-CLIP-GET-002: Handles empty clipboard correctly."""
        async def mock_run_blocking_io_paste_empty(*args, **kwargs):
            if args[0] == self.mock_pyperclip.paste: return ""
            return None
        self.mock_run_blocking_io.side_effect = mock_run_blocking_io_paste_empty
        
        text = await self.module.get_clipboard_text()
        self.assertEqual(text, "")
        self.mock_run_blocking_io.assert_any_call(self.mock_pyperclip.paste)

    async def test_get_clipboard_text_exception_propagated(self):
        """UT-CLIP-GET-003: Exception during pyperclip.paste is wrapped and raised."""
        async def mock_run_blocking_io_paste_fail(*args, **kwargs):
            if args[0] == self.mock_pyperclip.paste: raise self.mock_pyperclip.PyperclipException("Paste failed")
            return None
        self.mock_run_blocking_io.side_effect = mock_run_blocking_io_paste_fail
        
        with self.assertRaises(ClipboardError) as cm:
            await self.module.get_clipboard_text()
        self.assertIsInstance(cm.exception.__cause__, self.mock_pyperclip.PyperclipException)

    # --- Test set_clipboard_text --- (Based on UT-CLIP-SET-001 to UT-CLIP-SET-003)
    async def test_set_clipboard_text_success(self):
        """UT-CLIP-SET-001: Successfully sets text to clipboard."""
        text_to_set = "Set this text"
        # Mock copy to do nothing but be callable
        async def mock_run_blocking_io_copy(*args, **kwargs):
            if args[0] == self.mock_pyperclip.copy:
                 # args[1] should be text_to_set
                 self.assertEqual(args[1], text_to_set)
                 return None # copy returns None
            return None
        self.mock_run_blocking_io.side_effect = mock_run_blocking_io_copy
        
        await self.module.set_clipboard_text(text_to_set)
        self.mock_run_blocking_io.assert_any_call(self.mock_pyperclip.copy, text_to_set)

    async def test_set_clipboard_text_non_string_converted(self):
        """UT-CLIP-SET-002: Non-string input is converted to string."""
        number_to_set = 12345
        expected_string = "12345"
        async def mock_run_blocking_io_copy_num(*args, **kwargs):
            if args[0] == self.mock_pyperclip.copy:
                 self.assertEqual(args[1], expected_string)
                 return None
            return None
        self.mock_run_blocking_io.side_effect = mock_run_blocking_io_copy_num
        
        await self.module.set_clipboard_text(number_to_set)
        self.mock_run_blocking_io.assert_any_call(self.mock_pyperclip.copy, expected_string)

    async def test_set_clipboard_text_exception_propagated(self):
        """UT-CLIP-SET-003: Exception during pyperclip.copy is wrapped and raised."""
        text_to_set = "Fail to set this"
        async def mock_run_blocking_io_copy_fail(*args, **kwargs):
            if args[0] == self.mock_pyperclip.copy: raise self.mock_pyperclip.PyperclipException("Copy failed")
            return None
        self.mock_run_blocking_io.side_effect = mock_run_blocking_io_copy_fail
        
        with self.assertRaises(ClipboardError) as cm:
            await self.module.set_clipboard_text(text_to_set)
        self.assertIsInstance(cm.exception.__cause__, self.mock_pyperclip.PyperclipException)

    # --- Test find_type_and_enter --- (Based on UT-FTE-001 to UT-FTE-005)
    async def test_find_type_and_enter_success(self):
        """UT-FTE-001: Successfully finds, clicks, types, and presses enter."""
        image_path = "target_field.png"
        text_to_type = "Input text"
        
        # Mock the underlying methods that find_type_and_enter calls
        with patch.object(self.module, 'click_element', return_value=None) as mock_click, \
             patch.object(self.module, 'type_text', return_value=None) as mock_type:
            
            result = await self.module.find_type_and_enter(image_path, text_to_type)
            self.assertTrue(result)
            
            # Verify click_element was called correctly (it internally calls find_element)
            mock_click.assert_awaited_once_with(image_path=image_path, confidence=None, region=None, timeout=None, offset=(0,0))
            # Verify type_text was called correctly
            mock_type.assert_awaited_once_with(text_to_type, interval_seconds=ANY, press_enter_after=True, clear_before_typing=False, use_clipboard=False)

    async def test_find_type_and_enter_with_options(self):
        """UT-FTE-002: Uses optional parameters like clear_before_typing, confidence, region etc."""
        image_path = "target_field.png"
        text_to_type = "Input text"
        custom_confidence = 0.7
        custom_region = (0, 0, 100, 100)
        custom_timeout = 3.0
        custom_offset = (10, 10)

        with patch.object(self.module, 'click_element', return_value=None) as mock_click, \
             patch.object(self.module, 'type_text', return_value=None) as mock_type:
            
            result = await self.module.find_type_and_enter(
                image_path, text_to_type, 
                confidence=custom_confidence, region=custom_region, timeout=custom_timeout,
                offset=custom_offset, clear_before_typing=True, use_clipboard=True
            )
            self.assertTrue(result)
            
            mock_click.assert_awaited_once_with(image_path=image_path, confidence=custom_confidence, region=custom_region, timeout=custom_timeout, offset=custom_offset)
            mock_type.assert_awaited_once_with(text_to_type, interval_seconds=ANY, press_enter_after=True, clear_before_typing=True, use_clipboard=True)

    async def test_find_type_and_enter_image_not_found(self):
        """UT-FTE-003: Returns False if the initial image is not found (via click_element)."""
        image_path = "not_found.png"
        text_to_type = "Input text"

        with patch.object(self.module, 'click_element', side_effect=ImageNotFoundError("Not found")) as mock_click, \
             patch.object(self.module, 'type_text') as mock_type:
            
            result = await self.module.find_type_and_enter(image_path, text_to_type)
            self.assertFalse(result)
            mock_click.assert_awaited_once() # Ensure click was attempted
            mock_type.assert_not_awaited() # Type should not be attempted

    async def test_find_type_and_enter_click_fails(self):
        """UT-FTE-004: Returns False if click_element fails for reasons other than ImageNotFound."""
        image_path = "target.png"
        text_to_type = "Input text"

        with patch.object(self.module, 'click_element', side_effect=PyAutoGUIActionFailedError("Click failed")) as mock_click, \
             patch.object(self.module, 'type_text') as mock_type:
            
            result = await self.module.find_type_and_enter(image_path, text_to_type)
            self.assertFalse(result)
            mock_click.assert_awaited_once() # Ensure click was attempted
            mock_type.assert_not_awaited() # Type should not be attempted

    async def test_find_type_and_enter_type_fails(self):
        """UT-FTE-005: Returns False if type_text fails."""
        image_path = "target.png"
        text_to_type = "Input text"

        with patch.object(self.module, 'click_element', return_value=None) as mock_click, \
             patch.object(self.module, 'type_text', side_effect=PyAutoGUIActionFailedError("Type failed")) as mock_type:
            
            result = await self.module.find_type_and_enter(image_path, text_to_type)
            self.assertFalse(result)
            mock_click.assert_awaited_once() # Ensure click was attempted
            mock_type.assert_awaited_once() # Ensure type was attempted

    # --- Test find_click_select_all_copy --- (Based on UT-FCSAC-001 to UT-FCSAC-005)
    async def test_find_click_select_all_copy_success(self):
        """UT-FCSAC-001: Successfully finds, clicks, selects all, copies, and returns text."""
        image_path = "response_anchor.png"
        expected_clipboard_text = "Copied text"

        # Mock the sequence of underlying calls
        with patch.object(self.module, 'click_element', return_value=None) as mock_click, \
             patch.object(self.module, '_press_hotkey') as mock_press_hotkey, \
             patch.object(self.module, 'get_clipboard_text', return_value=expected_clipboard_text) as mock_get_clip, \
             patch.object(self.module, '_set_clipboard_text', return_value=None) as mock_set_clip: # Mock set too for priming
            
            result = await self.module.find_click_select_all_copy(image_path)
            self.assertEqual(result, expected_clipboard_text)
            
            # Verify the sequence
            mock_click.assert_awaited_once_with(image_path=image_path, confidence=None, region=None, timeout=None, offset=(0,0), clicks=1, button='left')
            # Expected hotkey calls: ctrl+a, ctrl+c
            mock_press_hotkey.assert_any_await('ctrl', 'a')
            mock_press_hotkey.assert_any_await('ctrl', 'c')
            mock_set_clip.assert_awaited_once_with("") # Priming the clipboard
            mock_get_clip.assert_awaited_once() # Getting the final result

    async def test_find_click_select_all_copy_with_options(self):
        """UT-FCSAC-002: Uses optional parameters correctly."""
        image_path = "response_anchor.png"
        expected_clipboard_text = "Copied text"
        custom_confidence = 0.6
        custom_region = (10, 10, 50, 50)
        custom_timeout = 4.0
        custom_offset = (0, 5)
        pause_duration = 0.15

        with patch.object(self.module, 'click_element', return_value=None) as mock_click, \
             patch.object(self.module, '_press_hotkey') as mock_press_hotkey, \
             patch.object(self.module, 'get_clipboard_text', return_value=expected_clipboard_text) as mock_get_clip, \
             patch.object(self.module, '_set_clipboard_text', return_value=None) as mock_set_clip, \
             patch('asyncio.sleep') as mock_sleep:
            
            result = await self.module.find_click_select_all_copy(
                image_path, 
                confidence=custom_confidence, region=custom_region, timeout=custom_timeout, 
                offset=custom_offset, pause_after_copy_sec=pause_duration
            )
            self.assertEqual(result, expected_clipboard_text)
            
            mock_click.assert_awaited_once_with(
                image_path=image_path, confidence=custom_confidence, region=custom_region, 
                timeout=custom_timeout, offset=custom_offset, clicks=1, button='left'
            )
            mock_press_hotkey.assert_any_await('ctrl', 'a')
            mock_press_hotkey.assert_any_await('ctrl', 'c')
            mock_set_clip.assert_awaited_once_with("")
            mock_get_clip.assert_awaited_once()
            mock_sleep.assert_awaited_with(pause_duration)

    async def test_find_click_select_all_copy_image_not_found(self):
        """UT-FCSAC-003: Returns None if the initial image is not found."""
        image_path = "not_found.png"

        with patch.object(self.module, 'click_element', side_effect=ImageNotFoundError("Not found")) as mock_click, \
             patch.object(self.module, '_press_hotkey') as mock_press_hotkey, \
             patch.object(self.module, 'get_clipboard_text') as mock_get_clip:

            result = await self.module.find_click_select_all_copy(image_path)
            self.assertIsNone(result)
            mock_click.assert_awaited_once() # Ensure click was attempted
            mock_press_hotkey.assert_not_awaited()
            mock_get_clip.assert_not_awaited()

    async def test_find_click_select_all_copy_click_fails(self):
        """UT-FCSAC-004: Returns None if click_element fails."""
        image_path = "target.png"

        with patch.object(self.module, 'click_element', side_effect=PyAutoGUIActionFailedError("Click failed")) as mock_click, \
             patch.object(self.module, '_press_hotkey') as mock_press_hotkey, \
             patch.object(self.module, 'get_clipboard_text') as mock_get_clip:

            result = await self.module.find_click_select_all_copy(image_path)
            self.assertIsNone(result)
            mock_click.assert_awaited_once()
            mock_press_hotkey.assert_not_awaited()
            mock_get_clip.assert_not_awaited()
            
    async def test_find_click_select_all_copy_clipboard_fails(self):
        """UT-FCSAC-005: Returns None if get_clipboard_text fails."""
        image_path = "target.png"

        with patch.object(self.module, 'click_element', return_value=None) as mock_click, \
             patch.object(self.module, '_press_hotkey', return_value=None) as mock_press_hotkey, \
             patch.object(self.module, 'get_clipboard_text', side_effect=ClipboardError("Get failed")) as mock_get_clip, \
             patch.object(self.module, '_set_clipboard_text', return_value=None) as mock_set_clip: # Mock set too for priming

            result = await self.module.find_click_select_all_copy(image_path)
            self.assertIsNone(result)
            mock_click.assert_awaited_once()
            mock_press_hotkey.assert_any_await('ctrl', 'a')
            mock_press_hotkey.assert_any_await('ctrl', 'c')
            mock_set_clip.assert_awaited_once_with("")
            mock_get_clip.assert_awaited_once() # Get was attempted

    # --- Test capture_region --- (Based on UT-CAPTURE-001 to UT-CAPTURE-004)
    async def test_capture_region_success_with_filename(self):
        """UT-CAPTURE-001: Successfully captures a region and saves to a file."""
        test_region = (10, 20, 100, 150)
        filename = "test_capture.png"
        expected_save_path = self.module.image_assets_base_path / filename
        
        mock_screenshot_obj = MagicMock()
        # Make _run_blocking_io return the mock_screenshot_obj only for pyautogui.screenshot call
        async def mock_run_blocking_io_capture(func, *args, **kwargs):
            if func == self.mock_pyautogui.screenshot:
                # Can add assertions here about args[0] being the region
                self.assertEqual(kwargs.get('region'), test_region)
                return mock_screenshot_obj
            # For the save call on the object, it will be called directly, not via _run_blocking_io
            return None # Should not be called for other funcs in this test
        
        self.mock_run_blocking_io.side_effect = mock_run_blocking_io_capture
        # Ensure the save_dir exists for the test
        with patch.object(Path, 'mkdir') as mock_mkdir:
            returned_path = await self.module.capture_region(test_region, filename=filename)
            
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
            self.mock_run_blocking_io.assert_any_call(self.mock_pyautogui.screenshot, region=test_region)
            mock_screenshot_obj.save.assert_called_once_with(str(expected_save_path))
            self.assertEqual(returned_path, str(expected_save_path))

    async def test_capture_region_success_no_filename_returns_object(self):
        """UT-CAPTURE-002: Returns PIL Image object when no filename is provided."""
        test_region = (0, 0, 50, 50)
        mock_screenshot_obj = MagicMock() # Simulate a PIL Image object
        
        async def mock_run_blocking_io_capture_obj(func, *args, **kwargs):
            if func == self.mock_pyautogui.screenshot:
                return mock_screenshot_obj
            return None
        self.mock_run_blocking_io.side_effect = mock_run_blocking_io_capture_obj
        
        returned_image = await self.module.capture_region(test_region, filename=None)
        self.mock_run_blocking_io.assert_any_call(self.mock_pyautogui.screenshot, region=test_region)
        self.assertIs(returned_image, mock_screenshot_obj) # Should be the object itself
        mock_screenshot_obj.save.assert_not_called()

    async def test_capture_region_invalid_region_raises_valueerror(self):
        """UT-CAPTURE-003: Invalid region tuple raises ValueError."""
        with self.assertRaises(ValueError):
            await self.module.capture_region((10, 20, -50, 100)) # Negative width
        with self.assertRaises(ValueError):
            await self.module.capture_region((10, 20, 50)) # Too few elements
        self.mock_run_blocking_io.assert_not_called() # pyautogui.screenshot should not be called
        
    async def test_capture_region_exception_during_screenshot_propagated(self):
        """UT-CAPTURE-004: Exception during pyautogui.screenshot is wrapped and raised."""
        test_region = (10, 10, 10, 10)
        async def mock_run_blocking_io_capture_fail(func, *args, **kwargs):
            if func == self.mock_pyautogui.screenshot: raise RuntimeError("Screenshot capture failed")
            return None
        self.mock_run_blocking_io.side_effect = mock_run_blocking_io_capture_fail
        
        with self.assertRaises(PyAutoGUIActionFailedError) as cm:
            await self.module.capture_region(test_region, filename="fail.png")
        self.assertIsInstance(cm.exception.__cause__, RuntimeError)

if __name__ == '__main__':
    unittest.main() 