"""A rule-based planner tool that generates a basic execution plan."""
import logging
import re
import os
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
        
        files, symbols = self._extract_targets(task_description)
        task_lower = task_description.lower()

        # --- Rule Processing --- 
        plan = None
        rule_methods = [
            self._rule_copy_file,
            self._rule_extract_symbol,
            self._rule_refactor_symbol,
            self._rule_create_file,
            self._rule_migrate_update_generic_refactor,
            self._rule_read_analyze,
            self._rule_search,
            # Fallback rule (applied last if no other rule matches)
            self._rule_fallback_log
        ]

        for rule_method in rule_methods:
            plan = rule_method(task_description, task_lower, files, symbols)
            if plan is not None: # First rule that returns a plan wins
                break
        
        # Ensure plan is a list, even if fallback didn't return one (shouldn't happen)
        plan = plan if plan is not None else []
        
        # --- Result Generation --- 
        plan_narration = self._generate_plan_narration(plan, task_description)
        version = "0.3.1" # Incremented version for refactor

        result = {
             "plan_version": version,
             "task_description": task_description,
             "plan_narration": plan_narration,
             "plan": plan
        }
        
        self._log_execution(args, f"Generated plan v{version} with {len(plan)} steps.")
        return result 

    # --- Individual Rule Methods --- 
    
    def _rule_copy_file(self, task: str, task_lower: str, files: List[str], symbols: List[str]) -> Optional[List[Dict]]:
        """Rule: Copy a file from source to destination."""
        # Look for 'copy' keyword and exactly two files
        if 'copy' in task_lower and len(files) == 2:
            # Basic heuristic: assume first file mentioned is source, second is destination
            # This could be improved by parsing phrases like "copy X to Y"
            source_file = files[0]
            dest_file = files[1]
            # A simple check to swap if the order seems wrong based on common phrasing
            if f"copy {dest_file}" in task_lower and f"to {source_file}" in task_lower:
                source_file, dest_file = dest_file, source_file
            elif f"copy of {dest_file}" in task_lower and f"named {source_file}" in task_lower:
                 source_file, dest_file = dest_file, source_file # less likely pattern

            logger.debug(f"Applying Copy File rule: {source_file} -> {dest_file}")
            plan = [
                {"tool": "read_file", "args": {"filepath": source_file}},
                # NOTE: The write_file content here is a placeholder.
                # A real implementation would require the executor to use the context
                # from the previous read_file step (e.g., context['step_0_result']['content'])
                {"tool": "write_file", "args": {"filepath": dest_file, "content": f"# TODO: Content should be copied from {source_file}"}}
            ]
            return plan
        return None

    def _rule_extract_symbol(self, task: str, task_lower: str, files: List[str], symbols: List[str]) -> Optional[List[Dict]]:
        """Rule: Extract Class/Function from one file to another."""
        if 'extract' in task_lower and symbols and len(files) >= 2:
            logger.debug("Applying Extract Symbol rule.")
            target_symbol = symbols[0]
            source_file = None
            target_file = None
            try:
                parts_from = task_lower.split(' from ', 1)
                if len(parts_from) > 1:
                    potential_source_part = parts_from[1]
                    parts_to = potential_source_part.split(' to ', 1)
                    if len(parts_to) > 1:
                        source_part = parts_to[0]
                        target_part = parts_to[1]
                        for f in files:
                            basename = os.path.basename(f)
                            if basename in source_part: source_file = f
                            if basename in target_part: target_file = f
                if not source_file or not target_file:
                     logger.warning("Could not reliably determine source/target for extraction. Skipping rule.")
                     return None # Rule doesn't match clearly
                else:
                    logger.info(f"Extraction plan: Extract '{target_symbol}' from '{source_file}' to '{target_file}'")
                    plan = []
                    plan.append({"tool": "read_file", "args": {"filepath": source_file}})
                    plan.append({"tool": "read_file", "args": {"filepath": target_file}})
                    plan.append({"tool": "write_file", "args": {"filepath": source_file, "content": f"# TODO: Remove extracted symbol '{target_symbol}' from {source_file}."}})
                    plan.append({"tool": "write_file", "args": {"filepath": target_file, "content": f"# TODO: Add extracted symbol '{target_symbol}' to {target_file}."}})
                    return plan
            except Exception as e:
                logger.warning(f"Error parsing extract command structure: {e}. Skipping rule.")
        return None # Rule condition not met
        
    def _rule_refactor_symbol(self, task: str, task_lower: str, files: List[str], symbols: List[str]) -> Optional[List[Dict]]:
        """Rule: Refactor a specific symbol (function/class) within a file."""
        if 'refactor' in task_lower and symbols and files:
            logger.debug("Applying Refactor Symbol rule.")
            target_symbol = symbols[0]
            target_file = files[0] 
            plan = [
                {"tool": "read_file", "args": {"filepath": target_file}},
                {"tool": "write_file", "args": {"filepath": target_file, "content": f"# TODO: Refactor symbol '{target_symbol}' in {target_file}."}}
            ]
            return plan
        return None
        
    def _rule_create_file(self, task: str, task_lower: str, files: List[str], symbols: List[str]) -> Optional[List[Dict]]:
         """Rule: If task involves creating a file."""
         if 'create' in task_lower and files:
             logger.debug("Applying Create File rule.")
             plan = []
             for fp in files:
                 basename = os.path.basename(fp)
                 class_name_parts = basename.replace(".py", "").split('_')
                 class_name = "".join(part.capitalize() for part in class_name_parts) or "MyClass"
                 placeholder = f"# TODO: Implement the {class_name} class\n\nclass {class_name}:\n    \"\"\"Placeholder for {class_name}.\"\"\"\n    pass\n"
                 plan.append({"tool": "write_file", "args": {"filepath": fp, "content": placeholder}})
             return plan
         return None

    def _rule_migrate_update_generic_refactor(self, task: str, task_lower: str, files: List[str], symbols: List[str]) -> Optional[List[Dict]]:
        """Rule: Migration / Update / Generic Refactor (no specific symbol mentioned)."""
        is_migration = 'migrate' in task_lower
        is_refactor = 'refactor' in task_lower
        is_update = 'update' in task_lower
        # Trigger if keywords match AND it's not a symbol refactor (handled above)
        if (is_migration or is_update or (is_refactor and not symbols)) and files:
            logger.debug("Applying Migration/Update/Generic Refactor rule.")
            # Simplified logic - assumes prior refined heuristic for target finding exists or is added here
            target_file = files[-1]
            source_files = files[:-1] if len(files) > 1 else files
            # TODO: Re-integrate the 'from ... to ...' target identification logic here if needed
            plan = []
            for src_file in source_files:
                 plan.append({"tool": "read_file", "args": {"filepath": src_file}})
            action_verb = "migrated" if is_migration else "refactored" if is_refactor else "updated"
            plan.append({"tool": "write_file", "args": {"filepath": target_file, "content": f"# TODO: Implement {action_verb} code for {target_file}."}})
            return plan
        return None

    def _rule_read_analyze(self, task: str, task_lower: str, files: List[str], symbols: List[str]) -> Optional[List[Dict]]:
        """Rule: If task involves reading/analyzing files."""
        if files and ('read' in task_lower or 'analyze' in task_lower or 'use' in task_lower or 'check' in task_lower):
             logger.debug("Applying Read/Analyze rule.")
             plan = []
             for file in files:
                 plan.append({"tool": "read_file", "args": {"filepath": file}})
             return plan
        return None
        
    def _rule_search(self, task: str, task_lower: str, files: List[str], symbols: List[str]) -> Optional[List[Dict]]:
        """Rule: If task involves searching."""
        if 'search' in task_lower or 'find' in task_lower or 'grep' in task_lower:
             logger.debug("Applying Search rule.")
             search_term = symbols[0] if symbols else files[0] if files else "<placeholder_search_term>"
             search_path = files[0] if files else "."
             plan = [{"tool": "grep_search", "args": {"query": search_term, "path": search_path}}]
             return plan
        return None
        
    def _rule_fallback_log(self, task: str, task_lower: str, files: List[str], symbols: List[str]) -> Optional[List[Dict]]:
        """Fallback Rule: Logs a message if no other rules matched."""
        logger.warning("Planner could not apply specific rules, adding generic log_message placeholder.")
        plan = [{
            "tool": "log_message", 
            "args": {"message": f"Placeholder action for task: {task}"} 
        }]
        return plan
        
    # --- Helper Methods --- 
    
    def _generate_plan_narration(self, plan: List[Dict[str, Any]], task: str) -> str:
        """Generates a simple human-readable narration of the plan."""
        if not plan:
            return "Based on the task, no specific actions are planned."
        
        parts = [f"Okay, for the task '{task[:50]}...', I plan to:"]
        for i, step in enumerate(plan):
            tool = step.get("tool")
            args = step.get("args", {})
            narration = f"{i+1}. Use the '{tool}' tool" 
            if 'filepath' in args:
                narration += f" on file '{args['filepath']}'"
            elif 'query' in args:
                narration += f" to search for '{args['query']}'"
            elif 'message' in args:
                 narration += f" to log a message."
            parts.append(narration)
            
        if len(plan) == 1:
            parts.append("This should accomplish the task.")
        else:
            parts.append(f"Executing these {len(plan)} steps should accomplish the task.")
            
        return "\n".join(parts)

    def _log_execution(self, args: Dict[str, Any], message: str):
        """Logs the execution result message."""
        # Simplified from previous version which took args
        logger.info(message) 