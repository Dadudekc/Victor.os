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
        
        plan: List[Dict[str, Any]] = []
        files, symbols = self._extract_targets(task_description)
        task_lower = task_description.lower()

        # --- Rule-Based Planning Logic --- 
        is_migration = 'migrate' in task_lower
        is_refactor = 'refactor' in task_lower
        is_update = 'update' in task_lower
        is_create = 'create' in task_lower
        is_extract = 'extract' in task_lower
        
        # Rule Order Matters! More specific rules should come first.

        # Rule: Extract Class/Function from one file to another
        if is_extract and symbols and len(files) >= 2:
            # Basic Assumption: extract <symbol> from <file1> to <file2>
            logger.debug("Applying Extract Symbol rule.")
            target_symbol = symbols[0]
            # Heuristic: file after 'from' is source, file after 'to' is target
            source_file = None
            target_file = None
            try:
                # Split robustly, considering potential missing keywords
                parts_from = task_lower.split(' from ', 1)
                if len(parts_from) > 1:
                    potential_source_part = parts_from[1]
                    parts_to = potential_source_part.split(' to ', 1)
                    if len(parts_to) > 1:
                        source_part = parts_to[0]
                        target_part = parts_to[1]
                        
                        # Find matching files in the parts
                        for f in files:
                            # Simple basename check
                            basename = os.path.basename(f) # Use os.path.basename
                            if basename in source_part:
                                source_file = f
                            if basename in target_part:
                                target_file = f
                                
                if not source_file or not target_file:
                     logger.warning("Could not reliably determine source/target for extraction. Skipping rule.")
                else:
                    logger.info(f"Extraction plan: Extract '{target_symbol}' from '{source_file}' to '{target_file}'")
                    # Plan: Read source, Read target, Write source (modified), Write target (modified)
                    plan.append({"tool": "read_file", "args": {"filepath": source_file}})
                    plan.append({"tool": "read_file", "args": {"filepath": target_file}})
                    plan.append({
                        "tool": "write_file", 
                        "args": {
                            "filepath": source_file, 
                            "content": f"# TODO: Remove extracted symbol '{target_symbol}' from this file ({source_file}). Content based on previous read step."
                        }
                    })
                    plan.append({
                        "tool": "write_file", 
                        "args": {
                            "filepath": target_file, 
                            "content": f"# TODO: Add extracted symbol '{target_symbol}' to this file ({target_file}). Content based on previous read steps and task."
                        }
                    })
            except Exception as e:
                logger.warning(f"Error parsing extract command structure: {e}. Skipping rule.")

        # Rule: Refactor a specific symbol (function/class) within a file
        elif is_refactor and symbols and files:
            logger.debug("Applying Refactor Symbol rule.")
            # Basic assumption: refactor first symbol in first file mentioned
            target_symbol = symbols[0]
            target_file = files[0] 
            # Plan: Read the file, (optionally grep for symbol), write back with TODO
            plan.append({"tool": "read_file", "args": {"filepath": target_file}})
            plan.append({
                "tool": "write_file",
                "args": {
                    "filepath": target_file,
                    "content": f"# TODO: Refactor symbol '{target_symbol}' in {target_file} based on task description and file content read in previous steps."
                }
            })
            
        # Rule: Migration / Update (Generic file movement/change, less specific than extract/refactor symbol)
        elif (is_migration or is_update or (is_refactor and not symbols)) and files:
            logger.debug("Applying Migration/Update/Generic Refactor rule.")
            # ... (existing migration/update/generic refactor logic) ...
            # This logic needs to correctly identify source/target and generate plan
            # Assuming the logic refined earlier for `to` keyword exists here
            # Simplified placeholder for demonstration:
            target_file = files[-1]
            source_files = files[:-1] if len(files) > 1 else files
            # (Add the refined heuristic logic here from previous steps if needed)
            for src_file in source_files:
                 plan.append({"tool": "read_file", "args": {"filepath": src_file}})
            action_verb = "migrated" if is_migration else "refactored" if is_refactor else "updated"
            plan.append({
                "tool": "write_file", 
                "args": {
                    "filepath": target_file, 
                    "content": f"# TODO: Implement {action_verb} code for {target_file} based on task and content of other files read in previous steps."
                 }
             })

        # Rule: If task involves creating a file
        elif is_create and files and not plan:
             logger.debug("Applying Create File rule.")
             for fp in files:
                 basename = os.path.basename(fp)
                 class_name_parts = basename.replace(".py", "").split('_')
                 class_name = "".join(part.capitalize() for part in class_name_parts)
                 if not class_name: class_name = "MyClass" 
                 placeholder = f"# TODO: Implement the {class_name} class\n\nclass {class_name}:\n    \"\"\"Placeholder for {class_name}.\"\"\"\n    pass\n"
                 plan.append({
                     "tool": "write_file",
                     "args": {"filepath": fp, "content": placeholder}
                 })

        # Rule: If task involves reading/analyzing files (and not covered above)
        elif files and not plan and ('read' in task_lower or 'analyze' in task_lower or 'use' in task_lower or 'check' in task_lower):
             logger.debug("Applying Read/Analyze rule.")
             for file in files:
                 plan.append({"tool": "read_file", "args": {"filepath": file}})
        
        # Rule: If task involves searching (and not covered above)
        elif not plan and ('search' in task_lower or 'find' in task_lower or 'grep' in task_lower):
             logger.debug("Applying Search rule.")
             search_term = symbols[0] if symbols else files[0] if files else "<placeholder_search_term>"
             search_path = files[0] if files else "."
             plan.append({"tool": "grep_search", "args": {"query": search_term, "path": search_path}})
            
        # Fallback: If no specific rules match and no plan generated yet
        if not plan and task_description:
            logger.warning("Planner could not generate specific steps based on rules, adding generic log_message placeholder.")
            plan.append({
                "tool": "log_message", 
                "args": {"message": f"Placeholder action for task: {task_description}"} 
            })

        # --- End Planning Logic ---
        
        # --- Add Narration and Versioning (Enhancements 3 & 4) ---
        plan_narration = self._generate_plan_narration(plan, task_description)
        version = "0.3.0" # Example version

        result = {
             "plan_version": version,
             "task_description": task_description,
             "plan_narration": plan_narration,
             "plan": plan
        }
        # --- End Enhancements --- 
        
        self._log_execution(args, f"Generated plan v{version} with {len(plan)} steps.")
        return result 

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
        """Logs the execution of the tool."""
        logger.info(message) 