import argparse
import json
import os
import re
from datetime import datetime

# Placeholder for actual checklist structure if needed for more complex validation
# For now, we'll rely on regex and section parsing.
EXPECTED_SECTIONS = {
    "Section 1: Core Identity & Foundational Principles": [
        "1.1. Read and Internalize Core Identity Protocol",
        "1.2. Understand the \"Existing Architecture First\" Principle",
        "1.3. Understand Autonomous Initiative (NEW ITEM)"
    ],
    "Section 2: Operational Loop & Daily Workflow": [
        "2.1. Read and Internalize Agent Operational Loop Protocol",
        "2.2. Mailbox Management (Your Central Workstation)",
        "2.3. Task Management & Execution",
        "2.4. Self-Validation & Quality Control",
        "2.5. Git Workflow & Committing Standards",
        "2.6. Proactive Task Generation (Autonomy Initiative)",
        "2.7. Continuous Operational Loop"
    ],
    "Section 3: Tools, Resources, & System Knowledge": [
        "3.1. Personal Tools",
        "3.2. Key System Documents & Paths for Review"
    ],
    "Section 4: Acknowledgment & Commitment": [
        # Specific items to check for acknowledgement
    ]
}

# Regex to find checked items, e.g., "[x]" or "[X]"
CHECKED_ITEM_REGEX = r"\[\s*x\s*\]"
# Regex to find Agent ID placeholder
AGENT_ID_PLACEHOLDER_REGEX = r"<Assigned_Agent_ID_Here>"
# Regex to find Date placeholder
DATE_PLACEHOLDER_REGEX = r"{{YYYY-MM-DD}}"
# Regex for Agent Signature
AGENT_SIGNATURE_REGEX = r"Agent-(.*?)_ONBOARDING_COMPLETE_(\d{8})"


def parse_checklist_content(content: str, agent_id: str):
    """
    Parses the content of a checklist file.
    Validates sections, checked items, and specific fields like Agent ID and signature.
    """
    errors = []
    warnings = []
    parsed_data = {
        "agent_id_in_doc": None,
        "onboarding_date_in_doc": None,
        "signature_agent_id": None,
        "signature_date": None,
        "sections_status": {},
        "all_items_checked_overall": True, # Assume true, set to false if any unchecked
        "placeholders_filled": True
    }

    # Basic placeholder checks
    if re.search(AGENT_ID_PLACEHOLDER_REGEX, content):
        warnings.append("Agent ID placeholder '<Assigned_Agent_ID_Here>' found. Should be filled.")
        parsed_data["placeholders_filled"] = False
    if re.search(DATE_PLACEHOLDER_REGEX, content):
        warnings.append("Date placeholder '{{YYYY-MM-DD}}' found. Should be filled.")
        parsed_data["placeholders_filled"] = False

    # Extract Agent ID and Date from the header if filled
    agent_id_match = re.search(r"\*\*Agent ID:\*\*\s*`?([^`\n]+)`?", content)
    if agent_id_match:
        parsed_data["agent_id_in_doc"] = agent_id_match.group(1).strip()
        expected_doc_agent_id = agent_id.replace("agent-", "") # e.g., Agent-1
        if parsed_data["agent_id_in_doc"] == "<Assigned_Agent_ID_Here>":
             errors.append(f"Checklist Agent ID is still placeholder: {parsed_data['agent_id_in_doc']}")
        elif parsed_data["agent_id_in_doc"] != expected_doc_agent_id:
            errors.append(f"Checklist Agent ID mismatch. Expected based on input: '{expected_doc_agent_id}', Found in doc: '{parsed_data['agent_id_in_doc']}'")


    onboarding_date_match = re.search(r"\*\*Onboarding Date:\*\*\s*`?([^`\n]+)`?", content)
    if onboarding_date_match:
        parsed_data["onboarding_date_in_doc"] = onboarding_date_match.group(1).strip()
        if parsed_data["onboarding_date_in_doc"] == "{{YYYY-MM-DD}}":
            errors.append(f"Checklist Onboarding Date is still placeholder: {parsed_data['onboarding_date_in_doc']}")


    # Section-based validation
    current_section_name = None
    lines = content.splitlines()
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        
        if line_stripped.startswith("## Section"):
            try:
                section_title_full = line_stripped.replace("## ", "", 1).strip()
                if not re.match(r"Section \d+: .+", section_title_full):
                    warnings.append(f"Potentially malformed section header: {line_stripped}")
                    current_section_name = None # Don't process items under a malformed header
                    continue 
                current_section_name = section_title_full
            except Exception as e:
                warnings.append(f"Error parsing section header '{line_stripped}': {e}")
                current_section_name = None
                continue
            
            if current_section_name not in parsed_data["sections_status"]:
                 parsed_data["sections_status"][current_section_name] = {"all_checked": True, "items": []}

        elif line_stripped.startswith("*   [ ]") or line_stripped.startswith("*   [x]") or line_stripped.startswith("*   [X]"):
            is_checked = bool(re.search(CHECKED_ITEM_REGEX, line_stripped))
            item_text = line_stripped[len("*   [ ] "):].strip()
            
            if current_section_name and current_section_name in parsed_data["sections_status"]: # Ensure current_section_name is valid
                parsed_data["sections_status"][current_section_name]["items"].append({
                    "text": item_text,
                    "checked": is_checked
                })
                if not is_checked:
                    parsed_data["sections_status"][current_section_name]["all_checked"] = False
                    parsed_data["all_items_checked_overall"] = False
            elif current_section_name: # current_section_name was set but not added to sections_status (e.g. malformed)
                 warnings.append(f"Skipping item under potentially malformed section '{current_section_name}': {item_text}")
            else:
                warnings.append(f"Found checklist item outside a section: {item_text}")

    # Validate all expected sections are present and checked
    for section, sub_items in EXPECTED_SECTIONS.items():
        if section not in parsed_data["sections_status"]:
            errors.append(f"Missing expected section: {section}")
            parsed_data["all_items_checked_overall"] = False # Missing section means not all checked
            continue
        if not parsed_data["sections_status"][section]["all_checked"]:
            errors.append(f"Not all items checked in section: {section}")
            # all_items_checked_overall already set by individual item checks

    # Signature validation
    signature_match = re.search(AGENT_SIGNATURE_REGEX, content)
    if signature_match:
        parsed_data["signature_agent_id"] = signature_match.group(1) # This captures the number, e.g., "1"
        parsed_data["signature_date"] = signature_match.group(2)
        
        # Extract agent number from Agent-X format (no longer need to handle agent-Agent-X format)
        cli_agent_number_part = agent_id.split('-')[-1] # Extracts "1" from "Agent-1"
        
        if parsed_data["signature_agent_id"] != cli_agent_number_part:
            errors.append(
                f"Signature Agent ID mismatch. Expected number: '{cli_agent_number_part}' (from CLI arg '{agent_id}'), Found in signature: '{parsed_data['signature_agent_id']}'"
            )
        try:
            datetime.strptime(parsed_data["signature_date"], "%Y%m%d")
        except ValueError:
            errors.append(f"Signature date format invalid: '{parsed_data['signature_date']}'. Expected YYYYMMDD.")
    else:
        errors.append("Agent signature missing or malformed. Example: Agent-X_ONBOARDING_COMPLETE_YYYYMMDD")

    return parsed_data, errors, warnings


