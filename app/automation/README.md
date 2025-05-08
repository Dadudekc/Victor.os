# App Automation Module

This module (`app/automation/`) is responsible for managing and executing GUI-based automation tasks within the Dream.os project.

## Scope & Vision:

The primary goal of this module is to provide a robust framework for automating interactions with graphical user interfaces. This includes, but is not limited to:
- Interacting with desktop applications.
- Automating web browser tasks (potentially in conjunction with browser-specific tools if PyAutoGUI is insufficient).
- Scripting repetitive UI-based workflows.

**Integration Vision:**
- **Agent-Driven:** Automation sequences will primarily be defined and triggered by autonomous agents based on tasks derived from `specs/current_plan.md` or `specs/mission_status.md`.
- **Task-Oriented:** The `AutomationInterface` will expose high-level functions for agents to request specific automated tasks (e.g., "login_to_platform_x", "extract_data_from_app_y").
- **Event-Triggered:** The `TaskTrigger` component will allow automations to be initiated by system events, schedules, or messages from other parts of the Dream.os system (e.g., via AgentBus).
- **Human-in-the-Loop:** While the goal is full automation, the system should allow for easy intervention, monitoring, and manual triggering of tasks if needed.
- **Configurable & Extensible:** Automation scripts and element locators should be configurable to adapt to UI changes. The module should be extensible to support new automation libraries or techniques.

## Key Components:

- **`gui_controller.py`**: 
    - Contains low-level functions for direct GUI manipulation (mouse clicks, keyboard input, image recognition) primarily using `pyautogui` or a similar library.
    - Provides an abstraction layer over the chosen GUI automation tool.

- **`task_trigger.py`**: 
    - Responsible for listening to various triggers (e.g., message queues, scheduled events, file system changes) that can initiate automation tasks.
    - Will invoke the `AutomationInterface` to execute the relevant automation sequence when a trigger condition is met.

- **`automation_interface.py`**: 
    - The main entry point for agents or other system components to request and manage automation tasks.
    - Orchestrates the `GUIController` and `TaskTrigger` to execute complex automation workflows.
    - Manages the state of ongoing automations and provides feedback.

## Future Considerations / TODOs:

- Implement robust error handling and recovery mechanisms for automation failures.
- Develop a standardized way to define and store automation task sequences (e.g., JSON, YAML configuration files).
- Integrate logging for all automation activities for debugging and auditing.
- Explore visual debugging tools for automation development.
- Consider security implications, especially when handling sensitive data via GUI automation.
- Add capabilities for OCR if text extraction from images becomes a common need.

## Modules

*   `gui_automation.py`: Core functions for executing GUI actions.
*   `automation_interface.py`: Defines the interface for automation tasks (TBD).
*   `gui_controller.py`: Higher-level control logic for GUI sequences (TBD).
*   `task_trigger.py`: Listens for automation triggers (TBD).

## `gui_automation.py`

Provides the `execute_gui_action` function to interact with the GUI.

### `execute_gui_action(action_name, target=None, text=None, **kwargs)`

Executes a specific PyAutoGUI action based on the provided parameters.

**Parameters:**

*   `action_name` (str): The action to perform (case-insensitive). See table below.
*   `target` (any, optional): The primary target (e.g., coordinates `(x, y)`, image path `str`, screenshot save path `str`). Usage depends on `action_name`.
*   `text` (str, optional): The text string for the `'type'` action.
*   `**kwargs`: Additional keyword arguments passed directly to the underlying PyAutoGUI function (e.g., `duration`, `button`, `interval`, `confidence`, `region`).

**Supported Actions:**

| `action_name` | PyAutoGUI Function(s)         | `target` Usage                       | `text` Usage      | Key `kwargs` Examples                     |
|---------------|-------------------------------|--------------------------------------|-------------------|-------------------------------------------|
| `click`       | `pyautogui.click()`           | `(x, y)` coordinates or `None`       | N/A               | `button`, `clicks`, `interval`, `duration` |
| `type`        | `pyautogui.typewrite()`       | N/A                                  | Text to type      | `interval`                                |
| `move`        | `pyautogui.moveTo()`          | `(x, y)` coordinates                 | N/A               | `duration`                                |
| `locate`      | `pyautogui.locateOnScreen()`  | Image file path (`str`)              | N/A               | `confidence`, `grayscale`, `region`       |
| `screenshot`  | `pyautogui.screenshot()`, `.save()` | Save file path (`str`, optional)     | N/A               | `region`                                  |

