#!/usr/bin/env python3
import json
import sys

def deduplicate_by_description(input_file: str, output_file: str):
    seen_descriptions = set()
    unique_tasks = []
    original_count = 0

    try:
        with open(input_file, "r", encoding="utf-8") as infile:
            data = json.load(infile)
            original_count = len(data)
            for task in data:
                desc = task.get("description")
                if desc is not None and desc not in seen_descriptions:
                    seen_descriptions.add(desc)
                    unique_tasks.append(task)
    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found.", file=sys.stderr)
        return False
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from '{input_file}': {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        return False

    try:
        with open(output_file, "w", encoding="utf-8") as outfile:
            json.dump(unique_tasks, outfile, indent=2)
    except Exception as e:
        print(f"Error writing to output file '{output_file}': {e}", file=sys.stderr)
        return False

    print(f"Deduplication complete.")
    print(f"Original tasks: {original_count}")
    print(f"Unique tasks (by description): {len(unique_tasks)}")
    print(f"Output written to: {output_file}")
    return True

if __name__ == "__main__":
    input_path = "_agent_coordination/tasks/master_task_list.json"
    output_path = "_agent_coordination/tasks/master_task_list_deduped.json"
    if deduplicate_by_description(input_path, output_path):
        # Optional: Replace original with deduped file (use with caution)
        # import os
        # try:
        #     os.replace(output_path, input_path)
        #     print(f"Replaced '{input_path}' with deduplicated version.")
        # except OSError as e:
        #     print(f"Error replacing file: {e}", file=sys.stderr)
        pass # Keep the deduped file separate for now
    else:
        sys.exit(1) 