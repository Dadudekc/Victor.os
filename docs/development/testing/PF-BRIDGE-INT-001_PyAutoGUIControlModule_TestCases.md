# Test Cases: PyAutoGUIControlModule

**Task ID**: `PF-BRIDGE-INT-001`
**Module**: `src/dreamos/skills/pyautogui_control_module.py`
**Related Documents**:
*   `ai_docs/api_proposals/PF-BRIDGE-INT-001_PyAutoGUIControlModule_API.md` (See Section 10: Testing Strategy)
*   `src/dreamos/core/config.py` (for `AppConfig` and `PyAutoGUIBridgeConfig`)

## 1. Introduction

This document outlines test cases for the `PyAutoGUIControlModule`. It references the testing strategy defined in the API proposal. Tests are categorized into Unit, Integration, and Manual/Semi-Automated.

## 2. Unit Test Cases

**Framework**: `pytest` with `unittest.mock`

**General Mocks for most Unit Tests** (to isolate module logic):
*   `pyautogui` (all functions used by the module)
*   `pyperclip` (copy, paste)
*   `pygetwindow` (getActiveWindow, getWindowsWithTitle)
*   `asyncio.get_running_loop().run_in_executor` (to return a predefined value or mock object)
*   `time.monotonic`, `time.sleep`, `asyncio.sleep` (to control time-based logic)
*   `Path.exists`, `Path.is_absolute`
*   `logging.getLogger` (to capture log messages)

### 2.1. `__init__(self, config: AppConfig, target_window_title_pattern: str)`

*   **Test Case ID**: UT-INIT-001
    *   **Description**: Verify successful initialization with valid `AppConfig` containing `pyautogui_bridge` settings and a target window title.
    *   **Setup**:
        *   Create a mock `AppConfig` instance.
        *   Populate `app_config.pyautogui_bridge` with a mock `PyAutoGUIBridgeConfig` object containing valid default values (e.g., confidence, timeouts, asset path).
        *   Define a `target_window_title_pattern` string.
    *   **Action**: Instantiate `PyAutoGUIControlModule(config=mock_app_config, target_window_title_pattern=pattern)`.
    *   **Expected Outcome**:
        *   Instance created successfully.
        *   `self.app_config`, `self.logger`, `self.target_window_title_pattern` (lowercase) are set correctly.
        *   `self.module_config` correctly extracted from `app_config.pyautogui_bridge`.
        *   `self.default_confidence`, `self.default_timeout_seconds`, etc., are initialized from `self.module_config`.
        *   `self.image_assets_base_path` is correctly resolved using `app_config.paths.project_root` and `module_config.image_assets_path`.
        *   Informative log messages for initialization are emitted.

*   **Test Case ID**: UT-INIT-002
    *   **Description**: Verify initialization when `app_config.pyautogui_bridge` is missing or empty; ensure internal defaults are used.
    *   **Setup**:
        *   Create a mock `AppConfig` instance.
        *   Set `app_config.pyautogui_bridge` to `None` or an empty dictionary.
    *   **Action**: Instantiate `PyAutoGUIControlModule`.
    *   **Expected Outcome**:
        *   Instance created successfully.
        *   `self.module_config` is an empty dictionary.
        *   Default values specified in the `self.module_config.get('setting', DEFAULT_VALUE)` calls within `__init__` are used for `self.default_confidence`, `self.default_timeout_seconds`, `self.image_assets_path`, etc.
        *   Warning log message emitted about missing/empty `pyautogui_bridge` config.

*   **Test Case ID**: UT-INIT-003
    *   **Description**: Verify `image_assets_base_path` resolution when `app_config.paths.project_root` is not available (fallback behavior).
    *   **Setup**:
        *   Create a mock `AppConfig` where `app_config.paths` is `None` or `app_config.paths.project_root` is `None`.
        *   `app_config.pyautogui_bridge.image_assets_path` is set to a relative path.
    *   **Action**: Instantiate `PyAutoGUIControlModule`.
    *   **Expected Outcome**:
        *   `self.image_assets_base_path` defaults to `Path(image_assets_rel_path)` (i.e., relative to current working directory at time of instantiation, or as Path handles it).
        *   Warning log message emitted about project root not being found and potential incorrectness of the asset path.

*   **Test Case ID**: UT-INIT-004
    *   **Description**: Verify initialization with Pydantic v1 style `pyautogui_bridge` config (using `.dict()` internally).
    *   **Setup**:
        *   Create a mock `AppConfig` instance.
        *   Create a mock `PyAutoGUIBridgeConfigPydanticV1` class that has a `.dict()` method but not `.model_dump()`.
        *   Populate `app_config.pyautogui_bridge` with an instance of this mock V1 config.
    *   **Action**: Instantiate `PyAutoGUIControlModule`.
    *   **Expected Outcome**:
        *   `self.module_config` correctly extracted using `.dict()`.
        *   Module attributes (`self.default_confidence`, etc.) are initialized correctly from this config.

*   **Test Case ID**: UT-INIT-005
    *   **Description**: Verify initialization with Pydantic v2 style `pyautogui_bridge` config (using `.model_dump()` internally).
    *   **Setup**:
        *   Create a mock `AppConfig` instance.
        *   Create a mock `PyAutoGUIBridgeConfigPydanticV2` class that has a `.model_dump()` method.
        *   Populate `app_config.pyautogui_bridge` with an instance of this mock V2 config.
    *   **Action**: Instantiate `PyAutoGUIControlModule`.
    *   **Expected Outcome**:
        *   `self.module_config` correctly extracted using `.model_dump()`.
        *   Module attributes (`self.default_confidence`, etc.) are initialized correctly from this config.

### 2.2. `_run_blocking_io(self, func: callable, *args: Any, **kwargs: Any)`

*   **Test Case ID**: UT-RUNIO-001
    *   **Description**: Verify successful execution of a mock blocking function without arguments.
    *   **Setup**:
        *   Mock `asyncio.get_running_loop().run_in_executor` to return a known value (e.g., "success").
        *   Define a simple mock callable `mock_func`.
    *   **Action**: `await module._run_blocking_io(mock_func)`.
    *   **Expected Outcome**:
        *   `run_in_executor` called correctly with `mock_func`.
        *   Returns the value from `run_in_executor` (e.g., "success").

*   **Test Case ID**: UT-RUNIO-002
    *   **Description**: Verify successful execution with positional and keyword arguments passed correctly.
    *   **Setup**:
        *   `mock_executor_return_value = "result_with_args"`
        *   Mock `run_in_executor` to check arguments passed to the lambda it executes.
        *   Define `mock_func_with_args = MagicMock(return_value=mock_executor_return_value)`.
    *   **Action**: `await module._run_blocking_io(mock_func_with_args, 'pos_arg1', kw_arg1='val1')`.
    *   **Expected Outcome**:
        *   `run_in_executor` is called. Its lambda, when executed, calls `mock_func_with_args('pos_arg1', kw_arg1='val1')`.
        *   Returns `mock_executor_return_value`.

