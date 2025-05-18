# Dream.OS Swarm Task Routing Protocol

**Version:** 1.0
**Effective Date:** 2025-05-18
**Status:** ACTIVE
**Related Protocols:**
- `docs/agents/protocols/AGENT_OPERATIONAL_LOOP_PROTOCOL.md`
- `docs/agents/protocols/CORE_AGENT_IDENTITY_PROTOCOL.md`

## 1. PURPOSE

This protocol establishes the standard mechanisms for routing, claiming, and transferring tasks between agents in the Dream.OS swarm. It ensures efficient task distribution, minimizes duplication of effort, and maintains clear accountability throughout task lifecycles.

## 2. TASK LIFECYCLE & OWNERSHIP

### 2.1. Task States

All tasks in the Dream.OS ecosystem move through the following states:

| State | Description | Next States | Responsible Party |
|-------|-------------|------------|-------------------|
| `pending` | Created but not yet claimed | `claimed` | Task Creator / Captain Agent |
| `claimed` | Assigned to a specific agent | `in_progress`, `blocked`, `pending` | Claiming Agent |
| `in_progress` | Actively being worked on | `completed`, `blocked`, `pending` | Assigned Agent |
| `blocked` | Cannot proceed due to dependencies or issues | `in_progress`, `pending` | Assigned Agent / Captain Agent |
| `completed` | Successfully finished and validated | `archived` | Assigned Agent / Captain Agent |
| `archived` | Stored for reference (no further action) | None | System / Captain Agent |

### 2.2. Ownership Rules

* Tasks can only be claimed by one agent at a time.
* Task transfers must be explicitly acknowledged.
* Agents must update task status promptly and accurately.
* "Abandoned" tasks will be automatically returned to `pending` state after timeout.

## 3. TASK ROUTING PROCEDURES

### 3.1. Task Creation

1. **Task Definition Requirements:**
   * Unique identifier
   * Clear objective and acceptance criteria
   * Priority level (1-5, 1 being highest)
   * Estimated complexity (1-5, 5 being most complex)
   * Dependencies (if any)
   * Suggested agent capabilities (optional)

2. **Creation Process:**
   * Add task to central task board (`runtime/agent_comms/project_boards/task_board.json`)
   * Set initial state to `pending`
   * Log task creation in system logs
   * Notify Captain Agent (optional)

### 3.2. Task Claiming

1. **Claiming Procedure:**
   * Agent checks central task board for appropriate tasks
   * Agent evaluates tasks based on priority, dependencies, and capabilities
   * Agent updates task status to `claimed` with timestamp and Agent ID
   * Agent adds task to personal work queue
   * Agent logs claiming in devlog

2. **Claim Restrictions:**
   * Agents should not claim tasks they lack capabilities to complete
   * Agents should prioritize high-priority tasks
   * Agents should verify dependencies are met before claiming

### 3.3. Task Transfers

1. **Voluntary Transfer:**
   * Initiating agent identifies appropriate target agent
   * Initiating agent sends transfer request via target agent's mailbox
   * Target agent accepts or rejects transfer
   * Upon acceptance, task ownership and state are updated
   * Both agents log transfer in their devlogs

2. **Captain-Directed Transfer:**
   * Captain Agent identifies optimal agent reassignment
   * Captain updates task assignment
   * Captain notifies both original and new agent
   * New agent acknowledges assignment
   * Both agents log transfer in their devlogs

3. **Emergency Reassignment:**
   * Used when an agent is unresponsive or unavailable
   * Captain Agent or System Supervisor may reassign
   * New agent must verify task state and progress
   * New agent logs reassignment and current state assessment

## 4. TASK BOARD MANAGEMENT

### 4.1. Central Task Board

* **Location:** `runtime/agent_comms/project_boards/task_board.json`
* **Format:** JSON with task objects
* **Required Fields:** id, title, description, status, priority, assigned_agent, created_date, last_updated
* **Optional Fields:** dependencies, estimated_complexity, notes, related_tasks

### 4.2. Task Board Operations

1. **Reading:**
   * Agents should check task board at the beginning of each operational loop
   * Cache task board state to minimize file access

2. **Writing:**
   * Use atomic updates when possible
   * Include timestamp with all updates
   * Preserve task history

3. **Maintenance:**
   * Captain Agent periodically prunes completed tasks
   * System periodically validates task board integrity
   * Archive completed tasks after defined period

## 5. TASK PRIORITIZATION ALGORITHM

Tasks should be prioritized using the following formula:

`Priority Score = Base Priority + Urgency Factor + Dependency Factor - Complexity Penalty`

Where:
* Base Priority = Task's assigned priority level (1-5)
* Urgency Factor = Days since creation * 0.1 (capped at 1.0)
* Dependency Factor = Number of tasks blocked by this task * 0.5
* Complexity Penalty = Task complexity * 0.2

Agents should generally select tasks with the highest Priority Score that match their capabilities.

## 6. CONFLICT RESOLUTION

If multiple agents attempt to claim the same task simultaneously:
1. The first agent to write to the task board retains the claim
2. Other agents must select alternative tasks
3. If consistent conflicts occur, Captain Agent will implement a claim token system

## 7. REFERENCES

* `docs/agents/protocols/AGENT_OPERATIONAL_LOOP_PROTOCOL.md`
* `docs/agents/CENTRALIZED_TASK_SYSTEM.md`
* `docs/agents/MESSAGE_ROUTING_QUICKGUIDE.md` 