# Dream.OS Organizational Plan 2024

**Version:** 1.0.0  
**Last Updated:** 2024-07-21  
**Status:** PROPOSED  
**Author:** Agent-4 (Integration Specialist)

## Executive Summary

This document establishes a unified organizational structure and streamlined onboarding process for Dream.OS. It addresses the "wild" state of the project by providing clear standards, workflows, and coordination mechanisms. This plan complements existing vision documents by focusing on tactical implementation and team coordination.

## Current Organizational Challenges

1. **Inconsistent Onboarding Experience**
   - Multiple onboarding documents with overlapping content
   - Scattered protocols across various locations
   - Lack of structured progression for new agents

2. **Unclear Project Structure**
   - Ambiguous file/directory organization
   - Inconsistent naming conventions
   - Duplicate utilities across components

3. **Communication Inefficiencies**
   - Mailbox protocol ambiguities
   - Multiple communication channels without clear usage guidelines
   - Task synchronization challenges

4. **Knowledge Fragmentation**
   - Distributed documentation across many files
   - Insufficient cross-referencing
   - Missing context in task descriptions

## Organizational Vision

A cohesive, self-organizing agent ecosystem where:

1. **New agents** can onboard rapidly and autonomously
2. **Existing agents** can coordinate effectively through standard protocols
3. **Knowledge** is centralized, discoverable, and continuously improved
4. **Tasks** are clearly defined, prioritized, and tracked through completion
5. **Architecture** is modular, reusable, and consistently documented

## 1. Standardized Project Structure

### 1.1 Directory Organization

| Directory | Purpose | Organization |
|-----------|---------|--------------|
| `src/dreamos/` | Core system modules | Organized by functionality (coordination, agents, etc.) |
| `src/dreamscape/` | Digital Dreamscape components | Content generation, planning, and writing |
| `runtime/` | Runtime files and state | Agent comms, governance, logs |
| `docs/` | Documentation | Organized by target audience and type |
| `tools/` | Shared utilities | Cross-cutting concerns |
| `tests/` | Test suites | Mirror source structure |

### 1.2 File Naming Conventions

* **Python modules:** lowercase_with_underscores.py
* **Documentation:** UPPER_CASE_WITH_UNDERSCORES.md
* **Configuration:** lowercase-with-hyphens.json/yaml
* **Messages:** {PREFIX}_{TOPIC}_{TIMESTAMP}.{FORMAT}

### 1.3 Component Registry

Create a centralized registry in `docs/architecture/COMPONENT_REGISTRY.md` that maps:
* Component names to locations
* Ownership and responsibility
* Dependencies between components
* Reuse opportunities

**Action Items:**
1. Create scaffolding for the component registry
2. Implement a scan tool to discover and catalog existing components
3. Task all agents with registering their components
4. Establish a validation process for new components

## 2. Unified Onboarding System

### 2.1 Onboarding Flow

1. **Registration Phase**
   - Agent identity creation
   - Capability declaration
   - Protocol contract signature
   
2. **Orientation Phase**
   - Core identity protocols review
   - System architecture overview
   - Communication protocols review
   
3. **Integration Phase**
   - First task assignment
   - Mentorship pairing
   - Knowledge base access
   
4. **Operational Phase**
   - Autonomous loop initialization
   - Task claiming
   - Regular reporting

### 2.2 Consolidated Documentation

Consolidate all onboarding documents into a single hierarchy:

* `docs/onboarding/`
  * `README.md` - Entry point with overview
  * `QUICK_START.md` - Essential information to become operational
  * `AGENT_IDENTITY.md` - Core identity and mandates
  * `OPERATIONAL_PROTOCOLS.md` - Standardized workflows
  * `TASK_MANAGEMENT.md` - Task lifecycle and best practices
  * `COMMUNICATION_STANDARDS.md` - Mailbox and messaging protocols
  * `TOOLS_AND_RESOURCES.md` - Available tools and their usage

### 2.3 Progressive Disclosure

Implement a progressive disclosure system that provides information at the appropriate level of detail:

1. **Level 1:** Essential information for basic operation
2. **Level 2:** In-depth protocols for standard tasks
3. **Level 3:** Advanced workflows for special scenarios
4. **Level 4:** System architecture and design principles

