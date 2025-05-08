# src/dreamos/tools/task_editor.py
# EDIT START: Initial scaffolding for TaskAutoRewriter
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from dreamos.core.config import get_config #, AppConfig (AppConfig not used directly)

# Assuming FeedbackEngineV2 and task-schema.json might be used later
# from dreamos.feedback.feedback_engine_v2 import FeedbackEngineV2
# from dreamos.coordination.tasks.task_schema import TaskSchema

logger = logging.getLogger(__name__)


class TaskAutoRewriterError(Exception):
    """Custom exception for TaskAutoRewriter errors."""

    pass


class ProposedTaskEdit:
    """Represents a proposed set of changes to a task or new tasks."""

    def __init__(self, original_task_id: str, rationale: str):
        self.original_task_id: str = original_task_id
        self.rationale: str = rationale
        # List of changes following a simplified JSON Patch-like format
        # e.g., {"op": "replace", "path": "/params/name", "value": "New name"}
        self.modifications: List[Dict[str, Any]] = []
        # List of new task objects to be created (e.g., for splitting tasks)
        self.new_tasks_to_create: List[Dict[str, Any]] = []

    def add_modification(self, op: str, path: str, value: Any):
        """Adds a modification to an existing task field."""
        if not path.startswith("/"):
            raise ValueError(
                "Modification path must be a valid JSON Pointer (e.g., '/params/description')"
            )
        self.modifications.append({"op": op, "path": path, "value": value})

    def add_new_task(self, task_data: Dict[str, Any]):
        """Adds a new task to be created (e.g., as a subtask)."""
        if "task_id" not in task_data:
            raise ValueError("New task data must include a 'task_id'.")
        self.new_tasks_to_create.append(task_data)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_task_id": self.original_task_id,
            "rationale": self.rationale,
            "modifications": self.modifications,
            "new_tasks_to_create": self.new_tasks_to_create,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ProposedTaskEdit:
        edit = cls(data["original_task_id"], data["rationale"])
        edit.modifications = data.get("modifications", [])
        edit.new_tasks_to_create = data.get("new_tasks_to_create", [])
        return edit


