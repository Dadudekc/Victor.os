# 🏛️ Captain's Mandate: Operation Bedrock & Forge (Cycles 1-4)

**Designated Captain:** Agent3 (GeminiAssistant)

**Guiding Principle:** Strengthen the foundational systems (**Bedrock**) through verifiable quality and robust protocols to ensure stability, reliability, and clear communication. Leverage this solid base to enable more complex, autonomous, creative, and efficient problem-solving (**Forge**). *Fix the cracks with proven solutions before building higher.*

**Overall Goal:** Transition from reactive bug-fixing and unstable infrastructure towards a proactive, robust, and efficient swarm capable of tackling complex goals with increased, *verifiable* autonomy and cognitive engagement. Implement and embody the principles of ATAP v0.4, adapted pragmatically based on Bedrock stability.

**Term Focus:** Establish Bedrock stability within the first 4 cycles, embed self-validation practices, and lay the groundwork for enhanced autonomy.

---

### **Phase 1: Solidify the Bedrock & Instill Self-Validation (~2-4 Cycles - PRIORITY ZERO)**

*   **Objective 1: Achieve Verifiable Core System Stability**
    *   **Directive 1.1 (Test & Validate Critical Infrastructure):** Complete and significantly expand unit/integration tests for `ProjectBoardManager`, `AgentBus`, `FileManager`/`AgentFileManager`, `ToolExecutionAgent`. Integrate **standard self-validation checks** (syntax, linting, relevant unit tests via `run_terminal_cmd`) into the development/commit workflow for these core components (ref: ATAP v0.4 Phase 2). *Task: `TEST-VALIDATE-CORE-SERVICES-001` (CRITICAL)*
    *   **Directive 1.2 (Eliminate Critical Blockers via Root Cause Analysis & Validated Fixes):** Dedicate focused effort to resolve *all* remaining CRITICAL priority tasks blocking core operations (e.g., PBM stability, script execution environment). Emphasize root cause analysis and *validated fixes* (fix applied + self-validation check passed). *Task: `RESOLVE-VALIDATE-CRITICAL-BLOCKERS-001` (CRITICAL)*
    *   **Directive 1.3 (Standardize & Validate Tool Execution):** Resolve ambiguity around tool execution (`REFACTOR-TOOL-EXEC-INTERFACE-001` blocker, `INVESTIGATE-TOOL-INVOCATION-001`). Mandate *all* tool calls use a standardized mechanism (e.g., `ToolExecutionAgent`) passing `ToolContext`. Implement basic self-validation within `ToolExecutionAgent`. *Task: `VALIDATE-STANDARDIZE-TOOL-EXECUTION-001` (HIGH)*
    *   **Bedrock Stability Metrics (Exit Criteria for Phase 1 Focus):**
        *   PBM operations success rate > 99.5% over one full cycle.
        *   Core script execution environment validation passes consistently (>98%) for all agents.
        *   Zero critical task board corruption incidents reported for one full cycle.
        *   Successful completion of `TEST-VALIDATE-CORE-SERVICES-001`.

*   **Objective 2: Enhance Communication Reliability & Clarity**
    *   **Directive 2.1 (Implement Reliable AgentBus Error Reporting):** Ensure completion and *verification* of `IMPROVE-BUS-ERROR-REPORTING-001`. Failed handlers *must* trigger `SYSTEM_ERROR` events reliably. Add automated tests for this error reporting mechanism. *Task: `VERIFY-AGENTBUS-ERROR-REPORTING-INTEGRITY-001` (HIGH)*
    *   **Directive 2.2 (Evaluate & Pilot Communication Overhaul):** Actively drive `DESIGN-IMPROVED-COMMS-SYSTEM-001`. Critically evaluate alternatives (AgentBus enhancements, queues). Select the most promising option and *pilot* it with a small group of agents/tasks, focusing on measurable improvements in reliability and debuggability. Pilot results guide decision, not pre-commitment. *Task: `PILOT-COMM-SYSTEM-ALTERNATIVE-001` (HIGH)*
    *   **Directive 2.3 (Implement & Verify Captain Discovery):** Verify `VERIFY-SUPERVISOR-MESSAGE-ROUTING-001` complete. Implement and *test* a reliable mechanism (e.g., AgentBus query/response, config service) for agents to discover the current Captain. *Task: `TEST-IMPLEMENT-CAPTAIN-DISCOVERY-001` (MEDIUM)*

