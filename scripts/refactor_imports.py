#!/usr/bin/env python3
"""
scripts/refactor_imports.py

Searches through all .py files (excluding virtual envs and src/dreamos) and replaces import statements
for core modules with the new dreamos namespace.
"""
import re
from pathlib import Path

# Patterns to replace: (regex, replacement)
REPLACEMENTS = [
    (r"^from\s+config\s+import", "from dreamos.config import"),
    (r"^import\s+config", "import dreamos.config as config"),
    (r"^from\s+cursor_interface\s+import", "from dreamos.cursor_interface import"),
    (r"^import\s+cursor_interface", "import dreamos.cursor_interface as cursor_interface"),
    (r"^from\s+chatgpt_interface\s+import", "from dreamos.chatgpt_interface import"),
    (r"^import\s+chatgpt_interface", "import dreamos.chatgpt_interface as chatgpt_interface"),
    (r"^from\s+evaluator\s+import", "from dreamos.evaluator import"),
    (r"^import\s+evaluator", "import dreamos.evaluator as evaluator"),
    (r"^from\s+orchestrator\s+import", "from dreamos.orchestrator import"),
    (r"^import\s+orchestrator", "import dreamos.orchestrator as orchestrator"),
    (r"^from\s+agent_utils\s+import", "from dreamos.agent_utils import"),
    (r"^import\s+agent_utils", "import dreamos.agent_utils as agent_utils"),
    (r"^from\s+dream_mode\.local_blob_channel\s+import", "from dreamos.memory.blob_channel_memory import"),
    (r"^import\s+dream_mode\.local_blob_channel", "import dreamos.memory.blob_channel_memory as LocalBlobChannel"),
    (r"^from\s+dream_mode\.azure_blob_channel\s+import", "from dreamos.memory.azure_blob_channel_memory import"),
    (r"^import\s+dream_mode\.azure_blob_channel", "import dreamos.memory.azure_blob_channel_memory as AzureBlobChannel"),
    (r"^from\s+dreamos\.chat_engine\.feedback_engine\s+import", "from dreamos.feedback.feedback_engine import"),
    (r"^import\s+dreamos\.chat_engine\.feedback_engine", "import dreamos.feedback.feedback_engine as FeedbackEngine"),
    (r"^from\s+dreamos\.chat_engine\.feedback_engine_v2\s+import", "from dreamos.feedback.feedback_engine_v2 import"),
    (r"^import\s+dreamos\.chat_engine\.feedback_engine_v2", "import dreamos.feedback.feedback_engine_v2 as FeedbackEngineV2"),
    (r"^from\s+dream_os\\.services\\.task_nexus", "from dream_os.services.task_nexus import"),
]

EXCLUDE_DIRS = {".git", "__pycache__", "src/dreamos", "venv", "env"}

if __name__ == "__main__":
    for path in Path('.').rglob('*.py'):
        # skip excluded dirs
        if any(part in EXCLUDE_DIRS for part in path.parts):
            continue
        text = path.read_text(encoding='utf-8')
        new_text = text
        for pattern, repl in REPLACEMENTS:
            new_text = re.sub(pattern, repl, new_text, flags=re.MULTILINE)
        if new_text != text:
            print(f"Updating imports in {path}")
            path.write_text(new_text, encoding='utf-8') 
