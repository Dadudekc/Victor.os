> This document is a developer-facing reference guide for Dream.OS agents and engineers. It contains critical "USE EXISTING X" principles distilled from earlier swarm documentation, now consolidated for clarity and future-proofing.

# Existing Architecture Utilization Guide

**Version:** 1.0 (Derived from Continuous Autonomy Protocol v1.3)
**Effective Date:** {{CURRENT_DATE}}

## Introduction

To ensure consistency, maintainability, and prevent unnecessary duplication of effort, all agents and developers working within the Dream.OS ecosystem MUST prioritize the use of existing architectural components, tools, and utilities before creating new ones. This guide consolidates key "Use Existing X" directives.

## 1. Architecture Utilization (Original Section 3)

### 1.1 Existing Components
- Use existing mailbox handlers
- Use existing task managers
- Use existing task allocators
- Use existing blocker resolvers
- Use existing fallback handlers
- Use existing loop managers
- Use existing error handlers
- Use existing state managers
- Use existing loggers
- Use existing validators

### 1.2 Code Organization
- Follow module structure
- Maintain file hierarchy
- Use consistent naming
- Follow style guides
- Document dependencies
- Track architecture
- Validate organization
- Review structure
- Check conventions
- Monitor patterns

### 1.3 Dependency Management
- Use existing dependencies
- Minimize new imports
- Track requirements
- Document versions
- Check compatibility
- Validate usage
- Review impacts
- Monitor changes
- Test integration
- Verify stability

### 1.4 Architecture Patterns
- Follow existing patterns
- Use standard approaches
- Maintain consistency
- Document decisions
- Track usage
- Validate design
- Review structure
- Check conventions
- Monitor patterns
- Test integration

## 2. Drift Control and Error Handling Principles (Original Section 4)

While detailed procedures are in `CONTINUOUS_OPERATION_AND_RESILIENCE_PROTOCOL.md`, agents must prioritize using:

*   Existing timeout handlers to prevent getting stuck.
*   Existing error handlers for failed operations.
*   Existing state managers for operation tracking.
*   Existing loggers for error recording.
*   Existing validators for state verification.

### 2.1 Error Recovery Components (Original Section 4.1)
When implementing error recovery logic, leverage:
- Existing error detectors
- Existing error handlers
- Existing state managers
- Existing loggers
- Existing validators
- Existing recovery handlers
- Existing cycle managers
- Existing health monitors
- Existing performance trackers
- Existing integration testers

## 3. Self-Correction and Governance Adherence Principles (Original Section 5)

When an agent needs to self-correct or ensure governance adherence (detailed procedures in `CONTINUOUS_OPERATION_AND_RESILIENCE_PROTOCOL.md`), it should utilize:

*   Existing drift detectors
*   Existing state analyzers
*   Existing protocol validators
*   Existing document updaters
*   Existing cycle managers
*   Existing health monitors
*   Existing performance trackers
*   Existing integration testers
*   Existing loggers
*   Existing validators

### 3.1 Self-Correction Components (Original Section 5.1)
For self-correction mechanisms, prioritize:
- Existing drift detectors
- Existing state analyzers
- Existing protocol validators
- Existing document updaters
- Existing cycle managers
- Existing health monitors
- Existing performance trackers
- Existing integration testers
- Existing loggers
- Existing validators

## 4. Task Validation Protocol Principles (Original Section 6)

For all aspects of task validation (detailed procedures may be part of `AGENT_OPERATIONAL_LOOP_PROTOCOL.md` or role-specific guides), prioritize using:

### 4.1 Automated Validation Components (Original Section 6.1)
- Existing validators
- Existing monitors
- Existing verifiers
- Existing loggers
- Existing reporters
- Existing checkers
- Existing testers
- Existing metrics
- Existing alerters
- Existing recoverers

### 4.2 Validation Rule Components (Original Section 6.2)
- Existing rule validators
- Existing state checkers
- Existing flow verifiers
- Existing cycle managers
- Existing health monitors
- Existing performance trackers
- Existing integration testers
- Existing loggers
- Existing reporters
- Existing validators

### 4.3 Validation Process Components (Original Section 6.3)
- Existing process managers
- Existing state monitors
- Existing flow checkers
- Existing cycle managers
- Existing health monitors
- Existing performance trackers
- Existing integration testers
- Existing loggers
- Existing reporters
- Existing validators

### 4.4 Validation Requirement Components (Original Section 6.4)
- Existing requirement validators
- Existing state checkers
- Existing flow verifiers
- Existing cycle managers
- Existing health monitors
- Existing performance trackers
- Existing integration testers
- Existing loggers
- Existing reporters
- Existing validators

## 5. Reporting Principles (Original Section 7)

Status reporting should occur only as defined in the `AGENT_OPERATIONAL_LOOP_PROTOCOL.md` and `system_prompt.md`. For implementing reporting mechanisms, use:

### 5.1 Reporting Rule Components (Original Section 7.1)
- Existing reporters
- Existing state monitors
- Existing flow checkers
- Existing cycle managers
- Existing health monitors
- Existing performance trackers
- Existing integration testers
- Existing loggers
- Existing validators
- Existing metrics

## 6. Protocol Review and Update Principles (Original Section 8)

Protocols are living documents. For processes related to their review and update (especially automated updates by agents as per `CONTINUOUS_OPERATION_AND_RESILIENCE_PROTOCOL.md`), utilize:

### 6.1 Update Protocol Components (Original Section 8.1)
- Existing document updaters
- Existing state analyzers
- Existing protocol validators
- Existing cycle managers
- Existing health monitors
- Existing performance trackers
- Existing integration testers
- Existing loggers
- Existing validators
- Existing metrics 