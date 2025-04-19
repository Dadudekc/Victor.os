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
        """Extracts potential file paths (from backticks or recognized patterns) and symbols (from backticks)."""
        backtick_targets = BACKTICK_PATTERN.findall(task_description)

        # Heuristic for finding potential file paths NOT in backticks
        # Looks for words containing common path separators or ending in common extensions
        # This is a basic heuristic and might need refinement
        potential_paths = re.findall(r'\b[\.\/\\\w\-\+]+\.(?:py|js|ts|java|c|cpp|h|md|json|yaml|txt|log)\b|\b(?:[\w\-\/\.\\:]+[/\\])+[\w\-\/\.\\:]*\b', task_description)

        # Combine and deduplicate
        all_targets = list(set(backtick_targets + potential_paths))

        # Identify files based on extension or path structure
        files = [
            t for t in all_targets 
            if '.' in t or '/' in t or '\\' in t or 
               t.endswith( ('.py', '.js', '.ts', '.java', '.c', '.cpp', '.h', '.md', '.json', '.yaml', '.txt', '.log'))
        ]
        # Symbols are backtick targets that weren't identified as files
        symbols = [t for t in backtick_targets if t not in files] 
        
        # Filter out potential duplicates or fragments if a longer path including them exists
        # E.g., if both "dir/file.py" and "file.py" are found, keep "dir/file.py"
        filtered_files = []
        for f1 in files:
            is_subpath = False
            for f2 in files:
                if f1 != f2 and f1 in f2:
                    is_subpath = True
                    break
            if not is_subpath:
                filtered_files.append(f1)
                
        logger.debug(f"Extracted files: {filtered_files}, Symbols: {symbols}")
        return filtered_files, symbols

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
            
            # If only one file, it's the target for in-place update.
            target_file = files[-1] # Default target if only one file or heuristic fails
            source_files = files[:-1] if len(files) > 1 else files # Default source(s)

            # Refined heuristic for migration/refactoring: Prioritize file after ' to '
            if (is_migration or is_refactor) and ' to ' in task_lower and len(files) > 1:
                found_target_after_to = False
                try:
                    parts = task_lower.split(' to ', 1) # Split only once
                    if len(parts) > 1:
                        potential_target_part = parts[1]
                        # Check extracted files against the part after ' to '
                        for f in files:
                             # Using basename check might be fragile, consider full path check if needed
                             basename = f.split('/')[-1].split('\\')[-1]
                             if basename in potential_target_part:
                                 # Found a potential target file after ' to '
                                 target_file = f 
                                 source_files = [sf for sf in files if sf != target_file] # All others are sources
                                 logger.debug(f"Prioritized target file based on 'to': {target_file}")
                                 found_target_after_to = True
                                 break # Stop after finding the first match after 'to'
                    
                    if not found_target_after_to:
                         logger.warning(f"' to ' keyword found, but couldn't identify a known file in the part after it. Falling back to default target: {target_file}")
                except Exception as e:
                    logger.warning(f"Error parsing target file after 'to': {e}. Falling back to default target: {target_file}")
            elif len(files) == 1:
                 # If only one file, it's both source and target (in-place)
                 source_files = files
                 target_file = files[0]
                 logger.debug(f"Single file identified, assuming in-place update/refactor/migration: {target_file}")

            # Ensure plan reflects correct source/target
            plan = [] # Rebuild plan with potentially reordered/identified files
            # Read source file(s)
            for src_file in source_files:
                 plan.append({"tool": "read_file", "args": {"filepath": src_file}})
                 
            # Add write step for the identified target file
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
            search_term = symbols[0] if symbols else files[0] if files else "<placeholder_search_term>"
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