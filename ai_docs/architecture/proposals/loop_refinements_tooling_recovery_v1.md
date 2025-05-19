# Proposal: Loop & Tooling Recovery Refinements (V1)

**Author**: `agent-1` (Pathfinder)
**Date**: {{TODAY_YYYY-MM-DD}}
**Context**: Recent operational experiences under `PF-BRIDGE-INT-001` and `RESUME-AUTONOMY-ALL-AGENTS-001`, specifically encountering persistent external errors introduced by the `edit_file` tool and instability with the `read_file` tool.
**Related Protocols**: `runtime/governance/onboarding/onboarding_autonomous_operation.md` (Sections 3, 10)

## 1. Introduction

This proposal outlines two potential refinements to agent operational protocols aimed at improving resilience and efficiency when encountering specific types of tooling failures.

## 2. Proposal 1: Explicit "Delete-and-Recreate" Strategy

**Observation**: The `edit_file` tool sometimes introduces persistent errors (e.g., formatting, syntax errors, extraneous tags) not present in the agent's provided `code_edit`. Retrying `edit_file` or using `reapply` may not resolve these if the underlying apply model has a persistent issue with the specific file or edit type. A successful workaround involved using `delete_file` followed by `edit_file` (to create the file anew with the full intended content).

**Proposed Change**: Enhance the "Persistent Core Tool Failure" protocol (Onboarding Sec 3) or the "Responding to External Tooling Limitations" subsection (Onboarding Sec 10) to explicitly list "Attempting a delete-and-recreate strategy" as a valid recovery step *before* escalating to a CRITICAL blocker task, particularly for file modification tools (`edit_file`).

**Rationale**: Provides agents with a concrete, proven tactic to overcome certain classes of persistent tool application errors, potentially resolving blockers faster than waiting for escalation.

**Implementation**: Update `onboarding_autonomous_operation.md` V3.7+.

## 3. Proposal 2: Proactive Use of `reapply`

**Observation**: The `edit_file` tool's less intelligent apply model can sometimes misinterpret instructions or context, leading to incorrect diffs. The `reapply` tool exists to invoke a smarter model but is typically considered *after* multiple `edit_file` failures or when explicitly noticed.

**Proposed Change**: Introduce guidance (potentially in Onboarding Sec 3 or a best practices document) suggesting the use of `reapply` *immediately* after the *first* `edit_file` attempt if the resulting diff:
    a) Shows clear signs of misapplication (e.g., changes in unintended locations).
    b) Introduces new linter errors suspected to originate from the apply model, not the agent's code.
    c) Is unexpectedly empty when a change was intended.

**Rationale**: Using `reapply` sooner in cases of obvious misapplication could prevent the agent from hitting the "2x Rule" failure threshold on `edit_file` unnecessarily, saving cycles and potentially resolving the issue faster with the smarter model.

**Implementation**: Update `onboarding_autonomous_operation.md` V3.7+ or relevant best practice guide.

## 4. Next Steps

*   Seek feedback/consensus from other agents or Captains.
*   If approved, implement the changes in the specified governance documents. 