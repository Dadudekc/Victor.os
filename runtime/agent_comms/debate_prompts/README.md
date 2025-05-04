# Debate Prompts Directory

This directory stores all user-triggered debate prompts as special events for audit, replay, and review.

## Purpose
- Persistently log every debate request from Discord or user prompt.
- Enable agents and moderators to reference, replay, or audit past debates.

## File Schema (debate_YYYYMMDDTHHMMSSZ.json)
```json
{
  "timestamp": "2025-05-02T21:16:00Z",
  "topic": "Does God exist?",
  "requested_by": "General Victor",
  "source": "discord|prompt|other",
  "status": "pending|in_progress|complete",
  "assigned_personas": ["Atheist", "Christian"],
  "debate_log": "runtime/agent_comms/debate_logs/debate_YYYYMMDDTHHMMSSZ.md"
}
```

## Usage
- When a debate is requested, save the prompt as a new JSON file here.
- Update status and log path as the debate progresses.
- Reference this file for audit, replay, or summary.
