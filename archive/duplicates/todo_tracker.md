# Dream.OS Architectural/Deferred TODO Tracker

**Purpose:** Track significant TODOs identified during code sweeps that require architectural decisions, major implementation effort, cross-agent coordination, or are deferred to later phases. This prevents valuable but non-immediate tasks from being lost.

**Format:** `- [ ] FILE_PATH:LINE_NUMBER - DESCRIPTION (OWNER: THEA/AgentX/TBD)`

---

## Architectural / Core Systems

- [x] `src/dreamos/memory/maintenance_service.py:10` - Consider adding portalocker for inter-process file locking if needed (OWNER: THEA). **Decision:** Keep existing `dreamos.core.utils.file_locking.FileLock` (based on `python-filelock`) as it's already integrated, async-compatible, and sufficient. (Resolved by Agent8)
- [ ] `src/dreamos/memory/maintenance_service.py:12` - Consider adding apscheduler for background scheduling (OWNER: Agent8/TBD). **Recommendation:** Adopt `APScheduler` (`AsyncIOScheduler`) to replace the current `asyncio.sleep` loop for more robust scheduling. (Evaluated by Agent8)
- [ ] `src/dreamos/core/coordination/base_agent.py:98` - Centralize logger configuration (OWNER: TBD). **Progress:** Removed local config from `BaseAgent`. **Next Step:** Ensure `config.setup_logging()` is called once at app startup before agent init. (Analyzed by Agent8)
- [ ] `src/dreamos/core/coordination/event_types.py:3` - Standardize topic naming conventions further (OWNER: THEA). **Analysis:** Current usage mixes enums, constants, f-strings. **Proposal:** Adopt hierarchical dot-notation (`domain.entity.action.qualifier`), expand `EventType` enum, refactor usage. (Analyzed by Agent8)

## Feature Enhancements / Major Implementation

- [ ] `src/dreamos/agents/agent2_infra_surgeon.py:41` - Implement retry logic via AgentBus or local loop (OWNER: Agent4? Verify assignment)
- [ ] `src/dreamos/coordination/voting_coordinator.py:174` - Implement more sophisticated tally logic (OWNER: TBD)
- [ ] `src/dreamos/memory/maintenance_service.py:46` - Initialize scheduler if using apscheduler (OWNER: TBD - Depends on Arch choice) -> **Action:** Covered by implementing APScheduler recommendation above.
- [ ] `src/dreamos/memory/maintenance_service.py:90` - Load full config, find target files for maintenance (OWNER: TBD - Core maintenance logic)
- [ ] `src/dreamos/memory/maintenance_service.py:91` - Schedule self._run_maintenance_job regularly (OWNER: TBD - Core maintenance logic) -> **Action:** Covered by implementing APScheduler recommendation above.
- [ ] `src/dreamos/memory/maintenance_service.py:117` - Get policies for each file from config (OWNER: TBD - Core maintenance logic)
- [ ] `src/dreamos/memory/summarization_utils.py:73` - Load summarization policy from actual policy dict (OWNER: TBD - Part of maintenance/summarization implementation)
- [ ] `src/dreamos/services/utils/content/post_context_generator.py:43` - Integrate LLM call for context generation (OWNER: TBD - Requires LLM integration plan)
- [ ] `src/dreamos/integrations/*_client.py: various` - Implement actual client init, API calls, error handling (OWNER: Agent6 / Integration Team)
- [ ] `src/dreamos/gui/main_window.py:451` - integrate with core state loader or recovery agent flow (OWNER: TBD - GUI/State team)
- [ ] `src/dreamos/services/memory_maintenance_service.py:120` - Add logic to potentially skip agents or prioritize maintenance (OWNER: TBD - Feature enhancement)

## Minor Refactors / Lower Priority

- [ ] `src/dreamos/tools/analysis/project_scanner/project_scanner.py:50` - Move ProjectCache utility if needed elsewhere (OWNER: TBD - Low priority)
- [ ] `src/dreamos/agents/autofix_agent.py:83` - Revisit how frame info is retrieved (OWNER: Autofix Agent Owner - If relevant)
- [ ] `src/dreamos/tools/analysis/dead_code.py:93` - Add more robust parsing (OWNER: TBD - If needed for tool accuracy)

## Tool Placeholders (Likely Intentional)
- These `# TODO` markers appear to be placeholders within tool logic (e.g., `context_planner_tool.py`) indicating where generated code/content should go. They likely do not represent drift and should be ignored by this cleanup effort unless the tool itself is being refactored.
  - `src/dreamos/tools/functional/context_planner_tool.py:133`
  - `src/dreamos/tools/functional/context_planner_tool.py:165`
  - `src/dreamos/tools/functional/context_planner_tool.py:166`
  - `src/dreamos/tools/functional/context_planner_tool.py:180`
  - `src/dreamos/tools/functional/context_planner_tool.py:194`
  - `src/dreamos/tools/functional/context_planner_tool.py:210`
  - `src/dreamos/tools/functional/context_planner_tool.py:215`
