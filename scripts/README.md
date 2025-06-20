# Dream.OS Tools

This directory contains various utilities and tools used in the Dream.OS project.

## Context Management Tools

These tools implement the [Context Management Protocol](../runtime/agent_comms/governance/protocols/CONTEXT_MANAGEMENT_PROTOCOL.md), which establishes a framework for planning, context switching, and managing large operational state in Dream.OS agents.

### context_manager.py

This utility helps manage context boundaries between planning phases by handling git commits and devlog entries when context forks occur.

#### Usage:

```bash
# Fork context - create a commit, add a devlog entry, and optionally update episode metadata
python tools/context_manager.py fork --agent <AGENT_ID> --planning-step <STEP> \
  --source "<SOURCE_CONTEXT>" --target "<TARGET_CONTEXT>" --reason "<REASON>" \
  [--episode <EPISODE_ID>] [--no-commit] [--tags <TAG1> <TAG2>]

# Example: Create a context fork for Agent-5 transitioning from Planning to Feature Documentation
python tools/context_manager.py fork --agent 5 --planning-step 2 \
  --source "Strategic Planning" --target "Feature Documentation" \
  --reason "Completed tech stack analysis, moving to feature specification" \
  --episode 08 --tags planning feature_documentation
```

### update_planning_tags.py

This utility adds or updates planning_step tags in episode YAML files and tasks to comply with the Planning + Context Management Protocol.

#### Usage:

```bash
# Update episode with planning stage
python tools/update_planning_tags.py episode <EPISODE_ID> --planning-stage <STAGE>

# Update all tasks with planning step
python tools/update_planning_tags.py tasks --planning-step <STEP> [--task-filter <FILTER>]

# Update both episode and tasks
python tools/update_planning_tags.py both <EPISODE_ID> --planning-stage <STAGE>

# Example: Update Episode 08 and all its tasks to Planning Stage 2
python tools/update_planning_tags.py both 08 --planning-stage 2
```

## Other Tools

### validate_json_schema.py

Validates JSON files against their corresponding schema definitions.

#### Usage:

```bash
python tools/validate_json_schema.py <JSON_FILE> <SCHEMA_FILE>
``` 