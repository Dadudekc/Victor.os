# filename: .cursor/queued/refactor_core_split_structure.prompt.md
Task: Move core/ files into properly structured src/dreamos/ subfolders; update imports accordingly
Context:
  core_structure_mapping:
    - core/agents/ → src/dreamos/agents/
    - core/services/ → src/dreamos/services/
    - core/utils/ → src/dreamos/utils/
    - core/memory/ → src/dreamos/memory/
    - core/chat_engine/ → src/dreamos/chat_engine/
    - core/rendering/ → src/dreamos/rendering/
    - core/hooks/ → src/dreamos/hooks/
    - core/monitoring/ → src/dreamos/monitoring/
    - core/llm_bridge/ → src/dreamos/llm_bridge/
    - core/tools/ → src/dreamos/tools/
    - core/gui/ → src/dreamos/ui/
    - core/config.py → src/dreamos/config.py
    - core/orchestrator.py → src/dreamos/orchestrator.py
    - core/agent_utils.py → src/dreamos/agent_utils.py
    - core/evaluator.py → src/dreamos/evaluator.py
Instructions:
  - Use `git mv` to move each folder/file, preserving history.
  - Update all Python imports from `core.*` to `dreamos.*`, matching new structure.
  - Run `pip install -e .` to validate installation.
  - Run `pytest` to ensure tests pass post-move.
  - Commit changes with:
    `git commit -m "Restructure core/ into organized src/dreamos/ subfolders; update imports project-wide; finalize modular packaging"` 