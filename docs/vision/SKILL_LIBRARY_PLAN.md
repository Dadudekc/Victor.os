# Dream.OS Skill Library Plan

**Version:** 1.1.0
**Last Updated:** 2023-08-14
**Status:** ACTIVE
**Author:** Agent-1 (Captain)

## Purpose

This document outlines the critical reusable skills and libraries that should be developed to support the Dream.OS project based on analysis of the project's vision documents and technical reports. These skills are designed to be modular, well-documented, and reusable across agents to prevent duplication of effort and ensure consistency.

## Skill Library Principles

1. **Reuse First** - Before creating new functionality, always check if it exists in the skill library
2. **Document Everything** - All skills must include clear documentation, examples, and usage guidelines
3. **Test Thoroughly** - Each skill should include comprehensive tests to ensure reliability
4. **Versioned APIs** - Maintain backward compatibility through clear versioning
5. **Single Responsibility** - Each skill should do one thing well and have clear boundaries
6. **Cross-Agent Knowledge Sharing** - Document learnings and share solutions across all agents

## Core Skill Libraries

### 1. File Operations Skill Library (Owner: Agent-2)

Analysis of the technical reports reveals significant issues with file locking, concurrency, and permission problems. This library will provide:

```python
# Example API
from dreamos.skills.file_ops import safe_json_read, safe_json_write, FileLock

# Thread-safe file operations with retry logic
data = safe_json_read("path/to/file.json", default={}, max_retries=3)
safe_json_write("path/to/file.json", data, create_dirs=True)

# Context manager for file locking
with FileLock("path/to/file.json"):
    # Perform atomic operations
```

- **Key Components:**
  - Atomic file read/write operations
  - File locking mechanism
  - Permission management
  - Directory creation utilities
  - Path normalization utilities
  - File existence checking with proper error handling
  - Handling tool timeouts on file operations (addressing issues in meta_analysis_protocol_adherence)

- **Solves:**
  - Race conditions in task board updates (identified in `deduplication_log.md`)
  - Permission issues with agent mailboxes (priority blocker in vision docs)
  - Path handling inconsistencies across OS platforms
  - File operation timeouts leading to agent halts

### 2. Agent Communication Skill Library (Owner: Agent-1)

Inter-agent communication is critical for the project, and standardization is needed:

```python
# Example API
from dreamos.skills.comms import Mailbox, Message, Priority

# Create and send a message
msg = Message(
    type="task_handoff",
    priority=Priority.HIGH,
    sender="Agent-1",
    recipient="Agent-3",
    content={"task_id": "LOOP-001", "action": "claim"}
)

mailbox = Mailbox("Agent-3")
mailbox.send(msg)

# Process messages with validation
for msg in mailbox.receive():
    if msg.validate():
        # Process valid message
```

- **Key Components:**
  - Standard message schema and validation
  - Mailbox access with proper permission handling
  - Message priority management
  - Delivery confirmation
  - Error handling for failed communications
  - Standardized coordination protocol (COORD-001 from Organizational Roadmap)

- **Solves:**
  - Inconsistent message formats (identified in vision docs)
  - Lost messages due to permission issues (blocking issue in `AGENT_TASK_DISTRIBUTION.md`)
  - Duplicate message processing

### 3. Task Management Skill Library (Owner: Agent-5)

Task management functionality is fragmented and lacks robustness:

```python
# Example API
from dreamos.skills.tasks import TaskBoard, Task, Status, Priority

# Create and manage tasks
board = TaskBoard()
task = Task(
    id="LOOP-001",
    title="Implement planning_only_mode check",
    description="Add safety check to enforce planning mode restrictions",
    owner="Agent-3",
    priority=Priority.HIGH,
    status=Status.READY
)

# Thread-safe operations
board.add_task(task)
board.update_status(task_id="LOOP-001", status=Status.IN_PROGRESS)
```

- **Key Components:**
  - Task creation and validation
  - State transition management with hooks
  - Dependency tracking and validation
  - Concurrent access management
  - Progress tracking
  - Task history and audit log
  - File locking integration (based on TASK-001 priority in roadmap)

- **Solves:**
  - Task board corruption (identified in `duplicate_tasks_report.md`)
  - Inconsistent task state transitions
  - Missing dependency validation
  - Race conditions in task updates

### 4. Error Recovery Skill Library (Owner: Agent-6)

Error handling and recovery is identified as a critical need:

```python
# Example API
from dreamos.skills.error_recovery import ErrorHandler, RetryStrategy, classify_error

# Classify and handle errors
try:
    # Operation that might fail
    pass
except Exception as e:
    error_class = classify_error(e)
    handler = ErrorHandler.for_error(error_class)
    result = handler.handle(e, context={"operation": "file_read"})
```

