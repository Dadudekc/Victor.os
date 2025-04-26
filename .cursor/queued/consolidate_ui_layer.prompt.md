Task: Consolidate split GUI layers in Dream.OS into a single unified ui/ package.
Context:
  duplication_issue:
    - core/gui/ and ui/ both exist with duplicate main_window.py, state handling, and tests.
Instructions:
  - Move/migrate all working components from core/gui/ into ui/.
  - Collapse duplicate files: keep only one main_window.py, state logic, and common components.
  - Refactor all imports throughout project to reference the new ui/ package structure.
  - Update or delete old tests under tests/core/gui/ to point at new ui/ system.
  - Refactor stale fragment tabs to use unified shared components from ui/.
  - Clean up orphaned, redundant, or dead code as necessary.
  - Validate all functionality and tests pass after consolidation.
  - Prepare clean git commit after restructuring.

Recommended Git Commit:
    git add .
    git commit -m "Consolidate GUI into unified ui/ package; remove core/gui duplication; update imports and tests" 