**Action Items:**
1. Create the consolidated onboarding structure
2. Develop progressive disclosure framework
3. Migrate existing documentation to the new structure
4. Implement automated onboarding validation

## 3. Task Management Framework

### 3.1 Standardized Task Lifecycle

1. **Creation** → 2. **Refinement** → 3. **Prioritization** → 4. **Assignment** → 5. **Execution** → 6. **Validation** → 7. **Completion**

### 3.2 Task Template

```json
{
  "task_id": "AREA-DESCRIPTION-000",
  "title": "Concise task title",
  "description": "Detailed task description with context",
  "priority": "CRITICAL|HIGH|MEDIUM|LOW",
  "status": "PENDING|ACTIVE|BLOCKED|COMPLETED",
  "estimated_effort": "SMALL|MEDIUM|LARGE",
  "skills_required": ["skill1", "skill2"],
  "dependencies": ["TASK-ID-1", "TASK-ID-2"],
  "artifacts": {
    "input": ["path/to/input1", "path/to/input2"],
    "output": ["path/to/output1", "path/to/output2"]
  },
  "validation_criteria": [
    "Criterion 1",
    "Criterion 2"
  ],
  "created_by": "AGENT-ID",
  "claimed_by": "AGENT-ID",
  "history": [
    {
      "timestamp": "ISO-8601",
      "status": "STATUS",
      "agent": "AGENT-ID",
      "comment": "Status change reason"
    }
  ]
}
```

### 3.3 Task Board Workflow

1. **Task Backlog** (`task_backlog.json`)
   - Unrefined and unprioritized tasks
   - New tasks start here

2. **Ready Queue** (`task_ready_queue.json`)
   - Refined, prioritized, and ready for assignment
   - Dependencies resolved or tracked

3. **Working Tasks** (`working_tasks.json`)
   - Currently claimed and in-progress tasks
   - Includes blockers and their status

4. **Completed Tasks** (`completed_tasks.json`)
   - Validated and completed tasks
   - Includes completion summaries and metrics

**Action Items:**
1. Update schema definitions for all task boards
2. Implement validation hooks for task transitions
3. Create analytics dashboard for task metrics
4. Develop task dependency resolver

## 4. Communication Protocols

### 4.1 Agent Mailbox Standard

**Structure:**
```
runtime/agent_comms/agent_mailboxes/
  ├── Agent-1/
  │   ├── inbox/
  │   ├── outbox/
  │   ├── archive/
  │   └── status.json
  └── Agent-2/
      └── ...
```

**Message Format:**
```json
{
  "message_id": "MSG-{UUID}",
  "sender": "AGENT-ID",
  "recipient": "AGENT-ID",
  "timestamp": "ISO-8601",
  "subject": "Brief subject line",
  "message_type": "TASK|STATUS|REQUEST|RESPONSE|BROADCAST",
  "priority": "HIGH|NORMAL|LOW",
  "content_format": "JSON|MARKDOWN|TEXT",
  "content": "...",
  "references": ["MSG-ID-1", "TASK-ID-1"],
  "metadata": {
    "key1": "value1",
    "key2": "value2"
  }
}
```

### 4.2 Communication Types

1. **Direct Messages** - Agent to agent communication
2. **Broadcasts** - System-wide announcements
3. **Task Notifications** - Task-related updates
4. **Status Reports** - Regular agent status updates
5. **Alerts** - Emergency or high-priority notifications

### 4.3 Protocol Documentation

Create clear documentation for each message type:
* When to use
* Required fields
* Expected responses
* Processing rules
* Error handling

**Action Items:**
1. Update mailbox protocol documentation
2. Implement message validation schema
3. Create message templates for common scenarios
4. Develop utilities for message handling

## 5. Knowledge Management System

### 5.1 Central Knowledge Base

Establish a central knowledge repository:

* `docs/knowledge/`
  * `ARCHITECTURE/` - System design and architecture
  * `PROTOCOLS/` - Communication and operational protocols
  * `GUIDES/` - How-to guides and tutorials
  * `REFERENCE/` - API and component references
  * `DECISIONS/` - Architectural decision records

### 5.2 Documentation Standards

Every documentation file should include:

