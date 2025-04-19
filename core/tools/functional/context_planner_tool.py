"""A rule-based planner tool that generates a basic execution plan."""
import logging
import re
from typing import Dict, Any, Optional, List

from core.tools.base import AgentTool

logger = logging.getLogger(__name__)

# Simple regex to find things quoted in backticks (potential symbols/files)
BACKTICK_PATTERN = re.compile(r"`([^`]+)`")

class ContextPlannerTool(AgentTool):
    """Generates a execution plan based on keywords and patterns in the task description.
       NOTE: This is a simplified rule-based planner, NOT an LLM-based planner.
    """

    @property
    def name(self) -> str:
        return "context_planner"

    @property
    def description(self) -> str:
        return ("Analyzes a task description and generates a sequence of tool calls (plan) to accomplish it. "
                "Input args: {'task_description': 'natural language task'}. "
                "Output: {'plan': [{'tool': 'tool_name', 'args': {...}}, ...]}")

    def _extract_targets(self, task_description: str) -> tuple[List[str], List[str]]:
        """Extracts potential file paths and symbols from backticks."""
        targets = BACKTICK_PATTERN.findall(task_description)
        # Improved heuristic: check for common code file extensions or paths
        files = [
            t for t in targets 
            if '.' in t or '/' in t or '\\' in t or 
               t.endswith( ('.py', '.js', '.ts', '.java', '.c', '.cpp', '.h', '.md', '.json', '.yaml'))
        ]
        symbols = [t for t in targets if t not in files] 
        logger.debug(f"Extracted files: {files}, Symbols: {symbols}")
        return files, symbols

    def execute(self, args: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        task_description = args.get("task_description")
        if not task_description:
            raise ValueError(f"Tool '{self.name}' requires 'task_description' argument.")

        logger.info(f"Executing '{self.name}' for task: {task_description[:100]}...")
        
        plan: List[Dict[str, Any]] = []
        files, symbols = self._extract_targets(task_description)
        task_lower = task_description.lower()

        # --- Rule-Based Planning Logic --- 
        
        # Rule: Migration / Refactoring / Update
        # Needs to read source(s) and write target(s)
        is_migration = 'migrate' in task_lower
        is_refactor = 'refactor' in task_lower
        is_update = 'update' in task_lower

        # Check if keywords match and we have at least one file (source). 
        # If only one file is mentioned, assume it's both source and target (in-place update).
        if (is_migration or is_refactor or is_update) and files:
            logger.debug("Applying Migration/Refactor/Update rule.")
            
            # Read all mentioned files
            for file_path in files:
                plan.append({"tool": "read_file", "args": {"filepath": file_path}})
            
            # Determine target file. Simplistic assumption: last file is target.
            # If only one file, it's the target for in-place update.
            target_file = files[-1] 
            
            # Try a slightly better heuristic for migration/refactoring: Look for 'to'
            if (is_migration or is_refactor) and ' to ' in task_lower:
                try:
                    # Extract the part after ' to ' and see if it contains a known file
                    potential_target_part = task_lower.split(' to ')[1]
                    for f in files:
                        # Check if the base filename (without path) is in the target part
                        # Escaped backslash for Windows paths
                        if f.split('/')[-1].split('\\')[-1] in potential_target_part:
                             target_file = f
                             logger.debug(f"Identified target file heuristically based on 'to': {target_file}")
                             break
                except Exception as e:
                    logger.warning(f"Error parsing target file after 'to': {e}. Falling back to last file.")

            action_verb = "migrated" if is_migration else "refactored" if is_refactor else "updated"
            plan.append({
                "tool": "write_file", 
                "args": {
                    "filepath": target_file, 
                    "content": f"# TODO: Implement {action_verb} code for {target_file} based on task and content of other files read in previous steps."
                    # In a real scenario, an LLM tool would generate this content using context from read_file steps.
                }
            })

        # Rule: If task involves reading/analyzing files (and not covered above)
        elif files and ('read' in task_lower or 'analyze' in task_lower or 'use' in task_lower or 'check' in task_lower):
            logger.debug("Applying Read/Analyze rule.")
            for file in files:
                plan.append({"tool": "read_file", "args": {"filepath": file}})
        
        # Rule: If task involves searching (and not covered above)
        elif 'search' in task_lower or 'find' in task_lower or 'grep' in task_lower:
            logger.debug("Applying Search rule.")
            # Prioritize symbol if available, else first target, else placeholder
            search_term = symbols[0] if symbols else targets[0] if targets else "<placeholder_search_term>"
            # Search in first file mentioned or default path
            search_path = files[0] if files else "."
            plan.append({"tool": "grep_search", "args": {"query": search_term, "path": search_path}})
            
        # Fallback: If no specific rules match, add a generic log message
        if not plan and task_description:
            logger.warning("Planner could not generate specific steps based on rules, adding generic log_message placeholder.")
            plan.append({
                "tool": "log_message", 
                "args": {"message": f"Placeholder action for task: {task_description}"} 
            })

        # --- End Planning Logic ---
        
        result = {"plan": plan}
        self._log_execution(args, f"Generated plan with {len(plan)} steps.")
        return result 