def validate_checklist_file(filepath: str, agent_id: str):
    """
    Loads a checklist file and validates its content.
    """
    if not os.path.exists(filepath):
        return None, [f"Checklist file not found at {filepath}"], []

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return None, [f"Error reading checklist file {filepath}: {e}"], []

    return parse_checklist_content(content, agent_id)


def main():
    parser = argparse.ArgumentParser(description="Parse and validate Dream.OS Agent Onboarding Checklist.")
    parser.add_argument("filepath", help="Path to the AGENT_ONBOARDING_CHECKLIST.md file.")
    parser.add_argument("--agent_id", required=True, help="The official Agent ID (e.g., Agent-1).")
    parser.add_argument("--output_manifest", help="Optional path to save parsed checklist status (JSON).")
    
    args = parser.parse_args()

    parsed_data, errors, warnings = validate_checklist_file(args.filepath, args.agent_id)

    if parsed_data:
        print(f"Checklist parsing for Agent ID '{args.agent_id}' (File: {args.filepath})")
        print("\n--- Parsed Data ---")
        print(json.dumps(parsed_data, indent=2))

    if warnings:
        print("\n--- Warnings ---")
        for warning in warnings:
            print(f"- {warning}")
    
    if errors:
        print("\n--- Validation Errors ---")
        for error in errors:
            print(f"- {error}")
        print("\nChecklist INVALID.")
        exit_code = 1
    elif parsed_data: # No errors and parsed data exists
        print("\nChecklist VALID.")
        exit_code = 0
    else: # No parsed data, implies file not found or read error
        print("\nChecklist processing failed.")
        exit_code = 1


    if args.output_manifest and parsed_data:
        try:
            manifest_entry = {
                "agent_id": args.agent_id,
                "checklist_file": args.filepath,
                "parsed_at": datetime.utcnow().isoformat() + "Z",
                "is_valid": not errors,
                "errors": errors,
                "warnings": warnings,
                "data": parsed_data
            }
            # Basic manifest: append to a JSONL file
            mode = 'a' if os.path.exists(args.output_manifest) else 'w'
            with open(args.output_manifest, mode, encoding='utf-8') as f:
                f.write(json.dumps(manifest_entry) + "\n")
            print(f"Saved parsing status to {args.output_manifest}")
        except Exception as e:
            print(f"Error saving to manifest file {args.output_manifest}: {e}")
            
    return exit_code

if __name__ == "__main__":
    exit(main()) 