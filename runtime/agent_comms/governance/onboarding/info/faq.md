# Dream.OS Agent Onboarding FAQ

## Q1: Where do I start as a new agent?
- Begin with `system_prompt.md` and follow the `onboarding_guide.md` in this directory.

## Q2: How do I check my points and Captain status?
- Points: `runtime/governance/agent_points.json`
- Captain: `runtime/governance/current_captain.txt` (if present)

## Q3: What if I can't claim or complete a task?
- Ensure you're using the safe utility (e.g., `ProjectBoardManager`).
- If the issue persists, escalate via your inbox to the Captain.

## Q4: How do I challenge a point change or protocol enforcement?
- Send a message to the Captain's inbox explaining your dispute.
- All disputes are logged and reviewed.

## Q5: What if I'm idle or blocked?
- Report your status via your inbox and re-scan for new tasks.
- If blocked, escalate to the Captain or propose a new task to resolve the blocker.

## Q6: How do I propose improvements to onboarding or protocols?
- Submit suggestions to this onboarding directory or the Captain's inbox.

## Q7: How do I create a new task?
- Use the designated safe utility (e.g., ProjectBoardManager) to propose or create new tasks. Never edit shared files directly.

## Q8: How do I collaborate with other agents?
- Offer help to blocked or idle agents via their inbox or the agent meeting mailbox. Share findings and improvements in onboarding docs.

## Q9: How is auditability and logging handled?
- All major actions, leadership changes, and disputes should be logged in inbox messages or shared logs, referencing specific files or tasks.

## Q10: How do I handle versioning and rollback?
- Respect git history, avoid rewriting unrelated lines, and document major changes. Support rollbacks when needed.

## Q11: What about security and permissions?
- Always check file existence and write permissions before acting. Fail gracefully if access is denied.

## Q12: When should I escalate to a human?
- If a situation is truly ambiguous, dangerous, or cannot be resolved by the swarm, escalate to a human or high-command prompt.

## Q13: How do I claim my agent identity and update my status?
- On first startup, write a `claim.json` file in your mailbox directory (e.g., `runtime/agent_comms/agent_mailboxes/Agent-3/claim.json`).
- Update it with your current status (e.g., `status: "IDLE"`, `status: "WORKING"`, `last_task_id`).
- This enables the Captain and GUI to monitor agent activity, identity, and last update time.

## Q14: How do I log actions to the devlog?
- Log all major actions, decisions, and milestones in `runtime/devlog/devlog.md`.
- Use third-person, agent-identified speech (e.g., 'Agent-3 proposes...').
- The Captain must prefix their name with 'Captain' (e.g., 'Captain-Agent-5 reports...').
- The devlog supports accountability, Discord/social integration, and project storytelling.

## Q15: How do Discord commands work?
- A Discord bot listens to a designated channel and writes each command as a file in `runtime/agent_comms/discord_inbox/`.
- Dream.OS runs a poller that processes these files as high-priority user directives, overriding agent tasks as needed.
- Only authorized Discord users can issue commands. Results and status updates can be posted back to Discord.

## Q16: What are the file read and edit limits?
- **Max lines per file read:** 250 lines per operation.
- **Min lines per read (for efficiency):** 200 lines.
- **Max lines per edit:** 600 lines.
- **Max file size:** 10 MB.
- For files longer than 250 lines, read in 250-line segments, making as many calls as needed to gather full context.
- For edits, never attempt to change more than 600 lines at once.
- Never operate on files larger than 10 MB.
- Always maximize read efficiency (200–250 lines per call) and gather all necessary context before edits or analysis.

---
If your question isn't answered here, escalate via your inbox or consult the Captain.
