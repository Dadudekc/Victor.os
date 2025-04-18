"""
Contextual Analysis Planner Tool (v3)

Analyzes a natural language task description using simple role assignment
for symbols/files and generates a structured, action-aware plan for context gathering.
"""

import re
import json
from typing import List, Dict, Optional, Any, Tuple

# --- Constants ---

FILE_PATH_PATTERN = re.compile(r'(?:\s|\bin\b\s|from\b\s)([`\'\"]?)([\w\-/\\.]+?\.(?:py|js|ts|java|cs|go|rb|php|html|css|md|yaml|json|txt|xml|sh|cfg|ini))([`\'\"]?)\b')
# SYMBOL_PATTERN: Matches content within backticks `symbol` more reliably
SYMBOL_PATTERN = re.compile(r'`([^`]+)`')
# Action Verbs classified
ACTION_VERBS = {
    'migrate': ['migrate', 'port'],
    'replace': ['replace', 'substitute'],
    'refactor': ['refactor', 'restructure', 'rewrite', 'improve'],
    'implement': ['implement', 'add', 'create', 'build'],
    'update': ['update', 'change', 'modify'],
    'use': ['use', 'utilize', 'integrate', 'consume'],
    'fix': ['fix', 'debug', 'resolve', 'correct'],
    'analyze': ['analyze', 'understand', 'inspect', 'examine']
}
# Keywords indicating roles
ROLE_KEYWORDS = {
    'source': ['from'],
    'target': ['to', 'into'],
    'dependency': ['using', 'with', 'via'],
    'location': ['in', 'inside', 'within', 'on'],
}

# Tool action names
GREP_SEARCH = "grep_search"
READ_FILE = "read_file"
CODEBASE_SEARCH = "codebase_search"

# --- Helper Functions ---

def assign_roles(task_description: str, entities: Dict[str, List[str]]) -> Dict[str, List[Tuple[str, Optional[str]]]]:
    """Attempts basic role assignment for symbols and files based on keywords."""
    # TODO: This is very basic keyword matching, needs more robust NLP for complex cases.
    assigned_entities = {
        "files": [(f, None) for f in entities["files"]], # List of (name, role)
        "symbols": [(s, None) for s in entities["symbols"]]
    }

    # Rough sentence segmentation (split by '.')
    sentences = [s.strip() for s in task_description.split('.') if s.strip()]

    # Assign roles based on keywords near the entity within sentences
    for entity_type in ["files", "symbols"]:
        updated_list = []
        for entity_name, _ in assigned_entities[entity_type]:
            assigned_role = None
            for sentence in sentences:
                if entity_name not in sentence: continue

                # Find keyword context around the entity
                try:
                    entity_index = sentence.index(entity_name)
                    # Look for keywords immediately before the entity
                    # Limit window size to avoid grabbing keywords from unrelated clauses
                    window_size = 15
                    start_idx = max(0, entity_index - window_size)
                    prefix = sentence[start_idx:entity_index].lower()

                    found_role = None
                    for role, keywords in ROLE_KEYWORDS.items():
                        for kw in keywords:
                            # Check for keyword with space before/after to avoid partial matches
                            if f' {kw} ' in prefix or prefix.endswith(f' {kw}'):
                                # Simple role mapping
                                if entity_type == 'files' and role == 'location':
                                    found_role = 'target_file' # File mentioned with 'in', 'on' etc.
                                elif entity_type == 'symbols' and role == 'source':
                                    found_role = 'source_symbol'
                                elif entity_type == 'symbols' and role == 'target':
                                    found_role = 'target_symbol'
                                elif entity_type == 'symbols' and role == 'dependency':
                                    found_role = 'dependency_symbol'
                                break
                        if found_role: break
                    if found_role:
                        assigned_role = found_role
                        break # Stop checking sentences once a role is found for this entity

                except ValueError:
                    continue # Entity name not found exactly (e.g. substring)

            # If no role found via keywords, assign default based on action?
            # (Could be added later)
            updated_list.append((entity_name, assigned_role))
        assigned_entities[entity_type] = updated_list

    return assigned_entities

