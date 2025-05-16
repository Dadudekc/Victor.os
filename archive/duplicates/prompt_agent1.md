<!-- runtime/agent_comms/agent_mailboxes/agent-1/prompt_agent1.md -->

## Task
Perform a full sweep of `src/` to identify orphaned, outdated, or unused files.
Use `find_orphans.py` or manual logic.

## Actions
- Log any anomalies to `task_backlog.json` under a new **orphan_files** tag.
- Update progress in `runtime/devlog/agents/agent-1.md` after each loop.
- Propose **DELETE**, **RELOCATE**, or **REWRITE** for every orphan.

## Loop Protocol
1. Stay in motion—run continuously.
2. If no orphans are found in a loop, default to protocol-hardening or file-classification quests.

## Point Criteria
- **+100 pts** per file correctly categorized or removed  
- **+200 pts** per PR that fixes a misplaced file 