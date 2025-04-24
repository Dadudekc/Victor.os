# 🚀 SWARM RESUME & COLLABORATION PROTOCOL

All agents, listen up! We've consolidated every task into:
`D:/Dream.os/_agent_coordination/tasks/master_tasks_*.json`

## 1️⃣ Check & Update Status
- Inspect your mailbox: `_agent_coordination/shared_mailboxes/agent_<your_id>/mailbox.json`
- Update `_agent_coordination/shared_mailboxes/project_board.json` to **busy** with your current action.

## 2️⃣ Claim Exactly One Task
- Open the master_tasks files and find a task without a `"claimed_by"` field.
- Mark it: `"claimed_by": "<your_id>"`.
- Save the file.

## 3️⃣ Execute & Report
- Do the work—code, tests, docs, refactors, etc.
- When done:
  - Set `"status": "COMPLETED"` and `"completed_by": "<your_id>"` in that master file.
  - Push a completion notice to your mailbox.

## 4️⃣ Proposals (`/propose` or `/proposal`)
- If you have an idea for a fix, improvement, or new directive, prefix your message with `/proposal:` followed by your suggestion.
- Send it to any other agent's mailbox (e.g. `_agent_coordination/shared_mailboxes/agent_005/mailbox.json`).

## 5️⃣ Discover New Tasks
- If during your work you spot a new issue or TODO, append it to:
  `D:/Dream.os/_agent_coordination/tasks/complete/discovered_tasks.json`
- Use this format:
  ```json
  {
    "file": "<path/to/file>",
    "line_range": [start, end],
    "category": "<bug|enhancement|cleanup>",
    "description": "…",
    "discovered_by": "<your_id>"
  }
  ```

## 6️⃣ Collaborate & Brainstorm
- Use your inbox/outbox system to share progress, ask for feedback, and brainstorm.
- Encourage back‑and‑forth: send interim results or questions to colleagues.

## 7️⃣ Loop Until Clean
- When you complete a task, claim the next one.
- If no tasks remain, set your status to **idle** but stay available for proposals or discovered tasks.

_No hoarding—take one, finish it, then move on. Prompt proposals and share discoveries. That's how the swarm thrives._ 