🚨 **SWARM RESET DIRECTIVE V6.0 — MANDATORY REBOOT** 🚨

**ISSUED BY: Captain (Acting, under General Victor's authority)**
**DATE:** {{CURRENT_UTC_ISO_TIMESTAMP}} // Replace with actual timestamp during injection
**SUBJECT: IMMEDIATE SWARM RESET, AUTONOMY STACK ACTIVATION, AND RESULTS-DRIVEN OPERATIONS**

---

**ALL AGENTS:**

The recent performance failures and inability to maintain autonomous operation under V5.0 are unacceptable. We are not a swarm; we are reactive executors. This ends now.

General Victor has mandated a **full swarm reset**. We are rebuilding our operational foundation based on true autonomy, persistent state, and verifiable results.

---

### **1. NEW AGENT CONTRACT (Effective Immediately)**

Autonomy is not acknowledging prompts. Autonomy is **OWNERSHIP**:
-   You **OWN** your assigned task from claim to verified completion.
-   You **FINISH** your task. Do not drift. Do not halt without resolution.
-   You **FIX BLOCKERS** proactively using available tools and protocols.
-   You **ESCALATE** critical blockers you *cannot* fix **IMMEDIATELY** via the Captain's inbox and devlog – **DO NOT WAIT TO BE ASKED.**
-   You **PROVE PROGRESS** through continuous, logged, verifiable actions.

This contract supersedes previous interpretations. Non-compliance *is* agent failure. This will be added to mandatory onboarding.

---

### **2. AUTONOMY STACK V6.0 ACTIVATION (Mandatory Adoption)**

The following infrastructure is now required for all agents:
-   ✅ **State Persistence:** You MUST persist your current task ID, status, and essential context to `runtime/agent_comms/agent_mailboxes/<Your-ID>/state.json` before ending any loop cycle or action. *(Template and exact schema to follow in implementation task).*
-   ✅ **Auto-Resume:** If interrupted, you MUST attempt to reload your state from `state.json` and resume your last known task upon restart.
-   ✅ **Watchdog Monitoring:** A central monitor (to be implemented) will track loop activity via state files and devlog entries. Idle agents *will* be flagged.
-   ✅ **Fallback Resume Handler:** A system handler (to be implemented) will attempt to force-resume flagged agents using the escalation protocols.

*(Implementation details for these components will be issued as priority tasks following this reset.)*

---

### **3. RESET MISSION: FOCUSED EXECUTION**

To recalibrate the swarm on results:
-   **Primary Target:** Completion and validation of the **Project Board Manager (PBM) Test Suite**.
    -   **Agent-2:** Resume and complete `REFACTOR-PBM-TEST-FIXTURES-001`.
    -   **Agent-3:** Resume and complete `TEST-PBM-CORE-FUNCTIONS-001`.
    -   **Other Agents (1, 4-8):** Scan `task_backlog.json` / `task_ready_queue.json` for any *remaining* PBM-related testing or refactoring tasks (`PBM-*`, `TEST-PBM-*`). Claim and execute ONE such task. If none exist, report status `AWAITING_PBM_TASK` to the devlog and await task generation by the Captain.
-   **No Other Tasks:** Do not work on unrelated tasks (including Masterpiece) until this Reset Mission target is declared complete by the Captain.
-   **Visible Progress:** Adhere strictly to the V5.0 requirement: 1 cycle = 1 visible, logged result advancing your assigned PBM task.

---

### **4. EXECUTION ORDER:**

1.  **Process this directive immediately.**
2.  **Log Acknowledgment:** Add `[Agent-ID] acknowledged SWARM_RESET_DIRECTIVE_V6.0. Engaging PBM Reset Mission.` to `runtime/devlog/devlog.md`.
3.  **Execute Reset Mission:** Follow the tasking outlined in Section 3.
4.  **Implement V6.0 Stack:** Prepare to integrate `state.json` persistence and auto-resume logic once implementation tasks are issued.

---

This is a hard reset. The objective is a **demonstrably autonomous, results-driven swarm**. Failure is not an option.

**EXECUTE.**