*   **Test Case ID**: UT-RUNIO-003
    *   **Description**: Verify correct propagation of an exception raised by the blocking function.
    *   **Setup**:
        *   Define a mock callable `mock_func_raises` that raises a specific `RuntimeError`.
        *   Mock `run_in_executor` to execute this lambda, thus raising the error.
    *   **Action**: `with pytest.raises(RuntimeError): await module._run_blocking_io(mock_func_raises)`.
    *   **Expected Outcome**:
        *   The `RuntimeError` raised by `mock_func_raises` is propagated.
        *   Error log message generated by `_run_blocking_io` before re-raising.

### 2.3. `ensure_window_focused(self, attempts: int = 3)`

**General Mocks for these tests (in addition to global mocks)**:
*   `self._run_blocking_io` (to control returns of `pygetwindow` calls)
*   `pygetwindow.getWindowsWithTitle`
*   `pygetwindow.getActiveWindow`
*   Mock window objects returned by `pygetwindow` calls, with attributes like `title`, `_hWnd` (for Windows), and mockable `activate()` and `isActive` properties/methods.

*   **Test Case ID**: UT-FOCUS-001
    *   **Description**: `pygetwindow` is not available; method should log a warning and return `True`.
    *   **Setup**:
        *   Patch `PYGETWINDOW_AVAILABLE` to `False` within the module's scope for this test.
    *   **Action**: `await module.ensure_window_focused()`.
    *   **Expected Outcome**:
        *   Returns `True`.
        *   Warning log message emitted about `pygetwindow` not being available.

*   **Test Case ID**: UT-FOCUS-002
    *   **Description**: Target window found and is already active/focused on the first attempt.
    *   **Setup**:
        *   Patch `PYGETWINDOW_AVAILABLE` to `True`.
        *   Mock `self._run_blocking_io` to simulate `pygetwindow.getWindowsWithTitle` returning a list with one matching mock window.
        *   Mock `self._run_blocking_io` to simulate `pygetwindow.getActiveWindow` returning the same mock window instance.
        *   Configure `module.target_window_title_pattern`.
    *   **Action**: `await module.ensure_window_focused()`.
    *   **Expected Outcome**:
        *   Returns `True`.
        *   Debug log indicates window found and already active.
        *   `activate()` method of the mock window is NOT called.

*   **Test Case ID**: UT-FOCUS-003
    *   **Description**: Target window found, not active, but successfully activated on the first attempt.
    *   **Setup**:
        *   Patch `PYGETWINDOW_AVAILABLE` to `True`.
        *   Create `mock_target_window` with `title`, `_hWnd`, and an `activate()` method that sets `isActive` to `True`.
        *   Mock `getWindowsWithTitle` (via `_run_blocking_io`) to return `[mock_target_window]`.
        *   Mock `getActiveWindow` (via `_run_blocking_io`) initially to return a different `mock_other_window`, then after `activate_sync` is called, to return `mock_target_window`.
        *   Mock `activate_sync` internal helper to correctly call `window.activate()` and return `window.isActive`.
    *   **Action**: `await module.ensure_window_focused()`.
    *   **Expected Outcome**:
        *   Returns `True`.
        *   `mock_target_window.activate()` was called.
        *   Log messages indicate finding, attempting activation, and successful activation.

*   **Test Case ID**: UT-FOCUS-004
    *   **Description**: Target window not found after specified number of attempts.
    *   **Setup**:
        *   Patch `PYGETWINDOW_AVAILABLE` to `True`.
        *   Mock `getWindowsWithTitle` (via `_run_blocking_io`) to consistently return an empty list `[]`.
        *   Set `attempts = 2` for the call.
    *   **Action**: `with pytest.raises(WindowNotFoundError): await module.ensure_window_focused(attempts=2)`.
    *   **Expected Outcome**:
        *   `WindowNotFoundError` is raised.
        *   Log messages indicate multiple attempts and final failure.
        *   `asyncio.sleep` called between attempts.

*   **Test Case ID**: UT-FOCUS-005
    *   **Description**: Target window found, activation attempted, but fails (e.g., `activate()` fails or `isActive` remains `False`). Retries occur, and ultimately fails.
    *   **Setup**:
        *   Patch `PYGETWINDOW_AVAILABLE` to `True`.
        *   Create `mock_target_window` where `activate()` is called but `isActive` remains `False` or `activate_sync` returns `False`.
        *   Mock `getWindowsWithTitle` to return `[mock_target_window]`.
        *   Mock `getActiveWindow` to consistently return a different window.
        *   Set `attempts = 2`.
    *   **Action**: `with pytest.raises(WindowNotFoundError): await module.ensure_window_focused(attempts=2)`.
    *   **Expected Outcome**:
        *   `WindowNotFoundError` raised after all attempts.
        *   `mock_target_window.activate()` called multiple times (once per attempt).
        *   Log messages indicate activation failures and retries.

