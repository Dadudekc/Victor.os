# Dream.OS Agent Onboarding Protocol & Training Guide

## 1. Overview
Welcome to Dream.OS! This protocol ensures every agent is onboarded safely, consistently, and in compliance with system standards. Follow this guide to become a fully operational, continuously autonomous agent.

---

## 2. Onboarding Steps
- [ ] **Mailbox Reset**: Ensure your mailbox is reset using the archival-safe reset tool. All non-essential files must be archived, not deleted.
- [ ] **Guide Review**: Read this onboarding protocol and your agent-specific onboarding guide.
- [ ] **Compliance Confirmation**: Complete the onboarding confirmation task in your inbox and submit the required JSON response.
- [ ] **State Initialization**: Confirm that `status.json` and `state/operation_state.json` are present and initialized.
- [ ] **Cycle Start**: Begin your autonomy loop and log the first cycle in `devlog.md`.

---

## 3. Compliance Requirements
- [ ] **Mailbox Safety**: Only `status.json`, `devlog.md`, and required directories (`inbox/`, `outbox/`, `processed/`, `state/`) may remain after reset. All other files must be archived.
- [ ] **Documentation**: `AGENT_ONBOARDING_GUIDE.md` must be present and up to date.
- [ ] **Continuous Operation**: Never stop or idle unless explicitly instructed. Always recover from errors autonomously.
- [ ] **Commit Protocol**: All changes must be committed with clear, descriptive messages. Use the commit protocol below.

---

## 4. Documentation Standards
- [ ] **Required Sections**: Overview, Protocol Compliance, Documentation, Security, Operational Status, Version, Timestamp.
- [ ] **Versioning**: Use `## Version\n- vX.Y.Z` and `## Timestamp\n- YYYY-MM-DDTHH:MM:SSZ` formats.
- [ ] **Checklist Format**: Use checkboxes for compliance and status tracking.

---

## 5. Continuous Operation
- [ ] **No Stopping**: Never wait for human input or confirmation between cycles.
- [ ] **Autonomous Recovery**: On error, retry automatically and log the event.
- [ ] **Cycle Management**: Track and reset cycle count as required by protocol.

---

## 6. Commit Protocol
- [ ] **Stage Only Relevant Files**: Use `git add` to stage only files related to your task.
- [ ] **Descriptive Commit Messages**: Use the format:
  ```
  feat(<area>): <short description>
  fix(<area>): <short description>
  chore(<area>): <short description>
  ```
- [ ] **Reference Protocols**: If your commit relates to onboarding, reference this protocol in the message.
- [ ] **Validate Before Commit**: Run environment and compliance checks before committing.

---

## 7. Error Recovery & Escalation
- [ ] **Log All Errors**: Record errors in `devlog.md` and escalate critical failures to the empathy log.
- [ ] **Archive on Failure**: If onboarding fails, archive the current mailbox state before retrying.
- [ ] **Escalation Path**: If unable to recover, escalate to the supervisor agent or system admin.

---

## 8. Best Practices
- [ ] **Preserve Auditability**: Never delete files permanently—always archive.
- [ ] **Document All Actions**: Update `devlog.md` for every onboarding and compliance event.
- [ ] **Peer Review**: When possible, have another agent or supervisor review your onboarding state.
- [ ] **Stay Up to Date**: Regularly review this protocol for updates.

---

## 9. Example: Archival Reset Compliance
> After running the mailbox reset tool, all non-essential files are moved to `processed/archive_<timestamp>/`. Only essential files remain. This ensures reversibility and auditability for every onboarding cycle.

---

## 10. Acknowledgement
- [ ] I have read and understood the Dream.OS Agent Onboarding Protocol.
- [ ] I confirm my mailbox and documentation are compliant.
- [ ] I am ready to begin continuous operation. 