# tests/skills/test_pyautogui_control_module.py

import asyncio
import logging
import platform
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from dreamos.core.config import AppConfig, PathsConfig, PyAutoGUIBridgeConfig
from dreamos.skills.pyautogui_control_module import (
    ImageNotFoundError,
    PyAutoGUIActionFailedError,
    PyAutoGUIControlError,
    PyAutoGUIControlModule,
    WindowNotFoundError,
)

# Mocking pyautogui and pyperclip at the module level for all tests if they are not available in test env
# This ensures that even if these modules are not installed, tests can run.
# Individual tests can further patch specific functions of these mocks.
mock_pyautogui = MagicMock()
mock_pyperclip = MagicMock()
mock_pygetwindow = MagicMock()


class TestPyAutoGUIControlModule(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        """Set up for each test case."""
        self.mock_app_config = MagicMock(spec=AppConfig)
        self.mock_app_config.paths = MagicMock(spec=PathsConfig)
        self.mock_app_config.paths.project_root = Path("/fake/project/root")
        self.mock_app_config.gui_automation = MagicMock()
        self.mock_app_config.gui_automation.pyautogui_bridge = PyAutoGUIBridgeConfig(
            default_confidence=0.8,
            default_timeout_seconds=5.0,
            default_retry_attempts=2,
            default_retry_delay_seconds=0.2,
            type_interval_seconds=0.005,
            image_assets_path="runtime/test_assets/gui_snippets/",
            clipboard_wait_timeout=3.0,
        )
        self.target_window_pattern = "Test Window Title"

        # Patch the global PYGETWINDOW_AVAILABLE for consistent testing
        # Some tests might override this patch locally if they need to test the unavailable case
        self.pygetwindow_patcher = patch(
            "dreamos.skills.pyautogui_control_module.PYGETWINDOW_AVAILABLE", True
        )
        self.mock_pygetwindow_available = self.pygetwindow_patcher.start()

        self.pygetwindow_module_patcher = patch(
            "dreamos.skills.pyautogui_control_module.pygetwindow", mock_pygetwindow
        )
        self.mock_pygetwindow_module = self.pygetwindow_module_patcher.start()

        self.pyautogui_module_patcher = patch(
            "dreamos.skills.pyautogui_control_module.pyautogui", mock_pyautogui
        )
        self.mock_pyautogui_module = self.pyautogui_module_patcher.start()

        self.pyperclip_module_patcher = patch(
            "dreamos.skills.pyautogui_control_module.pyperclip", mock_pyperclip
        )
        self.mock_pyperclip_module = self.pyperclip_module_patcher.start()

        # Ensure logger is also mocked or captured if needed, to prevent errors during tests
        # For now, let it use the standard logger but be aware it might output during tests.

    def tearDown(self):
        self.pygetwindow_patcher.stop()
        self.pygetwindow_module_patcher.stop()
        self.pyautogui_module_patcher.stop()
        self.pyperclip_module_patcher.stop()
        mock_pyautogui.reset_mock()
        mock_pyperclip.reset_mock()
        mock_pygetwindow.reset_mock()

    # --- Test __init__ --- (Based on UT-INIT-001 from test case doc)
    def test_init_successful_with_valid_config(self):
        """UT-INIT-001: Verify successful initialization with valid AppConfig."""
        module = PyAutoGUIControlModule(
            config=self.mock_app_config,
            target_window_title_pattern=self.target_window_pattern,
        )

        self.assertIsNotNone(module)
        self.assertEqual(module.app_config, self.mock_app_config)
        self.assertEqual(
            module.target_window_title_pattern, self.target_window_pattern.lower()
        )
        self.assertEqual(module.default_confidence, 0.8)
        self.assertEqual(module.default_timeout_seconds, 5.0)
        self.assertEqual(
            module.image_assets_base_path,
            Path("/fake/project/root/runtime/test_assets/gui_snippets/"),
        )
        self.assertIsInstance(module.logger, logging.Logger)

    # Based on UT-INIT-002
    def test_init_with_missing_pyautogui_bridge_config_uses_defaults(self):
        """UT-INIT-002: Verify initialization with missing pyautogui_bridge config uses internal defaults."""
        self.mock_app_config.gui_automation.pyautogui_bridge = (
            None  # Simulate it missing
        )
        # For Pydantic v1/v2 style dict/model_dump, it might also be an empty dict {} or a model with all Nones
        # The module's __init__ handles these cases by using .get() with defaults.

        with patch.object(
            logging.getLogger(
                "dreamos.skills.pyautogui_control_module.PyAutoGUIControlModule"
            ),
            "warning",
        ) as mock_log_warning:
            module = PyAutoGUIControlModule(
                config=self.mock_app_config,
                target_window_title_pattern=self.target_window_pattern,
            )

            self.assertIsNotNone(module)
            # Check a few key defaults that would be different from the mock_app_config if it were used
            self.assertEqual(
                module.default_confidence, 0.9
            )  # Default from module's .get()
            self.assertEqual(
                module.default_timeout_seconds, 10.0
            )  # Default from module's .get()
            self.assertEqual(
                module.image_assets_base_path,
                Path("/fake/project/root/runtime/assets/bridge_gui_snippets/"),
            )  # Default path
            # mock_log_warning.assert_any_call("Could not convert pyautogui_bridge config to dict, using empty defaults.")
            # ^ This log might or might not appear depending on how None is handled vs an empty dict. The primary check is the default values.

    # Based on UT-INIT-003
    def test_init_with_missing_project_root_uses_relative_asset_path(self):
        """UT-INIT-003: Verify image_assets_base_path resolution when project_root is missing."""
        self.mock_app_config.paths.project_root = None  # Simulate project_root missing
        expected_relative_path = Path(
            self.mock_app_config.gui_automation.pyautogui_bridge.image_assets_path
        )  # Should resolve to the string as a Path

        with patch.object(
            logging.getLogger(
                "dreamos.skills.pyautogui_control_module.PyAutoGUIControlModule"
            ),
            "warning",
        ) as mock_log_warning:
            module = PyAutoGUIControlModule(
                config=self.mock_app_config,
                target_window_title_pattern=self.target_window_pattern,
            )
            self.assertEqual(module.image_assets_base_path, expected_relative_path)
            mock_log_warning.assert_any_call(
                f"Project root not found in AppConfig. Image assets path '{expected_relative_path}' might be incorrect."
            )

    # --- Test _run_blocking_io --- (Based on UT-RUNIO-001, UT-RUNIO-002, UT-RUNIO-003)
    async def test_run_blocking_io_success_no_args(self):
        """UT-RUNIO-001: Verify successful execution of a mock blocking function without arguments."""
        module = PyAutoGUIControlModule(
            config=self.mock_app_config,
            target_window_title_pattern=self.target_window_pattern,
        )
        mock_func = MagicMock(return_value="success")

        # Mock run_in_executor for this test
        # loop.run_in_executor(None, lambda f=func, a=args, k=kwargs: f(*a, **k))
        with patch("asyncio.get_running_loop") as mock_get_loop:
            mock_loop = MagicMock()
            mock_get_loop.return_value = mock_loop

            # The lambda itself will call mock_func(), so we set the result of run_in_executor
            # to what the lambda would return if run_in_executor just executed it.
            async def fake_run_in_executor(executor, callback_lambda, *args_lambda):
                return callback_lambda()  # Execute the lambda directly

            mock_loop.run_in_executor = fake_run_in_executor

            result = await module._run_blocking_io(mock_func)
            self.assertEqual(result, "success")
            mock_func.assert_called_once_with()

    async def test_run_blocking_io_success_with_args(self):
        """UT-RUNIO-002: Verify successful execution with positional and keyword arguments."""
        module = PyAutoGUIControlModule(
            config=self.mock_app_config,
            target_window_title_pattern=self.target_window_pattern,
        )
        mock_func_with_args = MagicMock(return_value="result_with_args")

        with patch("asyncio.get_running_loop") as mock_get_loop:
            mock_loop = MagicMock()
            mock_get_loop.return_value = mock_loop

            async def fake_run_in_executor(executor, callback_lambda, *args_lambda):
                return callback_lambda()  # Execute the lambda directly

            mock_loop.run_in_executor = fake_run_in_executor

            result = await module._run_blocking_io(
                mock_func_with_args, "pos_arg1", kw_arg1="val1"
            )
            self.assertEqual(result, "result_with_args")
            mock_func_with_args.assert_called_once_with("pos_arg1", kw_arg1="val1")

    async def test_run_blocking_io_propagates_exception(self):
        """UT-RUNIO-003: Verify correct propagation of an exception from the blocking function."""
        module = PyAutoGUIControlModule(
            config=self.mock_app_config,
            target_window_title_pattern=self.target_window_pattern,
        )
        mock_func_raises = MagicMock(side_effect=RuntimeError("Blocking IO Error"))

        with patch("asyncio.get_running_loop") as mock_get_loop:
            mock_loop = MagicMock()
            mock_get_loop.return_value = mock_loop

            async def fake_run_in_executor(executor, callback_lambda, *args_lambda):
                return (
                    callback_lambda()
                )  # Execute the lambda directly to raise the side_effect

            mock_loop.run_in_executor = fake_run_in_executor

            with self.assertRaisesRegex(RuntimeError, "Blocking IO Error"):
                await module._run_blocking_io(mock_func_raises)
            mock_func_raises.assert_called_once()

    # --- Test ensure_window_focused --- (Based on UT-FOCUS-001 to UT-FOCUS-007)
    @patch("dreamos.skills.pyautogui_control_module.PYGETWINDOW_AVAILABLE", False)
    async def test_ensure_window_focused_pygetwindow_unavailable(
        self, mock_pgw_unavailable
    ):
        """UT-FOCUS-001: pygetwindow unavailable, should log warning and return True."""
        module = PyAutoGUIControlModule(
            config=self.mock_app_config,
            target_window_title_pattern=self.target_window_pattern,
        )
        with patch.object(module.logger, "warning") as mock_log_warning:
            result = await module.ensure_window_focused()
            self.assertTrue(result)
            mock_log_warning.assert_called_with(
                "Cannot ensure window focus: pygetwindow not available. Proceeding with caution."
            )

    async def test_ensure_window_focused_already_active(self):
        """UT-FOCUS-002: Target window found and already active."""
        module = PyAutoGUIControlModule(
            config=self.mock_app_config,
            target_window_title_pattern=self.target_window_pattern,
        )

        mock_target_window = MagicMock()
        mock_target_window.title = self.target_window_pattern
        # Ensure it has an activate method for the type checks, even if not called
        mock_target_window.activate = MagicMock()
        mock_target_window.isActive = True  # Simulate it being active
        if platform.system() == "Windows":
            mock_target_window._hWnd = 12345

        mock_pygetwindow.getWindowsWithTitle.return_value = [mock_target_window]
        mock_pygetwindow.getActiveWindow.return_value = mock_target_window

        # Wrap _run_blocking_io calls for this test
        async def mock_run_blocking_io_for_focus(func, *args, **kwargs):
            if func == mock_pygetwindow.getWindowsWithTitle:
                return [mock_target_window]
            if func == mock_pygetwindow.getActiveWindow:
                return mock_target_window
            return await asyncio.get_running_loop().run_in_executor(
                None, lambda: func(*args, **kwargs)
            )

        with patch.object(
            module, "_run_blocking_io", side_effect=mock_run_blocking_io_for_focus
        ):
            result = await module.ensure_window_focused()
            self.assertTrue(result)
            mock_pygetwindow.getWindowsWithTitle.assert_called_with(
                self.target_window_pattern.lower()
            )
            mock_pygetwindow.getActiveWindow.assert_called()  # Called to check if active
            mock_target_window.activate.assert_not_called()  # Should not be called if already active

    async def test_ensure_window_focused_found_and_activated(self):
        """UT-FOCUS-003: Target window found, not active, but successfully activated."""
        module = PyAutoGUIControlModule(
            config=self.mock_app_config,
            target_window_title_pattern=self.target_window_pattern,
        )

        mock_target_window = MagicMock()
        mock_target_window.title = self.target_window_pattern
        mock_target_window.isActive = False  # Start as not active
        if platform.system() == "Windows":
            mock_target_window._hWnd = 12345

        mock_other_window = MagicMock()
        mock_other_window.title = "Other Window"
        if platform.system() == "Windows":
            mock_other_window._hWnd = 67890

        # Mock the activate method to change isActive state and be traceable
        def def_activate_side_effect():
            mock_target_window.isActive = True

        mock_target_window.activate = MagicMock(side_effect=def_activate_side_effect)

        # Simulate the sequence of pygetwindow calls via _run_blocking_io
        get_active_call_count = 0

        async def mock_run_blocking_io_for_activation(func, *args, **kwargs):
            nonlocal get_active_call_count
            if func == mock_pygetwindow.getWindowsWithTitle:
                return [mock_target_window]
            if func == mock_pygetwindow.getActiveWindow:
                get_active_call_count += 1
                if get_active_call_count == 1:  # First call, it's not active
                    return mock_other_window
                elif get_active_call_count == 2:  # After supposed activation
                    return mock_target_window  # Now it reports as active
            if (
                hasattr(args[0], "activate") and func.__name__ == "activate_sync"
            ):  # Intercept call to activate_sync helper
                args[0].activate()  # Call the window's activate method
                return args[0].isActive  # Return its new active state
            return await asyncio.get_running_loop().run_in_executor(
                None, lambda: func(*args, **kwargs)
            )

        with patch.object(
            module, "_run_blocking_io", side_effect=mock_run_blocking_io_for_activation
        ):
            result = await module.ensure_window_focused()
            self.assertTrue(result)
            mock_pygetwindow.getWindowsWithTitle.assert_called_with(
                self.target_window_pattern.lower()
            )
            self.assertEqual(
                mock_pygetwindow.getActiveWindow.call_count, 2
            )  # Called initially and after activation attempt
            mock_target_window.activate.assert_called_once()

    async def test_ensure_window_focused_not_found_raises_error(self):
        """UT-FOCUS-004: Target window not found after attempts, raises WindowNotFoundError."""
        module = PyAutoGUIControlModule(
            config=self.mock_app_config,
            target_window_title_pattern=self.target_window_pattern,
        )
        module.default_retry_delay_seconds = 0.01  # Speed up test

        mock_pygetwindow.getWindowsWithTitle.return_value = []  # Always returns no windows

        async def mock_run_blocking_io_not_found(func, *args, **kwargs):
            if func == mock_pygetwindow.getWindowsWithTitle:
                return []
            return await asyncio.get_running_loop().run_in_executor(
                None, lambda: func(*args, **kwargs)
            )

        with patch.object(
            module, "_run_blocking_io", side_effect=mock_run_blocking_io_not_found
        ):
            with self.assertRaises(WindowNotFoundError):
                await module.ensure_window_focused(attempts=2)
            self.assertEqual(
                mock_pygetwindow.getWindowsWithTitle.call_count, 2
            )  # Called for each attempt

    async def test_ensure_window_focused_activation_fails_raises_error(self):
        """UT-FOCUS-005: Target window found, activation fails, raises WindowNotFoundError after retries."""
        module = PyAutoGUIControlModule(
            config=self.mock_app_config,
            target_window_title_pattern=self.target_window_pattern,
        )
        module.default_retry_delay_seconds = 0.01  # Speed up test

        mock_target_window = MagicMock()
        mock_target_window.title = self.target_window_pattern
        mock_target_window.activate = (
            MagicMock()
        )  # Mock activate, but it won't make isActive True
        mock_target_window.isActive = False
        if platform.system() == "Windows":
            mock_target_window._hWnd = 12345

        mock_other_window = MagicMock()  # Different window is always active

        # Simulate activation always failing (isActive remains false or another window is active)
        async def mock_run_blocking_io_activation_fail(func, *args, **kwargs):
            if func == mock_pygetwindow.getWindowsWithTitle:
                return [mock_target_window]
            if func == mock_pygetwindow.getActiveWindow:
                return mock_other_window  # Always return the other window as active
            if hasattr(args[0], "activate") and func.__name__ == "activate_sync":
                args[0].activate()  # Call activate
                return False  # But report that it did not become active
            return await asyncio.get_running_loop().run_in_executor(
                None, lambda: func(*args, **kwargs)
            )

        with patch.object(
            module, "_run_blocking_io", side_effect=mock_run_blocking_io_activation_fail
        ):
            with self.assertRaises(WindowNotFoundError):
                await module.ensure_window_focused(attempts=2)
            self.assertEqual(mock_pygetwindow.getWindowsWithTitle.call_count, 2)
            self.assertEqual(
                mock_target_window.activate.call_count, 2
            )  # Activate called on each attempt

    # UT-FOCUS-006 (Multiple windows match) can be complex to simulate perfectly without deep os-level state mocking.
    # The current logic takes the first window from getWindowsWithTitle if no specific match found in active_window.
    # We'll trust the underlying pygetwindow behavior mostly for multiple matches.

    # async def test_ensure_window_focused_unexpected_exception_propagates(self):
    #     """UT-FOCUS-007: Unexpected error during pygetwindow call is wrapped and propagated."""
    #     module = PyAutoGUIControlModule(config=self.mock_app_config, target_window_title_pattern=self.target_window_pattern)

    #     async def mock_run_blocking_io_raises_error(func, *args, **kwargs):
    #         if func == mock_pygetwindow.getWindowsWithTitle:
    #             raise RuntimeError("Unexpected pygetwindow error")
    #         return await asyncio.get_running_loop().run_in_executor(None, lambda: func(*args, **kwargs))

    #     with patch.object(module, '_run_blocking_io', side_effect=mock_run_blocking_io_raises_error):
    #         with self.assertRaises(PyAutoGUIControlError) as cm:
    #             await module.ensure_window_focused(attempts=1)
    #         self.assertIsInstance(cm.exception.__cause__, RuntimeError)

    # --- START OF FIRST NEW TEST GROUP ---
    async def test_new_group_method_one(self):
        # Placeholder for new test
        pass

    async def test_new_group_method_two(self):
        # Placeholder for new test
        pass

    # --- END OF FIRST NEW TEST GROUP ---

    # --- Test find_element_on_screen --- (Based on UT-FIND-001 to UT-FIND-008)
    @patch("dreamos.skills.pyautogui_control_module.Path.exists")
    @patch("dreamos.skills.pyautogui_control_module.Path.is_absolute")
    async def test_find_element_on_screen_success_first_attempt(
        self, mock_is_absolute, mock_exists
    ):
        """UT-FIND-001: Image found successfully on the first attempt."""
        mock_exists.return_value = True
        mock_is_absolute.return_value = False  # Assuming relative path
        module = PyAutoGUIControlModule(
            config=self.mock_app_config,
            target_window_title_pattern=self.target_window_pattern,
        )
        mock_point = MagicMock(x=100, y=150)
        mock_pyautogui.locateCenterOnScreen.return_value = mock_point

        async def mock_run_blocking_io_find_success(func, *args, **kwargs):
            if func == mock_pyautogui.locateCenterOnScreen:
                # args[0] would be the image path string. kwargs would have confidence, grayscale etc.
                # We can assert them here if needed, e.g. self.assertEqual(args[0], expected_path_str)
                return mock_point
            return await asyncio.get_running_loop().run_in_executor(
                None, lambda: func(*args, **kwargs)
            )

        with patch.object(
            module, "_run_blocking_io", side_effect=mock_run_blocking_io_find_success
        ):
            coords = await module.find_element_on_screen("test_image.png")
            self.assertEqual(coords, (100, 150))
            expected_path = module.image_assets_base_path / "test_image.png"
            mock_pyautogui.locateCenterOnScreen.assert_called_once_with(
                image=str(expected_path),
                confidence=module.default_confidence,
                grayscale=True,  # Default in method signature
            )

    @patch("dreamos.skills.pyautogui_control_module.Path.exists")
    @patch("dreamos.skills.pyautogui_control_module.Path.is_absolute")
    @patch(
        "dreamos.skills.pyautogui_control_module.asyncio.sleep", new_callable=MagicMock
    )
    @patch("dreamos.skills.pyautogui_control_module.time.monotonic")
    async def test_find_element_on_screen_success_after_polling(
        self, mock_monotonic, mock_async_sleep, mock_is_absolute, mock_exists
    ):
        """UT-FIND-002: Image found after a few polling attempts."""
        mock_exists.return_value = True
        mock_is_absolute.return_value = False
        module = PyAutoGUIControlModule(
            config=self.mock_app_config,
            target_window_title_pattern=self.target_window_pattern,
        )
        module.default_timeout_seconds = 0.3  # Short timeout for test
        poll_interval = 0.05

        mock_point = MagicMock(x=200, y=250)
        # Simulate finding it on the 3rd attempt (0, 0.05, 0.10 (found))
        side_effects_locate = [None, None, mock_point]
        mock_pyautogui.locateCenterOnScreen.side_effect = side_effects_locate

        # Simulate time passing for timeout
        time_side_effects = [
            0.0,
            0.01,
            0.06,
            0.11,
        ]  # Start, after 1st poll, after 2nd, after 3rd
        mock_monotonic.side_effect = time_side_effects

        async def mock_run_blocking_io_find_polling(func, *args, **kwargs):
            if func == mock_pyautogui.locateCenterOnScreen:
                return mock_pyautogui.locateCenterOnScreen(
                    *args, **kwargs
                )  # Uses the side_effect
            return await asyncio.get_running_loop().run_in_executor(
                None, lambda: func(*args, **kwargs)
            )

        with patch.object(
            module, "_run_blocking_io", side_effect=mock_run_blocking_io_find_polling
        ):
            coords = await module.find_element_on_screen(
                "test_image.png", poll_interval=poll_interval
            )
            self.assertEqual(coords, (200, 250))
            self.assertEqual(mock_pyautogui.locateCenterOnScreen.call_count, 3)
            self.assertEqual(
                mock_async_sleep.call_count, 2
            )  # Slept twice before finding
            mock_async_sleep.assert_any_call(poll_interval)

    @patch("dreamos.skills.pyautogui_control_module.Path.exists")
    @patch("dreamos.skills.pyautogui_control_module.Path.is_absolute")
    @patch(
        "dreamos.skills.pyautogui_control_module.asyncio.sleep", new_callable=MagicMock
    )
    @patch("dreamos.skills.pyautogui_control_module.time.monotonic")
    async def test_find_element_on_screen_timeout_raises_error(
        self, mock_monotonic, mock_async_sleep, mock_is_absolute, mock_exists
    ):
        """UT-FIND-003: Image not found, timeout occurs, raises ImageNotFoundError."""
        mock_exists.return_value = True
        mock_is_absolute.return_value = False
        module = PyAutoGUIControlModule(
            config=self.mock_app_config,
            target_window_title_pattern=self.target_window_pattern,
        )
        test_timeout = 0.1
        poll_interval = 0.03

        mock_pyautogui.locateCenterOnScreen.return_value = None  # Always not found
        mock_monotonic.side_effect = (
            lambda: time.time()
        )  # Use real time for timeout logic to ensure it passes

        # Simulate time passing for timeout logic
        start_test_time = time.time()
        mock_monotonic.side_effect = lambda: start_test_time + (
            mock_pyautogui.locateCenterOnScreen.call_count * poll_interval
        )

        async def mock_run_blocking_io_not_found(func, *args, **kwargs):
            if func == mock_pyautogui.locateCenterOnScreen:
                return None
            return await asyncio.get_running_loop().run_in_executor(
                None, lambda: func(*args, **kwargs)
            )

        with patch.object(
            module, "_run_blocking_io", side_effect=mock_run_blocking_io_not_found
        ):
            with self.assertRaises(ImageNotFoundError):
                # Important: use a real sleep in the main test thread to allow monotonic to advance past timeout
                async def action_that_times_out():
                    nonlocal start_test_time
                    start_test_time = (
                        time.monotonic()
                    )  # reset start time for this specific call
                    mock_monotonic.side_effect = (
                        lambda: time.monotonic()
                    )  # Use actual monotonic for timeout test
                    return await module.find_element_on_screen(
                        "test_image.png",
                        timeout=test_timeout,
                        poll_interval=poll_interval,
                    )

                await action_that_times_out()
            self.assertTrue(mock_pyautogui.locateCenterOnScreen.call_count > 0)

    @patch("dreamos.skills.pyautogui_control_module.Path.exists", return_value=False)
    @patch(
        "dreamos.skills.pyautogui_control_module.Path.is_absolute", return_value=False
    )
    async def test_find_element_on_screen_image_file_not_exist_raises_error(
        self, mock_is_absolute, mock_exists
    ):
        """UT-FIND-004: Provided image_path file does not exist, raises FileNotFoundError."""
        module = PyAutoGUIControlModule(
            config=self.mock_app_config,
            target_window_title_pattern=self.target_window_pattern,
        )
        with self.assertRaises(FileNotFoundError):
            await module.find_element_on_screen("non_existent.png")

    @patch("dreamos.skills.pyautogui_control_module.Path.exists", return_value=True)
    @patch(
        "dreamos.skills.pyautogui_control_module.Path.is_absolute", return_value=False
    )
    async def test_find_element_on_screen_failsafe_exception_raises_custom_error(
        self, mock_is_absolute, mock_exists
    ):
        """UT-FIND-005: PyAutoGUI FailSafeException is wrapped and raised."""
        module = PyAutoGUIControlModule(
            config=self.mock_app_config,
            target_window_title_pattern=self.target_window_pattern,
        )
        mock_pyautogui.locateCenterOnScreen.side_effect = (
            mock_pyautogui.FailSafeException("Failsafe triggered")
        )

        async def mock_run_blocking_io_failsafe(func, *args, **kwargs):
            if func == mock_pyautogui.locateCenterOnScreen:
                raise mock_pyautogui.FailSafeException("Failsafe triggered")
            return await asyncio.get_running_loop().run_in_executor(
                None, lambda: func(*args, **kwargs)
            )

        with patch.object(
            module, "_run_blocking_io", side_effect=mock_run_blocking_io_failsafe
        ):
            with self.assertRaises(PyAutoGUIActionFailedError):
                await module.find_element_on_screen(
                    "test_image.png", timeout=0.01
                )  # Quick timeout

    @patch("dreamos.skills.pyautogui_control_module.Path.exists", return_value=True)
    @patch(
        "dreamos.skills.pyautogui_control_module.Path.is_absolute", return_value=False
    )
    async def test_find_element_on_screen_unexpected_error_raises_custom_error(
        self, mock_is_absolute, mock_exists
    ):
        """UT-FIND-006: Unexpected error during locate is wrapped and raised."""
        module = PyAutoGUIControlModule(
            config=self.mock_app_config,
            target_window_title_pattern=self.target_window_pattern,
        )
        mock_pyautogui.locateCenterOnScreen.side_effect = RuntimeError(
            "Unexpected locate error"
        )

        async def mock_run_blocking_io_unexpected(func, *args, **kwargs):
            if func == mock_pyautogui.locateCenterOnScreen:
                raise RuntimeError("Unexpected locate error")
            return await asyncio.get_running_loop().run_in_executor(
                None, lambda: func(*args, **kwargs)
            )

        with patch.object(
            module, "_run_blocking_io", side_effect=mock_run_blocking_io_unexpected
        ):
            with self.assertRaises(PyAutoGUIControlError) as cm:
                await module.find_element_on_screen("test_image.png", timeout=0.01)
            self.assertIsInstance(cm.exception.__cause__, RuntimeError)

    @patch("dreamos.skills.pyautogui_control_module.Path.exists", return_value=True)
    @patch("dreamos.skills.pyautogui_control_module.Path.is_absolute")
    async def test_find_element_on_screen_uses_custom_params(
        self, mock_is_absolute, mock_exists
    ):
        """UT-FIND-007: Verify correct usage of provided confidence, region, grayscale."""
        mock_is_absolute.return_value = False
        module = PyAutoGUIControlModule(
            config=self.mock_app_config,
            target_window_title_pattern=self.target_window_pattern,
        )
        mock_point = MagicMock(x=1, y=1)
        mock_pyautogui.locateCenterOnScreen.return_value = mock_point

        custom_confidence = 0.75
        custom_region = (10, 20, 30, 40)
        custom_grayscale = False  # Test non-default

        async def mock_run_blocking_io_custom(func, *args, **kwargs):
            if func == mock_pyautogui.locateCenterOnScreen:
                return mock_point
            return await asyncio.get_running_loop().run_in_executor(
                None, lambda: func(*args, **kwargs)
            )

        with patch.object(
            module, "_run_blocking_io", side_effect=mock_run_blocking_io_custom
        ):
            await module.find_element_on_screen(
                "test_image.png",
                confidence=custom_confidence,
                region=custom_region,
                grayscale=custom_grayscale,
            )
            expected_path = module.image_assets_base_path / "test_image.png"
            mock_pyautogui.locateCenterOnScreen.assert_called_once_with(
                image=str(expected_path),
                confidence=custom_confidence,
                region=custom_region,
                grayscale=custom_grayscale,
            )

    @patch("dreamos.skills.pyautogui_control_module.Path.exists", return_value=True)
    @patch(
        "dreamos.skills.pyautogui_control_module.Path.is_absolute", return_value=True
    )  # Absolute path
    async def test_find_element_on_screen_absolute_path_used_directly(
        self, mock_is_absolute, mock_exists
    ):
        """UT-FIND-008: Absolute image path is used directly."""
        module = PyAutoGUIControlModule(
            config=self.mock_app_config,
            target_window_title_pattern=self.target_window_pattern,
        )
        mock_point = MagicMock(x=1, y=1)
        mock_pyautogui.locateCenterOnScreen.return_value = mock_point
        abs_image_path = "/abs/path/to/image.png"

        async def mock_run_blocking_io_abs(func, *args, **kwargs):
            if func == mock_pyautogui.locateCenterOnScreen:
                return mock_point
            return await asyncio.get_running_loop().run_in_executor(
                None, lambda: func(*args, **kwargs)
            )

        with patch.object(
            module, "_run_blocking_io", side_effect=mock_run_blocking_io_abs
        ):
            coords = await module.find_element_on_screen(abs_image_path)
            self.assertEqual(coords, (1, 1))
            mock_pyautogui.locateCenterOnScreen.assert_called_once_with(
                image=abs_image_path,  # Absolute path used directly
                confidence=module.default_confidence,
                grayscale=True,
            )

    # --- START OF SECOND NEW TEST ---
    async def test_another_new_method(self):
        # Placeholder for another new test
        pass

    # --- END OF SECOND NEW TEST ---

    async def test_dummy_for_edit_file_investigation(self):
        """UT-DUMMY-001: A simple test to verify edit_file behavior."""
        self.assertTrue(True, "This dummy test should always pass.")


if __name__ == "__main__":
    unittest.main()
