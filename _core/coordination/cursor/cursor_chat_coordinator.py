# _core coordination cursor ChatCoordinator stub for testing
import re

class CursorChatCoordinator:
    def __init__(self, instance_controller, bridge_adapter, state_machine, agent_bus_instance):
        self.instance_controller = instance_controller
        self.bridge_adapter = bridge_adapter
        self.state_machine = state_machine
        self.agent_bus = agent_bus_instance
        self.instance_states = {}

    def interpret_response(self, chat_text):
        # Return action based on chat_text patterns
        if not chat_text or chat_text.isspace():
            return None
        # Detect Python code block
        match = re.search(r"```python\n?(.*?)```", chat_text, re.DOTALL)
        if match:
            code = match.group(1).strip()
            return {"action": "save_file", "params": {"path": "file.py", "content": code}}
        # Detect accept/apply prompt
        text_lower = chat_text.lower()
        if "accept" in text_lower:
            return {"action": "execute_cursor_goal", "goal": {"type": "apply_changes"}}
        # Detect task complete signal
        if "task complete" in text_lower:
            return {"action": "task_complete"}
        return None 