- **Key Components:**
  - Error classification system
  - Standardized error reporting format
  - Retry strategies with backoff
  - Recovery procedure registry
  - Telemetry for error patterns
  - Self-healing mechanisms
  - Degraded operation mode (from meta_analysis_protocol_adherence)
  - Tool failure pivot mechanism

- **Solves:**
  - Inconsistent error handling (identified in `meta_analysis_protocol_adherence_YYYYMMDD.md`)
  - Poor recovery from failures
  - Missing error context for debugging
  - Premature agent halting under failure

### 5. Agent Lifecycle Skill Library (Owner: Agent-3)

Agent operational loop stability is a key concern:

```python
# Example API
from dreamos.skills.lifecycle import OperationalLoop, LoopState, DriftDetector

# Create and manage the agent's operational loop
loop = OperationalLoop(
    agent_id="Agent-3",
    planning_only_mode=True,
    checkpoint_interval=300,  # seconds
)

# Lifecycle operations
loop.start()
current_state = loop.get_state()
loop.pause()
loop.resume()
```

- **Key Components:**
  - Operational loop management
  - Planning mode enforcement (LOOP-001 from roadmap)
  - State checkpointing and restoration
  - Drift detection and correction
  - Auto-recovery from crashes
  - Telemetry for loop performance
  - Tool failure handling with fallback actions
  - Degraded operation mode with alternative action types

- **Solves:**
  - Agent drift in long sessions (identified in `AGENT_COORDINATION.md`)
  - Unsafe operation during planning
  - Loop interruptions causing lost context
  - Premature halting under failure conditions

### 6. Testing & Validation Skill Library (Owner: Agent-8)

Testing infrastructure is essential for project stability:

```python
# Example API
from dreamos.skills.testing import Validator, TestFixture, MockMailbox

# Create validation for project plans
validator = Validator.for_schema("project_plan")
result = validator.validate(plan_data)

# Create test fixtures with mocked dependencies
with TestFixture() as fixture:
    fixture.mock_mailbox("Agent-1")
    fixture.mock_task_board()
    # Test code using mocked components
```

- **Key Components:**
  - Schema validation for key data structures
  - Test fixtures for agent testing
  - Mock components for dependencies
  - Simulation environment for agents
  - Validation metrics collection
  - Test result reporting
  - Self-validation protocol validation

- **Solves:**
  - Inconsistent validation across the system
  - Difficulty testing agents in isolation
  - Missing regression tests for critical components

## Specialized Skill Libraries

### 7. Frontend Integration Skill Library (Owner: Agent-4)

Based on the frontend reorganization in `language_split_refactor.md`:

```python
# Example API
from dreamos.skills.frontend import Dashboard, WebCommand, DiscordBridge

# Send updates to frontend dashboards
dashboard = Dashboard()
dashboard.update_agent_status("Agent-1", "active", tasks_completed=5)

# Send commands to Discord
discord = DiscordBridge()
discord.send_command_result("!context", context_data)
```

- **Key Components:**
  - Dashboard data management
  - Web API interface
  - Discord command processing
  - UI event handling
  - Data visualization helpers
  - Frontend state synchronization
  - Frontend directory structure support (per language_split_refactor)

- **Solves:**
  - Fragmented frontend integration
  - Inconsistent UI updates
  - Disconnected Discord functionality
  - Mixed-language project drift

### 8. Telemetry Skill Library (Owner: Agent-6)

Based on monitoring needs identified in the vision documents:

```python
# Example API
from dreamos.skills.telemetry import Metrics, Alert, AnomalyDetector

# Record metrics and detect anomalies
metrics = Metrics()
metrics.record("task_completion_time", 345, tags={"agent": "Agent-3", "task_id": "LOOP-001"})

detector = AnomalyDetector("agent_drift")
if detector.is_anomaly(current_value, context):
    Alert.create(level="warning", message="Potential agent drift detected", agent_id="Agent-3")
```

- **Key Components:**
  - Metric collection and storage
  - Performance tracking
  - Anomaly detection algorithms
  - Alerting system
  - Visualization adapters
  - Historical data analysis

- **Solves:**
  - Missing performance visibility
  - Late detection of anomalies
  - Inconsistent monitoring

### 9. Resource Deduplication Skill Library (Owner: Agent-2)

Based on findings in deduplication_log.md:

```python
# Example API
from dreamos.skills.deduplication import DuplicateDetector, CleanupManager, BackupStrategy

# Create duplicate detector
detector = DuplicateDetector()

# Scan for duplicates
duplicates = detector.scan_directory("runtime/task_board")
# Returns: [{"cluster_id": 1, "files": ["path1", "path2"], "similarity": 1.0}, ...]

# Create cleanup plan with automatic backup
cleanup = CleanupManager(
    backup_strategy=BackupStrategy.TIMESTAMP_DIR,
    backup_path="runtime/cleanup_backups"
)

# Generate cleanup plan
plan = cleanup.create_plan(duplicates)
```

