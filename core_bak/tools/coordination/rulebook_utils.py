import datetime
from pathlib import Path
import sys
import os
import yaml
import re

# --- Constants --- # 
# Define paths relative to this script's location
TOOLS_DIR = Path(__file__).parent.resolve()
WORKSPACE_ROOT = TOOLS_DIR.parent # Assumes tools/ is one level down from root
DEFAULT_RULEBOOK_PATH = WORKSPACE_ROOT / "rulebook.md"

# --- Rule Formatting --- #
def format_rule(agent_name: str, stall_category: str, detected_issue: str, proposed_fix: str, timestamp: datetime.datetime) -> str:
    """Formats the details of a stall into a Markdown rule entry."""
    
    timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
    
    # Basic conversion of category to a condition phrase
    condition_map = {
        "LOOP_BREAK": f"Agent `{agent_name}` stalled due to potential loop break or passive mode.",
        "NO_INPUT": f"Agent `{agent_name}` stalled awaiting user input without fallback.",
        "MISSING_CONTEXT": f"Agent `{agent_name}` stalled likely due to missing context.",
        "NEEDS_TASKS": f"Agent `{agent_name}` stalled due to lack of assigned tasks.",
        "UNCLEAR_OBJECTIVE": f"Agent `{agent_name}` stalled with unclear objective."
    }
    condition = condition_map.get(stall_category, f"Agent `{agent_name}` stalled (Category: {stall_category}).")
    
    # Clean up detected issue for Markdown
    issue_snippet = detected_issue.strip().replace("\n", " ").replace("`", "'")[:200]
    
    # Use the proposed fix from context as the core rule action
    rule_action = proposed_fix.strip()
    if not rule_action.endswith("."):
        rule_action += "."
        
    # Use a simple rule counter (based on existing entries) for numbering
    # Note: This requires reading the file, which we do in the add_rule function.
    # Placeholder for now, will be calculated later.
    rule_number_placeholder = "[Auto-Generated Rule #X]"
        
    rule_md = f"\n---\n## {rule_number_placeholder}\n\n" \
              f"**Condition:** {condition}\n" \
              f"**Detected Issue Snippet:** `{issue_snippet}...`\n" \
              f"**Proposed Rule/Action:** {rule_action}\n\n" \
              f"*Metadata:*\n" \
              f"  - **Source:** Auto-generated by `rulebook_utils.py`\n" \
              f"  - **Agent:** {agent_name}\n" \
              f"  - **Stall Category:** {stall_category}\n" \
              f"  - **Timestamp:** {timestamp_str}\n"
              
    return rule_md

# --- Rule Addition --- #
def add_rule(agent_name: str, stall_category: str, detected_issue: str, proposed_fix: str, rulebook_path: Path = DEFAULT_RULEBOOK_PATH):
    """Generates a rule based on input and appends it to the rulebook file."""
    
    timestamp = datetime.datetime.now(datetime.timezone.utc)
    new_rule_md_template = format_rule(agent_name, stall_category, detected_issue, proposed_fix, timestamp)
    
    # Ensure the directory exists
    rulebook_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Read existing content to find the next rule number and check for duplicates (basic check)
    existing_content = ""
    next_rule_number = 1
    try:
        if rulebook_path.is_file():
            existing_content = rulebook_path.read_text(encoding='utf-8')
            # Very basic check for existing rule number headers
            rule_headers = [line for line in existing_content.splitlines() if line.startswith("## [Auto-Generated Rule #")]
            if rule_headers:
                 # Extract last number and increment
                 try:
                     last_num_str = rule_headers[-1].split('#')[1].split(']')[0]
                     next_rule_number = int(last_num_str) + 1
                 except (IndexError, ValueError):
                     print(f"Warning: Could not parse last rule number from {rulebook_path}. Starting from 1.", file=sys.stderr)
                     # Fallback, but ideally log this or handle more robustly
            
            # Basic duplicate check (naive check based on condition and action)
            # A more robust check would involve parsing the markdown properly or using hashes
            check_str = f"**Condition:** {format_rule.__defaults__[0]}".split('{')[0] # Get start of condition
            if f"**Condition:** {condition_map.get(stall_category)}" in existing_content and f"**Proposed Rule/Action:** {proposed_fix.strip()}" in existing_content:
                 print(f"Info: Potentially similar rule found for agent {agent_name}, category {stall_category}. Skipping append.")
                 return False # Indicate that no rule was added
                     
    except Exception as e:
        print(f"Warning: Could not read or parse existing rulebook {rulebook_path}: {e}", file=sys.stderr)
        # Continue with rule number 1

    # Finalize the rule markdown with the correct number
    new_rule_md = new_rule_md_template.replace("[Auto-Generated Rule #X]", f"[Auto-Generated Rule #{next_rule_number}]")

    # Append the new rule
    try:
        with rulebook_path.open("a", encoding='utf-8') as f:
            f.write(new_rule_md)
        print(f"✅ Successfully appended rule #{next_rule_number} for agent {agent_name} to {rulebook_path}")
        return True # Indicate success
    except Exception as e:
        print(f"Error: Could not append rule to {rulebook_path}: {e}", file=sys.stderr)
        return False # Indicate failure

