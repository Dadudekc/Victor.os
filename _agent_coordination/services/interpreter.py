from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import re
import uuid
import logging
from ..core.config import CursorCoordinatorConfig

logger = logging.getLogger("DefaultResponseInterpreter")

class ResponseInterpreter(ABC):
    """
    Service responsible for parsing chat response text into structured actions.
    """
    @abstractmethod
    def parse(
        self,
        chat_text: str,
        task_context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Parse the given chat response segment and return an action dict or None.

        Args:
            chat_text: The new chat text segment obtained via OCR.
            task_context: Optional context from the original task for parsing refinement.

        Returns:
            A dict with keys like 'action', 'params', and/or 'goal', or None if no action.
        """
        ...

class DefaultResponseInterpreter(ResponseInterpreter):
    """
    Parses chat response segments into actionable dictionaries
    for the CursorChatCoordinator.
    """
    def __init__(self, config: CursorCoordinatorConfig):
        self.config = config
        # Precompile regex patterns for performance
        self.python_pattern = re.compile(r"```python\s*(.*?)```", re.DOTALL)
        self.diff_pattern = re.compile(r"```diff\s*(.*?)```", re.DOTALL)
        self.generic_pattern = re.compile(r"```(?:\w*\s*)?(.*?)```", re.DOTALL)
        self.file_path_re = re.compile(
            r"(?:save to|in|path:|file:)\s*[`\"]?([\w\.\-/\\\s]+(?:\.[A-Za-z0-9]+)?)[`\"]?",
            re.IGNORECASE,
        )
        # Keyword sets
        self.accept_kw = {"click accept","apply changes","apply the diff","accept this","use this suggestion"}
        self.complete_kw = {"task complete","finished successfully","all done","applied successfully","code saved","refactoring complete","tests generated"}
        self.error_kw = {"error occurred","failed to","unable to proceed","encountered an issue","cannot apply","syntax error"}
        self.clarify_kw = {"which file","specify the path","need more details","ambiguous request"}

    def parse(
        self,
        chat_text: str,
        task_context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        text = chat_text or ""
        lower = text.lower()
        logger.debug("Parsing response text of length %d", len(text))

        # 1. Error detection
        if any(kw in lower for kw in self.error_kw):
            logger.warning("Interpreted ERROR signal.")
            return {"action": "error_detected", "params": {"message": text}}

        # 2. Accept/apply commands
        if any(kw in lower for kw in self.accept_kw):
            logger.info("Interpreted accept/apply command.")
            return {"action": "execute_cursor_goal", "goal": {"type": "apply_changes"}}

        # 3. Code block extraction
        match = self.python_pattern.search(text) or self.diff_pattern.search(text) or self.generic_pattern.search(text)
        if match:
            code_content = match.group(1).strip()
            # Determine code type
            if self.python_pattern.search(text):
                code_type = "python"
            elif self.diff_pattern.search(text):
                code_type = "diff"
            else:
                code_type = "generic"
            logger.info("Interpreted %s code block.", code_type)
            # Attempt filename extraction
            before = text[: text.find("```")]
            file_match = self.file_path_re.search(before)
            if file_match:
                filename = file_match.group(1).strip().replace("\\", "/")
                logger.info("Extracted filename: %s", filename)
            else:
                # Fallback filename generation
                base = "extracted"
                if task_context:
                    goal_params = task_context.get("params", {}).get("cursor_goal", {})
                    target = goal_params.get("target_file")
                    if target:
                        base = target
                ext = {"python": ".py", "diff": ".diff"}.get(code_type, ".txt")
                filename = f"{base}_{uuid.uuid4().hex[:6]}{ext}"
                logger.info("Generated fallback filename: %s", filename)
            return {"action": "save_file", "params": {"path": filename, "content": code_content, "type": code_type}}

        # 4. Completion
        if any(kw in lower for kw in self.complete_kw):
            logger.info("Interpreted completion signal.")
            return {"action": "task_complete"}

        # 5. Clarification
        if any(kw in lower for kw in self.clarify_kw):
            logger.info("Interpreted clarification need.")
            return {"action": "clarification_needed", "params": {"message": text}}

        # 6. No action identified
        logger.debug("No actionable patterns found.")
        return None 