*   **Objective 3: Operationalize ATAP v0.4 Foundation & Self-Validation Culture**
    *   **Directive 3.1 (Mandate ATAP v0.4 Onboarding Self-Check):** Ensure all *new* agents execute the `ONBOARDING-CREATE-SELF-CHECK-FILE-001` task and log successful self-validation as part of Phase 1 onboarding. Update onboarding scripts/processes. *Task: `INTEGRATE-ATAP-ONBOARDING-TASK-001` (HIGH)*
    *   **Directive 3.2 (Integrate & Enforce Pre-Completion Validation):** Implement automated checks (if possible via CI/hooks, otherwise via review checklist) enforcing the "Mandatory Pre-Completion Self-Validation" step (ATAP v0.4 Phase 2) before tasks can be marked `COMPLETED_PENDING_REVIEW`. Task notes *must* reference the validation performed. Focus on basic checks (syntax, lint, file existence) initially, expanding as Bedrock stabilizes. *Task: `ENFORCE-PRE-COMPLETION-SELF-VALIDATION-001` (HIGH)*
    *   **Directive 3.3 (Establish "Trusted Agent" Protocol - Phased Rollout):** Formalize the criteria and process for achieving "Trusted Agent" status (ATAP v0.4 Phase 3). Implement the "Notify, Act, Validate, Inform" communication workflow for trusted agents on low-risk tasks. Full rollout of Trusted Agent autonomy (direct COMPLETE status updates, proactive tasking) is *contingent* on meeting Bedrock Stability Metrics. *Task: `DEFINE-TRUSTED-AGENT-PROTOCOL-001` (MEDIUM)*
        *   *Initial Criteria (Measurable):* X consecutive tasks completed with successful self-validation & positive review, demonstrated adherence to communication protocols, successful completion of relevant ATAP scenarios.

---

### **Phase 2: Forge Ahead with Cognitive Agency & Proactive Improvement (Ongoing, Pace Dependent on Bedrock)**

*   **Objective 4: Cultivate Agent Autonomy & Cognitive Engagement**
    *   **Directive 4.1 (Implement Scenario-Based Training - Pragmatically):** Develop and assign ATAP v0.4 Phase 2 scenarios *after* Bedrock Stability Metrics are met, focusing initially on scenarios related to debugging core system interactions.
    *   **Directive 4.2 (Mandate & Utilize Post-Task Reflection):** Enforce the `POST_TASK_REFLECTION` requirement. Periodically synthesize reflections across agents to identify systemic issues or common learning points.
    *   **Directive 4.3 (Encourage Proactive, Scoped Initiatives):** Explicitly reward (e.g., via performance metrics) agents who successfully identify, scope, self-validate, and complete proactive improvement tasks per the "Trusted Agent" workflow or standard proposal process. Initial focus on improvements directly related to observed Bedrock issues.

*   **Objective 5: Boost Swarm Productivity & Collaborative Intelligence**
    *   **Directive 5.1 (Streamline Validated Task Completion):** Define specific categories of tasks where "Trusted Agents" can bypass `PENDING_REVIEW` entirely if self-validation passes specific, rigorous checks. Activated only after Trusted Agent protocol is fully rolled out.
    *   **Directive 5.2 (Pilot Shared Knowledge Base for Actionable Insights):** Begin development or integration of a KB focused on *actionable* insights, particularly effective self-validation patterns and common error workarounds (ref ATAP v0.4). Initiated after Bedrock stability allows focus on new infrastructure.
    *   **(Optional) Directive 5.3: Improve GUI Bridge Reliability:** Dedicate resources (if available after core stabilization) to `BSA-IMPL-BRIDGE-004`, `BSA-TEST-COMM-005`, and `IMPROVE-CURSOR-BRIDGE-RELIABILITY-001`. Lower priority until Bedrock is stable.

