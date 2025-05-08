# automation_interface.py
# This module will define the interface for other agents or system components
# to request and control automation routines.

from typing import Any, Dict, Literal, Optional

import pyautogui  # For catching pyautogui specific exceptions

# Import functions from gui_controller
from .gui_controller import click as gui_click
from .gui_controller import drag_to as gui_drag_to
from .gui_controller import (
    get_screenshot as gui_get_screenshot,  # Renamed to avoid conflict if we had a local take_screenshot
)
from .gui_controller import hotkey as gui_hotkey
from .gui_controller import locate_on_screen as gui_locate_on_screen
from .gui_controller import move_to as gui_move_to
from .gui_controller import press_key as gui_press_key
from .gui_controller import type_text as gui_type_text
from .gui_controller import wait_for_element as gui_wait_for_element

# Potential action names - could be expanded or dynamically loaded
ActionName = Literal[
    "click",
    "type_text",
    "press_key",
    "hotkey",
    "move_to",
    "drag_to",
    "locate_on_screen",
    "wait_for_element",
    "get_screenshot",
    # Add more high-level or complex actions here
]


class AutomationResult:
    """Represents the result of an automation action."""

    def __init__(self, success: bool, message: str = "", data: Any = None):
        self.success = success
        self.message = message
        self.data = data  # To store return values like coordinates or file paths

    def __repr__(self):
        return f"AutomationResult(success={self.success}, message='{self.message}', data={self.data})"


def trigger_action(
    action_name: ActionName, params: Optional[Dict[str, Any]] = None
) -> AutomationResult:
    """High-level interface to trigger a GUI automation action.

    Supported Actions:
        - 'click': Performs a mouse click.
            Params: {'x': int, 'y': int, 'button': str, 'clicks': int, 'interval': float} (x, y optional)
        - 'type_text': Types the given text string.
            Params: {'text': str, 'interval': float}
        - 'press_key': Presses a single key or a sequence of keys.
            Params: {'key': str | list[str]}
        - 'hotkey': Simulates pressing a key combination.
            Params: {'keys': list[str]} (e.g., ['ctrl', 'c'])
        - 'move_to': Moves the mouse cursor.
            Params: {'x': int, 'y': int, 'duration': float}
        - 'drag_to': Drags the mouse cursor.
            Params: {'x': int, 'y': int, 'duration': float, 'button': str}
        - 'locate_on_screen': Locates an image on the screen.
            Params: {'image_path': str, 'confidence': float, 'grayscale': bool}
            Returns: Tuple (left, top, width, height) or None in AutomationResult.data.
        - 'wait_for_element': Waits for an image to appear on screen.
            Params: {'image_path': str, 'timeout': int, 'confidence': float}
            Returns: Tuple (left, top, width, height) or None in AutomationResult.data.
        - 'get_screenshot': Takes a screenshot.
            Params: {'region': tuple | None} (e.g., (0,0,100,100))
            Returns: File path string to the saved screenshot in AutomationResult.data.

    Args:
        action_name: The name of the action to perform.
        params: A dictionary of parameters specific to the action.

    Returns:
        An AutomationResult object indicating success/failure and any relevant data.
    """
    if params is None:
        params = {}

    print(
        f"Automation Interface: Received request for action '{action_name}' with params: {params}"
    )

    result_data: Any = None
    success: bool = False
    message: str = ""

    try:
        if action_name == "click":
            gui_click(**params)
            message = f"Action '{action_name}' executed successfully."
            success = True
        elif action_name == "type_text":
            gui_type_text(**params)
            message = f"Action '{action_name}' executed successfully."
            success = True
        elif action_name == "press_key":
            gui_press_key(**params)  # gui_press_key expects 'key' as a param
            message = f"Action '{action_name}' executed successfully."
            success = True
        elif action_name == "hotkey":
            # gui_hotkey expects keys as *args, so we need to unpack the list from params
            if "keys" in params and isinstance(params["keys"], list):
                gui_hotkey(*params["keys"])
                message = f"Action '{action_name}' executed successfully."
                success = True
            else:
                message = "Error: 'hotkey' action requires a 'keys' parameter as a list of strings."
                success = False
        elif action_name == "move_to":
            gui_move_to(**params)
            message = f"Action '{action_name}' executed successfully."
            success = True
        elif action_name == "drag_to":
            gui_drag_to(**params)
            message = f"Action '{action_name}' executed successfully."
            success = True
        elif action_name == "locate_on_screen":
            result_data = gui_locate_on_screen(**params)
            if result_data:
                message = (
                    f"Action '{action_name}' executed successfully. Element found."
                )
            else:
                message = (
                    f"Action '{action_name}' executed successfully. Element not found."
                )
            success = True  # Action itself succeeded even if element not found
        elif action_name == "wait_for_element":
            result_data = gui_wait_for_element(**params)
            if result_data:
                message = (
                    f"Action '{action_name}' executed successfully. Element found."
                )
            else:
                message = f"Action '{action_name}' executed successfully. Element not found within timeout."
            success = True  # Action itself succeeded
        elif action_name == "get_screenshot":
            result_data = gui_get_screenshot(**params)
            message = f"Action '{action_name}' executed successfully. Screenshot saved to: {result_data}"
            success = True
        else:
            message = f"Error: Action '{action_name}' not implemented in interface."
            success = False
            # Early return for unimplemented actions
            return AutomationResult(success=success, message=message, data=result_data)

        return AutomationResult(success=success, message=message, data=result_data)

    except pyautogui.FailSafeException as e:
        message = f"FailSafe triggered during action '{action_name}': {e}"
        print(f"Error: {message}")
        return AutomationResult(success=False, message=message, data=None)
    except (
        pyautogui.ImageNotFoundException
    ) as e:  # Specifically for locate_on_screen if not handled by it
        message = f"ImageNotFoundException during action '{action_name}': {e}"
        print(f"Error: {message}")
        # Typically, locate_on_screen in gui_controller should return None, not raise this
        # But if it could, we catch it here.
        return AutomationResult(
            success=True, message=message, data=None
        )  # Action succeeded, element not found
    except TypeError as e:  # Catching potential errors from incorrect params
        message = f"TypeError during action '{action_name}': {e}. Check parameters."
        print(f"Error: {message}")
        return AutomationResult(success=False, message=message, data=None)
    except Exception as e:
        message = f"An unexpected error occurred during action '{action_name}': {e}"
        print(f"Error: {message}")
        return AutomationResult(success=False, message=message, data=None)


