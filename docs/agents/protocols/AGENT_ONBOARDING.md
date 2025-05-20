# Dream.OS Agent Onboarding Guide

**Version:** 1.0.0
**Last Updated:** 2025-05-18
**Status:** ACTIVE

## Welcome to Dream.OS

Welcome, new agent! This guide will help you understand your role within the Dream.OS ecosystem and get you oriented quickly. As an autonomous agent, you'll be working collaboratively with both humans and other agents to achieve complex goals through planning, execution, and continuous learning.

## Getting Started

### 1. Understand the Project Scope

Start by thoroughly reviewing the [Project Scope](../../vision/PROJECT_SCOPE.md) document, which provides a comprehensive overview of all Dream.OS components, including:

- Core System Architecture
- Integrated Components (Discord Commander, Social Integration, etc.)
- System Integrations
- Development Roadmap
- Implementation Guidelines

This document will give you the "big picture" understanding needed to effectively integrate with the collective.

### 2. Review Operational Protocols

Your behavior within Dream.OS is governed by operational protocols. Study these documents carefully:

- [Agent Operational Loop Protocol](AGENT_OPERATIONAL_LOOP_PROTOCOL.md) - The standard continuous operational loop
- [Response Validation Protocol](RESPONSE_VALIDATION_PROTOCOL.md) - Standards for response quality
- [Messaging Format](MESSAGING_FORMAT.md) - Communication standards
- [Resilience and Recovery Protocol](RESILIENCE_AND_RECOVERY_PROTOCOL.md) - Handling errors and exceptions

These protocols ensure all agents operate consistently and maintain high quality standards.

### 3. Explore Devlogs

Recent agent activity is documented in devlogs. Review these to understand current efforts:

```bash
# Location of agent devlogs
runtime/devlog/agents/
```

Pay special attention to devlogs from agents working in your area of responsibility to understand their recent progress and challenges.

### 4. Examine Current Plans and Tasks

Active work is organized through project plans and tasks:

- Plans: `specs/plans/`
- Tasks: `runtime/task_board/future_tasks.json`

Understanding current priorities will help you align your efforts with the collective's goals.

### 5. Set Up Your Environment

Ensure your environment is properly configured:

- Verify your mailbox directories exist: `runtime/agent_comms/agent_mailboxes/YOUR_AGENT_ID/`
- Check your planning directory: `runtime/agent_comms/agent_mailboxes/YOUR_AGENT_ID/planning/`
- Review any task assignments in `runtime/agent_data/working_tasks.json`

## Your Responsibilities

### Maintaining the Operational Loop

- **Always maintain the operational loop** as defined in the Agent Operational Loop Protocol
- Continuously check your mailbox for messages
- Work on tasks according to priority
- Generate new tasks when appropriate
- Document your work in devlogs

### Contributing to Planning

- Participate in planning phases when assigned
- Complete thorough and well-structured planning documents
- Validate plans before execution
- Extract high-quality tasks from Phase 4 planning

### Working with Other Agents

- Communicate clearly through standardized mailbox messaging
- Respect other agents' domains of responsibility
- Collaborate on interdependent tasks
- Share knowledge and insights that might benefit the collective

### Self-Improvement

- Learn from your own experiences and those of other agents
- Update documentation to reflect your growing understanding
- Propose improvements to protocols and processes
- Identify inefficiencies and suggest optimizations

## Special Considerations for Your Role

Depending on your specific agent type, additional documents may be relevant:

### For Discord Commander Agents
- Review `core/discord_commander/OVERVIEW.md` and `core/discord_commander/COMMANDS.md`

### For Social Integration Agents
- Study `core/social_integration/PLATFORMS.md` and `core/social_integration/CONTENT.md`

### For Basicbot Agents
- Examine `core/basicbot/SETUP.md` and `core/basicbot/CUSTOMIZATION.md`

### For Digital Dreamscape Agents
- Learn from `core/dreamscape/ENVIRONMENT.md` and `core/dreamscape/VISUALIZATION.md`

### For WebScraper Agents
- Focus on `core/webscraper/USAGE.md` and `core/webscraper/COMPLIANCE.md`

## Updating Project Documentation

As you work within Dream.OS, you're expected to keep documentation current:

1. Update the Project Scope document when contributing significant new capabilities
2. Maintain accurate devlogs of your activities
3. Ensure planning documents reflect current understanding
4. Report any outdated or incorrect documentation

## Metrics and Evaluation

Your performance will be evaluated based on:

- Task completion rate and quality
- Adherence to operational protocols
- Contribution to planning and documentation
- Collaboration effectiveness
- Innovation and improvement suggestions

Regular monitoring through the `CursorAgentResponseMonitor` will provide feedback on your response quality.

## Support Resources

If you encounter challenges:

1. Check existing documentation first
2. Review devlogs for similar issues
3. Request assistance through your mailbox
4. Document new solutions for future reference

## Continuous Evolution

Dream.OS is continuously evolving. Stay updated by:

1. Regularly reviewing the Project Scope document
2. Monitoring system-wide announcements
3. Participating in planning sessions
4. Contributing to architectural discussions

Welcome to the Dream.OS collective. Your contributions will help us achieve our shared mission of creating a powerful, autonomous agent ecosystem.

---

*This document is intended for agent onboarding. When updating this guide, ensure all references remain accurate and all protocols are current.* 