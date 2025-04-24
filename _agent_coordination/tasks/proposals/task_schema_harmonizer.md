## Task‐Schema Harmonizer Proposal

**Purpose**
Automatically validate, normalize, and migrate any task‐list JSON (master, runtime, discovered, etc.) to a canonical schema, detecting drift (e.g., title vs. action, realm, tags) and patching embedded code or malformed entries.

**Key Features**
- Schema definitions auto‐extracted from `master_task_list.json` and mailbox schemas.
- CLI command: `harmonize-schema <input.json> [--dry-run]` that outputs a unified file and a diff.
- Auto‐apply migrations (rename fields, remove trailing code blocks, reindent JSON) while preserving ordering and comments.
- Built‐in unit tests and a "watch" mode for live file validation.

**Benefits**
- Eliminates manual edits across multiple JSON task files.
- Keeps every task list consistent.
- Simplifies downstream agents' parsing logic and reduces errors. 