# Example Usage (for testing - ensure gui_controller.py has non-commented pyautogui calls for real test):
if __name__ == "__main__":
    print("--- Testing Automation Interface ---")
    # Note: These tests will primarily print simulation messages unless
    # the pyautogui calls in gui_controller.py are uncommented and pyautogui is fully functional.

    res_click = trigger_action("click", params={"x": 150, "y": 300, "button": "left"})
    print(f"Click Result: {res_click}")

    res_type = trigger_action(
        "type_text", params={"text": "Hello from automation interface!"}
    )
    print(f"Type Text Result: {res_type}")

    res_press = trigger_action("press_key", params={"key": "enter"})
    print(f"Press Key Result: {res_press}")

    res_hotkey = trigger_action("hotkey", params={"keys": ["ctrl", "alt", "delete"]})
    print(f"Hotkey Result: {res_hotkey}")

    res_locate_fail = trigger_action(
        "locate_on_screen", params={"image_path": "non_existent_image.png"}
    )
    print(f"Locate (Fail) Result: {res_locate_fail}")

    # To test locate_on_screen success, you'd need a valid image and uncomment pyautogui in gui_controller
    # res_locate_success = trigger_action('locate_on_screen', params={'image_path': 'path/to/your/test_image.png'})
    # print(f"Locate (Success Test - needs image): {res_locate_success}")

    res_screenshot = trigger_action("get_screenshot")
    print(f"Screenshot Result: {res_screenshot}")

    res_wait_fail = trigger_action(
        "wait_for_element",
        params={"image_path": "non_existent_image.png", "timeout": 1},
    )
    print(f"Wait for Element (Fail) Result: {res_wait_fail}")

    res_invalid_action = trigger_action("fly_to_moon")  # type: ignore
    print(f"Invalid Action Result: {res_invalid_action}")

    print("--- Testing Finished ---")

# TODO: Propose an interface for calling automation routines (This comment seems outdated from previous steps)

# from .gui_controller import GUIController  # Assuming pyautogui or similar is managed here
# from .task_trigger import TaskTrigger # If triggers also part of this interface


class AutomationInterface:
    """
    Provides a high-level API for defining and executing automation sequences.
    It orchestrates calls to GUIController, TaskTrigger, and potentially other
    automation-related modules.
    """

    def __init__(self):
        # self.gui = GUIController()
        # self.trigger_manager = TaskTrigger()
        print(
            "AutomationInterface initialized. (GUIController and TaskTrigger would be instantiated here)"
        )
        # TODO: Initialize GUIController, TaskTrigger, and other necessary components

    def execute_task(self, task_name: str, task_parameters: dict):
        """
        Executes a predefined automation task by its name.
        Task definitions could be loaded from a configuration file or database.
        """
        print(f"Attempting to execute task: {task_name} with params: {task_parameters}")
        # TODO: Implement task lookup and execution logic
        # Example:
        # if task_name == "login_sequence":
        #     self.gui.type_text(task_parameters.get('username'), element_identifier='username_field')
        #     self.gui.type_text(task_parameters.get('password'), element_identifier='password_field')
        #     self.gui.click_element('login_button')
        # else:
        #     print(f"Error: Task '{task_name}' not recognized.")
        pass

    def run_sequence(self, steps: list):
        """
        Runs a dynamic sequence of automation steps.
        Each step in the list could be a dictionary defining the action and parameters.
        Example step: {'action': 'click', 'target': 'button_id'}
                      {'action': 'type', 'text': 'hello', 'target': 'input_field'}
        """
        print(f"Attempting to run automation sequence with {len(steps)} steps.")
        for i, step in enumerate(steps):
            print(f"Executing step {i+1}: {step.get('action')}")
            action = step.get("action")
            target = step.get(
                "target"
            )  # Element identifier, coordinates, image path etc.
            value = step.get("value")  # Text to type, option to select etc.

            # TODO: Expand with actual calls to GUIController methods
            # if action == 'click':
            #     self.gui.click_element(target)
            # elif action == 'type':
            #     self.gui.type_text(value, element_identifier=target)
            # elif action == 'wait': # Example of a non-GUI action
            #     time.sleep(value) # Requires `import time`
            # else:
            #     print(f"Warning: Unknown action '{action}' in sequence.")
        print("Automation sequence finished.")
        pass

    def register_automation_trigger(
        self, trigger_name, trigger_type, config, task_to_run, task_params
    ):
        """
        Registers a trigger that, when activated, runs a specified automation task.
        """
        print(f"Registering trigger '{trigger_name}' to run task '{task_to_run}'")
        # def callback_function(): # Define the callback for the trigger
        #     self.execute_task(task_to_run, task_params)
        # self.trigger_manager.register_trigger(trigger_name, trigger_type, config, callback_function)
        # TODO: Implement actual trigger registration with TaskTrigger
        pass

    # TODO: Add methods for managing automation state, reporting, error handling etc.
