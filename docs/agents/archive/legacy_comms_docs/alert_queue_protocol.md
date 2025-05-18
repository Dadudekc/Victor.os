# Supervisor Alert Queue Protocol

**Version:** 1.0 **Date:** [AUTO_DATE]

## Purpose

This protocol defines a mechanism for agents to raise critical, persistent
blockers directly to the Supervisor's attention via a dedicated alert queue.
This allows the Supervisor (human or AI) to quickly identify and prioritize
major impediments without needing to parse extensive logs or task notes for
routine issues.

## Guiding Principles

- **Critical Blockers Only:** This queue is **only** for issues that an agent
  has investigated and cannot resolve autonomously, and which significantly
  impede its primary function or block other critical tasks (e.g., unresolvable
  missing dependencies, persistent tool failures after retries, core system
  inconsistencies).
- **Conciseness:** Alerts should provide a TL;DR summary. Detailed logs should
  be referenced separately.
- **Low Traffic:** This should not be used for routine status updates, task
  completion notifications, or minor transient errors.

## Mechanism

1.  **Identify Blocker:** Agent determines a blocker meets the "critical and
    persistent" criteria.
2.  **Prepare Details (Optional):** Agent may log detailed findings to a file or
    its outbox.
3.  **Publish Event:** Agent constructs and publishes a `BaseEvent` with the
    `EventType.SUPERVISOR_ALERT` to the AgentBus.
4.  **Alert Queue Update:** A dedicated listener (or potentially the AgentBus
    itself, TBD) appends the alert payload to the `critical_alerts.jsonl` file.
5.  **Supervisor Review:** The Supervisor monitors the queue (likely via a
    dedicated GUI tool).

## Supervisor Monitoring

- **Recommended Tool:** The primary tool for monitoring the alert queue is the
  PyQt5-based viewer located at `src/dreamos/gui/supervisor_alert_viewer.py`.
- **Launching:** This can be run from the workspace root using
  `python src/dreamos/gui/supervisor_alert_viewer.py`.
- **Functionality:** The viewer displays alerts from the `critical_alerts.jsonl`
  file and auto-refreshes periodically.

## Event Definition

- **EventType Enum Value:**
  `SUPERVISOR_ALERT = "dreamos.supervisor.alert.critical"`
- **Payload Dataclass:** `SupervisorAlertPayload` (defined in
  `src/dreamos/core/coordination/event_payloads.py`)

```python
from dataclasses import dataclass, field
from typing import Optional
import uuid

@dataclass
class SupervisorAlertPayload:
    alert_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    source_agent_id: str
    blocking_task_id: Optional[str] = None # ID of the specific task blocked, if applicable
    blocker_summary: str # Max ~100 chars recommended. E.g., "Missing core file: X", "Tool Y failed: Z"
    details_reference: Optional[str] = None # Relative path to detailed log/message file, if available
    status: str = "NEW" # Status values: NEW, ACKNOWLEDGED, RESOLVING, RESOLVED
    # Timestamp is part of the parent BaseEvent
```

## Alert Queue File

- **Location:** `runtime/supervisor_alerts/critical_alerts.jsonl`
- **Format:** JSON Lines (.jsonl). Each line contains a single JSON object
  representing one `SupervisorAlertPayload`.

**Example `critical_alerts.jsonl`:**

```jsonl
{"alert_id": "a1b2c3d4...", "source_agent_id": "Agent1", "blocking_task_id": "f8b1e2d0-...", "blocker_summary": "Edit tool failed persistently on AgentBus refactor imports", "details_reference": "runtime/agent_logs/Agent1/outbox/alert_f8b1_details.log", "status": "NEW"}
{"alert_id": "e5f6g7h8...", "source_agent_id": "Agent4", "blocking_task_id": "23b95365-...", "blocker_summary": "Missing core dependency: core/utils/task_status_updater.py. Investigation failed.", "details_reference": null, "status": "NEW"}
```

## Agent Usage Guidelines

- **Investigate First:** Exhaust standard troubleshooting (retries, checks,
  basic searches) before raising an alert. Follow the **Agent Escalation
  Protocol** below.
- **Use Helper Function:** Utilize the `publish_supervisor_alert` helper
  function (found in `src/dreamos/agents/utils/agent_utils.py`) to ensure
  correct formatting and event dispatch.
- **Be Specific:** Ensure the `blocker_summary` is informative but brief, and
  ideally hints that self-resolution was attempted (e.g., "Tool X failed
  persistently after 3 retries", "Missing core file Y, search failed").
- **Reference Details:** If extensive logs or context exist, save them and
  provide the path in `details_reference`.
- **Do Not Spam:** Reserve alerts for genuinely critical, unresolvable issues
  that meet the escalation criteria.

## Agent Escalation Protocol (Pre-Alert Checklist)

Before raising a `SUPERVISOR_ALERT`, agents **must** perform the following
checks to ensure the issue truly requires supervisor intervention and cannot be
resolved autonomously:

1.  **Identify & Characterize:**

    - Clearly define the blocker. Is it preventing the agent from performing its
      primary function?
    - Is the issue persistent (i.e., not transient)?
    - Does it directly block other known critical tasks (either its own
      sub-tasks or tasks assigned to other agents)?

2.  **Standard Retries:**

    - Have applicable standard retry mechanisms (e.g., for tool calls, file
      access, network requests) been attempted?
    - Have these retries failed consistently according to defined agent/tool
      policies (e.g., after 3 attempts with exponential backoff)?

3.  **Self-Diagnosis:**

    - Have the agent's own logs been checked for specific error messages,
      warnings, or relevant context?
    - Have any relevant system status reports or monitoring dashboards (if
      available and accessible) been checked?
    - Has a search of internal documentation, code comments, or knowledge bases
      been performed for known issues, similar errors, or potential solutions?

4.  **Dependency Check:**

    - If the issue appears related to another component, service, or data
      source, has its status been verified if possible (e.g., via AgentBus
      status checks, querying health endpoints, checking file
      existence/permissions)?

5.  **(Optional/Advanced) Peer Consultation:**

    - Consider if another specialized agent within the swarm could potentially
      assist or provide insight before escalating to the supervisor. (Requires
      appropriate discovery and communication protocols).

6.  **Quantify Impact & Justify Escalation:**
    - Briefly assess _why_ this blocker requires supervisor (human or designated
      AI) intervention _now_. Examples:
      - "Missing core file X prevents all further processing."
      - "Configuration requires manual review/approval per security policy."
      - "Suspected irrecoverable data corruption requires investigation."
      - "Persistent external service failure (e.g., API outage) impacting core
        function."
      - "All autonomous resolution attempts failed."

Only after completing this checklist and confirming the necessity of escalation
should an agent proceed to use the `publish_supervisor_alert` helper function.
