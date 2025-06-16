# Deduplication and Cleanup Plan

This document outlines how to reduce duplicate files, remove orphaned code, and simplify the directory layout.

## 1. Use Existing Deduplication Reports
- Review `deduplication_tasks.md` which lists directories with the highest duplicate counts. Prioritize cleanup starting from the top of that list.
- Follow the recommended process:
  - Consolidate redundant versions and delete obsolete or temporary files.
  - Re-run `python deduplication_scanner.py` after each cleanup pass to verify progress.

## 2. Remove Confirmed Obsolete Files
- Files listed in `safe_to_delete.yaml` are confirmed obsolete. Delete them safely with `git rm` and commit the removal.
- Clean up archived utils directories under `archive/orphans` and the empty `src/core/utils` folder.

## 3. Finalize Task and Episode File Locations
- According to `reorganization_plan.md`, all episode YAML files belong in `episodes/` and task lists in `runtime/tasks/`.
- Update code references and remove the duplicated originals as summarized in `REORGANIZATION_SUMMARY.md` once references are updated.

## 4. Identify Orphaned Files
- Generate an import graph and list orphaned files using the tasks in `runtime/validation/pending_tasks_agent1.json`.
- Export the orphan list to `audit/orphaned-files.json` and summarize findings in `audit/summary.md`.

## 5. Simplify Directory Structure
- Follow the directory-structure tasks in `pending_tasks_agent1.json` to move feature code under `src/features` and shared utilities under `src/shared`.
- Update imports accordingly and commit each structural change.

## 6. Remove Unused Archives and Backups
- Prune old backups under `archive/` once important content is migrated or verified.
- Keep a minimal archive of essential historical documents only.

## 7. Validate and Document
- After cleanup, run lint and tests to ensure everything still works.
- Document final directory layout and conventions in the project README and supporting docs.
