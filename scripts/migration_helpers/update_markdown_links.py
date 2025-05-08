#!/usr/bin/env python
import os
import re
import argparse
import json # For potential mapping file

# Placeholder for a script to update Markdown links after docs/ -> ai_docs/ migration.
# This is a complex task, especially recalculating relative paths.

# Example of what a mapping file might look like (docs_path_mapping.json):
# {
#   "docs/DEVELOPER_GUIDE.md": "ai_docs/onboarding/developer_guide.md",
#   "docs/architecture/diagram.png": "ai_docs/architecture/assets/diagram.png",
#   "docs/standards/": "ai_docs/protocols_and_standards/"
# }
PATH_MAPPING_FILE = "specs/verification/docs_path_mapping.json" # Agent 1/4 to ensure this is created
# TODO (Agent 6): This script critically depends on a comprehensive and accurate PATH_MAPPING_FILE.
# Agent 1/4 needs to finalize the detailed file-by-file migration plan for all content from `docs/` to `ai_docs/`
# and populate `docs_path_mapping.json`. Example entries are illustrative; the actual file needs to be exhaustive.
# UPDATE: Agent 1/Co-Captain has created an initial version of docs_path_mapping.json. Agent 6 to refine this script further.

# Regex to find markdown links: [text](url)
MD_LINK_PATTERN = re.compile(r"(\[[^\]]+\]\()([^\)]+)(\))")

SEARCH_DIRECTORIES_MD = ["ai_docs", "src", "tests"] # Directories to scan for .md files

def update_links_in_md_file(filepath, path_mapping, dry_run=True):
    """Updates Markdown links in a single file based on path_mapping."""
    changes_made = False
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        new_content = content
        offset = 0

        for match in MD_LINK_PATTERN.finditer(original_content):
            link_text_full = match.group(1) # e.g., "["
            original_url = match.group(2)
            link_suffix_full = match.group(3) # e.g., ")"
            
            # Skip absolute URLs (http, https, mailto) and pure anchor links (#)
            if original_url.startswith(("http://", "https://", "mailto:", "#")):
                continue

            # This is where the complex logic for resolving and re-calculating paths goes.
            # 1. Resolve original_url to an absolute path based on `filepath`.
            # 2. Check if this absolute path (or a prefix of it) is in `path_mapping` keys.
            # 3. If yes, determine the new absolute path from `path_mapping` values.
            # 4. Convert this new absolute path to be relative to `filepath`.
            # For this placeholder, we'll do a very simple direct lookup for exact matches
            # and assume target paths in mapping are already correct relative/absolute forms needed.
            
            new_url = original_url # Default to no change
            found_in_mapping = False

            # Highly simplified placeholder logic:
            # A real implementation needs to handle relative paths, directory mappings, etc.
            if original_url in path_mapping: # Exact match in mapping keys
                new_url = path_mapping[original_url]
                found_in_mapping = True
            else:
                # Attempt to see if original_url starts with a mapped directory
                for old_dir, new_dir in path_mapping.items():
                    if old_dir.endswith("/") and original_url.startswith(old_dir):
                        new_url = original_url.replace(old_dir, new_dir, 1)
                        found_in_mapping = True
                        break
            
            if found_in_mapping and new_url != original_url:
                # Actual replacement in new_content requires careful handling of offsets if doing multiple replaces
                # For simplicity, this placeholder might misbehave on multiple links in one line if not careful
                # A better approach is to build a list of changes and apply them once.
                start, end = match.span(2) # Get span of the URL part
                # Adjust for previous replacements in the same line
                current_match_start_in_new = start + offset
                current_match_end_in_new = end + offset
                
                # Replace in new_content string
                new_content = new_content[:current_match_start_in_new] + new_url + new_content[current_match_end_in_new:]
                offset += len(new_url) - len(original_url)
                
                changes_made = True
                print(f"  - In {filepath}: Replaced '{original_url}' with '{new_url}'")

        if changes_made and not dry_run:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"  - Updated file: {filepath}")
        elif changes_made and dry_run:
            print(f"  - DRY-RUN: Would update file: {filepath}")
        
        return changes_made

    except Exception as e:
        print(f"Error processing file {filepath}: {e}")
        return False

def find_and_update_md_files(root_dirs, path_mapping, dry_run=True):
    if not path_mapping:
        print("Error: Path mapping is empty or not loaded. Cannot update links.")
        print(f"Ensure {PATH_MAPPING_FILE} exists, is valid JSON, and is populated.")
        return

    print(f"Starting Markdown link update scan in: {root_dirs} using mapping from {PATH_MAPPING_FILE}")
    # ... (similar file walking logic as update_python_imports.py) ...
    files_processed_count = 0
    files_changed_count = 0

    for root_dir in root_dirs:
        for dirpath, _, filenames in os.walk(root_dir):
            if ".git" in dirpath or ".venv" in dirpath: # Skip .git and .venv
                continue
            for filename in filenames:
                if filename.endswith(".md"):
                    filepath = os.path.join(dirpath, filename)
                    files_processed_count +=1
                    if update_links_in_md_file(filepath, path_mapping, dry_run=dry_run):
                        files_changed_count +=1
    
    print(f"Finished Markdown link update scan.")
    print(f"Files processed: {files_processed_count}")
    print(f"Files changed (or would change in dry-run): {files_changed_count}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update Markdown links after project reorganization.")
    parser.add_argument("--execute", action="store_true", help="Actually execute the file changes. Defaults to dry-run.")
    parser.add_argument("--mapping_file", default=PATH_MAPPING_FILE, help=f"Path to the JSON mapping file for old to new doc paths. Defaults to {PATH_MAPPING_FILE}")
    args = parser.parse_args()

    doc_path_mapping = {}
    try:
        with open(args.mapping_file, 'r') as f:
            doc_path_mapping = json.load(f)
        print(f"Loaded path mapping from {args.mapping_file}")
        if not doc_path_mapping:
            print(f"Warning: Mapping file {args.mapping_file} was loaded but is empty. Link updates will likely do nothing.")
    except FileNotFoundError:
        print(f"Error: Mapping file {args.mapping_file} not found. Please create it or verify path.")
        exit(1)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {args.mapping_file}: {e}")
        exit(1)

    find_and_update_md_files(SEARCH_DIRECTORIES_MD, doc_path_mapping, dry_run=not args.execute) 