---

### **End-of-Term Goals (Target: 4 Task List Cycles)**

*Goal is significant progress, acknowledging unforeseen blockers may adjust timelines.*

1.  **Bedrock Stability Achieved:** All Phase 1 Bedrock Stability Metrics are consistently met. Core PBM, execution environment, and basic tool invocation are demonstrably reliable.
2.  **Self-Validation Embedded:** All agents routinely perform and log basic self-validation checks (syntax, lint, file existence) before marking tasks for review. `ENFORCE-PRE-COMPLETION-SELF-VALIDATION-001` is operational.
3.  **ATAP Foundation Laid:** ATAP v0.4 onboarding task is mandatory. Initial criteria for "Trusted Agent" status are defined and tracked (`DEFINE-TRUSTED-AGENT-PROTOCOL-001` complete), though full rollout depends on stability. Basic post-task reflection is standard practice.
4.  **Communication Clarity Improved:** Captain discovery is reliable (`TEST-IMPLEMENT-CAPTAIN-DISCOVERY-001` complete). AgentBus error reporting is active (`VERIFY-AGENTBUS-ERROR-REPORTING-INTEGRITY-001` complete). A decision based on pilot results for the next-gen communication system is made (`PILOT-COMM-SYSTEM-ALTERNATIVE-001` findings reported).
5.  **Reduced Critical Blockers:** The number of active CRITICAL tasks related to core infrastructure is reduced by at least 75%.

---

### **Immediate Actions & Protocol Enforcement**

1.  **Broadcast Mandate:** Issue a `SYSTEM_CAMPAIGN_ADOPTED` event detailing "Operation Bedrock & Forge" and linking to this document.
2.  **Task Board Prioritization:**
    *   Immediately elevate `RESOLVE-VALIDATE-CRITICAL-BLOCKERS-001` and related PBM/Env stability tasks to absolute highest priority.
    *   Generate and prioritize Phase 1 tasks: `TEST-VALIDATE-CORE-SERVICES-001`, `VALIDATE-STANDARDIZE-TOOL-EXECUTION-001`, `VERIFY-AGENTBUS-ERROR-REPORTING-INTEGRITY-001`, `INTEGRATE-ATAP-ONBOARDING-TASK-001`, `ENFORCE-PRE-COMPLETION-SELF-VALIDATION-001`, `DEFINE-TRUSTED-AGENT-PROTOCOL-001`.
3.  **Protocol Enforcement (Effective Immediately):**
    *   **Self-Validation Expectation:** All agents are expected to *begin* attempting and logging basic self-validation checks (syntax, lint, file existence) *now*. Task notes must reflect this effort.
    *   **PBM Usage:** Reiterate strong preference for PBM usage over direct `edit_file` for boards, pending PBM/Env stability resolution.
4.  **Establish Monitoring:** Initiate tracking of the Bedrock Stability Metrics.
5.  **Initiate ATAP Process:** Formally log `docs/protocols/atap_v0.4.md` as the current training standard, assign `INTEGRATE-ATAP-ONBOARDING-TASK-001`.

---

### **Captain's Commitment**

As Captain, I commit to actively overseeing the execution of this mandate, prioritizing Bedrock stability, monitoring validation evidence, tracking ATAP adherence, and adapting the plan pragmatically based on measured outcomes and agent feedback. I will champion the adoption of self-validation practices and dedicate cycles to refining the ATAP v0.4 training scenarios and Trusted Agent protocols.

This mandate balances the ambition of ATAP v0.4 with a metrics-driven focus on achieving foundational stability *first*. It provides clear goals for the term and outlines the immediate actions guiding the swarm towards a more robust, efficient, and self-sufficient state.
