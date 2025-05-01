Task: Refactor and organize the core/ directory for Dream.OS into a clean modular structure.
Context:
  current_core_grabbag:
    - utils
    - coordination
    - services
    - hooks
    - agents
    - chat_engine
    - monitoring
    - gui
    - rendering
    - memory
    - llm_bridge
    - tools
Instructions:
  - Create new grouped subfolders under core/ such as:
      - core/agents/
      - core/services/
      - core/utils/
      - core/memory/
      - core/chat_engine/
      - core/rendering/
      - core/hooks/
      - core/monitoring/
      - core/llm_bridge/
      - core/tools/
  - Move corresponding files into their new logical subfolders using git mv to preserve history.
  - Update all intra-core imports to match new paths.
  - Update any external project-wide imports that reference core/ files.
  - Remove orphaned files or legacy stubs after consolidation (optional stretch goal).
  - Validate that all modules and imports are functioning after refactor.
  - Prepare a clean git commit summarizing the entire move.
