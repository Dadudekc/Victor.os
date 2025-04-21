# Cleanup Audit Report

This report summarizes deprecated or unused code removed from the `Dream.os` codebase under `_agent_coordination` and project root.

## Removals

1. **Agents Directory**: Deleted `_agent_coordination/agents/` (empty stubs, not referenced).
2. **Bridge Adapters**: Removed `_agent_coordination/bridge_adapters/` (unused `CursorBridgeAdapter`).
3. **Legacy Archives**: Archived or removed legacy prompt files under `prompt_library/archive/`.
4. **Quorum Simulation**: Flag `_agent_coordination/quorum_web_simulation.py` as archive candidate (no tests).
5. **Web Council**: `_agent_coordination/web_council/` folder removed (or to be archived).
6. **Chrome Profiles & Logs**: Clean up `chrome_profile/`, `cookies/`, `logs/` directories (environment artifacts).

## Consolidations

- Prompts are now grouped by genre under `prompt_library`: 
  - `autonomy/`, `cleanup/`, `coordination/`, `onboarding/`, `testing/`.
- Protocols remain in `protocols/`, proposals in `proposals/`.

## Next Steps

1. **Generate Pending Tasks**: Export current pending and blocked tasks to `tasks/complete/pending_tasks.json`.
2. **CI Integration**: Run the CI pipeline to validate no broken imports or overlooked references.
3. **High-Priority Task List**: Classify any remaining cleanup actions under high/medium/low and human-only categories.
4. **Documentation**: Archive deprecated scripts in `docs/archive/` and remove from main source tree.
5. **Finalize PR**: Bundle these changes under `chore(cleanup): prune deprecated modules and directories`. 