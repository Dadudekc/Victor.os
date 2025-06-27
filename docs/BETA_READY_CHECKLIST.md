# Dream.OS Beta-Ready Checklist & Implementation Plan

This checklist consolidates the work required to bring Dream.OS to a stable beta release. Items are derived from the PRD and 2025 roadmap.

-## Agent Infrastructure
- [x] **INFRA-001 Mailbox Locking**
  - ✅ `src/dreamos/core/comms/mailbox_utils.py` – ensure `write_mailbox_message` and `read_mailbox_messages` acquire locks
  - 🧪 Integration: `tests/integration/test_mailbox_locking.py`
  - 📊 Validate zero message loss under concurrent writes; coverage ≥80%
- [ ] **TASK-001 Task Board Locking**
  - ✅ `src/dreamos/tools/task_board_updater.py` – atomic writes with `filelock`
  - 🧪 Integration: `tests/integration/test_task_board_locking.py` (new)
  - 📊 Updates succeed with multiple writers (>95% success)
- [x] **LOOP-001 Planning Mode Check**
  - ✅ `src/dreamos/tools/agent_bootstrap_runner.py` – respect `PLANNING_ONLY_MODE`
  - 🧪 Unit: `tests/core/test_planning_only_mode.py`
  - 📊 Bootstrapping skips execution when variable set
- [x] **Agent Lifecycle Events**
  - ✅ `src/dreamos/agents/agent_manager.py` – `start_agent`, `pause_agent`, `resume_agent`, `terminate_agent`
  - 🧪 Unit: `tests/agents/test_agent_lifecycle.py`
  - 📊 State transitions logged; coverage ≥80%

## Planning & Context Management
- [ ] **Planning Phases** (`capture`, `plan`, `commit`, `evolve`)
  - ✅ `src/dreamos/tools/agent_bootstrap_runner.py` – `get_prompt_by_planning_step`
  - 🧪 Unit: `tests/core/test_planning_phases.py`
  - 📊 Each phase executed in order; >90% branch coverage
- [ ] **Context Fork Tracking**
  - ✅ `src/dreamos/tools/context_manager.py` – track context boundaries
  - 🧪 Unit: `tests/core/test_context_forks.py`
  - 📊 Fork events logged; no stale contexts
- [ ] **Devlog Sync**
  - ✅ `src/dreamos/tools/devlog_sync.py`
  - 🧪 Integration: `tests/integration/test_devlog_sync.py`
  - 📊 Devlog updates reflected within 1 cycle
- [ ] **Planning Step Tags & Validation Hooks**
  - ✅ `src/dreamos/coordination/tasks/task_manager_stable.py` – tag tasks with `planning_step`; hook `validate_task`
  - 🧪 Unit: `tests/coordination/test_validation_hooks.py`
  - 📊 Duplicate tasks detected; validation pass rate ≥90%

## Task System
- [ ] **Transaction Logging**
  - ✅ `src/dreamos/coordination/tasks/task_manager_stable.py` – append to `transaction_log.jsonl`
  - 🧪 Unit: `tests/coordination/test_transaction_logging.py`
  - 📊 All task changes logged; log integrity verified
- [ ] **Schema Validation**
  - ✅ `src/dreamos/agents/task_schema.py` and `TaskManager.validate_task`
  - 🧪 Unit: `tests/coordination/test_schema_validation.py`
  - 📊 Tasks conform to schema; failure rate <5%
- [ ] **Atomic Board Operations** (`backlog`, `ready`, `working`, `completed`)
  - ✅ `src/dreamos/coordination/tasks/task_manager_stable.py` – atomic moves with locks
  - 🧪 Integration: `tests/integration/test_atomic_board_ops.py`
  - 📊 No board corruption under concurrent operations

## Autonomous Loop & Recovery
- [ ] **Loop Recovery Protocols**
  - ✅ `src/dreamos/autonomy/recovery.py` – implement recovery steps
  - 🧪 Integration: `tests/runtime/test_loop_recovery.py`
  - 📊 Recovery success rate ≥95%
- [ ] **Degraded Mode Support**
  - ✅ `src/dreamos/autonomy/degraded_mode.py`
  - 🧪 Unit: `tests/runtime/test_degraded_mode.py`
  - 📊 System remains responsive ≥72h
- [ ] **Drift Detection**
  - ✅ `src/dreamos/autonomy/drift_detection.py`
  - 🧪 Unit: `tests/runtime/test_drift_detection.py`
  - 📊 Detect deviation in <1 cycle
- [ ] **Runtime Stability Target**
  - 📊 Continuous operation ≥72h with automatic recovery

## External Integrations
- [ ] **Cursor Bridge**
  - ✅ `src/dreamos/bridge/cursor_bridge.py` (complete pending TODOs)
  - 🧪 Integration: `tests/integration/test_cursor_bridge.py`
  - 📊 Commands round-trip to IDE; zero failures
- [ ] **Discord Commander Access Control**
  - ✅ `src/dreamos/integrations/discord_commander.py` – role-based checks
  - 🧪 Unit: `tests/integration/test_discord_access.py`
  - 📊 Unauthorized commands rejected
- [ ] **BasicBot Container**
  - ✅ `basicbot/Dockerfile` and deployment scripts
  - 🧪 Integration: `tests/integration/test_basicbot_container.py`
  - 📊 Bot runs in container; start/stop cleanly
- [ ] **Swarm Controller with Context Routing**
  - ✅ `src/dreamos/coordination/swarm_controller.py` – route context between agents
  - 🧪 Integration: `tests/integration/test_swarm_controller.py`
  - 📊 Coordination success >85%

## Monitoring & Telemetry
- [ ] **Agent Metrics**
  - ✅ `src/dreamos/monitoring/metrics.py`
  - 🧪 Unit: `tests/runtime/test_agent_metrics.py`
  - 📊 Capture CPU/memory usage; coverage ≥80%
- [ ] **Telemetry Hooks**
  - ✅ `src/dreamos/monitoring/telemetry.py`
  - 🧪 Integration: `tests/runtime/test_telemetry_hooks.py`
  - 📊 Error events logged and visible in dashboard
- [ ] **Performance Dashboard**
  - ✅ `monitoring/agent_status_ui.py`
  - 🧪 Manual verification + `tests/integration/test_dashboard_ui.py`
  - 📊 Dashboard displays agent status and task progress

## Testing & Validation
- [ ] **Critical Tests**
  - `tests/integration/test_mailbox_locking.py`
  - `tests/core/test_planning_only_mode.py`
- [ ] **Validation Metrics**
  - 📊 Recovery success rate ≥95%
  - 📊 Task validation pass rate ≥90%