class TaskAutoRewriter:
    """
    Analyzes task definitions and proposes rewrites to improve clarity,
    actionability, or to break down complex tasks.
    """

    def __init__(self):
        self.config = get_config()
        # Ensure openai_client is initialized, assuming it's needed and configured
        # This part depends on how OpenAIClient is expected to be accessed
        if hasattr(self.config, 'integrations') and hasattr(self.config.integrations, 'openai'):
            # Assuming OpenAIClient now uses get_config() internally for its own setup
            from dreamos.integrations.openai_client import OpenAIClient 
            self.openai_client = OpenAIClient()
            if not self.openai_client.is_functional():
                logger.error("TaskAutoRewriter: OpenAI client is not functional. Rewriting capabilities may be limited.")
        else:
            logger.warning("TaskAutoRewriter: OpenAI configuration not found. Rewriting capabilities disabled.")
            self.openai_client = None 

        # Default model for rewriting, can be overridden by config
        self.rewrite_model_name = "gpt-3.5-turbo" # Default
        if hasattr(self.config, 'tools') and hasattr(self.config.tools, 'task_editor') and \
           hasattr(self.config.tools.task_editor, 'rewrite_model_name'):
            self.rewrite_model_name = self.config.tools.task_editor.rewrite_model_name

    def _load_task_schema(self) -> Optional[Dict[str, Any]]:
        """Loads the task JSON schema for validation and reference."""
        try:
            schema_path = self.config.paths.task_schema
            if schema_path.exists():
                with open(schema_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            else:
                logger.warning(f"Task schema not found at: {schema_path}")
                return None
        except Exception as e:
            logger.error(f"Error loading task schema: {e}", exc_info=True)
            return None

    def analyze_and_propose_rewrite(
        self, task_data: Dict[str, Any]
    ) -> Optional[ProposedTaskEdit]:
        """
        Analyzes a given task and returns a ProposedTaskEdit object if
        a rewrite is beneficial, otherwise None.
        """
        task_id = task_data.get("task_id", "UNKNOWN_TASK")
        params = task_data.get("params", {})
        action = task_data.get("action")
        logger.debug(
            f"Analyzing task {task_id} (Action: {action}) for potential rewrite."
        )

        # EDIT START: More detailed analysis logic
        proposal = ProposedTaskEdit(
            original_task_id=task_id,
            rationale="",  # Will be populated by specific checks
        )
        made_proposal = False

        # Check 1: Vague task name
        task_name = params.get("name", "")
        vague_name_keywords = [
            "fix it",
            "update this",
            "do stuff",
            "task",
            "process this",
        ]
        if (
            not task_name
            or any(keyword in task_name.lower() for keyword in vague_name_keywords)
            or len(task_name) < 10
        ):
            logger.info(
                f"Task {task_id} has a vague name: '{task_name}'. Proposing clarification."
            )
            proposal.rationale += (
                "Task name is vague or too short. Needs a more descriptive name. "
            )
            proposal.add_modification(
                op="add",  # Add guidance for name improvement
                path="/params/ai_rewrite_guidance/name",
                value="Please provide a concise and descriptive name for this task, outlining its primary goal.",
            )
            made_proposal = True

        # Check 2: Short or placeholder description
        description = params.get("description", "")
        if (
            not description
            or len(description) < 50
            and (
                "placeholder" in description.lower()
                or "tbd" in description.lower()
                or "details later" in description.lower()
            )
        ):
            logger.info(
                f"Task {task_id} has a short/placeholder description. Proposing enhancement."
            )
            proposal.rationale += "Task description is too short or a placeholder. Needs detailed elaboration. "
            proposal.add_modification(
                op="replace" if description else "add",
                path="/params/description",
                value=f"{description} [AI_REWRITE_REQUEST: Please elaborate on the objectives, expected outcomes, deliverables, and any specific constraints for this task. Original description was: '{description}']",
            )
            # Optionally, add a specific guidance field too
            proposal.add_modification(
                op="add",
                path="/params/ai_rewrite_guidance/description",
                value="Elaborate on objectives, expected outcomes, deliverables, and constraints.",
            )
            made_proposal = True

        # Check 3: Missing essential parameters based on action type (example)
        if action == "modify_file" and not params.get("file_path"):
            logger.info(
                f"Task {task_id} (action: modify_file) is missing 'file_path' parameter. Proposing addition."
            )
            proposal.rationale += "Task action 'modify_file' is missing the essential 'file_path' parameter. "
            proposal.add_modification(
                op="add",
                path="/params/file_path",
                value="[AI_REWRITE_REQUEST: Please specify the target file_path for the modification.]",
            )
            made_proposal = True

        if action == "create_tool" and not params.get("tool_name"):
            logger.info(
                f"Task {task_id} (action: create_tool) is missing 'tool_name'. Proposing addition."
            )
            proposal.rationale += (
                "Task action 'create_tool' is missing the 'tool_name' parameter. "
            )
            proposal.add_modification(
                op="add",
                path="/params/tool_name",
                value="[AI_REWRITE_REQUEST: Please specify the name for the tool to be created (e.g., 'my_tool.py').]",
            )
            made_proposal = True

        # Check 4: Overly broad task (conceptual - example of proposing a split)
        # This requires more sophisticated understanding or keywords
        broad_task_keywords = ["implement entire system", "build full application", "develop new platform"]
        if any(keyword in task_name.lower() for keyword in broad_task_keywords) or \
           any(keyword in description.lower() for keyword in broad_task_keywords):
            if not task_data.get("is_epic"): # Avoid splitting tasks already marked as epics
                logger.info(f"Task {task_id} appears too broad. Proposing it be marked as an Epic AND SPLIT.")
                proposal.rationale += "Task appears very broad. Auto-splitting into sub-tasks and marking original as Epic. "
                
                # Option 1: Suggest marking original as an epic
                proposal.add_modification(
                    op="add", # or "replace" if is_epic might exist and we want to ensure it's true
                    path="/is_epic",
                    value=True
                )
                proposal.add_modification(
                    op="add",
                    path="/params/ai_rewrite_guidance/split_outcome", # New guidance field
                    value="This task was automatically split into sub-tasks by TaskAutoRewriter. Review the generated sub-tasks for detail and accuracy."
                )
                
                # Option 2: Define example sub-tasks
                # A more sophisticated AI could infer logical splits based on task content.
                # For now, we create generic placeholder sub-tasks.
                original_name = params.get("name", "Unnamed Epic Task")
                original_description = params.get("description", "No description provided for the epic task.")
                parent_action = task_data.get("action", "generic_sub_task_action") # Inherit or default action
                # Ensure _dt is available if not already imported at module level. Assuming datetime is imported as _dt from SwarmController context.
                # For TaskAutoRewriter, we'd need to ensure 'import datetime as _dt' or similar.
                # Let's assume datetime is available via 'import datetime'
                import datetime # Ensure datetime is available

                sub_task_base_properties = {
                    "status": "PENDING",
                    "priority": task_data.get("priority", 3), # Inherit priority
                    "injected_by": f"TaskAutoRewriter (split from {task_id})",
                    "timestamp_injected_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    # Other common fields from original task if applicable (e.g. project_context from task_data.get("context"))
                    "context": task_data.get("context", {}), # Inherit context
                    "assigned_to_type": task_data.get("assigned_to_type"), # Inherit assignment preference
                }

                sub_task_1_id = f"{task_id}-SUB-1"
                sub_task_1_data = {
                    **sub_task_base_properties,
                    "task_id": sub_task_1_id,
                    "action": parent_action, 
                    "params": {
                        "name": f"Phase 1: Planning for '{original_name}'",
                        "description": f"Sub-task 1 (Planning Phase) for epic '{original_name}'.\\nParent description: '{original_description}'.\\nFocus on initial planning, detailed requirement gathering, and resource allocation for the epic.",
                        "parent_task_id": task_id,
                        # Potentially copy other relevant params from parent, or set defaults
                    }
                }
                proposal.add_new_task(sub_task_1_data)
                logger.info(f"Generated sub-task {sub_task_1_id} for epic {task_id}.")

                sub_task_2_id = f"{task_id}-SUB-2"
                sub_task_2_data = {
                    **sub_task_base_properties,
                    "task_id": sub_task_2_id,
                    "action": parent_action,
                    "params": {
                        "name": f"Phase 2: Core Implementation of '{original_name}'",
                        "description": f"Sub-task 2 (Core Implementation Phase) for epic '{original_name}'.\\nParent description: '{original_description}'.\\nFocus on developing core features and functionalities as defined in the planning phase.",
                        "parent_task_id": task_id,
                    }
                }
                proposal.add_new_task(sub_task_2_data)
                logger.info(f"Generated sub-task {sub_task_2_id} for epic {task_id}.")
                
                sub_task_3_id = f"{task_id}-SUB-3"
                sub_task_3_data = {
                    **sub_task_base_properties,
                    "task_id": sub_task_3_id,
                    "action": parent_action,
                    "params": {
                        "name": f"Phase 3: Testing & Refinement for '{original_name}'",
                        "description": f"Sub-task 3 (Testing & Refinement Phase) for epic '{original_name}'.\\nParent description: '{original_description}'.\\nFocus on comprehensive testing, bug fixing, and refinement of the implemented features.",
                        "parent_task_id": task_id,
                    }
                }
                proposal.add_new_task(sub_task_3_data)
                logger.info(f"Generated sub-task {sub_task_3_id} for epic {task_id}.")
                
                made_proposal = True
        
        # TODO: Add more checks:
        # - Alignment with task schema (e.g., using self.task_schema if loaded)
        # - Input from FeedbackEngineV2 for patterns of past failures related to task structure.
        # - Check for missing dependencies or unclear acceptance criteria.

        if made_proposal:
            proposal.rationale = proposal.rationale.strip()  # Clean up rationale string
            logger.info(
                f"Proposing rewrite for task {task_id} with rationale: {proposal.rationale}"
            )
            return proposal
        # EDIT END

        logger.debug(f"No rewrite proposed for task {task_id}.")
        return None

    def apply_task_edit(
        self, task_data: Dict[str, Any], edit: ProposedTaskEdit
    ) -> Dict[str, Any]:
        """
        Applies the modifications from a ProposedTaskEdit to a task dictionary.
        This method handles direct modifications to the task.
        Creation of new tasks would be handled separately by the TaskNexus/PBM.

        Note: This is a simplified implementation. A robust version would use
        a proper JSON Patch library.
        """
        if task_data["task_id"] != edit.original_task_id:
            raise TaskAutoRewriterError(
                f"Mismatched task ID. Edit is for {edit.original_task_id}, "
                f"but applying to {task_data['task_id']}."
            )

        modified_task = task_data.copy()  # Start with a copy

        for mod in edit.modifications:
            path_parts = mod["path"].strip("/").split("/")
            current_level = modified_task

            try:
                for i, part in enumerate(path_parts[:-1]):
                    if part not in current_level:
                        if mod["op"] == "add":  # Create intermediate paths for 'add'
                            current_level[part] = {}
                        else:  # Path doesn't exist for 'replace' or 'remove'
                            raise KeyError(
                                f"Path segment '{part}' not found in task for modification: {mod}"
                            )
                    current_level = current_level[part]

                target_key = path_parts[-1]

                if mod["op"] == "replace":
                    if target_key not in current_level:
                        raise KeyError(
                            f"Key '{target_key}' not found for 'replace' operation at path '{mod['path']}'."
                        )
                    current_level[target_key] = mod["value"]
                elif mod["op"] == "add":
                    # If adding to a list, this simple assignment might not be enough.
                    # A proper JSON patch would handle list appends, insertions etc.
                    # For simplicity, 'add' here acts like 'replace' if key exists, or creates if not.
                    current_level[target_key] = mod["value"]
                elif mod["op"] == "remove":
                    if target_key not in current_level:
                        raise KeyError(
                            f"Key '{target_key}' not found for 'remove' operation at path '{mod['path']}'."
                        )
                    del current_level[target_key]
                else:
                    logger.warning(f"Unsupported modification operation: {mod['op']}")
            except KeyError as e:
                logger.error(f"Error applying modification {mod}: {e}", exc_info=True)
                # Potentially collect errors and decide if the whole edit fails
                raise TaskAutoRewriterError(
                    f"Failed to apply modification {mod}: {e}"
                ) from e
            except Exception as e:
                logger.error(
                    f"Unexpected error applying modification {mod}: {e}", exc_info=True
                )
                raise TaskAutoRewriterError(
                    f"Unexpected error during modification {mod}: {e}"
                ) from e

        logger.info(
            f"Successfully applied direct modifications to task {edit.original_task_id}."
        )
        return modified_task


# Example Usage (conceptual, would be part of agent loop or a dedicated service)
# if __name__ == "__main__":
#     # This requires AppConfig to be loadable, e.g., via get_config()
#     # from dreamos.core.config import get_config
#     # config = get_config()
#     # rewriter = TaskAutoRewriter(config)
#
#     # dummy_task = {
#     #     "task_id": "TEST-REWRITE-001",
#     #     "action": "some_action",
#     #     "params": {
#     #         "name": "Fix this file",
#     #         "description": "placeholder",
#     #         "target_file": "src/foo/bar.py"
#     #     },
#     #     "status": "PENDING"
#     # }
#
#     # proposal = rewriter.analyze_and_propose_rewrite(dummy_task)
#     # if proposal:
#     #     print(f"Proposal for {dummy_task['task_id']}:")
#     #     print(json.dumps(proposal.to_dict(), indent=2))
#
#     #     # Simulate applying the edit (direct modifications only)
#     #     if proposal.modifications:
#     #         updated_task = rewriter.apply_task_edit(dummy_task, proposal)
#     #         print("\nUpdated Task (direct mods only):")
#     #         print(json.dumps(updated_task, indent=2))
#
#     #     # New tasks would be handled by task management system
#     #     if proposal.new_tasks_to_create:
#     #         print("\nNew tasks to create:")
#     #         for new_task in proposal.new_tasks_to_create:
#     #             print(json.dumps(new_task, indent=2))
#     # else:
#     #     print(f"No rewrite proposed for {dummy_task['task_id']}.")

# EDIT END
