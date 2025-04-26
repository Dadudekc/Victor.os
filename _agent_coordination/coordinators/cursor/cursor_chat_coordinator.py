# Stub CursorChatCoordinator for tests
documentation = """Stub module for CursorChatCoordinator to satisfy tests."""
import re

class CursorChatCoordinator:
    """Stub coordinator for cursor chat tasks."""

    def __init__(self, instance_controller, bridge_adapter, state_machine, agent_bus_instance):
        # Store dependencies for signature compatibility
        self.instance_controller = instance_controller
        self.bridge_adapter = bridge_adapter
        self.state_machine = state_machine
        self.agent_bus = agent_bus_instance
        self.instance_states = {}

    def interpret_response(self, response: str):
        """Interpret the cursor response and return an action dict or None."""
        # 1. Save file from Python code block
        match = re.search(r"```python\n(.+?)\n```", response, re.DOTALL)
        if match:
            code = match.group(1)
            return {"action": "save_file", "params": {"path": None, "content": code}}
        # 2. Execute changes when prompt accepted
        if "Click Accept" in response:
            return {"action": "execute_cursor_goal", "goal": {"type": "apply_changes"}}
        # 3. Task complete signal
        if "Task complete" in response:
            return {"action": "task_complete"}
        # No actionable response
        return None 
