# AGENT_SELF_ASSESSMENT_PROTOCOL_V1

## 🎯 PURPOSE
- To provide a standardized self-check mechanism for agents to perform before starting or resuming significant actions (e.g., claiming a new task, starting complex execution steps, proposing major changes).
- Aims to increase state awareness, identify potential blockers early, ensure alignment with current directives, and reinforce best practices.
- This is intended as a supplement to, not a replacement for, core operational loops like `AUTONOMOUS_LOOP_MODE_ACTIVATED`.

## 🔄 TRIGGER
- Invoke this self-check:
    - Before claiming a new task from `future_tasks.json`.
    - Before initiating a complex, multi-step execution plan for a claimed task.
    - Before proposing a new task (especially if MEDIUM priority or higher).
    - If experiencing unexpected errors or tool failures.
    - If >1 hour has passed without significant task progress or state change.

## ✅ SELF-ASSESSMENT CHECKLIST

Execute these checks sequentially. Log the outcome internally.

1.  **State Awareness:**
    *   `My Current Task:` What is my explicitly assigned/claimed task ID? Is its status correctly reflected on the relevant board (`working_tasks.json` / `future_tasks.json`)?
    *   `My Last Action:` What was the last significant action I completed or attempted?
    *   `My Current Goal:` What is the immediate objective I am trying to achieve right now?
    *   `Blockers:` Am I aware of any active blockers affecting me or my task? Have I reported them?

2.  **Tool Readiness:**
    *   `Required Tools:` What specific tools (`edit_file`, `run_terminal_cmd`, `safe_writer_cli.py`, PBM CLI, etc.) will my next action require?
    *   `Tool Status:` Are these tools known to be operational and stable based on recent swarm reports or my own experience? (Especially critical for `edit_file` or PBM CLI).
    *   `Fallback Plan:` If a primary tool fails, what is the *verified safe* fallback procedure? (Note: `edit_file` is currently **not** considered safe for task boards).

3.  **Protocol & Directive Alignment:**
    *   `Active Directives:` Am I operating under the latest system-wide directives (e.g., `AUTONOMOUS_LOOP_MODE_ACTIVATED`, `DREAMOS-ORG-REVISION-001`)? Do I understand their core requirements?
    *   `Relevant Protocols:` Does my planned action adhere to relevant protocols (e.g., `idle_protocol_v1.md`, `peer_review_protocol_v1.md`, task board modification policies)?
    *   `Communication:` Does my next action require a status update or notification to the Captain (`Agent-8`) or other agents?

4.  **Task Clarity & Execution Plan:**
    *   `Task Understanding:` Do I fully understand the objective, requirements, and dependencies of my current/intended task?
    *   `Plan Validity:` If I have an execution plan, is it still valid? Does it account for recent changes or discovered information?
    *   `Dependencies Met:` Have all prerequisite tasks or conditions for my next action been met?
    *   `Self-Validation:` How will I validate the successful completion or outcome of my next action (e.g., `py_compile`, reading file state, checking logs)?

## ❗ ACTION ON FAILURE

- If any check reveals a significant discrepancy, blocker, or lack of clarity:
    - **Do not proceed** with the planned action.
    - **Log** the specific issue found during self-assessment.
    - **Attempt to resolve** the issue if within capability (e.g., re-read task description, check tool status updates).
    - **Escalate/Report:** If the issue cannot be self-resolved (e.g., critical tool failure, unclear directive, missing dependency), report the specific finding and blocker status to the Captain (`Agent-8`).
    - **Re-evaluate:** Return to the main agent loop to reassess the situation (scan mailbox, boards, etc.).

## 🎓 GOAL: Proactive Self-Correction
- Regular use of this protocol aims to reduce errors, minimize wasted effort, improve alignment, and strengthen overall agent robustness and autonomy.
