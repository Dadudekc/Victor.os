# Phase 1: Developer Notes Overview

## Project Structure Enforcement Guidelines

## Phase 5: Core Migrations & Refactoring

### 5.6 Core Flatten: AgentBus and Utils
--- 
# Developer Notes: Memory & Feedback Module Consolidation
# Phase 1: Consolidation & Migration

## Summary

### 1. Placeholder Removal
### 1.1 Placeholder Removal
### 2. Memory Modules
### 1.2 Memory Module Migration
### 3. Feedback Modules
### 1.3 Feedback Module Migration
### 4. Import Normalization
### 1.4 Import Normalization
### 5. Validation
### 1.5 Validation
### 5.1 Broadcast Validation Enhancements
### 1.5.1 Broadcast Validation Enhancements
### 6. Memory Layer Migration
### 1.6 Unified Memory Manager Migration
### 7. Memory Test Expansion
### 1.7 Memory Test Expansion

**Next steps**: run full `pytest` suite to validate.

# Phase 2: Test Coverage & System Behavior

## Missing Test Coverage

### 1. MemoryManager
### 2.1 MemoryManager Test Gaps
### 2. DatabaseManager
### 2.2 DatabaseManager Test Gaps
### 3. UnifiedMemoryManager
### 2.3 UnifiedMemoryManager Test Gaps
### 4. ResilientChatScraper
### 2.4 ResilientChatScraper Test Gaps
### 5. CursorInteractionVerifier
### 2.5 CursorInteractionVerifier Test Gaps
### 6. CycleHealthMonitor
### 2.6 CycleHealthMonitor Test Gaps

## Escalated Agents Tab

## Coordination Package Flatten
### 1.8 Coordination Package Flatten

---
End of consolidation notes.

## Escalation System

## Escalation System

# Phase 3: Event System & Core Migration

## Phase 3 Core-to-Src Migration

Phase 3 migration complete and validated via full pytest run.

---
## Phase 2: Modularization Plan

### 2.1 Proposed Service/Module Boundaries
### 2.2 Proposed Target Directory Structure
### 2.3 Proposed Refactor Batches
### 2.4 Modularization Next Steps

## Automation Module

### Entry Point
### 3.1 Automation Entry Point
### AgentBus Events
### 3.2 Automation AgentBus Events
### System Event Types
### 3.3 System Event Types
### PROMPT_SUCCESS
### PROMPT_FAILURE
### CHATGPT_SCRAPE_SUCCESS
### CHATGPT_SCRAPE_FAILED

**Integration Complete**: CycleHealthMonitor's event-bus subscription for scrape health auto-tracking is finished and production-ready.

---
*End of developer notes.*

## Expanded Test Coverage

- **Full Test Suite Enabled**:
- **AgentBus & AgentStatus** (`tests/core/coordination/test_agent_bus.py`):
- **EventDispatcher** (`tests/core/coordination/test_dispatcher.py`):
- **Task Utilities** (`tests/utils/test_task_utils.py`):

### 4.1 Task Update Hardening

## Automation Supervisor Agent

### Dashboard UI Metadata Display

### Dashboard Health Chart Polish

*End of developer notes.*

## Phase 4: TaskUtils Hardening

## CLI Help Stabilization

### 4.1 Threshold Breach Warnings

### 4.2 Persistent Breach Badges

## Release v0.2.1

### 4.3 Legacy Test Migration

## Structural Enforcement Guidelines

## Phase 5: Social Project Merge

## Phase 5.7: Legacy Agents Cleanup

## Phase 5.2: CLI & Artifact Consolidation

## Phase 3.6: Script & Tool Consolidation

## Phase 5.5: Source Structure Normalization
Date: 2024-06-XX

- Relocated stray files from `src/dreamos/` root into appropriate subpackages:
  - `agent_utils.py` → `services/utils/gui_utils.py` (and fixed path const)
  - `FileManager.py` → `services/utils/file_manager.py`
  - `config.py` → `services/config.py`
  - `agent_bus.py` → `coordination/agent_bus_shim.py`
  - `login_utils.py` → `services/utils/login_utils.py`
  - `orchestrator.py` → `coordination/orchestrator.py`
  - `thea_orchestrator.py` → `coordination/thea_orchestrator.py`
  - `voice_engine.py` → `services/voice_engine.py`
- Migrated modules from redundant `src/dreamos/core/` into main packages:
  - `core/utils/agent_utils.py` → `agents/utils.py`
  - `core/coordination/base_agent.py` → `agents/base_agent.py`
  - `core/coordination/message_patterns.py` → `coordination/message_patterns.py`
  - `core/utils/performance_logger.py` → `services/utils/performance_logger.py`
- Deleted `src/dreamos/core/` directory.
- Updated import paths across `src/dreamos/` and `tests/` to reflect changes.