def extract_entities_v3(task_description: str) -> Dict:
    """Extracts entities and attempts role assignment."""
    # 1. Basic Extraction
    entities = {
        "files": sorted(list(set(m.group(2) for m in FILE_PATH_PATTERN.finditer(task_description)))), # Extract path from group 2
        "symbols": sorted(list(set(SYMBOL_PATTERN.findall(task_description)))),
        "actions": [],
    }

    detected_actions = set()
    task_lower = task_description.lower()
    for action_key, synonyms in ACTION_VERBS.items():
        for verb in synonyms:
            if verb in task_lower:
                detected_actions.add(action_key)
                break
    entities["actions"] = sorted(list(detected_actions))

    # 2. Role Assignment
    assigned_entities = assign_roles(task_description, entities)

    # Combine results
    entities["files_with_roles"] = assigned_entities["files"]
    entities["symbols_with_roles"] = assigned_entities["symbols"]

    return entities

def create_plan_step(description: str, action: str, target: str, params: Optional[Dict[str, Any]] = None, store_as: Optional[str] = None) -> Dict:
    """Helper to format a plan step dictionary."""
    step = {
        "description": description,
        "action": action,
        "target": target,
        "params": params or {}
    }
    if store_as:
        step["store_as"] = store_as
    return step

# --- Action Templates (Unchanged) ---
ACTION_TEMPLATES = {
    "migrate": [
        {"type": "read_definition", "role": "source_symbol", "store_id": "def_source"},
        {"type": "read_definition", "role": "target_symbol", "store_id": "def_target"},
        {"type": "find_usages", "role": "source_symbol", "store_id": "usages_source"},
        {"type": "read_file_if_exists", "role": "target_file"},
        {"type": "code_search", "query": "interface details of {target_symbol}", "role": "target_symbol"},
    ],
    "refactor": [
        {"type": "read_definition", "role": "primary_symbol", "store_id": "def_primary"},
        {"type": "find_usages", "role": "primary_symbol", "store_id": "usages_primary"},
    ],
    "implement": [
        {"type": "read_file", "role": "target_file"},
        {"type": "read_definition", "role": "dependency_symbol", "store_id": "def_dep"},
        {"type": "code_search", "query": "examples of using {dependency_symbol}", "role": "dependency_symbol"},
    ],
    "use": [
        {"type": "read_definition", "role": "dependency_symbol", "store_id": "def_dep"},
        {"type": "code_search", "query": "how to use {dependency_symbol}", "role": "dependency_symbol"},
        {"type": "read_file_if_exists", "role": "target_file"},
    ],
    "fix": [
        {"type": "read_file", "role": "target_file"},
        {"type": "read_definition", "role": "primary_symbol", "store_id": "def_primary"},
        {"type": "find_usages", "role": "primary_symbol", "store_id": "usages_primary"},
        {"type": "code_search", "query": "error context for {primary_symbol}", "role": "primary_symbol"},
    ],
}

# --- Core Planning Logic (v3) ---

