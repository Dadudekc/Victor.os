# dreamos/automation/gui_interaction.py

class CursorInjector:
    def __init__(self, agent_id=None):
        self.agent_id = agent_id

    def inject_prompt(self, prompt):
        print(f"[Stub] Injecting prompt for {self.agent_id}: {prompt}")
        return True  # Simulate success

    def verify_injection(self):
        return True

    def reset(self):
        pass 