**Returns:**

*   `click`, `type`, `move`: `True` on success.
*   `locate`: PyAutoGUI `Box` object `(left, top, width, height)` if found, else `None`.
*   `screenshot`: Path (`str`) to the saved image file.

**Raises:**

*   `GuiActionError`: For unsupported actions, PyAutoGUI failsafe triggers, image not found, or other execution errors.
*   `ValueError`: For invalid or missing arguments (`target`, `text`).

**Usage Example:**

```python
from app.automation.gui_automation import execute_gui_action, GuiActionError

try:
    # Move mouse to top-left corner
    execute_gui_action('move', target=(0, 0), duration=1)

    # Click the center of the screen
    import pyautogui
    width, height = pyautogui.size()
    execute_gui_action('click', target=(width // 2, height // 2))

    # Type into an active field
    execute_gui_action('type', text='Automated input!\n', interval=0.1)

    # Find an image and click its center
    # image_loc = execute_gui_action('locate', target='images/button.png', confidence=0.9)
    # if image_loc:
    #     button_center = pyautogui.center(image_loc)
    #     execute_gui_action('click', target=button_center)
    # else:
    #     print("Button image not found.")

    # Take a screenshot
    screenshot_path = execute_gui_action('screenshot', target='output/my_screenshot.png')
    print(f"Screenshot saved to: {screenshot_path}")

except GuiActionError as e:
    print(f"GUI Action Failed: {e}")
except ValueError as e:
    print(f"Invalid Argument: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")

```

## Purpose

- To provide a centralized location for all GUI automation scripts.
- To define standards and best practices for creating robust and maintainable automation tasks.

## Key Modules

- `gui_automation.py`: The primary module containing core functions for GUI interaction, task execution logic, and integration points with the wider agent swarm.
- `(Other modules)`: As automation tasks grow in complexity, consider creating separate modules for specific applications or workflows (e.g., `web_browser_automation.py`, `specific_app_automation.py`).

## Best Practices & Protocols

1.  **Modularity**: Encapsulate distinct automation tasks within their own functions or classes.
2.  **Configuration Management**: 
    - **AVOID HARDCODING**: Do not hardcode coordinates, timings, application paths, or other parameters directly in the scripts.
    - **Use Configuration Files**: Store parameters in external files (e.g., `config/automation_config.yaml` or `.env` files) loaded by a central configuration module (e.g., in `core/config.py`).
    - **Environment Variables**: Utilize environment variables for sensitive data or deployment-specific settings.
3.  **Error Handling**: 
    - Implement `try...except` blocks generously around `pyautogui` calls.
    - Specifically catch `pyautogui.FailSafeException`.
    - Handle potential errors like elements not found, unexpected popups, or application crashes gracefully.
    - Use detailed logging (see below) to report errors.
4.  **Logging**: 
    - Implement comprehensive logging using Python's `logging` module.
    - Log key steps, decisions, successes, and failures.
    - Include timestamps and severity levels.
5.  **Dependencies**: 
    - Clearly list all dependencies (Python version, `pyautogui` version, etc.) in the main project `requirements.txt` or `pyproject.toml`.
    - Document any OS-level dependencies (e.g., specific libraries needed for screenshots or GUI interaction on Linux).
6.  **Readability**: Write clear, well-commented code. Use meaningful variable and function names.
7.  **Coordination / Swarm Integration**: (Further defined in `DEV-003`)
    - Scripts should be designed to be triggered by external events or commands (e.g., via a message queue, API call, or direct function call from a coordinating agent).
    - Provide mechanisms to report status (e.g., `IN_PROGRESS`, `COMPLETED`, `FAILED`) and results back to the triggering system.
    - Use task IDs for tracking and correlation.
8.  **Timing and Waits**: 
    - Avoid fixed `time.sleep()` calls where possible.
    - Prefer waiting for specific visual cues (e.g., an image appearing on screen using `pyautogui.locateOnScreen`) or application states before proceeding.
    - Use reasonable default timeouts for waits.

## Getting Started

- Ensure `pyautogui` and its dependencies are installed (`pip install pyautogui`).
- Review the configuration loading mechanism used in the project.
- Add new automation functions to `gui_automation.py` or create new modules as needed, following the protocols above. 