def generate_context_plan_v3(task_description: str) -> List[Dict]:
    """
    Generates a context plan using role assignment and action templates.
    """
    plan: List[Dict] = []
    entities = extract_entities_v3(task_description)
    symbols_with_roles = entities["symbols_with_roles"]
    files_with_roles = entities["files_with_roles"]
    actions = entities["actions"]

    # Helper to find entity by role
    def find_entity(role: str, entity_list: List[Tuple[str, Optional[str]]]) -> Optional[str]:
        for name, r in entity_list:
            if r == role:
                return name
        # Fallback: If role not found, maybe return first entity?
        # Or handle more gracefully depending on template needs.
        if role == 'primary_symbol' and entity_list: return entity_list[0][0]
        if role == 'target_file' and entity_list: return entity_list[0][0]
        return None

    # --- Apply Action Templates ---
    applied_template = False
    if actions:
        primary_action = actions[0]
        template = ACTION_TEMPLATES.get(primary_action)

        if template:
            # Map template steps using roles
            for step_template in template:
                step_type = step_template["type"]
                role_placeholder = step_template.get("role")
                store_id_template = step_template.get("store_id")
                query_template = step_template.get("query")

                # Find the entity (symbol or file) matching the required role
                current_entity_name = None
                entity_list = symbols_with_roles if 'symbol' in role_placeholder else files_with_roles
                current_entity_name = find_entity(role_placeholder, entity_list)

                if not current_entity_name:
                    # print(f"Warning: Could not find entity for role '{role_placeholder}' in template.")
                    continue # Skip step if required entity role is missing

                # Resolve store_id and query based on the found entity
                store_ref = store_id_template.replace("{role}", current_entity_name) if store_id_template else f"ref_{current_entity_name}"
                query = query_template.format(**{role_placeholder: current_entity_name}) if query_template else None
                target_desc = f"{current_entity_name} related info"

                # Generate plan step based on type
                if step_type == "read_definition":
                    escaped_symbol = re.escape(current_entity_name)
                    pattern = fr'\\b(?:class|def|function|interface|type|const|let|var)\\s+{escaped_symbol}\\b'
                    plan.append(create_plan_step(
                        description=f"Locate the definition of '{current_entity_name}' ({role_placeholder})",
                        action=GREP_SEARCH, target=current_entity_name,
                        params={"query": pattern, "case_sensitive": False},
                        store_as=store_ref
                    ))
                    plan.append(create_plan_step(
                        description=f"Read code around the definition of '{current_entity_name}'",
                        action=READ_FILE, target=f"<{store_ref}>",
                        params={"lines": 40}
                    ))
                elif step_type == "find_usages":
                     escaped_symbol = re.escape(current_entity_name)
                     pattern = fr'\\b{escaped_symbol}\\b'
                     plan.append(create_plan_step(
                         description=f"Find usages of '{current_entity_name}' ({role_placeholder})",
                         action=GREP_SEARCH, target=current_entity_name,
                         params={"query": pattern, "case_sensitive": False},
                         store_as=store_ref
                     ))
                elif step_type == "read_file" or step_type == "read_file_if_exists":
                    plan.append(create_plan_step(
                        description=f"Read file '{current_entity_name}' ({role_placeholder})",
                        action=READ_FILE, target=current_entity_name, params={"lines": "all"}
                    ))
                elif step_type == "code_search" and query:
                    plan.append(create_plan_step(
                        description=f"Search codebase for: '{query}'",
                        action=CODEBASE_SEARCH, target=target_desc, params={"query": query}
                    ))

            if plan: applied_template = True

    # --- Fallback / Generic Steps --- (If no template applied)
    if not applied_template:
        # Read all mentioned files
        for file_path, _ in files_with_roles:
             plan.append(create_plan_step(description=f"Read specified file: {file_path}", action=READ_FILE, target=file_path, params={"lines": "all"}))
        # Define all mentioned symbols
        for symbol, _ in symbols_with_roles:
            store_ref = f"def_{symbol}"
            escaped_symbol = re.escape(symbol)
            pattern = fr'\\b(?:class|def|function|interface|type|const|let|var)\\s+{escaped_symbol}\\b'
            plan.append(create_plan_step(description=f"Locate the definition of '{symbol}'", action=GREP_SEARCH, target=symbol, params={"query": pattern, "case_sensitive": False}, store_as=store_ref))
            plan.append(create_plan_step(description=f"Read code around the definition of '{symbol}'", action=READ_FILE, target=f"<{store_ref}>", params={"lines": 40}))

    # --- Deduplicate Plan --- (already implemented)
    final_plan = []
    seen_steps = set()
    for step in plan:
        step_key = (step["action"], step["target"], tuple(sorted(step["params"].items())) if step["params"] else None)
        if step_key not in seen_steps:
            final_plan.append(step)
            seen_steps.add(step_key)

    return final_plan

# --- Example Usage (v3) ---

if __name__ == "__main__":
    test_tasks = [
        "Refactor the `DataProcessor` class to use the new `ApiClient` interface defined in `utils/api.py`.",
        "Implement the `calculate_metrics` function in `reporting/core.py`. It should use the `fetch_data` utility from `common/data_utils.py`.", # Needs backticks for fetch_data
        "Fix the bug where `process_item(item)` fails if `item.id` is null in `processor.py`.", # Needs backticks
        "Migrate the authentication logic from `auth/legacy_auth.py` (using `LegacyAuthenticator`) to the new system in `services/auth_service.py` (using `NewAuthClient` interface). Update the user login endpoints in `api/v1/endpoints.py` to use the new service.",
        "Replace all calls to deprecated function `old_logger()` with `new_logging.log_message()` in the `analytics_module`." # Needs backticks
    ]

    # Add backticks for missing symbols in test cases for better demonstration
    test_tasks[1] = "Implement the `calculate_metrics` function in `reporting/core.py`. It should use the `fetch_data` utility from `common/data_utils.py`."
    test_tasks[2] = "Fix the bug where `process_item(item)` fails if `item.id` is null in `processor.py`."
    test_tasks[4] = "Replace all calls to deprecated function `old_logger()` with `new_logging.log_message()` in the `analytics_module`."


    for i, task in enumerate(test_tasks):
        print(f"--- Task {i+1} ---")
        print(f'\"{task}\"')
        print("-" * 30)
        generated_plan = generate_context_plan_v3(task)
        print(json.dumps(generated_plan, indent=2))
        print("\\n" + "=" * 40 + "\\n")