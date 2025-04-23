import os
import time
import json
import re
from pathlib import Path
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from core.browser.unified_driver_manager import UnifiedDriverManager
from dream_mode.task_nexus.task_nexus import TaskNexus

CHAT_URL = "https://chat.openai.com"
TASK_OUTPUT_PATH = Path(".cursor/queued_tasks/from_thea.json")

THEA_DIRECTIVE_TEMPLATE = """
You are Thea, the Dream Architect.

Given a directive, output the following:
1. A summary of the request.
2. A task.json file in raw JSON format that contains:
  - task_id
  - prompt_template
  - target_files
  - autotest (bool)
  - level (base, optimized, experimental)
3. Levels of improvement if applicable.

Directive:
---
{directive}
---
Respond only with JSON or a markdown JSON block. No extra commentary.
"""

class TheaOrchestrator:
    def __init__(self, directive: str):
        self.directive = directive
        self.driver = UnifiedDriverManager().get_driver()
        self.nexus = TaskNexus()

    def dispatch_directive(self) -> bool:
        self.driver.get(CHAT_URL)
        time.sleep(10)  # Let ChatGPT load completely
        try:
            textarea = self.driver.find_element(By.TAG_NAME, "textarea")
            textarea.clear()
            textarea.send_keys(THEA_DIRECTIVE_TEMPLATE.format(directive=self.directive))
            textarea.send_keys(Keys.ENTER)
        except Exception as e:
            print(f"[ERROR] Failed to send directive: {e}")
            return False
        return True

    def extract_json_from_response(self) -> str | None:
        time.sleep(15)  # Wait for ChatGPT to reply
        messages = self.driver.find_elements(By.CLASS_NAME, "markdown")
        if not messages:
            print("[THEA] No messages found.")
            return None
        last_message = messages[-1].text
        match = re.search(r"```json\n(.*?)```", last_message, re.DOTALL)
        if match:
            return match.group(1)
        if last_message.strip().startswith("{") and last_message.strip().endswith("}"):
            return last_message.strip()
        print("[THEA] Could not extract JSON from message.")
        return None

    def run(self):
        if not self.dispatch_directive():
            return
        result = self.extract_json_from_response()
        if result:
            parsed = json.loads(result)
            # Inject into TaskNexus for centralized tracking
            self.nexus.add_task(parsed)
            # Backup to file
            TASK_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
            TASK_OUTPUT_PATH.write_text(json.dumps(parsed, indent=2))
            print(f"[THEA] Task written to {TASK_OUTPUT_PATH}")
        else:
            print("[THEA] Failed to parse JSON.")
        self.driver.quit()

    def run_loop(self, poll_interval: int = 60):
        """
        Continuously dispatch directives and add resulting tasks to Nexus at intervals.
        """
        try:
            while True:
                if not self.dispatch_directive():
                    break
                result = self.extract_json_from_response()
                if result:
                    parsed = json.loads(result)
                    # Inject into TaskNexus for centralized tracking
                    self.nexus.add_task(parsed)
                    # Backup to file
                    TASK_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
                    TASK_OUTPUT_PATH.write_text(json.dumps(parsed, indent=2))
                    print(f"[THEA] Task written to {TASK_OUTPUT_PATH}")
                else:
                    print("[THEA] Failed to parse JSON.")
                time.sleep(poll_interval)
        finally:
            self.driver.quit()

    def list_history(self) -> list[dict]:
        """
        Return all tasks from runtime TaskNexus.
        """
        return self.nexus.get_all_tasks()

# 🔁 Entry point for standalone use
if __name__ == "__main__":
    while True:
        directive = input("🧠 Enter your directive for Thea (or 'exit' to quit): ")
        if directive.lower() in ('exit', 'quit'):
            break
        orchestrator = TheaOrchestrator(directive)
        orchestrator.run_loop() 