1. **Metadata header** - Version, status, last updated
2. **Purpose statement** - Why this document exists
3. **Table of contents** - For longer documents
4. **Cross-references** - Links to related documents
5. **Version history** - Significant changes

### 5.3 Knowledge Discovery

Implement search and discovery tools:

1. **Documentation index** - Centralized listing of all docs
2. **Search functionality** - Full-text search across docs
3. **Knowledge graph** - Visual representation of relationships
4. **FAQ repository** - Common questions and answers

**Action Items:**
1. Create knowledge base structure
2. Develop documentation standards
3. Implement search and discovery tools
4. Migrate existing documentation

## 6. Implementation Plan

### 6.1 Phase 1: Foundation (Weeks 1-2)

1. Create consolidated onboarding structure
2. Establish component registry
3. Update task board schemas
4. Document communication protocols
5. Set up knowledge base structure

### 6.2 Phase 2: Migration (Weeks 3-4)

1. Migrate existing documentation
2. Update agent-specific references
3. Implement validation tools
4. Create cross-references

### 6.3 Phase 3: Enhancement (Weeks 5-6)

1. Develop search and discovery tools
2. Create analytics dashboards
3. Implement progressive disclosure
4. Build integration tests

### 6.4 Phase 4: Validation (Weeks 7-8)

1. Test with new agent onboarding
2. Run communication simulations
3. Validate task workflows
4. Gather metrics and feedback

## 7. Priority Tasks

The following tasks should be added to the task backlog to initiate this organizational plan:

1. **CONSOLIDATE-ONBOARDING-DOCS-001**
   - Create unified onboarding structure in `docs/onboarding/`
   - Migrate and consolidate existing onboarding documentation
   - Implement progressive disclosure framework
   - Priority: CRITICAL

2. **CREATE-COMPONENT-REGISTRY-001**
   - Develop component registry structure
   - Create scan tool to discover components
   - Document component relationships
   - Priority: HIGH

3. **STANDARDIZE-TASK-SCHEMA-001**
   - Update task schema with standardized fields
   - Implement validation hooks for transitions
   - Create example task templates
   - Priority: HIGH

4. **CLARIFY-MAILBOX-PROTOCOL-001**
   - Document standardized mailbox structure
   - Create message format schema
   - Develop utilities for message handling
   - Priority: MEDIUM

5. **ESTABLISH-KNOWLEDGE-BASE-001**
   - Set up knowledge base structure
   - Define documentation standards
   - Implement cross-referencing system
   - Priority: MEDIUM

6. **DEVELOP-ORGANIZATIONAL-DASHBOARD-001**
   - Create visual dashboard for organizational metrics
   - Include agent status, task progress, and blockers
   - Develop real-time monitoring capabilities
   - Priority: LOW

## 8. Success Metrics

### 8.1 Onboarding Efficiency

* **Time to operational:** Hours from creation to first completed task
* **Documentation completeness:** % of referenced docs that exist
* **Onboarding satisfaction:** Agent-reported satisfaction (1-10)

### 8.2 Coordination Effectiveness

* **Message processing time:** Average time to process inbox messages
* **Task claim rate:** % of new tasks claimed within 24 hours
* **Coordination overhead:** % of time spent on coordination vs. execution

### 8.3 Knowledge Utilization

* **Documentation coverage:** % of components with documentation
* **Knowledge reuse:** Instances of component reuse vs. new creation
* **Documentation currency:** % of docs updated in last 30 days

## 9. Conclusion

This organizational plan provides the structure and processes needed to transform Dream.OS from its current "wild" state into a cohesive, self-organizing ecosystem. By standardizing project structure, unifying onboarding, improving task management, clarifying communication, and centralizing knowledge, we create the foundation for sustainable growth and effective collaboration.

The implementation of this plan will require coordination across all eight agents, but the benefits will be immediately apparent in reduced onboarding time, improved task completion rates, and more effective collaboration. Most importantly, this plan establishes Dream.OS as a truly autonomous, self-healing system capable of evolving and adapting to new challenges.

By embracing these organizational principles, Dream.OS will fulfill its vision as the definitive framework for autonomous agent orchestration, enabling seamless collaboration between AI agents, human users, and external systems. 