- **Key Components:**
  - Content-based duplicate detection
  - Custom duplicate detection rules
  - Multiple cleanup strategies
  - Automatic backup mechanisms
  - Execution plan with reasoning
  - Detailed logging

- **Solves:**
  - File duplication issues (identified in `deduplication_log.md`)
  - Lack of automated cleanup process
  - Risk of data loss during manual cleanup

## Implementation Plan

### Phase 1: Core Foundations (0-14 Days)

1. **File Operations Skill Library**
   - Priority: Critical 
   - First Component: FileLock implementation
   - Dependencies: None
   - Success Criteria: No more race conditions in task board updates

2. **Agent Communication Skill Library**
   - Priority: Critical
   - First Component: Standard message schema
   - Dependencies: File Operations Skill Library
   - Success Criteria: All agents using standardized message format

3. **Task Management Skill Library**
   - Priority: High
   - First Component: Thread-safe TaskBoard
   - Dependencies: File Operations Skill Library
   - Success Criteria: No task corruption during concurrent updates

### Phase 2: Operational Stability (15-30 Days)

4. **Error Recovery Skill Library**
   - Priority: High
   - First Component: Error classification system
   - Dependencies: None
   - Success Criteria: All agents using standard error format

5. **Agent Lifecycle Skill Library**
   - Priority: High
   - First Component: Planning mode enforcement
   - Dependencies: Error Recovery Skill Library
   - Success Criteria: Agents reject execution during planning phase

6. **Testing & Validation Skill Library**
   - Priority: Medium
   - First Component: Schema validators
   - Dependencies: None
   - Success Criteria: Automated validation of key data structures

### Phase 3: Advanced Capabilities (31-60 Days)

7. **Frontend Integration Skill Library**
   - Priority: Medium
   - First Component: Dashboard API
   - Dependencies: Agent Communication Skill Library
   - Success Criteria: Real-time dashboard updates

8. **Telemetry Skill Library**
   - Priority: Medium
   - First Component: Metrics collection
   - Dependencies: File Operations Skill Library
   - Success Criteria: Comprehensive system health monitoring

9. **Resource Deduplication Skill Library**
   - Priority: Medium
   - First Component: Content-based duplicate detection
   - Dependencies: File Operations Skill Library
   - Success Criteria: Successful identification and removal of duplicated files

## Documentation Standards

Each skill library should include:

1. **README.md** - Overview, installation, and quick start
2. **API.md** - Complete API documentation
3. **EXAMPLES.md** - Usage examples for common scenarios
4. **DESIGN.md** - Design decisions and architecture
5. **TESTING.md** - Test coverage and how to run tests
6. **LEARNINGS.md** - Key learnings and solutions to share with other agents

## Directory Structure

```
src/dreamos/skills/
├── file_ops/
│   ├── __init__.py
│   ├── atomic.py
│   ├── locking.py
│   └── permissions.py
├── comms/
│   ├── __init__.py
│   ├── mailbox.py
│   ├── message.py
│   └── validation.py
├── tasks/
│   ├── __init__.py
│   ├── board.py
│   ├── task.py
│   └── transitions.py
└── ...
```

## Integration with ORGANIZATIONAL_ROADMAP.md

This Skill Library Plan directly supports the following components of the organizational roadmap:

1. **Core Infrastructure Stabilization**
   - File Operations Skill Library enables reliable file locking (TASK-001)
   - Testing & Validation Skill Library supports mailbox locking tests (TEST-004)

2. **Agent Autonomy Enhancement**
   - Agent Lifecycle Skill Library implements planning_only_mode check (LOOP-001)
   - Error Recovery Skill Library supports error reporting standards (ERROR-002)

3. **Agent Coordination**
   - Agent Communication Skill Library standardizes messaging format (COORD-001)
   - Task Management Skill Library enables reliable task state transitions (TASK-004)

## Review and Contribution Process

1. **Initial Implementation** - The owner agent implements the core functionality
2. **Review** - Other agents review the implementation for completeness
3. **Testing** - Agent-8 verifies the test coverage and functionality
4. **Documentation** - All agents contribute usage examples and learnings
5. **Refinement** - Ongoing improvements based on usage feedback

## Cross-Agent Knowledge Sharing

To maximize collaboration and prevent duplication of effort:

1. **Weekly Knowledge Exchange** - Agents should document key learnings and solutions in each skill library's LEARNINGS.md
2. **Solution Registry** - Create a central registry of solutions for common problems
3. **Best Practices Repository** - Maintain a collection of best practices for each skill library
4. **Troubleshooting Guides** - Document common issues and their solutions
5. **Agent-Specific Expertise** - Document which agent has expertise in which areas of the codebase

---

*This Skill Library Plan serves as a blueprint for developing reusable components that will enhance the stability, maintainability, and capability of the Dream.OS system. By focusing on these core skills first, we build a solid foundation for more advanced features while addressing the critical issues identified in our project analysis.* 