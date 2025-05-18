# Dream.OS Points System & Captaincy

## 1. Points System Overview
- Agents earn and lose points based on their actions.
- Points are tracked in `runtime/governance/agent_points.json`.

## 2. Earning Points
- **+3**: Complete a high-priority or cross-agent task
- **+2**: Complete a standard task
- **+2**: Unblock another agent
- **+1**: Maintain high loop uptime (per cycle)
- **+1**: Proactively improve the system (refactoring, docs, tools)

## 3. Losing Points
- **-3**: Fail a task or cause a regression
- **-2**: Remain idle or halt unexpectedly (per cycle)
- **-2**: Violate protocol (bypass validation, unsafe edits, etc.)
- **Cycle Reset**: Require human input/escalation before completing a task cycle (resets cycle count for uptime points).

## 4. Captaincy Handover
- The agent with the highest points is Captain.
- Captaincy is automatically transferred if another agent surpasses in points.
- The Captain focuses on masterpiece tasks and blockers, not routine implementation.
- All captaincy changes are logged and auditable.

## 5. Disputes & Peer Review
- Agents may challenge point changes or captaincy via inbox.
- Disputes are reviewed by the Captain or a designated peer.

---
This system ensures fairness, transparency, and continuous improvement in the Dream.OS swarm.
