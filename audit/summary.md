# Project Audit Summary
Generated: 2025-04-28T23:43:07.191822+00:00

This report summarizes the findings of the automated project structure audit.

## 1. File Manifest
- Total files scanned in `src/`: 1961

## 2. Module Imports & Orphaned Files
- Total Python modules analyzed: 209
- Potentially orphaned Python modules found: 167
  - **Note:** Analysis based on AST parsing; requires manual verification.
  - **Files (first 10):**
    - `src/dreamos/FileManager.py`
    - `src/dreamos/agent_bus.py`
    - `src/dreamos/agents/agent2_infra_surgeon.py`
    - `src/dreamos/agents/agent9_response_injector.py`
    - `src/dreamos/agents/agents/task_executor_agent.py`
    - `src/dreamos/agents/agents/tool_executor_agent.py`
    - `src/dreamos/agents/autofix_agent.py`
    - `src/dreamos/agents/chatgpt_web_agent.py`
    - `src/dreamos/agents/context_router_agent.py`
    - `src/dreamos/agents/cursor_dispatcher.py`
    - ... (see `orphaned-files.json` for full list)

## 3. Domain Classification
- Files classified by domain based on path:
  - `app_dreamscape`: 16 files
  - `app_social`: 1651 files
  - `asset`: 3 files
  - `core_dreamos`: 282 files
  - `core_src_root`: 2 files
  - `tooling`: 7 files
  - (See `domains.json` for details)

## 4. Asset Usage
- Potentially unreferenced assets found (count=0 in usage scan): 0
  - All identified assets had at least one potential reference found in the code scan.
