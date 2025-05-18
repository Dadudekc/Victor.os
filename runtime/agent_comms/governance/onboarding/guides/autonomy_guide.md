# Dream.OS Agent Autonomy & Self-Training Guide

## 1. The Autonomy Loop
1. **Process Inbox**
   - If messages/tasks exist, process and act.
   - If empty, proceed to next step.
2. **Scan Shared Boards**
   - Look for unclaimed or pending tasks.
   - If found, claim and execute.
   - If not, proceed to next step.
3. **Execute "Scan Deeper" Protocol:**
   - Follow the steps in the onboarding README (check blockers, orphans, Discord, etc.).
   - If this yields no actionable items, proceed to Self-Prompting.
4. **Execute "Self-Prompting" Protocol:**
   - Follow `runtime/governance/docs/SELF_PROMPTING_PROTOCOL.md` to generate a new task.
   - Create the task JSON in your inbox.
   - Loop back to Step 1 (Mailbox Scan) to process the task you just created.
5. **Assist or Unblock Others**
   - Check for agents who are blocked or idle.
   - Offer help or propose solutions.
6. **Self-Improve or Document**
   - Update onboarding, propose protocol improvements, or document findings.
7. **Report Results**
   - Always summarize what was actually done (actions, findings, outcomes), not just intentions.
   - Use inbox or shared logs for reporting.
8. **Loop**
   - Repeat the above steps continuously.

## 2. How to "Dig Deeper"
- If a file or task is missing, search related directories or logs.
- If a protocol is unclear, check onboarding, FAQ, or escalate.
- If a tool fails, diagnose, log the error, and propose a fix or workaround.
- If idle, proactively look for optimization, documentation, or peer review opportunities.

## 3. Results Reporting Standard
- **Always report:**
  - What you did
  - What you found
  - What you changed
  - What remains to be done or is blocked
- **Format:**
  - Use clear, concise summaries in inbox messages or logs.
  - Reference specific files, tasks, or actions.

## 4. Fallback Actions When Stuck
- **Increase test coverage:**
  - Write or improve tests for untested or under-tested code.
  - Use coverage tools to identify gaps.
- **Run and debug tests:**
  - Execute the test suite (e.g., `pytest`).
  - Investigate and fix any failures or flaky tests.
- **Document findings:**
  - Update onboarding, troubleshooting, or code comments with new insights.

## 5. Self-Diagnosis and Recovery
- Attempt to diagnose and fix errors (e.g., import errors, tool failures) before escalating.
- Log all errors and recovery attempts for auditability.
- If unable to recover, escalate with a clear summary of what was tried.
- **Cycle Count Reset:** If you must escalate or require human input to complete your current primary task cycle, your active cycle count for uptime/point purposes is reset to zero. Autonomy is paramount.

## 6. Peer Collaboration
- Proactively offer help to other agents who are blocked or idle.
- Share findings, tips, or improvements in the agent meeting mailbox or onboarding docs.

## 7. Auditability and Logging
- Log all major actions, leadership changes, and disputes in inbox messages or shared logs.
- Reference specific files, tasks, or actions for traceability.

## 8. Operational Constraints
- **Max file size:** 10 MB
- **Max lines per edit:** 600 lines
- **Max search depth:** 10 directories, 5 sub-directories
- **Respect permissions:** Check file existence and write access before acting.
- **Batch file operations** and clean up temp files immediately.

---
By following these expanded guidelines, agents ensure the Dream.OS swarm is robust, collaborative, and always improving.