# --- Example Usage (can be run directly for testing) --- # 
if __name__ == "__main__":
    print("Testing rulebook_utils.py...")
    
    # Example data mimicking recovery context output
    test_agent = "TestAgent"
    test_category = "LOOP_BREAK"
    test_issue = "Agent seems stuck repeating the same action without progress. Log shows repeated 'Processing item X' messages."
    test_fix = "Implement a counter or state check to break the loop after N iterations. Ensure item status is updated correctly."
    
    rulebook_file = WORKSPACE_ROOT / "test_rulebook.md"
    print(f"Using test rulebook file: {rulebook_file}")
    
    # Clean up test file if it exists
    if rulebook_file.exists():
        rulebook_file.unlink()
        
    # Add a first rule
    success1 = add_rule(test_agent, test_category, test_issue, test_fix, rulebook_path=rulebook_file)
    
    # Add another rule
    success2 = add_rule("AnotherAgent", "NO_INPUT", "Agent waiting indefinitely for user prompt.", "Check task queue or default behavior if user is idle.", rulebook_path=rulebook_file)
    
    # Try adding the first rule again (should be skipped by basic duplicate check)
    success3 = add_rule(test_agent, test_category, test_issue, test_fix, rulebook_path=rulebook_file)
    
    print("\nTest rulebook content:")
    if rulebook_file.exists():
        print(rulebook_file.read_text(encoding='utf-8'))
    else:
        print("Test rulebook file not created.")
        
    # Basic assertion for testing
    assert success1 is True
    assert success2 is True
    assert success3 is False # Expecting the duplicate to be skipped
    print("\nTest completed successfully (basic checks passed).")

# --- Rule Loading and Parsing ---

def parse_yaml_block(yaml_string: str) -> dict | None:
    """Safely parses a YAML block string into a dictionary."""
    try:
        # Ensure proper indentation might be needed depending on source format
        data = yaml.safe_load(yaml_string)
        if isinstance(data, dict):
            # Handle potential single-list wrapping from some markdown parsers
            if 'rules' in data and isinstance(data['rules'], list) and len(data['rules']) == 1:
                 return data['rules'][0] 
            return data
        else:
            logger.warning(f"Parsed YAML block is not a dictionary: {yaml_string[:100]}...")
            return None
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML block: {e}\nBlock content:\n{yaml_string}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Unexpected error parsing YAML: {e}", exc_info=True)
        return None


def load_rules(rulebook_path: Path, load_full_yaml=False) -> dict:
    """Loads rules from the rulebook markdown file.
    
    Args:
        rulebook_path: Path object for the rulebook.md file.
        load_full_yaml: If True, attempts to parse the full YAML block 
                          for each rule and stores it under 'yaml_data'. 
                          Otherwise, only extracts ID and locked status.
                          
    Returns:
        A dictionary where keys are rule IDs and values are dictionaries
        containing at least {'id': rule_id, 'locked': bool}.
        If load_full_yaml is True, the value dict may also contain 'yaml_data'.
    """
    rules = {}
    if not rulebook_path.is_file():
        logger.error(f"Rulebook file not found: {rulebook_path}")
        return rules

    try:
        content = rulebook_path.read_text(encoding='utf-8')
        
        # Regex to find rule blocks starting with ### and potentially containing YAML
        # It captures the rule ID from the markdown line AND the optional YAML block
        rule_pattern = re.compile(
            r"^###.*?\n" + # Header line
            r"^-\s*\*\*ID:\*\*\s*([\w\-]+).*?\n" + # ID line (Capture Group 1)
            r"(.*?)" + # Optional description lines (Capture Group 2)
            r"(?:^```yaml\s*\n(.*?)^```\s*\n)?", # Optional YAML block (Capture Group 3)
            re.MULTILINE | re.DOTALL
        )

        for match in rule_pattern.finditer(content):
            rule_id = match.group(1)
            yaml_block_str = match.group(3)
            
            if rule_id in rules:
                 logger.warning(f"Duplicate rule ID '{rule_id}' found in rulebook. Overwriting.")
                 
            rule_data = {"id": rule_id, "locked": False} # Default locked to False
            
            if yaml_block_str:
                yaml_data = parse_yaml_block(yaml_block_str.strip())
                if yaml_data:
                    # Check for 'locked: true' within the parsed YAML
                    if yaml_data.get('locked') == True: # Explicit check for True
                        rule_data["locked"] = True
                    if load_full_yaml:
                         rule_data["yaml_data"] = yaml_data
            else:
                # Check description lines for simple lock flags if needed?
                # E.g., if a line contains "[LOCKED]"?
                pass

            rules[rule_id] = rule_data
            logger.debug(f"Loaded rule: ID={rule_id}, Locked={rule_data['locked']}")

        logger.info(f"Loaded {len(rules)} rules from {rulebook_path}.")
        
    except FileNotFoundError:
        logger.error(f"Rulebook file not found during processing: {rulebook_path}") # Should be caught above
    except Exception as e:
        logger.error(f"Error reading or parsing rulebook {rulebook_path}: {e}", exc_info=True)
        
    return rules 