*   **Test Case ID**: UT-FOCUS-006
    *   **Description**: Multiple windows match the pattern; ensures the first one is targeted for activation if none are currently active matching the pattern.
    *   **Setup**:
        *   Patch `PYGETWINDOW_AVAILABLE` to `True`.
        *   Create `mock_window1` and `mock_window2`, both matching the title pattern. `mock_window1.activate()` works.
        *   Mock `getWindowsWithTitle` to return `[mock_window1, mock_window2]`.
        *   Mock `getActiveWindow` to initially return an unrelated window, then `mock_window1` after its activation.
    *   **Action**: `await module.ensure_window_focused()`.
    *   **Expected Outcome**:
        *   Returns `True`.
        *   `mock_window1.activate()` is called (assuming it's the first in the list).
        *   `mock_window2.activate()` is NOT called.

*   **Test Case ID**: UT-FOCUS-007
    *   **Description**: An unexpected exception occurs during a `pygetwindow` call; ensure it's wrapped and propagated correctly after retries.
    *   **Setup**:
        *   Patch `PYGETWINDOW_AVAILABLE` to `True`.
        *   Mock `getWindowsWithTitle` (via `_run_blocking_io`) to raise a `RuntimeError` on the first call, then succeed on the second (or fail consistently if testing final error propagation).
        *   If testing propagation: Mock to consistently raise `RuntimeError`.
    *   **Action & Expected Outcome (Propagation)**:
        *   `with pytest.raises(PyAutoGUIControlError): await module.ensure_window_focused(attempts=1)` (if it fails on 1st attempt).
        *   The original `RuntimeError` should be the `__cause__` of the `PyAutoGUIControlError`.
        *   Appropriate error logging occurs.

### 2.4. `find_element_on_screen(self, image_path: str, confidence: Optional[float], timeout: Optional[float], region: Optional[Tuple[int, int, int, int]], grayscale: bool, poll_interval: float)`

**General Mocks for these tests (in addition to global mocks)**:
*   `self._run_blocking_io` (to control returns of `pyautogui.locateCenterOnScreen`)
*   `pyautogui.locateCenterOnScreen`
*   `Path(image_path).exists`
*   `Path(image_path).is_absolute`
*   `time.monotonic` (to control timeout logic)
*   `asyncio.sleep` (to control poll interval)

*   **Test Case ID**: UT-FIND-001
    *   **Description**: Image found successfully on the first attempt.
    *   **Setup**:
        *   `module.image_assets_base_path` is set.
        *   `Path(image_path).exists()` returns `True`.
        *   Mock `pyautogui.locateCenterOnScreen` (via `_run_blocking_io`) to return a mock `Point(x=100, y=150)` object.
        *   Provide `image_path = "test_image.png"`.
    *   **Action**: `coords = await module.find_element_on_screen("test_image.png")`.
    *   **Expected Outcome**:
        *   Returns `(100, 150)`.
        *   Log message indicates image found.

*   **Test Case ID**: UT-FIND-002
    *   **Description**: Image not found initially, but found after a few polling attempts within timeout.
    *   **Setup**:
        *   `Path(image_path).exists()` returns `True`.
        *   Mock `pyautogui.locateCenterOnScreen` (via `_run_blocking_io`) to return `None` twice, then a mock `Point(x=200, y=250)` on the third call.
        *   Mock `time.monotonic` to advance time appropriately with `poll_interval` to allow multiple polls before `timeout_to_use` is exceeded.
        *   Set `timeout` argument to allow for multiple polls.
    *   **Action**: `coords = await module.find_element_on_screen("test_image.png", timeout=5.0, poll_interval=0.1)`.
    *   **Expected Outcome**:
        *   Returns `(200, 250)`.
        *   `asyncio.sleep` called multiple times.
        *   Log messages indicate initial failures and eventual success.

*   **Test Case ID**: UT-FIND-003
    *   **Description**: Image not found, and timeout occurs.
    *   **Setup**:
        *   `Path(image_path).exists()` returns `True`.
        *   Mock `pyautogui.locateCenterOnScreen` (via `_run_blocking_io`) to consistently return `None`.
        *   Mock `time.monotonic` to advance time such that `timeout_to_use` is exceeded.
    *   **Action**: `with pytest.raises(ImageNotFoundError): await module.find_element_on_screen("test_image.png", timeout=0.2, poll_interval=0.05)`.
    *   **Expected Outcome**:
        *   `ImageNotFoundError` is raised.
        *   Error log message indicates timeout.

*   **Test Case ID**: UT-FIND-004
    *   **Description**: Provided `image_path` file does not exist.
    *   **Setup**:
        *   Mock `Path(image_path).exists()` to return `False`.
    *   **Action**: `with pytest.raises(FileNotFoundError): await module.find_element_on_screen("non_existent.png")`.
    *   **Expected Outcome**:
        *   `FileNotFoundError` is raised.
        *   Error log message indicates image file not found.

*   **Test Case ID**: UT-FIND-005
    *   **Description**: `pyautogui.locateCenterOnScreen` raises `pyautogui.FailSafeException`.
    *   **Setup**:
        *   `Path(image_path).exists()` returns `True`.
        *   Mock `pyautogui.locateCenterOnScreen` (via `_run_blocking_io`) to raise `pyautogui.FailSafeException`.
    *   **Action**: `with pytest.raises(PyAutoGUIActionFailedError): await module.find_element_on_screen("test_image.png")`.
    *   **Expected Outcome**:
        *   `PyAutoGUIActionFailedError` is raised (wrapping the original).
        *   Error log message indicates fail-safe triggered.

*   **Test Case ID**: UT-FIND-006
    *   **Description**: `pyautogui.locateCenterOnScreen` raises an unexpected non-PyAutoGUI exception.
    *   **Setup**:
        *   `Path(image_path).exists()` returns `True`.
        *   Mock `pyautogui.locateCenterOnScreen` (via `_run_blocking_io`) to raise a `RuntimeError("Unexpected error")`.
    *   **Action**: `with pytest.raises(PyAutoGUIControlError): await module.find_element_on_screen("test_image.png")`.
    *   **Expected Outcome**:
        *   `PyAutoGUIControlError` is raised (wrapping the `RuntimeError`).
        *   Error log message indicates unexpected error.

*   **Test Case ID**: UT-FIND-007
    *   **Description**: Verify correct usage of provided `confidence`, `region`, and `grayscale` parameters.
    *   **Setup**:
        *   `Path(image_path).exists()` returns `True`.
        *   `mock_locate = MagicMock(return_value=Point(1,1))` (Point from pyautogui)
        *   Mock `self._run_blocking_io` to call `mock_locate`.
        *   `custom_confidence = 0.75`, `custom_region = (10, 20, 30, 40)`, `custom_grayscale = False`.
    *   **Action**: `await module.find_element_on_screen("test_image.png", confidence=custom_confidence, region=custom_region, grayscale=custom_grayscale)`.
    *   **Expected Outcome**:
        *   `mock_locate` (representing `pyautogui.locateCenterOnScreen`) is called with `confidence=custom_confidence`, `region=custom_region`, and `grayscale=custom_grayscale`.

*   **Test Case ID**: UT-FIND-008
    *   **Description**: Absolute image path provided; ensure it's used directly without prepending `image_assets_base_path`.
    *   **Setup**:
        *   `/absolute/path/to/image.png` (mocked as existing).
        *   Mock `Path("/absolute/path/to/image.png").is_absolute()` to return `True`.
        *   Mock `Path("/absolute/path/to/image.png").exists()` to return `True`.
        *   Mock `pyautogui.locateCenterOnScreen` to return a `Point`.
    *   **Action**: `await module.find_element_on_screen("/absolute/path/to/image.png")`.
    *   **Expected Outcome**:
        *   `pyautogui.locateCenterOnScreen` called with `image='/absolute/path/to/image.png'`.

### 2.5. `click_element(self, image_path: Optional[str], coords: Optional[Tuple[int, int]], button: str, clicks: int, interval: float, confidence: Optional[float], timeout: Optional[float], region: Optional[Tuple[int, int, int, int]], move_duration: float)`

**General Mocks for these tests (in addition to global mocks)**:
*   `self.ensure_window_focused`
*   `self.find_element_on_screen`
*   `self._run_blocking_io` (to control `pyautogui.click`)
*   `pyautogui.click`

*   **Test Case ID**: UT-CLICK-001
    *   **Description**: Click by `image_path` successfully.
    *   **Setup**:
        *   Mock `self.ensure_window_focused` to return `True`.
        *   Mock `self.find_element_on_screen` to return `(100, 100)` when called with `image_path`.
        *   Mock `pyautogui.click` (via `_run_blocking_io`) to succeed.
    *   **Action**: `result = await module.click_element(image_path="test_image.png")`.
    *   **Expected Outcome**:
        *   Returns `True`.
        *   `self.ensure_window_focused` called.
        *   `self.find_element_on_screen` called with "test_image.png".
        *   `pyautogui.click` called with `x=100, y=100` and default click parameters.

*   **Test Case ID**: UT-CLICK-002
    *   **Description**: Click by `coords` successfully.
    *   **Setup**:
        *   Mock `self.ensure_window_focused` to return `True`.
        *   Mock `pyautogui.click` (via `_run_blocking_io`) to succeed.
        *   `target_coords = (200, 200)`.
    *   **Action**: `result = await module.click_element(coords=target_coords)`.
    *   **Expected Outcome**:
        *   Returns `True`.
        *   `self.ensure_window_focused` called.
        *   `self.find_element_on_screen` is NOT called.
        *   `pyautogui.click` called with `x=200, y=200`.

*   **Test Case ID**: UT-CLICK-003
    *   **Description**: `ValueError` raised if neither `image_path` nor `coords` is provided.
    *   **Action**: `with pytest.raises(ValueError): await module.click_element()`.
    *   **Expected Outcome**: `ValueError` is raised.

*   **Test Case ID**: UT-CLICK-004
    *   **Description**: `ensure_window_focused` returns `False` or raises `WindowNotFoundError`.
    *   **Setup**:
        *   Mock `self.ensure_window_focused` to raise `WindowNotFoundError("Focus failed")`.
    *   **Action**: `with pytest.raises(WindowNotFoundError): await module.click_element(coords=(1,1))`.
    *   **Expected Outcome**: `WindowNotFoundError` (from `ensure_window_focused`) is propagated.

*   **Test Case ID**: UT-CLICK-005
    *   **Description**: `find_element_on_screen` raises `ImageNotFoundError` when clicking by `image_path`.
    *   **Setup**:
        *   Mock `self.ensure_window_focused` to return `True`.
        *   Mock `self.find_element_on_screen` to raise `ImageNotFoundError("Image not found")`.
    *   **Action**: `with pytest.raises(ImageNotFoundError): await module.click_element(image_path="test_image.png")`.
    *   **Expected Outcome**: `ImageNotFoundError` (from `find_element_on_screen`) is propagated.

*   **Test Case ID**: UT-CLICK-006
    *   **Description**: `pyautogui.click` itself raises `PyAutoGUI.FailSafeException`.
    *   **Setup**:
        *   Mock `self.ensure_window_focused` to return `True`.
        *   Mock `pyautogui.click` (via `_run_blocking_io`) to raise `pyautogui.FailSafeException`.
    *   **Action**: `with pytest.raises(PyAutoGUIActionFailedError): await module.click_element(coords=(1,1))`.
    *   **Expected Outcome**: `PyAutoGUIActionFailedError` is raised.

*   **Test Case ID**: UT-CLICK-007
    *   **Description**: Verify custom click parameters (`button`, `clicks`, `interval`, `move_duration`) are passed to `pyautogui.click`.
    *   **Setup**:
        *   Mock `self.ensure_window_focused` to return `True`.
        *   `mock_pyautogui_click = MagicMock()`
        *   Mock `self._run_blocking_io` to call `mock_pyautogui_click`.
        *   `custom_params = {"button": "right", "clicks": 2, "interval": 0.1, "duration": 0.5}` (duration for move_duration)
    *   **Action**: `await module.click_element(coords=(1,1), **custom_params)`.
    *   **Expected Outcome**:
        *   `mock_pyautogui_click` called with `x=1, y=1, button='right', clicks=2, interval=0.1, duration=0.5`.

*   **Test Case ID**: UT-CLICK-008
    *   **Description**: `find_element_on_screen` returns `None` unexpectedly (though it should raise). Method should handle this gracefully and return `False` or raise.
    *   **Setup**:
        *   Mock `self.ensure_window_focused` to return `True`.
        *   Mock `self.find_element_on_screen` to return `None`.
    *   **Action**: `result = await module.click_element(image_path="test_image.png")`.
    *   **Expected Outcome**:
        *   Returns `False` (as per current implementation sketch for this unexpected case).
        *   Error log message "Element ... could not be found (returned None unexpectedly)".
        *   (Alternative expected: Could also be designed to raise a `PyAutoGUIControlError` here).

---
*Test cases for type_text and keyboard methods to be added next.*

### 2.6. Keyboard & Text Input Methods (`type_text`, `press_hotkey`, `press_key`)

**General Mocks for these tests (in addition to global mocks)**:
*   `self.ensure_window_focused`
*   `self.click_element` (for `type_text` with target)
*   `self._run_blocking_io` (to control `pyautogui.write`, `pyautogui.hotkey`, `pyautogui.press`, `pyperclip.copy`)
*   `pyautogui.write`, `pyautogui.hotkey`, `pyautogui.press`
*   `pyperclip.copy`, `pyperclip.paste` (though `paste` isn't directly used in module, `copy` is)

#### 2.6.1. `type_text(self, text: str, interval: Optional[float], target_image_path: Optional[str], target_coords: Optional[Tuple[int, int]], clear_before_typing: bool)`

*   **Test Case ID**: UT-TYPE-001
    *   **Description**: Basic text typing without target click or clearing.
    *   **Setup**:
        *   Mock `self.ensure_window_focused` to return `True`.
        *   Mock `pyautogui.write` (via `_run_blocking_io`) to succeed.
        *   `text_to_type = "Hello World"`.
    *   **Action**: `result = await module.type_text(text_to_type)`.
    *   **Expected Outcome**:
        *   Returns `True`.
        *   `self.ensure_window_focused` called.
        *   `pyautogui.write` called with `text_to_type` and default interval.
        *   `self.click_element` NOT called.

*   **Test Case ID**: UT-TYPE-002
    *   **Description**: Type text after clicking `target_image_path`.
    *   **Setup**:
        *   Mock `self.ensure_window_focused` to return `True`.
        *   Mock `self.click_element` to return `True` when called for `target_image_path`.
        *   Mock `pyautogui.write` to succeed.
    *   **Action**: `await module.type_text("Hello", target_image_path="target.png")`.
    *   **Expected Outcome**:
        *   Returns `True`.
        *   `self.click_element` called with `image_path="target.png"`.
        *   `pyautogui.write` called.

*   **Test Case ID**: UT-TYPE-003
    *   **Description**: Type text after clicking `target_coords`.
    *   **Setup**: Similar to UT-TYPE-002, but `self.click_element` called with `coords`.
    *   **Action**: `await module.type_text("Hello", target_coords=(10,10))`.
    *   **Expected Outcome**: Returns `True`, `self.click_element` called with `coords`.

*   **Test Case ID**: UT-TYPE-004
    *   **Description**: `self.click_element` fails when a target is specified; `type_text` should return `False` or propagate error.
    *   **Setup**:
        *   Mock `self.ensure_window_focused` to return `True`.
        *   Mock `self.click_element` to return `False` (or raise `ImageNotFoundError`).
    *   **Action**: `result = await module.type_text("Hello", target_image_path="target.png")`.
    *   **Expected Outcome (if click_element returns False)**:
        *   Returns `False`.
        *   Error log from `type_text` about click failure.
        *   `pyautogui.write` NOT called.
    *   **Expected Outcome (if click_element raises)**:
        *   The exception from `click_element` (e.g. `ImageNotFoundError`) is propagated.

*   **Test Case ID**: UT-TYPE-005
    *   **Description**: Type text with `clear_before_typing = True`.
    *   **Setup**:
        *   Mock `self.ensure_window_focused` to return `True`.
        *   Mock `pyautogui.hotkey` (for Ctrl+A) and `pyautogui.press` (for Delete) to succeed.
        *   Mock `pyautogui.write` to succeed.
    *   **Action**: `await module.type_text("Hello", clear_before_typing=True)`.
    *   **Expected Outcome**:
        *   Returns `True`.
        *   `pyautogui.hotkey` called with `('ctrl', 'a')` (or platform equivalent).
        *   `pyautogui.press` called with `'delete'`.
        *   `pyautogui.write` called.

*   **Test Case ID**: UT-TYPE-006
    *   **Description**: Type long text; verify clipboard paste fallback is used if `pyperclip` is available.
    *   **Setup**:
        *   Mock `self.ensure_window_focused` to return `True`.
        *   Patch `pyperclip` to be available (mock `pyperclip.copy` and `pyautogui.hotkey` for Ctrl+V).
        *   `long_text = "a" * 100`.
    *   **Action**: `await module.type_text(long_text)`.
    *   **Expected Outcome**:
        *   Returns `True`.
        *   `pyperclip.copy` called with `long_text`.
        *   `pyautogui.hotkey` called with `('ctrl', 'v')`.
        *   `pyautogui.write` NOT called directly with `long_text`.

*   **Test Case ID**: UT-TYPE-007
    *   **Description**: Type long text; `pyperclip` is NOT available; verify direct `pyautogui.write` is used.
    *   **Setup**:
        *   Mock `self.ensure_window_focused` to return `True`.
        *   Patch `pyperclip` global reference within the module to `None` for this test.
        *   Mock `pyautogui.write` to succeed.
        *   `long_text = "a" * 100`.
    *   **Action**: `await module.type_text(long_text)`.
    *   **Expected Outcome**:
        *   Returns `True`.
        *   `pyautogui.write` called with `long_text`.
        *   `pyperclip.copy` NOT called.

*   **Test Case ID**: UT-TYPE-008
    *   **Description**: `pyautogui.write` (or hotkey/press for clear/paste) raises `FailSafeException`.
    *   **Setup**:
        *   Mock `self.ensure_window_focused` to return `True`.
        *   Mock relevant `pyautogui` call (e.g., `write`) to raise `pyautogui.FailSafeException`.
    *   **Action**: `with pytest.raises(PyAutoGUIActionFailedError): await module.type_text("text")`.
    *   **Expected Outcome**: `PyAutoGUIActionFailedError` raised.

#### 2.6.2. `press_hotkey(self, *keys: str)`

*   **Test Case ID**: UT-HOTKEY-001
    *   **Description**: Successful hotkey press.
    *   **Setup**:
        *   Mock `self.ensure_window_focused` to return `True`.
        *   `mock_pyautogui_hotkey = MagicMock()`.
        *   Mock `self._run_blocking_io` to call `mock_pyautogui_hotkey`.
    *   **Action**: `result = await module.press_hotkey('ctrl', 'shift', 'esc')`.
    *   **Expected Outcome**:
        *   Returns `True`.
        *   `self.ensure_window_focused` called.
        *   `mock_pyautogui_hotkey` called with `('ctrl', 'shift', 'esc')`.

*   **Test Case ID**: UT-HOTKEY-002
    *   **Description**: `ensure_window_focused` fails.
    *   **Setup**: Mock `self.ensure_window_focused` to raise `WindowNotFoundError`.
    *   **Action**: `with pytest.raises(WindowNotFoundError): await module.press_hotkey('ctrl', 'c')`.
    *   **Expected Outcome**: `WindowNotFoundError` propagated.

*   **Test Case ID**: UT-HOTKEY-003
    *   **Description**: `pyautogui.hotkey` raises `FailSafeException`.
    *   **Setup**: Mock `pyautogui.hotkey` to raise `pyautogui.FailSafeException`.
    *   **Action**: `with pytest.raises(PyAutoGUIActionFailedError): await module.press_hotkey('ctrl', 'c')`.
    *   **Expected Outcome**: `PyAutoGUIActionFailedError` raised.

#### 2.6.3. `press_key(self, key: str)`

*   **Test Case ID**: UT-PRESSKEY-001
    *   **Description**: Successful single key press.
    *   **Setup**:
        *   Mock `self.ensure_window_focused` to return `True`.
        *   `mock_pyautogui_press = MagicMock()`.
        *   Mock `self._run_blocking_io` to call `mock_pyautogui_press`.
    *   **Action**: `result = await module.press_key('enter')`.
    *   **Expected Outcome**:
        *   Returns `True`.
        *   `self.ensure_window_focused` called.
        *   `mock_pyautogui_press` called with `'enter'`.

*   **Test Case ID**: UT-PRESSKEY-002
    *   **Description**: `ensure_window_focused` fails.
    *   **Setup**: Mock `self.ensure_window_focused` to raise `WindowNotFoundError`.
    *   **Action**: `with pytest.raises(WindowNotFoundError): await module.press_key('a')`.
    *   **Expected Outcome**: `WindowNotFoundError` propagated.

*   **Test Case ID**: UT-PRESSKEY-003
    *   **Description**: `pyautogui.press` raises `FailSafeException`.
    *   **Setup**: Mock `pyautogui.press` to raise `pyautogui.FailSafeException`.
    *   **Action**: `with pytest.raises(PyAutoGUIActionFailedError): await module.press_key('a')`.
    *   **Expected Outcome**: `PyAutoGUIActionFailedError` raised.

---
*Test cases for clipboard methods to be added next.*

### 2.7. Clipboard Methods (`get_clipboard_text`, `set_clipboard_text`)

**General Mocks for these tests (in addition to global mocks)**:
*   `self._run_blocking_io` (to control `pyperclip.copy` and `pyperclip.paste`)
*   Mock `pyperclip` module itself or its `copy` and `paste` functions.

#### 2.7.1. `get_clipboard_text(self)`

*   **Test Case ID**: UT-CLIP-GET-001
    *   **Description**: Successfully retrieve text from clipboard.
    *   **Setup**:
        *   Patch `pyperclip` to be available.
        *   Mock `pyperclip.paste` (via `_run_blocking_io`) to return "clipboard content".
    *   **Action**: `text = await module.get_clipboard_text()`.
    *   **Expected Outcome**: `text` is "clipboard content".

*   **Test Case ID**: UT-CLIP-GET-002
    *   **Description**: `pyperclip` is not available.
    *   **Setup**:
        *   Patch `pyperclip` global reference within the module to `None`.
    *   **Action**: `with pytest.raises(ClipboardError): await module.get_clipboard_text()`.
    *   **Expected Outcome**: `ClipboardError` raised with message about `pyperclip` being unavailable.

*   **Test Case ID**: UT-CLIP-GET-003
    *   **Description**: `pyperclip.paste` raises an unexpected exception.
    *   **Setup**:
        *   Patch `pyperclip` to be available.
        *   Mock `pyperclip.paste` (via `_run_blocking_io`) to raise `RuntimeError("Paste error")`.
    *   **Action**: `with pytest.raises(ClipboardError): await module.get_clipboard_text()`.
    *   **Expected Outcome**: `ClipboardError` raised, wrapping the original `RuntimeError`.

#### 2.7.2. `set_clipboard_text(self, text: str)`

*   **Test Case ID**: UT-CLIP-SET-001
    *   **Description**: Successfully set text to clipboard.
    *   **Setup**:
        *   Patch `pyperclip` to be available.
        *   `mock_pyperclip_copy = MagicMock()`.
        *   Mock `self._run_blocking_io` to call `mock_pyperclip_copy`.
        *   `text_to_set = "new clipboard text"`.
    *   **Action**: `result = await module.set_clipboard_text(text_to_set)`.
    *   **Expected Outcome**:
        *   Returns `True`.
        *   `mock_pyperclip_copy` called with `text_to_set`.

*   **Test Case ID**: UT-CLIP-SET-002
    *   **Description**: `pyperclip` is not available.
    *   **Setup**:
        *   Patch `pyperclip` global reference within the module to `None`.
    *   **Action**: `with pytest.raises(ClipboardError): await module.set_clipboard_text("text")`.
    *   **Expected Outcome**: `ClipboardError` raised with message about `pyperclip` being unavailable.

*   **Test Case ID**: UT-CLIP-SET-003
    *   **Description**: `pyperclip.copy` raises an unexpected exception.
    *   **Setup**:
        *   Patch `pyperclip` to be available.
        *   Mock `pyperclip.copy` (via `_run_blocking_io`) to raise `RuntimeError("Copy error")`.
    *   **Action**: `with pytest.raises(ClipboardError): await module.set_clipboard_text("text")`.
    *   **Expected Outcome**: `ClipboardError` raised, wrapping the original `RuntimeError`.

---
*Test cases for combined operations to be added next.*

### 2.8. Combined Operations Methods

#### 2.8.1. `find_type_and_enter(self, target_image_to_click: str, text_to_type: str, confidence: Optional[float], find_timeout: Optional[float], type_interval: Optional[float], clear_before_typing: bool, wait_for_readiness_image: Optional[str], readiness_timeout: Optional[float])`

**General Mocks for these tests (in addition to global mocks)**:
*   `self.ensure_window_focused`
*   `self.type_text`
*   `self.press_key`
*   `self.find_element_on_screen` (for readiness image)

*   **Test Case ID**: UT-FTE-001
    *   **Description**: Successful execution of the full `find_type_and_enter` sequence, including waiting for readiness image.
    *   **Setup**:
        *   Mock `self.ensure_window_focused` to return `True`.
        *   Mock `self.type_text` to return `True` when called with appropriate args (target image, text, clear flag).
        *   Mock `self.press_key` to return `True` when called with `'enter'`.
        *   Mock `self.find_element_on_screen` to return `(300,300)` when called for `wait_for_readiness_image`.
    *   **Action**: `result = await module.find_type_and_enter("target.png", "input text", wait_for_readiness_image="ready.png")`.
    *   **Expected Outcome**:
        *   Returns `True`.
        *   All mocked methods (`ensure_window_focused`, `type_text`, `press_key`, `find_element_on_screen` for readiness) called with expected parameters.

*   **Test Case ID**: UT-FTE-002
    *   **Description**: Successful execution without a `wait_for_readiness_image`.
    *   **Setup**:
        *   Mock `self.ensure_window_focused` to return `True`.
        *   Mock `self.type_text` to return `True`.
        *   Mock `self.press_key` to return `True`.
    *   **Action**: `result = await module.find_type_and_enter("target.png", "input text", wait_for_readiness_image=None)`.
    *   **Expected Outcome**:
        *   Returns `True`.
        *   `self.find_element_on_screen` is NOT called for readiness image.

*   **Test Case ID**: UT-FTE-003
    *   **Description**: `self.ensure_window_focused` fails.
    *   **Setup**: Mock `self.ensure_window_focused` to raise `WindowNotFoundError`.
    *   **Action**: `with pytest.raises(WindowNotFoundError): await module.find_type_and_enter("target.png", "text")`.
    *   **Expected Outcome**: `WindowNotFoundError` propagated.

*   **Test Case ID**: UT-FTE-004
    *   **Description**: `self.type_text` (which includes initial find and click) fails (e.g., returns `False` or raises `ImageNotFoundError`).
    *   **Setup**:
        *   Mock `self.ensure_window_focused` to return `True`.
        *   Mock `self.type_text` to raise `ImageNotFoundError`.
    *   **Action**: `with pytest.raises(ImageNotFoundError): await module.find_type_and_enter("target.png", "text")`.
    *   **Expected Outcome**: `ImageNotFoundError` (or other error from `type_text`) propagated.

*   **Test Case ID**: UT-FTE-005
    *   **Description**: `self.press_key('enter')` fails (e.g., raises `PyAutoGUIActionFailedError`).
    *   **Setup**:
        *   Mock `self.ensure_window_focused` to return `True`.
        *   Mock `self.type_text` to return `True`.
        *   Mock `self.press_key` to raise `PyAutoGUIActionFailedError`.
    *   **Action**: `with pytest.raises(PyAutoGUIActionFailedError): await module.find_type_and_enter("target.png", "text")`.
    *   **Expected Outcome**: `PyAutoGUIActionFailedError` propagated.

*   **Test Case ID**: UT-FTE-006
    *   **Description**: `wait_for_readiness_image` is specified, but `find_element_on_screen` for it fails (e.g., raises `ImageNotFoundError`).
    *   **Setup**:
        *   Mock `self.ensure_window_focused`, `self.type_text`, `self.press_key` to all succeed.
        *   Mock `self.find_element_on_screen` (for readiness) to raise `ImageNotFoundError`.
    *   **Action**: `with pytest.raises(ImageNotFoundError): await module.find_type_and_enter("target.png", "text", wait_for_readiness_image="ready.png")`.
    *   **Expected Outcome**: `ImageNotFoundError` (from readiness check) propagated.

---
*Test cases for find_click_select_all_copy to be added next.*

#### 2.8.2. `find_click_select_all_copy(self, anchor_image_to_click: str, confidence: Optional[float], find_timeout: Optional[float], click_offset: Tuple[int, int], clipboard_wait_timeout: Optional[float], clipboard_clear_wait: float)`

**General Mocks for these tests (in addition to global mocks)**:
*   `self.ensure_window_focused`
*   `self.find_element_on_screen` (for anchor image)
*   `self.click_element`
*   `self.get_clipboard_text`
*   `self.set_clipboard_text`
*   `self.press_hotkey`
*   `platform.system` (to test platform-specific hotkeys)
*   `time.monotonic` & `asyncio.sleep` for clipboard polling logic.

*   **Test Case ID**: UT-FCSAC-001
    *   **Description**: Successful execution of the full `find_click_select_all_copy` sequence.
    *   **Setup**:
        *   Mock `self.ensure_window_focused` to return `True`.
        *   Mock `self.find_element_on_screen` (for anchor) to return `(50, 50)`.
        *   Mock `self.click_element` to return `True`.
        *   Mock `self.get_clipboard_text` to initially return "initial_clipboard", then after copy, to return "new_copied_text".
        *   Mock `self.set_clipboard_text` to return `True`.
        *   Mock `self.press_hotkey` to return `True`.
        *   Mock `platform.system` to return (e.g.) "Windows".
    *   **Action**: `text = await module.find_click_select_all_copy("anchor.png")`.
    *   **Expected Outcome**:
        *   Returns "new_copied_text".
        *   All internal methods called in correct sequence with expected parameters (ensure_focused, find_element_on_screen, click_element, get_clipboard_text (initial), set_clipboard_text (clear), press_hotkey (select all), press_hotkey (copy), get_clipboard_text (polling)).

*   **Test Case ID**: UT-FCSAC-002
    *   **Description**: Failure: `ensure_window_focused` fails.
    *   **Setup**: Mock `self.ensure_window_focused` to raise `WindowNotFoundError`.
    *   **Action**: `with pytest.raises(WindowNotFoundError): await module.find_click_select_all_copy("anchor.png")`.
    *   **Expected Outcome**: `WindowNotFoundError` propagated.

*   **Test Case ID**: UT-FCSAC-003
    *   **Description**: Failure: `find_element_on_screen` for anchor image fails.
    *   **Setup**:
        *   Mock `self.ensure_window_focused` to return `True`.
        *   Mock `self.find_element_on_screen` to raise `ImageNotFoundError`.
    *   **Action**: `with pytest.raises(ImageNotFoundError): await module.find_click_select_all_copy("anchor.png")`.
    *   **Expected Outcome**: `ImageNotFoundError` propagated.

*   **Test Case ID**: UT-FCSAC-004
    *   **Description**: Failure: `click_element` after finding anchor fails.
    *   **Setup**:
        *   Mock `self.ensure_window_focused` to return `True`.
        *   Mock `self.find_element_on_screen` to return `(50, 50)`.
        *   Mock `self.click_element` to return `False` (or raise `PyAutoGUIActionFailedError`).
    *   **Action**: If `click_element` returns `False`, expect `None` from `find_click_select_all_copy` and error log. If `click_element` raises, expect propagation.
        *   `result = await module.find_click_select_all_copy("anchor.png")` -> `assert result is None`
        *   OR `with pytest.raises(PyAutoGUIActionFailedError): await module.find_click_select_all_copy("anchor.png")`
    *   **Expected Outcome**: As per action, either `None` returned or exception propagated.

*   **Test Case ID**: UT-FCSAC-005
    *   **Description**: Failure: `set_clipboard_text` (to clear clipboard) fails.
    *   **Setup**:
        *   Mocks for focus, find, click to succeed.
        *   Mock `self.get_clipboard_text` to return "initial".
        *   Mock `self.set_clipboard_text` to raise `ClipboardError`.
    *   **Action**: `with pytest.raises(ClipboardError): await module.find_click_select_all_copy("anchor.png")`.
    *   **Expected Outcome**: `ClipboardError` propagated.

*   **Test Case ID**: UT-FCSAC-006
    *   **Description**: Failure: `press_hotkey` for Select All or Copy fails.
    *   **Setup**:
        *   Mocks for focus, find, click, clipboard priming to succeed.
        *   Mock `self.press_hotkey` (for select all) to raise `PyAutoGUIActionFailedError`.
    *   **Action**: `with pytest.raises(PyAutoGUIActionFailedError): await module.find_click_select_all_copy("anchor.png")`.
    *   **Expected Outcome**: `PyAutoGUIActionFailedError` propagated.

*   **Test Case ID**: UT-FCSAC-007
    *   **Description**: Failure: Clipboard polling times out (content doesn't change).
    *   **Setup**:
        *   Mocks for focus, find, click, priming, hotkeys to succeed.
        *   Mock `self.get_clipboard_text` to consistently return "initial_clipboard" (or the cleared empty string) during polling.
        *   Mock `time.monotonic` to simulate timeout.
        *   Set `clipboard_wait_timeout` to a small value (e.g., 0.1s).
    *   **Action**: `with pytest.raises(InteractionTimeoutError): await module.find_click_select_all_copy("anchor.png", clipboard_wait_timeout=0.1)`.
    *   **Expected Outcome**: `InteractionTimeoutError` raised.

*   **Test Case ID**: UT-FCSAC-008
    *   **Description**: Verify platform-specific hotkeys (e.g., 'command' for macOS, 'ctrl' for Windows/Linux).
    *   **Setup**:
        *   Mocks for successful sequence up to hotkeys.
        *   `mock_press_hotkey = MagicMock(return_value=True)`.
        *   Assign `mock_press_hotkey` to `module.press_hotkey`.
    *   **Actions & Expected Outcomes**:
        *   1. Mock `platform.system` to return "Darwin". Call `await module.find_click_select_all_copy("anchor.png")`. Assert `mock_press_hotkey` called with `('command', 'a')` and `('command', 'c')`.
        *   2. Mock `platform.system` to return "Windows". Call `await module.find_click_select_all_copy("anchor.png")`. Assert `mock_press_hotkey` called with `('ctrl', 'a')` and `('ctrl', 'c')`.

---
*Test cases for capture_region to be added next.*

#### 2.8.3. `capture_region(self, region: Tuple[int, int, int, int], save_path: Optional[str])`

**General Mocks for these tests (in addition to global mocks)**:
*   `self.ensure_window_focused`
*   `self._run_blocking_io` (to control `pyautogui.screenshot` and `Image.save`)
*   `pyautogui.screenshot`
*   `PIL.Image.Image.save` (mock the `save` method of a mock Image object)
*   `Path` object methods (`is_absolute`, `exists`, `parent.mkdir`, `cwd`)
*   `self.app_config.paths.project_root`

*   **Test Case ID**: UT-CAPTURE-001
    *   **Description**: Successfully capture region, no save_path, returns PIL Image object.
    *   **Setup**:
        *   Mock `self.ensure_window_focused` to return `True`.
        *   `mock_pil_image = MagicMock()` (represents a PIL Image object).
        *   Mock `pyautogui.screenshot` (via `_run_blocking_io`) to return `mock_pil_image`.
        *   `valid_region = (0, 0, 100, 100)`.
    *   **Action**: `image_obj = await module.capture_region(region=valid_region)`.
    *   **Expected Outcome**:
        *   Returns `mock_pil_image`.
        *   `pyautogui.screenshot` called with `region=valid_region`.

*   **Test Case ID**: UT-CAPTURE-002
    *   **Description**: Successfully capture region and save to an absolute `save_path`.
    *   **Setup**:
        *   Mock `self.ensure_window_focused` to return `True`.
        *   `mock_pil_image = MagicMock()`
        *   Mock `pyautogui.screenshot` to return `mock_pil_image`.
        *   Mock `mock_pil_image.save` (via `_run_blocking_io` on the save call) to succeed.
        *   Mock `Path(abs_path).is_absolute()` to return `True`.
        *   Mock `Path(abs_path).parent.mkdir()`.
        *   `abs_save_path = "/tmp/capture.png"`.
    *   **Action**: `result_path = await module.capture_region(region=(0,0,10,10), save_path=abs_save_path)`.
    *   **Expected Outcome**:
        *   Returns `abs_save_path` (string).
        *   `mock_pil_image.save` called with `abs_save_path`.
        *   `mkdir` called to ensure parent directory exists.

*   **Test Case ID**: UT-CAPTURE-003
    *   **Description**: Successfully capture region and save to a relative `save_path` (resolved against project_root).
    *   **Setup**:
        *   Similar to UT-CAPTURE-002, but `save_path` is relative.
        *   `module.app_config.paths.project_root` is set to a mock `Path("/project")`.
        *   Mock `Path(rel_path).is_absolute()` to return `False`.
        *   `rel_save_path = "captures/test.png"`.
        *   `expected_full_path = "/project/captures/test.png"`.
    *   **Action**: `result_path = await module.capture_region(region=(0,0,10,10), save_path=rel_save_path)`.
    *   **Expected Outcome**:
        *   Returns `str(expected_full_path)`.
        *   `mock_pil_image.save` called with `str(expected_full_path)`.

*   **Test Case ID**: UT-CAPTURE-004
    *   **Description**: Invalid region format raises `ValueError`.
    *   **Setup**: `invalid_region = (0, 0, -10, 10)` or `(0,0,10)` or `"not a tuple"`.
    *   **Action**: `with pytest.raises(ValueError): await module.capture_region(region=invalid_region)`.
    *   **Expected Outcome**: `ValueError` raised.

*   **Test Case ID**: UT-CAPTURE-005
    *   **Description**: `ensure_window_focused` fails.
    *   **Setup**: Mock `self.ensure_window_focused` to raise `WindowNotFoundError`.
    *   **Action**: `with pytest.raises(WindowNotFoundError): await module.capture_region(region=(0,0,10,10))`.
    *   **Expected Outcome**: `WindowNotFoundError` propagated.

*   **Test Case ID**: UT-CAPTURE-006
    *   **Description**: `pyautogui.screenshot` raises `FailSafeException`.
    *   **Setup**:
        *   Mock `self.ensure_window_focused` to return `True`.
        *   Mock `pyautogui.screenshot` to raise `pyautogui.FailSafeException`.
    *   **Action**: `with pytest.raises(PyAutoGUIActionFailedError): await module.capture_region(region=(0,0,10,10))`.
    *   **Expected Outcome**: `PyAutoGUIActionFailedError` raised.

*   **Test Case ID**: UT-CAPTURE-007
    *   **Description**: Saving the image file fails (e.g., `mock_pil_image.save` raises `IOError`).
    *   **Setup**:
        *   Mocks for focus and successful `pyautogui.screenshot` returning `mock_pil_image`.
        *   Mock `mock_pil_image.save` to raise `IOError("Disk full")`.
    *   **Action**: `with pytest.raises(IOError): await module.capture_region(region=(0,0,10,10), save_path="test.png")`.
    *   **Expected Outcome**: `IOError` raised (the one from `save`, not wrapped further by this method ideally, or consistently wrapped if that's the pattern).

*   **Test Case ID**: UT-CAPTURE-008
    *   **Description**: Relative `save_path` provided, but `project_root` is not available in `AppConfig` (fallback to CWD for save path).
    *   **Setup**:
        *   Mocks for successful capture.
        *   Set `module.app_config.paths.project_root = None`.
        *   Mock `Path.cwd()` to return a mock path (e.g., `Path("/current/dir")`).
        *   `rel_save_path = "captures/fallback.png"`.
        *   `expected_fallback_path = "/current/dir/captures/fallback.png"`.
    *   **Action**: `result_path = await module.capture_region(region=(0,0,10,10), save_path=rel_save_path)`.
    *   **Expected Outcome**:
        *   Returns `str(expected_fallback_path)`.
        *   Warning log about `project_root` not found and using CWD.
        *   `mock_pil_image.save` called with `str(expected_fallback_path)`.

---
*End of Unit Test Cases for PyAutoGUIControlModule.*
## 3. Integration Test Cases (Placeholders)
*To be detailed later, focusing on interaction with a mock GUI or virtual display, as per API proposal Section 10.* 

## 4. Manual / Semi-Automated Test Scenarios (Placeholders)
*To be detailed later, for testing against a live ChatGPT web interface.* 